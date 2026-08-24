# tkxdpm_2

Project skeleton with a Python backend, SQLite database, and a TypeScript frontend.

> Round 0 status: development environment only. No business features implemented yet.

## Tech stack

| Layer      | Choice                                              |
| ---------- | --------------------------------------------------- |
| Backend    | Python 3.11 · FastAPI · Uvicorn                     |
| Database   | SQLite (via SQLAlchemy)                             |
| Frontend   | TypeScript · Vite                                   |
| Tooling    | pip + pinned requirements · pytest · ruff · npm     |

## Layout

```
.
├── .venv/                  # Python virtualenv (not committed)
├── backend/
│   ├── app/
│   │   ├── config.py       # settings from environment / .env
│   │   ├── db.py           # SQLAlchemy engine + session (SQLite)
│   │   └── main.py         # FastAPI app: GET / and GET /health
│   ├── tests/              # pytest
│   ├── run.py              # dev entry point (reads host/port from .env)
│   ├── requirements.in     # direct runtime deps
│   ├── requirements.txt    # pinned runtime lock file
│   ├── requirements-dev.in # direct dev deps
│   └── requirements-dev.txt# pinned dev lock file
├── frontend/               # Vite + TypeScript app
├── data/                   # local SQLite files (contents not committed)
├── docs/prompt-driven-log.md
└── .env.example            # template; copy to .env (never commit .env)
```

## Prerequisites

- Python 3.11+
- Node.js 20+ and npm
- Git

## Setup

```bash
git clone https://github.com/Dubu0312/tkxdpm_2.git
cd tkxdpm_2

# 1. Environment variables
cp .env.example .env         # then edit values as needed

# 2. Backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements-dev.txt   # or requirements.txt for runtime only

# 3. Frontend
cd frontend
npm install
cd ..
```

`requirements.txt` / `requirements-dev.txt` are fully pinned, so the same
environment can be reproduced on another machine. To add a dependency, edit
`backend/requirements.in` (or `requirements-dev.in`) and regenerate the lock:

```bash
pip install -r backend/requirements.in
pip freeze > backend/requirements.txt
```

## Running

### Backend

```bash
source .venv/bin/activate
cd backend
python run.py                # host/port from .env (default 127.0.0.1:8001)
```

Or explicitly:

```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

- API root: <http://127.0.0.1:8001/>
- Health check: <http://127.0.0.1:8001/health>
- OpenAPI docs: <http://127.0.0.1:8001/docs>

> The default port is **8001**, not 8000, because port 8000 is already in use on
> the current development machine. Change `BACKEND_PORT` in `.env` if needed
> (and keep `VITE_API_BASE_URL` in sync).

### Frontend

```bash
cd frontend
npm run dev                  # http://localhost:5173
```

The dev page calls the backend `/health` endpoint, so start the backend first to
see an "ok" status.

Other frontend scripts:

```bash
npm run typecheck            # tsc --noEmit
npm run build                # type check + production build into frontend/dist
npm run preview              # serve the production build
```

## Tests and linting

```bash
source .venv/bin/activate
cd backend
pytest                       # backend tests
ruff check .                 # backend lint
```

## Database

SQLite is used by default; the database file is created automatically at
`data/app.db` on first connection. The `data/` directory is tracked but its
`*.db` contents are ignored by Git. Point `DATABASE_URL` elsewhere in `.env` to
use a different location or engine.

## Environment variables

All variables are documented in [`.env.example`](.env.example). Copy it to
`.env` and fill in real values there — `.env` and any credential files are
git-ignored and must never be committed. Only variables prefixed with `VITE_`
are exposed to browser code.
