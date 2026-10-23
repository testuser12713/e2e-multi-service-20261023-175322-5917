"""FastAPI application: CORS, error bodies, schema bootstrap and routers.

Every failure answers with the same body, ``{"error": {"code": str, "message": str}}``.
That body never carries the submitted job text, a stack trace or a filesystem path,
and log lines carry only method, path, status and the error class.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app import db
from app.routes import jobs

logger = logging.getLogger("app")

ERROR_CODES: dict[int, str] = {
    400: "bad_request",
    404: "not_found",
    405: "method_not_allowed",
    413: "payload_too_large",
    422: "validation_error",
    500: "internal_error",
    501: "not_implemented",
    503: "service_unavailable",
}

INTERNAL_ERROR_MESSAGE = "Internal server error"
MAX_MESSAGE_LENGTH = 500


def parse_cors_origins(raw: str | None) -> list[str]:
    """Split ``CORS_ORIGINS`` (comma-separated) into exact origins.

    Blank entries and the wildcard ``*`` are dropped: only origins that are named
    explicitly are ever allowed. Unset or empty means no cross-origin access at all.
    """
    origins: list[str] = []
    for part in (raw or "").split(","):
        origin = part.strip().rstrip("/")
        if not origin or origin == "*" or origin in origins:
            continue
        origins.append(origin)
    return origins


def error_body(code: str, message: str) -> dict[str, dict[str, str]]:
    """The one error body every failure of this API answers with."""
    return {"error": {"code": code, "message": message[:MAX_MESSAGE_LENGTH]}}


def error_response(
    status_code: int,
    code: str | None = None,
    message: str | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    try:
        phrase = HTTPStatus(status_code).phrase
    except ValueError:
        phrase = "Error"
    return JSONResponse(
        status_code=status_code,
        content=error_body(code or ERROR_CODES.get(status_code, "http_error"), message or phrase),
        headers=headers,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """HTTPException (ours and the router's own 404/405) -> error body.

    ``detail`` may be a plain message or a ``{"code": ..., "message": ...}`` mapping.
    """
    detail: Any = exc.detail
    code: str | None = None
    message: str | None = None
    if isinstance(detail, dict):
        code = str(detail["code"]) if detail.get("code") else None
        message = str(detail["message"]) if detail.get("message") else None
    elif isinstance(detail, str) and detail:
        message = detail
    return error_response(exc.status_code, code, message, headers=exc.headers)


def _validation_message(exc: RequestValidationError) -> str:
    """Field location plus pydantic's message per error — never the rejected input."""
    parts: list[str] = []
    for err in exc.errors():
        loc = [str(p) for p in err.get("loc", ()) if p != "body"]
        msg = str(err.get("msg", "invalid value"))
        parts.append(f"{'.'.join(loc)}: {msg}" if loc else msg)
    return "; ".join(parts) or "Request validation failed"


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return error_response(422, "validation_error", _validation_message(exc))


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last resort for an error raised outside the routes (answered outside CORS)."""
    logger.error(
        "unhandled error on %s %s: %s", request.method, request.url.path, type(exc).__name__
    )
    return error_response(500, "internal_error", INTERNAL_ERROR_MESSAGE)


class UnhandledErrorMiddleware:
    """Turn an unhandled exception into a 500 error body INSIDE the CORS layer.

    Starlette answers an uncaught exception from its outermost middleware, outside
    CORSMiddleware, so the browser would get a 500 without Access-Control-Allow-Origin
    and report a CORS failure instead of the server error. This middleware sits inside
    CORS and produces the response there.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            logger.error(
                "unhandled error on %s %s: %s",
                scope.get("method", "?"),
                scope.get("path", "?"),
                type(exc).__name__,
            )
            if response_started:
                raise
            response = error_response(500, "internal_error", INTERNAL_ERROR_MESSAGE)
            await response(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Touch the configuration once at startup: an unusable JOBS_DB_PATH stops the
    # process here, with the reason, instead of on the first request.
    db.init_schema()
    logger.info("jobs schema ready")
    yield


def create_app() -> FastAPI:
    """Build the API. Configuration is read from the environment at call time."""
    app = FastAPI(title="Job API", version="1.0.0", lifespan=lifespan)

    # Order matters: the middleware added last is the outermost one, so CORS wraps
    # the error middleware and every response — including a 500 — gets its headers.
    app.add_middleware(UnhandledErrorMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=parse_cors_origins(os.environ.get("CORS_ORIGINS")),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        """Liveness plus a round trip to the same database the job routes use."""
        try:
            conn = db.get_connection()
            try:
                conn.execute("SELECT 1").fetchone()
            finally:
                conn.close()
        except (OSError, sqlite3.Error) as exc:
            logger.error("health check failed: %s", type(exc).__name__)
            raise HTTPException(
                status_code=503,
                detail={"code": "service_unavailable", "message": "Database unavailable"},
            ) from None
        return {"status": "ok"}

    app.include_router(jobs.router)
    return app


app = create_app()
