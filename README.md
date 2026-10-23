# Job-Verarbeitung – API, Worker und Dashboard

Ein kleines Job-Verarbeitungssystem aus drei unabhängig startbaren Diensten: Eine
FastAPI-**API** nimmt Textanalyse-Jobs entgegen und speichert sie in einer SQLite-Datei,
ein eigenständiger Python-**Worker** holt wartende Jobs aus derselben Datenbank, führt die
Analyse aus (Wörter zählen, häufigste Wörter, Lesezeit) und schreibt Ergebnis und Status
zurück, und ein **Web-Dashboard** (Vite/React/TypeScript) legt Jobs an und zeigt die
Job-Liste mit Status und Ergebnis, die sich alle 3 Sekunden selbst aktualisiert.

## Tech-Stack

| Dienst   | Verzeichnis | Technik                                                        |
|----------|-------------|----------------------------------------------------------------|
| api      | `backend/`  | Python 3.12+, FastAPI, uvicorn, pydantic, sqlite3 (ohne ORM)   |
| worker   | `worker/`   | Python 3.12+, sqlite3, eigener Prozess                         |
| web      | `frontend/` | Vite, React, TypeScript, Vitest, React Testing Library         |
| Datenbank | –          | eine SQLite-Datei, gemeinsam genutzt von API und Worker (`JOBS_DB_PATH`) |
| Tests    | –           | pytest (API, Worker), Vitest (Frontend)                        |

## Projektstruktur

```
backend/            API-Dienst (FastAPI)
  app/main.py       App, CORS, Fehlerbehandlung, Router
  app/db.py         SQLite-Verbindung und Schema
  app/schemas.py    Request-/Response-Modelle
  app/routes/jobs.py  Job-Endpunkte
  tests/            pytest-Tests der API
worker/             Worker-Dienst (python -m worker)
  analyses.py       die drei Textanalysen
  db.py             SQLite-Verbindung, Schema, Job-Claiming
  runner.py         Verarbeitungsschleife
  tests/            pytest-Tests des Workers
frontend/           Web-Dashboard (Vite/React/TypeScript)
  src/api.ts        API-Client und Typen
  src/App.tsx       Seitenaufbau und Polling
  src/components/   Formular und Job-Liste
dev.py              startet alle drei Dienste mit einem Befehl
RUN.json            maschinenlesbarer Startvertrag aller Dienste
DESIGN.md           verbindliches Design (Farben, Abstände, Komponenten)
```

## Voraussetzungen

- Python 3.12 oder neuer (mit `pip`)
- Node.js 22 oder neuer (mit `npm`)

## Installation

Alle Befehle gehen vom Wurzelverzeichnis des Repositorys aus.

```bash
# API
cd backend
python -m pip install -r requirements.txt
cd ..

# Worker
python -m pip install -r worker/requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

Eine virtuelle Umgebung (`python -m venv .venv`) wird empfohlen, ist aber nicht nötig.

## Konfiguration (Umgebungsvariablen)

| Variable                       | Dienst      | Standard        | Bedeutung |
|--------------------------------|-------------|-----------------|-----------|
| `JOBS_DB_PATH`                 | api, worker | `data/jobs.db`  | Pfad der gemeinsamen SQLite-Datei. Ein relativer Pfad gilt ab dem Arbeitsverzeichnis des jeweiligen Prozesses; das übergeordnete Verzeichnis wird automatisch angelegt. API und Worker müssen auf **dieselbe** Datei zeigen. |
| `CORS_ORIGINS`                 | api         | leer            | Kommagetrennte Liste der Origins, die die API aus dem Browser aufrufen dürfen, z. B. `http://localhost:5173`. Ein Wildcard `*` wird ignoriert; ohne Wert ist kein Cross-Origin-Zugriff erlaubt. |
| `WORKER_POLL_INTERVAL_SECONDS` | worker      | `2`             | Wartezeit in Sekunden zwischen zwei Abfragen, wenn kein Job wartet. |
| `VITE_API_BASE_URL`            | web         | –               | Basis-URL der API ohne abschließenden Schrägstrich, z. B. `http://localhost:8000`. Wird beim Start bzw. Build des Frontends eingelesen. |

