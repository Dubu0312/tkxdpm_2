# Prompt-Driven Development Log

Nhật ký các round phát triển theo prompt. Mỗi round ghi lại: yêu cầu, những gì
đã làm, các kiểm tra đã chạy, và vấn đề còn tồn tại.

---

## Round 0 — Setup development environment

**Ngày:** 2026-08-25
**Commit:** `round 00: setup development environment`

### Yêu cầu

Chuẩn bị môi trường development cho project (backend Python, database SQLite,
frontend TypeScript) trên repo Git đã có sẵn remote. Không `git init` lại,
không đổi remote, không triển khai business feature.

### Đã setup

**Repository / Git**
- Giữ nguyên repository và remote `origin`
  (`https://github.com/Dubu0312/tkxdpm_2.git`). Không init lại, không đổi remote.
- Tạo `.gitignore` bao phủ: `.venv/`, `node_modules/`, build artifacts
  (`dist/`, `build/`, `*.tsbuildinfo`), cache (`__pycache__/`, `.pytest_cache/`,
  `.ruff_cache/`, `.mypy_cache/`), `.env` (giữ lại `.env.example`), credentials
  (`*.pem`, `*.key`, `credentials.json`, `service-account*.json`, …) và file
  SQLite local (`*.db`, `*.sqlite3`, `*-wal`, `*-shm`).

**Backend (Python)**
- Virtualenv tại `.venv` ở root project (Python 3.11.4), không commit.
- Dependency management dạng 2 lớp để tái tạo được môi trường:
  - `backend/requirements.in` / `requirements-dev.in`: khai báo dependency trực tiếp.
  - `backend/requirements.txt` / `requirements-dev.txt`: lock file pin đầy đủ version.
- Stack: FastAPI + Uvicorn + SQLAlchemy + pydantic-settings + python-dotenv.
  Dev: pytest, httpx, ruff.
- Code skeleton (không có business logic):
  - `backend/app/config.py` — settings đọc từ `.env`; đường dẫn SQLite tương đối
    được resolve theo project root thay vì theo CWD.
  - `backend/app/db.py` — engine/session SQLAlchemy, tự tạo thư mục `data/`,
    hàm `check_connection()`.
  - `backend/app/main.py` — FastAPI app, CORS cho frontend dev server,
    endpoint `GET /` và `GET /health`.
  - `backend/run.py` — entry point dev, đọc host/port từ `.env`.
  - `backend/tests/test_health.py` — smoke test.
  - `backend/pyproject.toml` — cấu hình pytest và ruff.

**Database**
- SQLite, file mặc định `data/app.db`, tạo tự động khi kết nối lần đầu.
- Thư mục `data/` được track (qua `.gitkeep`) nhưng nội dung `*.db` bị ignore.

**Frontend (TypeScript)**
- Scaffold bằng `npm create vite@latest frontend -- --template vanilla-ts`
  (Vite 8, TypeScript 6), `npm install` đã chạy.
- Bật `"strict": true` trong `tsconfig.json`.
- Thêm script `typecheck`; `vite.config.ts` đặt `envDir: ".."` để dùng chung
  file `.env` ở root, port dev 5173.
- Source tối thiểu: `src/env.ts`, `src/api.ts` (gọi `/health`), `src/main.ts`,
  `src/style.css`. Đã xoá asset demo của template.

**Environment variables**
- `.env.example` ở root, chứa biến backend (`APP_NAME`, `ENVIRONMENT`, `DEBUG`,
  `BACKEND_HOST`, `BACKEND_PORT`, `DATABASE_URL`, `CORS_ORIGINS`, `SECRET_KEY`)
  và frontend (`VITE_API_BASE_URL`). Không chứa secret thật.
- `.env` local được tạo từ template và bị git-ignore.

**Tài liệu**
- `README.md`: tech stack, cấu trúc thư mục, hướng dẫn setup, lệnh chạy backend
  / frontend, test, lint, ghi chú về database và environment variables.

### Các check đã chạy

| Check | Lệnh | Kết quả |
| --- | --- | --- |
| Virtualenv | `python3 -m venv .venv` → `.venv/bin/python -V` | Python 3.11.4 |
| Cài backend deps | `pip install -r backend/requirements-dev.txt` | OK |
| Load settings | import `app.config.settings` | OK, resolve `DATABASE_URL` thành đường dẫn tuyệt đối |
| Backend tests | `pytest` | 2 passed |
| Backend lint | `ruff check .` | All checks passed |
| Backend khởi động | `python run.py` (127.0.0.1:8001) | Startup complete |
| `GET /` | `curl http://127.0.0.1:8001/` | 200 · `{"app":"tkxdpm_2","environment":"development"}` |
| `GET /health` | `curl http://127.0.0.1:8001/health` | 200 · `{"status":"ok","database":"ok","detail":null}` |
| `GET /docs` | `curl -o /dev/null -w "%{http_code}"` | 200 |
| CORS | request kèm `Origin: http://localhost:5173` | trả về `access-control-allow-origin: http://localhost:5173` |
| SQLite | kết nối lần đầu | tự tạo `data/app.db` |
| Frontend typecheck | `npm run typecheck` | OK, không lỗi |
| Frontend build | `npm run build` | Built in 73ms, output vào `frontend/dist` |
| Frontend dev server | `npm run dev` | Vite ready, `http://localhost:5173` trả HTML 200, `/src/main.ts` 200 |

