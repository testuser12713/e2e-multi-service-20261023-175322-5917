import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiBaseUrl, createJob, listJobs, type Job } from "./api.ts";

const job: Job = {
  id: 1,
  text: "Ein kurzer Text",
  analysis: "word_count",
  status: "pending",
  result: null,
  error: null,
  created_at: "2026-01-01T12:00:00Z",
  updated_at: "2026-01-01T12:00:00Z",
};

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("apiBaseUrl", () => {
  it("falls back to the page origin when VITE_API_BASE_URL is empty", () => {
    vi.stubEnv("VITE_API_BASE_URL", "");
    expect(apiBaseUrl()).toBe("");
  });

  it("drops a trailing slash", () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://127.0.0.1:8000/");
    expect(apiBaseUrl()).toBe("http://127.0.0.1:8000");
  });
});

describe("listJobs", () => {
  it("requests GET /api/jobs on the configured base URL", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://127.0.0.1:8000");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([job], 200));
    vi.stubGlobal("fetch", fetchMock);

    await expect(listJobs()).resolves.toEqual([job]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe("http://127.0.0.1:8000/api/jobs");
  });

  it("throws an ApiError when the API answers outside 2xx", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("upstream down", { status: 502 })));

    await expect(listJobs()).rejects.toMatchObject({ name: "ApiError", status: 502 });
  });
});

describe("createJob", () => {
  it("posts text and analysis as JSON and returns the created job", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(job, 201));
    vi.stubGlobal("fetch", fetchMock);

    await expect(createJob("Ein kurzer Text", "word_count")).resolves.toEqual(job);

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/jobs");
    expect(init.method).toBe("POST");
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
    expect(JSON.parse(String(init.body))).toEqual({ text: "Ein kurzer Text", analysis: "word_count" });
  });

  it("throws with the message of the standard error body on 422", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "");
    const body = { error: { code: "validation_error", message: "Text darf nicht leer sein." } };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(body, 422)));

    const failure = await createJob(" ", "word_count").catch((err: unknown) => err);

    expect(failure).toBeInstanceOf(ApiError);
    expect(failure).toMatchObject({
      status: 422,
      code: "validation_error",
      message: "Text darf nicht leer sein.",
    });
  });
});
