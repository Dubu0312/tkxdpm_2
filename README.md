# tkxdpm_2

Ứng dụng đặt lịch (scheduling) chạy local: backend Python + SQLite, frontend TypeScript.

Chức năng hiện có: tạo lịch, xem danh sách, xem chi tiết, chỉnh sửa và xóa lịch.
Mỗi lịch gồm tiêu đề, thời gian bắt đầu / kết thúc, múi giờ, địa điểm và mô tả
(hai trường sau không bắt buộc), kèm mốc `created_at` / `updated_at`. Lịch có thể
được tạo ở bất kỳ múi giờ nào và xem lại ở múi giờ khác mà không đổi thời điểm
thực. Backend từ chối các lịch bị trùng khung giờ với lịch đã có.

## Tech stack

| Layer      | Choice                                              |
| ---------- | --------------------------------------------------- |
| Backend    | Python 3.11 · FastAPI · Uvicorn                     |
| Database   | SQLite (via SQLAlchemy)                             |
| Frontend   | TypeScript · Vite (vanilla, không framework UI)     |
| Tooling    | pip + pinned requirements · pytest · ruff · vitest  |

## Layout

```
.
├── .venv/                  # Python virtualenv (not committed)
├── backend/
│   ├── app/
│   │   ├── config.py       # settings from environment / .env
│   │   ├── db.py           # SQLAlchemy engine + session (SQLite)
│   │   ├── models.py       # Schedule ORM model (instants stored in UTC)
│   │   ├── schemas.py      # Pydantic schemas + timezone conversion
│   │   ├── routers/
│   │   │   └── schedules.py# CRUD endpoints under /api/schedules
│   │   └── main.py         # FastAPI app: GET /, GET /health, router
│   ├── migrate.py          # one-off upgrade of pre-timezone databases
│   ├── tests/              # pytest
│   ├── run.py              # dev entry point (reads host/port from .env)
│   ├── requirements.in     # direct runtime deps
│   ├── requirements.txt    # pinned runtime lock file
│   ├── requirements-dev.in # direct dev deps
│   └── requirements-dev.txt# pinned dev lock file
├── frontend/               # Vite + TypeScript app
│   └── src/
│       ├── api.ts          # typed fetch client
│       ├── types.ts        # Schedule types
│       ├── format.ts       # timezone-aware datetime helpers
│       ├── views.ts        # list / detail / form rendering
│       └── main.ts         # app state + wiring
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

The `schedules` table is created automatically on startup.

> The default port is **8001**, not 8000, because port 8000 is already in use on
> the current development machine. Change `BACKEND_PORT` in `.env` if needed
> (and keep `VITE_API_BASE_URL` in sync).

### Frontend

```bash
cd frontend
npm run dev                  # http://localhost:5173
```

Open <http://localhost:5173>. The page talks to the backend, so start the backend
first — otherwise the list shows a connection error.

Other frontend scripts:

```bash
npm run typecheck            # tsc --noEmit
npm run test                 # vitest (jsdom)
npm run build                # type check + production build into frontend/dist
npm run preview              # serve the production build
```

## API

Base URL: `http://127.0.0.1:8001`.

| Method | Path                   | Mô tả                                       |
| ------ | ---------------------- | ------------------------------------------- |
| GET    | `/api/schedules`       | Danh sách lịch, sắp xếp theo thời gian bắt đầu |
| POST   | `/api/schedules`       | Tạo lịch (201)                              |
| GET    | `/api/schedules/{id}`  | Chi tiết một lịch                           |
| PUT    | `/api/schedules/{id}`  | Cập nhật toàn bộ một lịch                   |
| DELETE | `/api/schedules/{id}`  | Xóa lịch (204)                              |

Schedule fields: `title` (bắt buộc, ≤200 ký tự), `start_time`, `end_time` (bắt
buộc, `end_time` phải sau `start_time`), `timezone` (tên IANA, mặc định
`DEFAULT_TIMEZONE`), `location` và `description` (tùy chọn), cùng `id`,
`created_at`, `updated_at` do server sinh ra. Dữ liệu không hợp lệ trả về `422`
kèm thông báo, id không tồn tại trả về `404`.

### Múi giờ

Quy ước xử lý thời gian:

| Tầng | Cách xử lý |
| --- | --- |
| SQLite | `start_time` / `end_time` / `created_at` / `updated_at` lưu **UTC** (naive, vì SQLite không có kiểu aware); `timezone` lưu tên IANA riêng |
| Backend | Chuyển input về UTC lúc validate, so sánh và sắp xếp bằng UTC, dựng response về múi giờ của từng lịch |
| API | ISO-8601 kèm offset tường minh, ví dụ `2026-09-01T09:00:00+09:00`; `created_at`/`updated_at` là `+00:00` |
| Frontend | Hiển thị mọi thời điểm theo *múi giờ đang xem* bằng `Intl.DateTimeFormat`; ô nhập gửi giờ wall-clock kèm `timezone`, không tự tính offset |

Input `start_time` / `end_time` chấp nhận hai dạng:

* **kèm offset** (`2026-09-01T09:00:00+09:00`) — offset quyết định thời điểm,
  trường `timezone` chỉ dùng để hiển thị lại;
* **không offset** (`2026-09-01T09:00:00`) — được hiểu là giờ địa phương của
  `timezone` trong cùng request. Đây là dạng frontend gửi.

Vì mọi so sánh diễn ra trên UTC, phát hiện xung đột hoạt động đúng giữa các múi
giờ khác nhau và qua các mốc đổi giờ DST. Một `timezone` không hợp lệ trả về `422`.

Ví dụ — hai lịch dưới đây xung đột dù giờ hiển thị khác nhau (cùng là 09:00 UTC):

```bash
curl -X POST http://127.0.0.1:8001/api/schedules -H 'Content-Type: application/json' \
  -d '{"title":"Tokyo","start_time":"2026-12-15T18:00:00","end_time":"2026-12-15T19:00:00","timezone":"Asia/Tokyo"}'

curl -X POST http://127.0.0.1:8001/api/schedules -H 'Content-Type: application/json' \
  -d '{"title":"Saigon","start_time":"2026-12-15T16:30:00","end_time":"2026-12-15T17:30:00","timezone":"Asia/Saigon"}'
# -> 409 Conflict
```

### Xung đột thời gian

`POST` và `PUT` từ chối lịch có khung giờ chồng lấn lịch đã tồn tại và trả về
`409 Conflict`. Hai khoảng thời gian được coi là chồng lấn khi mỗi khoảng bắt đầu
trước khi khoảng kia kết thúc — nên hai lịch **liền kề** (một lịch kết thúc đúng
lúc lịch kia bắt đầu) vẫn hợp lệ. Khi cập nhật, lịch đang sửa không tự xung đột
với chính nó.

Kiểm tra này nằm ở backend và là nguồn duy nhất quyết định hợp lệ hay không;
frontend chỉ hiển thị lại kết quả, không kiểm tra trùng lịch riêng.

Body của `409`:

```json
{
  "detail": {
    "code": "schedule_conflict",
    "message": "Time range overlaps 1 existing schedule",
    "conflicts": [ { "id": 1, "title": "Họp nhóm", "start_time": "...", "end_time": "...", "...": "..." } ]
  }
}
```

Frontend dùng danh sách `conflicts` để hiện tên và khung giờ của lịch bị trùng,
đồng thời giữ nguyên dữ liệu đang nhập trong form.

Ví dụ:

```bash
curl -X POST http://127.0.0.1:8001/api/schedules \
  -H 'Content-Type: application/json' \
  -d '{"title":"Họp nhóm","start_time":"2026-09-01T09:00:00","end_time":"2026-09-01T10:30:00","timezone":"Asia/Ho_Chi_Minh"}'
```

## Tests and linting

```bash
# Backend
source .venv/bin/activate
cd backend && pytest && ruff check .

# Frontend
cd frontend && npm run typecheck && npm test
```

## Database

SQLite is used by default; the database file and the `schedules` table are
created automatically at `data/app.db` when the app starts.

Nếu database được tạo **trước** khi có hỗ trợ múi giờ (trước Round 3), app sẽ báo
lỗi khi khởi động vì bảng `schedules` còn thiếu cột `timezone`. Nâng cấp bằng:

```bash
cd backend
python migrate.py --timezone Asia/Ho_Chi_Minh   # múi giờ các bản ghi cũ đã nhập
```

Script này thêm cột `timezone` và đổi các mốc thời gian cũ (giờ địa phương) sang
UTC. Chạy lại lần nữa là no-op. The `data/` directory is tracked but its
`*.db` contents are ignored by Git. Point `DATABASE_URL` elsewhere in `.env` to
use a different location or engine.

## Environment variables

All variables are documented in [`.env.example`](.env.example). Copy it to
`.env` and fill in real values there — `.env` and any credential files are
git-ignored and must never be committed. Only variables prefixed with `VITE_`
are exposed to browser code.