Backend và frontend đã được chạy đồng thời để xác nhận hai bên khởi động được
cùng lúc và CORS cấu hình đúng.

### Vấn đề còn tồn tại / lưu ý

1. **Port 8000 đã bị chiếm trên máy dev hiện tại** (một tiến trình `vllm` đang
   listen `0.0.0.0:8000`), nên lần khởi động đầu tiên với port 8000 thất bại.
   Đã đổi port mặc định của project sang **8001** (`BACKEND_PORT`,
   `VITE_API_BASE_URL`). Trên máy khác có thể đổi lại 8000 nếu muốn — nhớ sửa cả
   hai biến cho khớp.
2. **Chưa có database migration tool** (Alembic). Hiện chỉ có `Base` của
   SQLAlchemy, chưa có model nào và chưa tạo bảng. Cần bổ sung khi bắt đầu làm
   data model ở round sau.
3. **Chưa có linter/formatter cho frontend** (ESLint / Prettier) và chưa có test
   frontend. Mới chỉ có `tsc --noEmit`.
4. **Chưa có CI** (GitHub Actions) chạy test/lint tự động.
5. **Cảnh báo deprecation từ Starlette TestClient**: gợi ý dùng `httpx2` thay
   `httpx`. Không ảnh hưởng, test vẫn pass; theo dõi ở round sau.
6. **Lock file được sinh bằng `pip freeze`** trên Python 3.11/Linux. Nếu cần
   cross-platform chặt chẽ hơn, cân nhắc `pip-tools` hoặc `uv`.
7. Chưa triển khai business feature nào — đúng phạm vi Round 0.

---

## Round 1 — Initialize scheduling application

**Ngày:** 2026-08-25
**Commit:** `round 01: initialize scheduling application`

### Yêu cầu

Xây dựng ứng dụng đặt lịch chạy end-to-end trên môi trường của Round 0: backend
Python, database SQLite, frontend TypeScript, dùng `.venv` sẵn có và npm. Hỗ trợ
tạo / xem danh sách / xem chi tiết / chỉnh sửa / xóa lịch. Không đổi Git remote,
không thêm Docker, ưu tiên đơn giản, không triển khai tính năng chưa được yêu cầu.

### Quyết định kiến trúc

- **Giữ nguyên stack Round 0**: FastAPI + SQLAlchemy + SQLite ở backend, Vite +
  TypeScript ở frontend. Không thêm framework UI (React/Vue) — với 5 thao tác
  CRUD thì vanilla TypeScript đủ và ít phụ thuộc hơn.
- **Không thêm Docker**: chạy local bằng `.venv` + npm là đủ.
- **Không thêm Alembic**: schema mới có một bảng, tạo bằng
  `Base.metadata.create_all()` lúc khởi động (FastAPI `lifespan`). Sẽ chuyển sang
  migration tool khi schema bắt đầu thay đổi.
- **Quy ước thời gian**: toàn bộ datetime là *naive local wall-clock*
  (`2026-09-01T09:00:00`) — đúng định dạng `<input type="datetime-local">` sinh
  ra, nên không có bước đổi múi giờ nào giữa frontend, backend và SQLite. Input
  có offset (`+07:00`) được chuyển về local rồi bỏ offset để dữ liệu lưu đồng nhất.
- **PUT (full update)** thay vì PATCH: form ở frontend luôn gửi đủ trường, nên
  không cần partial update.

### Data model

Bảng `schedules`:

| Trường | Kiểu | Ghi chú |
| --- | --- | --- |
| `id` | INTEGER PK | |
| `title` | VARCHAR(200) NOT NULL | bắt buộc, không rỗng |
| `description` | TEXT NULL | tùy chọn |
| `location` | VARCHAR(200) NULL | tùy chọn |
| `start_time` | DATETIME NOT NULL | có index |
| `end_time` | DATETIME NOT NULL | |
| `created_at` / `updated_at` | DATETIME NOT NULL | tự sinh, `updated_at` tự cập nhật |

Ràng buộc `CHECK (end_time > start_time)` ở mức bảng, cộng thêm validate cùng
điều kiện ở tầng Pydantic (trả `422` với thông báo rõ ràng).