Es gibt keine Geheimnisse (Schlüssel, Passwörter) – alle Werte oben sind unkritisch.

Die Datenbank legt beim Start jeder Dienst selbst an (`CREATE TABLE IF NOT EXISTS`), es ist
also egal, ob zuerst die API oder zuerst der Worker gestartet wird. SQLite läuft im
WAL-Modus mit Busy-Timeout, damit API und Worker gleichzeitig ohne
„database is locked“ zugreifen können.

## Starten in der Entwicklung

### Ein Befehl für alles

Nach der Installation startet ein Befehl aus dem Wurzelverzeichnis alle drei Dienste
(api, worker, web) gemeinsam:

```bash
python dev.py
```

Danach `http://localhost:5173` im Browser öffnen; die API läuft auf Port 8000. Beide
nutzen dieselbe Datenbank `data/jobs.db` im Wurzelverzeichnis, CORS und API-Adresse sind
bereits verdrahtet. Strg+C beendet alle drei Dienste. Andere Ports lassen sich über
`API_PORT` und `WEB_PORT` setzen, die Datenbank über `JOBS_DB_PATH`.

### Jeder Dienst einzeln

In den Beispielen liegt die Datenbank unter `data/jobs.db` im Wurzelverzeichnis; die API
läuft auf Port 8000, das Frontend auf dem Vite-Standardport 5173.

**API** (aus `backend/`):

```bash
cd backend
JOBS_DB_PATH=../data/jobs.db CORS_ORIGINS=http://localhost:5173 \
  python -m uvicorn app.main:app --port 8000
```

Danach antwortet `http://localhost:8000/health` mit `{"status": "ok"}`; die interaktive
API-Dokumentation liegt unter `http://localhost:8000/docs`.

**Worker** (aus dem Wurzelverzeichnis, damit `python -m worker` das Paket findet):

```bash
JOBS_DB_PATH=data/jobs.db python -m worker          # läuft dauerhaft, Strg+C beendet
JOBS_DB_PATH=data/jobs.db python -m worker --once   # arbeitet alle wartenden Jobs ab und endet mit Code 0
```

**Frontend** (aus `frontend/`):

```bash
cd frontend
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

Dann `http://localhost:5173` im Browser öffnen. Die Seite nicht als `file://` öffnen –
sie braucht den Vite-Server (oder einen anderen HTTP-Server für den Build, siehe unten).

Unter Windows (PowerShell) werden Variablen vorher gesetzt, z. B.
`$env:JOBS_DB_PATH="../data/jobs.db"; $env:CORS_ORIGINS="http://localhost:5173"`.

### Alle drei zusammen

Von Hand: die drei Befehle oben in drei Terminals starten – zuerst API und Worker, dann das
Frontend. Wichtig ist nur, dass `CORS_ORIGINS` der API genau die Adresse des Frontends
enthält und `VITE_API_BASE_URL` des Frontends genau die Adresse der API.

Automatisch: `RUN.json` im Wurzelverzeichnis beschreibt jeden Dienst maschinenlesbar –
Verzeichnis, Installation, Startbefehl, Port, Health-Check, Umgebung und Testbefehl. Ein
Runner, der diesen Startvertrag ausführt, installiert und startet alle drei Dienste
gemeinsam. Die Verdrahtung läuft dabei über Dienst-Referenzen statt fester Ports:
`CORS_ORIGINS` der API ist `${service:web.origin}` (die tatsächliche Adresse des
Frontends), `VITE_API_BASE_URL` des Frontends ist `${service:api.origin}` (die tatsächliche
Adresse der API), und `${PORT}` ist der jeweils vergebene Port. Die API liest
`JOBS_DB_PATH=../data/jobs.db` aus `backend/`, also dieselbe Datei `data/jobs.db` im
Wurzelverzeichnis, die auch der Worker nutzt.

## Build für die Produktion

Nur das Frontend hat einen Build-Schritt:

```bash
cd frontend
VITE_API_BASE_URL=https://api.example.org npm run build
```

