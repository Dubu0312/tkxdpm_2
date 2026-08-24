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