Chọn thêm `description`, `location`, `created_at`, `updated_at` — đây là mức tối
thiểu để một lịch hẹn dùng được thật (biết ở đâu, ghi chú gì, sửa lần cuối khi
nào). Không thêm recurrence, participants, reminder, status… vì chưa được yêu cầu.

### Đã làm

**Backend**
- `backend/app/models.py` — ORM model `Schedule` (+ CHECK constraint).
- `backend/app/schemas.py` — `ScheduleCreate` / `ScheduleUpdate` / `ScheduleRead`,
  validate `end_time > start_time` và chuẩn hóa datetime về naive local.
- `backend/app/routers/schedules.py` — 5 endpoint CRUD dưới `/api/schedules`,
  dùng `Annotated[Session, Depends(get_session)]`, 404 khi không tìm thấy.
- `backend/app/db.py` — thêm `init_db()`.
- `backend/app/main.py` — chuyển `on_event("startup")` sang `lifespan`, gắn router.

**Frontend**
- `src/types.ts`, `src/api.ts` (client fetch có kiểu, `ApiError` gói lại lỗi
  mạng và bóc `detail` dạng chuỗi lẫn mảng validation của FastAPI),
  `src/format.ts` (chuyển đổi & hiển thị thời gian, tính thời lượng),
  `src/views.ts` (render danh sách / chi tiết / form), `src/main.ts` (state, điều
  hướng giữa 4 view: rỗng · chi tiết · tạo · sửa).
- Giao diện 2 cột: danh sách nhóm theo ngày ở trái, panel chi tiết/form ở phải;
  có xác nhận trước khi xóa, hiển thị lỗi từ backend, responsive và dark mode.
- Toàn bộ dữ liệu người dùng render bằng `textContent` (không `innerHTML`) nên
  không dính XSS; có test khẳng định điều này.
- Thêm `vitest` + `jsdom` (dev deps) và script `npm test` / `npm run test:watch`.

### Các check đã chạy

| Check | Lệnh | Kết quả |
| --- | --- | --- |
| Backend lint | `ruff check backend` | All checks passed |
| Backend test | `pytest` | **16 passed** (CRUD, sắp xếp, 404, 422, trường tùy chọn, datetime có offset) |
| Frontend test | `npm test` | **25 passed** / 3 file (format, api client, render DOM) |
| Frontend typecheck | `npm run typecheck` | Sạch (strict mode) |
| Frontend build | `npm run build` | Built OK (~7.6 kB JS gzip 3.2 kB) |
| **End-to-end thật** | app frontend chạy trong jsdom, gọi backend thật trên `127.0.0.1:8001` | **2 passed** — tạo → xem danh sách → xem chi tiết → sửa → xóa đều đi qua HTTP thật và ghi vào `data/app.db`; lỗi `end_time <= start_time` hiển thị đúng trên UI |
| CRUD qua curl | POST / GET / PUT / DELETE `/api/schedules` | 201 · 200 · 200 · 204, GET sau khi xóa trả 404, `updated_at` có thay đổi sau PUT |
| SQLite thật | đọc `data/app.db` bằng `sqlite3` | bảng `schedules` được tạo đúng schema kèm CHECK constraint |
| Dev servers | backend `:8001` + Vite `:5173` chạy song song | trang `http://localhost:5173` trả HTML đúng, `/src/main.ts` 200 |

File test end-to-end là script kiểm tra một lần, đã xóa sau khi chạy vì nó yêu
cầu backend đang chạy nên không phù hợp để nằm trong bộ test mặc định.

### Vấn đề còn tồn tại / lưu ý

1. **Chưa có E2E test tự động trong repo.** Luồng end-to-end đã được xác minh
   thủ công ở round này nhưng chưa có test cố định (cần cơ chế tự bật/tắt backend,
   hoặc Playwright). Bộ test hiện tại dừng ở mức API (pytest) và unit/DOM (vitest).
2. **Chưa có migration tool** (Alembic) — vẫn dùng `create_all()`. Cần bổ sung
   trước lần đổi schema đầu tiên, nếu không dữ liệu cũ sẽ không được nâng cấp.
3. **Chưa có phân trang / tìm kiếm / lọc theo khoảng ngày.** `GET /api/schedules`
   trả về toàn bộ bản ghi — đủ cho quy mô hiện tại, sẽ thành vấn đề khi dữ liệu lớn.
4. **Chưa phát hiện trùng lịch (overlap)** và chưa có xác thực người dùng — chưa
   nằm trong yêu cầu.
5. **Không hỗ trợ đa múi giờ**: mọi thời gian là giờ local của máy chạy. Hợp lý
   cho ứng dụng local, nhưng cần thiết kế lại nếu triển khai nhiều vùng.
6. Port mặc định vẫn là **8001** (port 8000 bị chiếm trên máy dev hiện tại).
7. Cảnh báo deprecation `httpx` → `httpx2` của Starlette TestClient vẫn còn; chưa
   ảnh hưởng.