Das Ergebnis liegt in `frontend/dist/` und kann von jedem statischen Webserver
ausgeliefert werden, lokal z. B. mit `npm run preview` oder
`python -m http.server 8080 --directory dist`. Die API wird in der Produktion wie oben mit
uvicorn gestartet (ohne `--reload`), der Worker mit `python -m worker`; `CORS_ORIGINS`
enthält dann die öffentliche Adresse des Frontends.

## Tests

```bash
# API
cd backend && PYTHONPATH=. python -m pytest

# Worker
cd worker && PYTHONPATH=. python -m pytest

# Frontend (Vitest)
cd frontend && npm test
```

Die Python-Tests verwenden jeweils eine eigene temporäre Datenbank und brauchen keinen
laufenden Server.

## Bedienung

### Dashboard (Frontend)

Das Dashboard „Job-Verarbeitung“ ist eine einzige Seite mit diesen Bereichen:

- **Kopfzeile** mit dem Live-Hinweis „Aktualisiert alle 3 Sekunden“; schlägt die letzte
  Abfrage fehl, zeigt er „Offline“.
- **Kennzahlen**: je eine Kachel für Wartend, In Arbeit, Fertig und Fehlgeschlagen, berechnet
  aus der aktuellen Job-Liste.
- **Formular**: Feld **Text** (bis 20.000 Zeichen, mit Zeichenzähler) und Auswahl
  **Analyse** mit „Wörter zählen“, „Häufigste Wörter“ und „Lesezeit schätzen“. Der
  Absende-Knopf legt den Job an; während des Sendens ist er deaktiviert und zeigt
  „Wird gesendet…“. Wer ohne Text absendet, sieht den Hinweis „Bitte gib einen Text ein.“,
  und es wird nichts gesendet. Nach erfolgreichem Absenden wird das Formular geleert.
- **Job-Liste** (neueste zuerst): pro Job die Nummer (`#42`), die Analyse, ein Statusabzeichen
  – „wartend“, „in Arbeit“, „fertig“ oder „fehlgeschlagen“ –, Zeitpunkt, eine Textvorschau und
  das lesbare Ergebnis (z. B. „Wörter: 42“, „ca. 1,2 Min. (240 Wörter)“ oder die fünf
  häufigsten Wörter) bzw. die Fehlermeldung. Ohne Jobs erscheint „Noch keine Jobs“.
- Die Liste aktualisiert sich alle 3 Sekunden von selbst, ohne Neuladen und ohne den gerade
  getippten Text zu verlieren – ein neuer Job wandert sichtbar von „wartend“ nach „fertig“.
- Ist die API nicht erreichbar, erscheint oben der Hinweis „Verbindung zur API
  fehlgeschlagen. Neuer Versuch in wenigen Sekunden …“; er verschwindet von selbst, sobald
  die API wieder antwortet. Die zuletzt geladenen Jobs bleiben sichtbar.

### Worker

`python -m worker` fragt die Datenbank in einer Schleife ab: Er übernimmt einen wartenden Job
atomar (Status `running`), führt die Analyse aus und speichert das Ergebnis mit Status `done`.
Wirft die Analyse einen Fehler oder ist sie unbekannt, endet der Job mit Status `failed` und
einer kurzen Fehlermeldung, und der Worker macht mit dem nächsten Job weiter. Auch mehrere
Worker gleichzeitig verarbeiten keinen Job doppelt. Mit `--once` arbeitet er alle wartenden
Jobs ab und beendet sich mit Code 0.

Status-Ablauf eines Jobs: `pending` → `running` → `done` oder `failed`.

### Analysen und Ergebnisformate

| Analyse        | Ergebnis (`result`) | Regeln |
|----------------|---------------------|--------|
| `word_count`   | `{"words": 42}` | Anzahl der Wörter |
| `top_words`    | `{"top_words": [{"word": "die", "count": 3}, …]}` | höchstens 5 Einträge, Groß-/Kleinschreibung egal, Satzzeichen ignoriert, bei Gleichstand alphabetisch |
| `reading_time` | `{"minutes": 1.2, "words": 240}` | 200 Wörter pro Minute, eine Nachkommastelle |

### REST-API

Basis-URL: z. B. `http://localhost:8000`. Keine Authentifizierung. Alle Antworten sind JSON.

**Job-Objekt**

```json
{
  "id": 1,
  "text": "Der Text, der analysiert werden soll.",
  "analysis": "word_count",
  "status": "done",
  "result": {"words": 7},
  "error": null,
  "created_at": "2026-01-01T12:00:00Z",
  "updated_at": "2026-01-01T12:00:02Z"
}
```

`status` ist `pending`, `running`, `done` oder `failed`; `result` ist bis zum Abschluss
`null`, `error` ist nur bei `failed` gesetzt. Zeitstempel sind ISO 8601 in UTC.

**Fehlerkörper** – jede Fehlerantwort (404, 413, 422, 500 …) hat diese Form und enthält nie
den Jobtext, einen Stacktrace oder Dateipfade:

```json
{"error": {"code": "not_found", "message": "…"}}
```

#### `GET /health`

Prüft, ob die API läuft und die Datenbank erreichbar ist.

- Antwort `200`: `{"status": "ok"}`

#### `POST /api/jobs`

Legt einen Job im Status `pending` an.

- Body:
  ```json
  {"text": "Ein kurzer Beispieltext.", "analysis": "top_words"}
  ```
  `text`: 1 bis 20.000 Zeichen, nicht nur Leerzeichen. `analysis`: `word_count`,
  `top_words` oder `reading_time`.
- Antwort `201`: das neue Job-Objekt, z. B.
  ```json
  {"id": 2, "text": "Ein kurzer Beispieltext.", "analysis": "top_words", "status": "pending",
   "result": null, "error": null,
   "created_at": "2026-01-01T12:05:00Z", "updated_at": "2026-01-01T12:05:00Z"}
  ```
- Antwort `422`: ungültige Eingabe (leerer Text, zu langer Text, unbekannte Analyse), z. B.
  `{"error": {"code": "validation_error", "message": "text: String should have at most 20000 characters"}}`.
  Ein deutlich zu großer Body (über 1 MB) wird mit `413` oder `422` abgelehnt. In keinem
  Fehlerfall wird etwas gespeichert.

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"text": "Ein kurzer Beispieltext.", "analysis": "word_count"}'
```

#### `GET /api/jobs`

Listet alle Jobs, neueste zuerst (`created_at` absteigend, bei Gleichstand `id` absteigend).

- Antwort `200`: Liste von Job-Objekten, z. B. `[{"id": 2, …}, {"id": 1, …}]`

#### `GET /api/jobs/{id}`

Liefert einen einzelnen Job.

- Antwort `200`: das Job-Objekt
- Antwort `404`: `{"error": {"code": "not_found", "message": "…"}}`

## Funktionen

- Jobs per Web-Formular oder REST-API anlegen, mit Eingabeprüfung (Länge, Analyseart)
- Drei Textanalysen: Wörter zählen, fünf häufigste Wörter, Lesezeit
- Separater Worker-Prozess mit atomarem Job-Claiming – kein Job wird doppelt verarbeitet,
  auch nicht mit mehreren Workern; Fehler beenden nur den betroffenen Job
- Einmal-Modus `--once` für den Worker
- Gemeinsame SQLite-Datei im WAL-Modus; Schema wird von jedem Dienst selbst angelegt
- Dashboard mit Kennzahlen, Statusabzeichen, lesbaren Ergebnissen und Fehlermeldungen
- Automatische Aktualisierung alle 3 Sekunden, ohne Formulareingaben zu verlieren
- Sichtbarer Hinweis bei nicht erreichbarer API mit automatischer Erholung
- Einheitlicher Fehlerkörper für alle API-Fehler
- Sicherheit und Datenschutz: nur parametrisierte SQL-Abfragen; CORS nur für die in
  `CORS_ORIGINS` genannten Origins (kein Wildcard); Fehlerantworten und Logzeilen enthalten
  weder Jobtext noch Stacktraces oder Pfade; das Frontend rendert alle Inhalte als reinen
  Text und lädt keine Ressourcen von Drittanbietern (Schriften sind selbst gehostet)
- Startvertrag `RUN.json`, mit dem alle drei Dienste gemeinsam gestartet werden
