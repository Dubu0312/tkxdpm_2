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

---

## Round 2 — Add scheduling conflict detection

**Ngày:** 2026-08-25
**Commit:** `round 02: add scheduling conflict detection`

### Yêu cầu

Khi tạo hoặc chỉnh sửa lịch, không cho phép lịch mới overlap với lịch đã tồn tại.
Hai lịch liền kề (một lịch kết thúc đúng lúc lịch kia bắt đầu) vẫn hợp lệ. Logic
phải nằm ở backend chứ không chỉ ở frontend; frontend hiển thị lỗi rõ ràng khi bị
từ chối. Không duplicate business logic, không đụng phần không liên quan.

### Quyết định triển khai

- **Một nguồn logic duy nhất ở backend.** `find_conflicts()` trong
  `backend/app/routers/schedules.py` là nơi duy nhất định nghĩa thế nào là trùng
  giờ; cả `POST` và `PUT` gọi chung qua `_reject_conflicts()`. Frontend **không**
  tự kiểm tra trùng lịch — nếu làm sẽ là bản sao thứ hai của cùng một quy tắc.
- **Điều kiện overlap**: `existing.start_time < new.end_time AND
  existing.end_time > new.start_time`. Dùng so sánh chặt (`<`, `>`) nên khoảng
  chạm nhau (`10:00–11:00` sau `09:00–10:00`) không bị tính là xung đột — đúng
  yêu cầu. Kiểm tra chạy bằng một câu SQL, không load toàn bộ bảng.
- **Khi sửa**: truyền `exclude_id=schedule_id` để lịch không tự xung đột với
  chính nó; nhờ vậy có thể đổi tiêu đề mà giữ nguyên giờ, hoặc thu hẹp khung giờ
  nằm trong chính nó.
- **HTTP 409 Conflict** (không phải 422) vì dữ liệu gửi lên hợp lệ về mặt cú
  pháp, chỉ mâu thuẫn với trạng thái hiện có. Thứ tự kiểm tra: validate payload
  (422) → tồn tại bản ghi (404) → xung đột (409).
- **Body 409 có cấu trúc** (`schemas.ConflictDetail`: `code`, `message`,
  `conflicts: list[ScheduleRead]`) thay vì chỉ một chuỗi. Backend nêu *sự thật*
  (những lịch nào bị trùng), frontend lo phần *diễn đạt* — nhờ vậy thông báo
  tiếng Việt nằm ở frontend, không lẫn vào backend.
- **Giữ lại dữ liệu form khi bị từ chối.** Trước đây mọi lỗi submit đều làm form
  render lại từ đầu và mất hết những gì đã nhập. Đã thêm `state.draft`: khi bị từ
  chối, form giữ nguyên dữ liệu để người dùng chỉ cần sửa giờ. Đây là phần cần
  thiết để "hiển thị lỗi rõ ràng" thực sự dùng được, và cũng khắc phục luôn cho
  lỗi 422 sẵn có.

### Đã thay đổi

**Backend**
- `app/schemas.py` — thêm `ConflictDetail`.
- `app/routers/schedules.py` — thêm `find_conflicts()`, `_reject_conflicts()`,
  `CONFLICT_RESPONSE` (khai báo 409 trong OpenAPI); `POST` và `PUT` gọi kiểm tra
  trước khi ghi.

**Frontend**
- `src/api.ts` — `ApiError` mang thêm `conflicts`; hàm dựng lỗi nhận diện body
  `schedule_conflict`, vẫn xử lý được lỗi chuỗi và mảng validation như cũ.
- `src/views.ts` — thêm `renderError()` (liệt kê tên + khung giờ từng lịch bị
  trùng, kèm nhắc rằng lịch liền kề vẫn hợp lệ); `renderForm()` nhận thêm tham số
  `draft`.
- `src/main.ts` — `state.error` chuyển thành `ApiError`, thêm `state.draft`.
- `index.html` / `style.css` — khối `#error` từ `<p>` thành `<div>` để chứa danh
  sách, thêm style cho danh sách xung đột.

Không đụng tới model, database schema, endpoint `GET`/`DELETE` hay các phần khác.

### Các check đã chạy

| Check | Lệnh | Kết quả |
| --- | --- | --- |
| Backend lint | `ruff check backend` | All checks passed |
| Backend test | `pytest` | **35 passed** (16 cũ + 19 mới, không có regression) |
| Frontend test | `npm test` | **33 passed** (25 cũ + 8 mới) |
| Frontend typecheck | `npm run typecheck` | Sạch |
| Frontend build | `npm run build` | Built OK |
| **End-to-end thật** | UI thật trong jsdom → backend `:8001` → SQLite | **1 passed**: tạo lịch 09:00–10:00 → tạo 09:30–10:30 bị **409** và UI hiện đúng tên + giờ lịch trùng, form giữ nguyên dữ liệu, DB không có bản ghi thừa → tạo 10:00–11:00 (liền kề) **201** → sửa lịch đó về 09:15–09:45 bị **409** và bản ghi không đổi → sửa tiêu đề mà giữ nguyên giờ **200** |

Các trường hợp overlap được phủ trong pytest: trùng hoàn toàn, nằm trong, bao
trùm, chồng đầu, chồng cuối, chồng đúng một phút ở hai đầu; và các trường hợp hợp
lệ: chạm đầu, chạm cuối, tách rời, khác ngày. Ngoài ra có test khẳng định request
bị 409 không ghi gì vào database và báo cáo *tất cả* lịch bị trùng chứ không chỉ
lịch đầu tiên.

### Vấn đề còn tồn tại / lưu ý

1. **Race condition về mặt lý thuyết**: kiểm tra xung đột và phần ghi nằm trong
   cùng một transaction nhưng không khóa bảng, nên hai request gửi đồng thời vẫn
   có thể tạo ra hai lịch chồng nhau. Với SQLite + một người dùng local thì gần
   như không xảy ra; nếu cần chắc chắn thì phải dùng ràng buộc ở tầng database
   hoặc khóa ghi.
2. **Chưa có tính năng "vẫn tạo dù trùng" (force)** — hiện xung đột là chặn cứng,
   đúng theo yêu cầu.
3. **Frontend chưa highlight lịch bị trùng trong danh sách** — thông báo lỗi đã
   nêu tên và khung giờ; highlight là cải tiến có thể làm sau.
4. Các mục còn tồn tại của Round 1 (chưa có E2E test cố định trong repo, chưa có
   Alembic, chưa phân trang/tìm kiếm, chưa xác thực người dùng, chỉ hỗ trợ một
   múi giờ, port mặc định 8001) vẫn giữ nguyên.

---

## Round 3 — Add timezone support

**Ngày:** 2026-08-25
**Commit:** `round 03: add timezone support`

### Yêu cầu

Cho phép tạo và xem lịch ở các múi giờ khác nhau. Thời gian phải nhất quán giữa
frontend, API, backend và SQLite; một lịch phải giữ nguyên thời điểm thực khi
được xem ở múi giờ khác. Conflict detection đã có phải tiếp tục chính xác khi các
lịch dùng múi giờ khác nhau.

### Quyết định kỹ thuật (tóm tắt)

| Câu hỏi | Quyết định |
| --- | --- |
| **Lưu datetime thế nào** | Lưu **UTC** dưới dạng naive datetime trong SQLite (SQLite không có kiểu timezone-aware). Áp dụng cho cả `start_time`, `end_time`, `created_at`, `updated_at`. |
| **Lưu timezone thế nào** | Cột riêng `timezone` chứa **tên IANA** (`Asia/Tokyo`), không lưu offset. Offset thay đổi theo DST nên lưu offset sẽ sai; tên vùng thì không. |
| **Format qua API** | ISO-8601 **kèm offset tường minh**: `2026-09-01T09:00:00+09:00`. Response render theo múi giờ của chính lịch đó nên giữ đúng giờ người dùng đã nhập; `created_at`/`updated_at` render `+00:00`. |
| **Convert ở đâu** | Chỉ ở backend, trong tầng schema. Input naive được hiểu theo `timezone` của request; input có offset thì offset quyết định thời điểm. Frontend **không** làm phép tính offset nào. |
| **Hiển thị ở frontend** | `Intl.DateTimeFormat` với `timeZone` — trình duyệt giữ luật DST. Có ô chọn "Xem theo" ở thanh trên, mặc định là múi giờ của trình duyệt; đổi ô này chỉ render lại, không đụng dữ liệu. |

Lý do chọn "UTC + tên vùng" thay vì chỉ lưu UTC: chỉ có UTC thì mất thông tin
người dùng đã nhập giờ theo vùng nào, và khi sửa lại lịch sẽ không tái tạo được
đúng wall-clock ban đầu (đặc biệt quanh mốc DST). Ngược lại, chỉ lưu giờ địa
phương + tên vùng thì mọi so sánh đều phải convert lúc query — chậm và dễ sai.

Một hệ quả quan trọng: **conflict detection không cần sửa logic**. Nó vốn so
sánh `start_time`/`end_time`, mà hai cột này giờ là UTC — nên tự động đúng giữa
các múi giờ và qua mốc DST.

### Đã thay đổi

**Backend**
- `app/models.py` — thêm cột `timezone`; ghi rõ quy ước lưu UTC; `utcnow()` thay
  cho `datetime.now()` địa phương.
- `app/schemas.py` — tách `ScheduleFields` (không có ngữ nghĩa thời gian) khỏi
  `ScheduleInput` (validate + convert sang UTC) và `ScheduleRead` (render theo
  múi giờ của lịch). Thêm `resolve_timezone` / `to_utc` / `from_utc` và
  `field_serializer` ép offset dạng số (mặc định pydantic in UTC thành `Z`, làm
  các vùng offset 0 như London mùa đông trông khác phần còn lại).
- `app/routers/schedules.py` — dựng response bằng `ScheduleRead.from_model`;
  logic tìm xung đột giữ nguyên, chỉ bổ sung tài liệu vì nay so sánh trên UTC.
- `app/config.py`, `.env.example` — thêm `DEFAULT_TIMEZONE`.
- `app/db.py` — `init_db()` kiểm tra bảng cũ và báo lỗi rõ ràng nếu thiếu cột
  `timezone`, thay vì đọc sai dữ liệu trong im lặng.
- `migrate.py` (mới) — nâng cấp database tạo trước Round 3: thêm cột `timezone`,
  đổi các mốc thời gian cũ từ giờ địa phương sang UTC. Idempotent. Đây là giải
  pháp tạm cho đúng một lần đổi schema; Alembic vẫn là hướng đúng về sau.
- `requirements.in/.txt` — thêm `tzdata` để `zoneinfo` chạy được cả trên máy
  không có tzdb hệ thống (Windows, image tối giản).
- `tests/conftest.py` — trỏ `DATABASE_URL` sang thư mục tạm **trước khi** import
  app, nên bộ test không còn đụng vào `data/app.db` của máy dev.

**Frontend**
- `src/format.ts` — viết lại theo hướng timezone-aware: `dayKeyInZone`,
  `wallClockInZone`, `formatTime/formatDate/formatRange` nhận tham số vùng,
  `offsetLabel`, `browserTimezone`, `listTimezones`, `canonicalTimezone`,
  `sameZone`.
- `src/views.ts` — danh sách nhóm theo ngày **của múi giờ đang xem**; thẻ lịch
  ghi thêm tên vùng khi khác vùng đang xem; panel chi tiết hiện thêm dòng "Giờ
  gốc" theo vùng của lịch; form có ô chọn múi giờ (`timezoneSelect`).
- `src/main.ts` — thêm `state.viewTimezone` và ô chọn ở thanh trên.
- `src/types.ts`, `src/api.ts`, `index.html`, `style.css` — cập nhật theo.

### Vấn đề gặp phải khi làm

- **Bí danh múi giờ.** `Intl.supportedValuesOf("timeZone")` chỉ trả về id chuẩn
  hóa: runtime này liệt kê `Asia/Saigon` chứ không có `Asia/Ho_Chi_Minh` (hai tên
  của cùng một vùng), và cũng không có `UTC`. Nếu so sánh chuỗi thuần thì một
  lịch tạo bằng giá trị mặc định `Asia/Ho_Chi_Minh` khi xem ở `Asia/Saigon` sẽ bị
  coi là "khác vùng". Đã xử lý bằng `canonicalTimezone()` / `sameZone()` (dùng
  chính `Intl` để chuẩn hóa) cho mọi phép so sánh, đồng thời vẫn **giữ nguyên
  chuỗi người dùng đã chọn** khi lưu, và thêm `UTC` vào đầu danh sách chọn.
- **Pydantic in UTC thành `Z`.** Làm `Europe/London` mùa đông (offset 0) trả về
  `...Z` trong khi các lịch khác trả về `+07:00`. Đã ép offset dạng số cho nhất
  quán.

### Các check đã chạy

| Check | Lệnh | Kết quả |
| --- | --- | --- |
| Backend lint | `ruff check backend` | All checks passed |
| Backend test | `pytest` | **54 passed** (35 cũ + 19 test timezone mới) |
| Frontend test | `npm test` | **49 passed** (33 cũ + 16 mới) |
| Frontend typecheck / build | `npm run typecheck`, `npm run build` | Sạch / Built OK |
| Migration | chạy `migrate.py` trên bản sao database kiểu cũ | 09:00 giờ Sài Gòn → `02:00` UTC, thêm cột `timezone`, chạy lần hai là no-op |
| **End-to-end thật** | UI thật trong jsdom → backend `:8001` → SQLite | **1 passed** (xem chi tiết bên dưới) |
| Kiểm chứng bằng curl | tạo lịch Tokyo 18:00 và Saigon 16:30 | Tokyo lưu `2026-12-15 09:00:00` UTC; Saigon 16:30 (=09:30Z) bị **409**; Saigon 17:00 (=10:00Z, liền kề) được **201** |

Nội dung bài E2E: tạo lịch 11:00–12:00 giờ Tokyo → API trả
`2026-12-10T11:00:00+09:00` → xem ở Sài Gòn thành 09:00–10:00 kèm dòng "Giờ gốc"
11:00–12:00, xem ở New York thành 21:00–22:00 và rơi sang **ngày hôm trước**
trong danh sách, thời lượng vẫn 1 giờ → tạo lịch Sài Gòn 09:30–10:30 (trùng thời
điểm thực) bị **409** và thông báo hiển thị lịch trùng theo múi giờ đang xem →
cùng wall-clock đó nhưng ở London là thời điểm khác nên được **201** → Sài Gòn
10:00 (đúng lúc lịch Tokyo kết thúc) được **201** → mở form sửa lịch Tokyo trong
lúc đang xem theo giờ Sài Gòn thì form vẫn hiện 11:00 và vùng `Asia/Tokyo`.

Các trường hợp timezone phủ trong pytest: naive input hiểu theo `timezone`,
input có offset, offset thắng `timezone` khi xác định thời điểm, lưu đúng UTC,
render lại đúng wall-clock, sắp xếp theo thời điểm thực (không theo giờ hiển
thị), timezone lạ trả 422, cùng wall-clock ở hai vùng khác nhau **không** xung
đột, xung đột chéo múi giờ, liền kề chéo múi giờ, xung đột vắt qua ranh giới
ngày, đổi mỗi `timezone` cũng làm lịch dịch thời điểm và có thể sinh xung đột,
offset khác nhau giữa mùa đông/mùa hè, khoảng thời gian vắt qua mốc DST
(spring-forward giữ đúng 1 giờ thực, fall-back thành 2 giờ thực), và xung đột
quanh mốc DST.

### Vấn đề còn tồn tại / lưu ý

1. **Giờ địa phương không tồn tại hoặc lặp lại quanh DST** được Python `zoneinfo`
   xử lý theo mặc định (`fold=0`) chứ ứng dụng không hỏi lại người dùng. Ví dụ
   02:30 ngày spring-forward ở New York là giờ không tồn tại nhưng vẫn được nhận.
   Ứng dụng đặt lịch nghiêm túc nên cảnh báo ở những mốc này.
2. **Ô chọn múi giờ liệt kê toàn bộ ~420 vùng**, chưa có tìm kiếm hay nhóm theo
   khu vực. Dùng được nhưng chưa tiện.
3. **Múi giờ hiển thị không được lưu lại** giữa các lần mở trang — luôn quay về
   múi giờ của trình duyệt.
4. **`migrate.py` là script một lần**, không có bảng version. Lần đổi schema tiếp
   theo nên chuyển hẳn sang Alembic.
5. Các mục tồn đọng từ Round 1–2 vẫn giữ nguyên (chưa có E2E test cố định trong
   repo, chưa phân trang/tìm kiếm, chưa xác thực người dùng, race condition lý
   thuyết khi kiểm tra xung đột, port mặc định 8001).

---

## Round 4 — Add country holiday validation

**Ngày:** 2026-08-25
**Commit:** `round 04: add country holiday validation`

### Yêu cầu

Người dùng có thể xác định quốc gia liên quan đến lịch. Nếu ngày được chọn là
ngày nghỉ chính thức của quốc gia đó thì không được tạo lịch, và frontend phải
nêu rõ lý do. Ưu tiên: đơn giản để chạy/demo, mở rộng thêm quốc gia được, không
hard-code logic hoặc dữ liệu rải rác. Phải hoạt động đúng cùng timezone và áp
dụng cho cả tạo mới lẫn chỉnh sửa.

### Hệ thống xác định ngày nghỉ như thế nào

**Nguồn dữ liệu: package [`holidays`](https://pypi.org/project/holidays/) (thuần
Python, offline).** Package này **tính** ngày nghỉ từ luật của từng quốc gia chứ
không tra một bảng cố định — nên nó ra đúng cả ngày lễ trôi theo lịch âm hoặc
theo Easter. Ví dụ kiểm chứng: Tết Nguyên đán Việt Nam 2026 rơi vào 17/02, và
package tính ra đúng cả chuỗi 16–20/02 (giao thừa + 4 ngày Tết) mà không cần khai
báo gì.

Các phương án đã cân nhắc và lý do loại:

| Phương án | Lý do không chọn |
| --- | --- |
| File JSON/YAML tự quản lý trong repo | Phải tự nhập dữ liệu cho từng nước **và từng năm**; ngày lễ âm lịch phải tra tay. Demo được nhưng sẽ mục sau một năm. |
| Gọi API bên ngoài (nager.date…) | Cần mạng khi chạy và khi test — trái với "đơn giản để chạy và demo", làm test giòn. |
| Hard-code trong code validation | Vi phạm trực tiếp yêu cầu "không hard-code dữ liệu rải rác". |

**Cách xác định một lịch có rơi vào ngày nghỉ:**

1. Lấy `start`/`end` của lịch (đang lưu UTC) đổi về **giờ địa phương theo
   `timezone` của chính lịch đó** — nên "ngày nào" khớp với cuốn lịch người dùng
   nhìn thấy, chứ không phải ngày theo UTC.
2. Duyệt từng ngày trong khoảng **nửa mở** `[start_local, end_local)` — lịch kết
   thúc đúng 00:00 không chạm sang ngày hôm sau.
3. Với mỗi ngày, tra tên ngày nghỉ của `country`. Có kết quả → từ chối `409` kèm
   danh sách đầy đủ (ngày + tên).

**Không rải rác:** toàn bộ hiểu biết về ngày nghỉ nằm trong một module duy nhất
`backend/app/holiday_calendar.py` (danh sách quốc gia, chuẩn hóa mã, tra cứu,
quy tắc khoảng ngày). Router chỉ gọi `_reject_holidays()`, dùng chung cho cả
`POST` và `PUT`. Frontend không chứa danh sách quốc gia nào — nó lấy từ
`GET /api/countries`, vốn cũng sinh ra từ registry của package.

**Mở rộng quốc gia:** không cần sửa code. 250 quốc gia package hỗ trợ đều hiện ra
trong ô chọn; muốn thêm nước mới thì nâng phiên bản package.

### Quyết định thiết kế khác

- **`country` là tùy chọn** (`NULL` = không kiểm tra ngày nghỉ). Ép buộc chọn
  quốc gia sẽ chặn cả những lịch không liên quan đến ngày nghỉ nước nào.
- **Mã ISO 3166-1 alpha-2**, chuẩn hóa in hoa khi lưu; mã lạ trả `422`.
- **Trả `409 Conflict`** với `code: "holiday_conflict"`, cùng dạng cấu trúc như
  `schedule_conflict` đã có. `422` vẫn dành riêng cho payload sai định dạng; cả
  hai kiểu từ chối "khung giờ này không dùng được" đều là `409` để frontend xử lý
  thống nhất.
- **Kiểm tra ngày nghỉ trước kiểm tra trùng lịch**: ngày nghỉ chặn cả ngày nên
  đó là thông báo hữu ích hơn cho người dùng.
- **Frontend gom hai kiểu từ chối vào một union có discriminator**
  (`ApiError.detail: {kind:"conflict"|"holiday", …}`) thay vì thêm mảng thứ hai
  song song, để thêm kiểu từ chối sau này không làm phình lớp lỗi.

### Đã thay đổi

**Backend**
- `app/holiday_calendar.py` (mới) — `supported_countries()`, `is_supported()`,
  `holiday_on()`, `holidays_in_range()`.
- `app/models.py` — thêm cột `country VARCHAR(2)` nullable.
- `app/schemas.py` — `country` trong `ScheduleInput`/`ScheduleRead` kèm validator;
  `ScheduleInput.local_range()`; thêm `HolidayHit`, `HolidayDetail`, `CountryRead`.
- `app/routers/schedules.py` — `_reject_holidays()` dùng chung cho `POST` và `PUT`.
- `app/routers/countries.py` (mới) — `GET /api/countries`.
- `migrate.py` — tổng quát hóa thành nhiều bước idempotent, thêm bước cột `country`.
- `app/db.py` — schema guard kiểm tra cả `timezone` lẫn `country`.
- `requirements.in/.txt` — thêm `holidays`.

**Frontend**
- `src/types.ts` — `country` trên `Schedule`/`ScheduleInput`, thêm `Country`,
  `HolidayHit`.
- `src/api.ts` — `RefusalDetail` dạng union, nhận diện body `holiday_conflict`,
  thêm `listCountries()`.
- `src/views.ts` — `countrySelect()`, `countryLabel()`, ô chọn quốc gia trong
  form, dòng "Quốc gia" ở panel chi tiết, `renderError()` xử lý cả hai kiểu từ chối.
- `src/format.ts` — `formatDay()` cho khóa ngày dạng `2026-02-17` (gộp luôn mẹo
  format vốn đang lặp ở tiêu đề nhóm ngày).
- `src/main.ts` — tải danh sách quốc gia một lần khi khởi động.

### Các check đã chạy

| Check | Lệnh | Kết quả |
| --- | --- | --- |
| Backend lint | `ruff check backend` | All checks passed |
| Backend test | `pytest` | **77 passed** (54 cũ + 23 test ngày nghỉ) — không regression |
| Frontend test | `npm test` | **62 passed** (49 cũ + 13 mới) |
| Frontend typecheck / build | `npm run typecheck`, `npm run build` | Sạch / Built OK |
| Migration | chạy `migrate.py` trên bản sao database kiểu Round 2 | thêm cả `timezone` (đổi sang UTC) lẫn `country`, chạy lần hai là no-op |
| **End-to-end thật** | UI thật trong jsdom → backend `:8001` → SQLite | **1 passed** (chi tiết bên dưới) |
| Kiểm chứng bằng curl | 4 request | Tết VN → **409** kèm `Lunar New Year`; cùng ngày với `JP` → **201**; 01/01 08:00 giờ Tokyo với `JP` → **409**; không chọn quốc gia → **201** |

Nội dung bài E2E: ô chọn quốc gia được nạp từ backend (>100 mục, frontend không
hard-code) → tạo lịch mùng 1 Tết với `VN` bị **409**, thông báo hiện "ngày nghỉ
chính thức của Vietnam (VN)", tên `Lunar New Year`, ngày `17/02/2026`, database
vẫn rỗng và form giữ nguyên dữ liệu đã nhập kể cả quốc gia → đổi sang `JP` cùng
ngày đó thì **được tạo**, panel chi tiết hiện "Japan (JP)" → sửa lịch đó sang
01/01 (ngày nghỉ Nhật) bị **409** và bản ghi không đổi → tạo lịch 01/01 08:00 giờ
Tokyo (theo UTC còn là 31/12) vẫn bị **409**, xác nhận ngày nghỉ xét theo giờ địa
phương.

Regression đã chạy lại đầy đủ: toàn bộ test CRUD, timezone và conflict của các
round trước đều pass không sửa gì (ngoài việc bổ sung trường `country` vào dữ
liệu mẫu của test frontend).

### Vấn đề còn tồn tại / lưu ý

1. **Chỉ chặn ngày nghỉ cấp quốc gia**, chưa xét ngày nghỉ theo bang/tỉnh
   (package có hỗ trợ `subdiv`, chưa dùng) và chưa xét cuối tuần.
2. **Chặn cứng, không cho ghi đè.** Không có tùy chọn "vẫn tạo dù là ngày nghỉ" —
   đúng theo yêu cầu, nhưng thực tế nhiều nơi vẫn cần đặt lịch ngày lễ.
3. **Một lịch chỉ gắn được một quốc gia.** Cuộc họp xuyên biên giới liên quan
   nhiều nước thì chưa diễn tả được.
4. **Tên ngày nghỉ chỉ có tiếng Anh** (package hỗ trợ đa ngôn ngữ qua tham số
   `language`, chưa dùng); giao diện còn lại là tiếng Việt.
5. **Danh sách ngày nghỉ được cache trong tiến trình** (`lru_cache`), đối tượng
   của package tự mở rộng dữ liệu theo năm khi tra cứu — về lý thuyết có thể bị
   truy cập đồng thời từ threadpool của FastAPI. Rủi ro thấp với ứng dụng local.
6. **Ô chọn quốc gia liệt kê cả 250 mục**, chưa có tìm kiếm — cùng vấn đề với ô
   chọn múi giờ ở Round 3.
7. Các mục tồn đọng từ Round 1–3 vẫn giữ nguyên.

---

## Round 5 — Support overnight scheduling

**Ngày:** 2026-08-25
**Commit:** `round 05: support overnight scheduling`

### Yêu cầu

Hỗ trợ lịch kéo dài qua nửa đêm (ví dụ 23:30 hôm nay → 01:00 hôm sau). Kiểm tra
cách hệ thống đang xử lý start time, end time, ngày, timezone và conflict
detection; điều chỉnh phần cần thiết; đảm bảo conflict detection vẫn đúng với
lịch qua đêm.

### Audit trước khi sửa

Chạy 12 probe trực tiếp lên API trước khi thay đổi bất cứ thứ gì:

| Trường hợp | Kết quả |
| --- | --- |
| 23:30 → 01:00 hôm sau | 201 |
| Chồng phần sau nửa đêm (00:30–01:30) | 409 |
| Chồng phần trước nửa đêm (23:00–23:45) | 409 |
| Liền kề trước (22:00–23:30) / sau (01:00–02:00) | 201 / 201 |
| Qua ranh giới tháng, năm | 201 |
| Kéo dài 48 giờ | 201 |
| Lịch đêm ở Tokyo vs cùng thời điểm ở Sài Gòn | 409 (đúng) |
| Qua mốc DST spring-forward | 201, offset hai đầu khác nhau |
| `end == start` | 422 |
| Qua nửa đêm vào ngày nghỉ | 409 |

**Kết luận: backend đã đúng hoàn toàn, không cần sửa dòng nào.** Lý do có tính hệ
thống: từ Round 3 mọi thứ lưu và so sánh theo **thời điểm (UTC)**, không có chỗ
nào suy luận theo "ngày". Validation chỉ là `end_time > start_time` (so sánh
datetime, nên 23:30 hôm nay < 01:00 hôm sau), sắp xếp theo `start_time`, và điều
kiện overlap `existing.start < new.end AND existing.end > new.start` không hề
quan tâm hai đầu có cùng ngày hay không. Chuyện "qua nửa đêm" thực ra chỉ là
chuyện hiển thị: lịch 23:30–01:00 giờ Việt Nam được lưu là `16:30–18:00` UTC —
thậm chí không chạm nửa đêm.

Audit tiếp frontend bằng một probe render thì tìm ra **hai khiếm khuyết thật**:

1. **Thẻ trong danh sách gây hiểu nhầm.** Nó chỉ in `23:30 – 01:00`, không có dấu
   hiệu nào cho biết giờ kết thúc thuộc ngày hôm sau — đọc lướt sẽ tưởng lịch kết
   thúc trước khi bắt đầu 22 tiếng rưỡi. (Panel chi tiết thì đã hiện đủ hai ngày.)
2. **Form không giúp tạo lịch qua đêm.** Đổi giờ bắt đầu không kéo theo giờ kết
   thúc, nên muốn tạo lịch 23:30 → 01:00 phải tự sửa cả *ngày* kết thúc; làm theo
   phản xạ (chỉ đổi giờ) sẽ nhận `422 end_time must be after start_time`.

### Đã thay đổi

Chỉ frontend — backend giữ nguyên.

- `src/format.ts` — thêm `dayOffsetInZone()` (đếm số ngày lịch chênh nhau **theo
  múi giờ đang xem**), `wallClockDeltaMinutes()` và `shiftWallClock()`. Hai hàm
  sau tính trên chuỗi wall-clock bằng cách parse như UTC, nên chênh lệch đúng
  bằng cái người dùng thấy trên đồng hồ, không bị múi giờ hay DST của máy chen vào.
- `src/views.ts` — thẻ trong danh sách gắn nhãn `+1` (hoặc `+2`…) khi giờ kết
  thúc rơi sang ngày sau, kèm tooltip ghi đủ khoảng thời gian. Trong form, đổi
  giờ bắt đầu sẽ dời giờ kết thúc để **giữ nguyên độ dài**, nhờ đó giờ kết thúc
  tự chuyển sang ngày hôm sau. Nếu khoảng hiện tại đang không hợp lệ
  (kết thúc ≤ bắt đầu) thì không tự đoán, để nguyên cho người dùng sửa.
- `src/style.css` — style cho nhãn `+1`.
- Gợi ý dưới ô "Kết thúc" ghi rõ có thể rơi vào ngày hôm sau.

Lịch qua đêm vẫn được xếp vào **ngày nó bắt đầu** (không nhân bản sang ngày hôm
sau) — nhân bản một lịch thành hai dòng sẽ gây nhầm hơn là giúp.

### Các check đã chạy

| Check | Lệnh | Kết quả |
| --- | --- | --- |
| Backend lint | `ruff check backend` | All checks passed |
| Backend test | `pytest` | **108 passed** (77 cũ + 31 test overnight) |
| Regression timezone + conflict + holiday | `pytest tests/test_timezones.py tests/test_conflicts.py tests/test_holidays.py` | **61 passed**, không sửa gì |
| Frontend test | `npm test` | **84 passed** (62 cũ + 22 mới) |
| Frontend typecheck / build | `npm run typecheck`, `npm run build` | Sạch / Built OK |
| **End-to-end thật** | UI thật trong jsdom → backend `:8001` → SQLite | **1 passed** (chi tiết bên dưới) |
| Kiểm chứng bằng curl | 5 request | Ca đêm **201**; chồng sau nửa đêm **409**; chồng trước nửa đêm **409**; liền kề hai đầu **201/201**; SQLite lưu `16:30–18:00` UTC |

31 test overnight ở backend phủ: tạo/đọc lịch qua nửa đêm, giữ đúng độ dài thực,
qua ranh giới tháng/năm/cuối tháng 2, khoảng 48 giờ, khoảng 2 phút quanh nửa đêm,
kết thúc đúng 00:00, `end < start` vẫn bị từ chối, thứ tự trong danh sách, sáu
kiểu chồng lấn quanh nửa đêm, bốn kiểu không chồng lấn, hai lịch đêm liên tiếp,
sửa lịch ban ngày thành lịch đêm, lịch đêm không tự xung đột với chính nó, lịch
đêm ở múi giờ này là lịch ban ngày ở múi giờ khác, qua cả spring-forward
(23:30→03:30 chỉ là 3 giờ thực) lẫn fall-back (5 giờ thực), xung đột quanh mốc
DST, và tương tác với ngày nghỉ.

Nội dung bài E2E: mở form, đặt giờ bắt đầu 23:30 → giờ kết thúc **tự nhảy sang
ngày hôm sau** → tạo lịch 23:30–01:00 thành công, API trả đúng hai mốc
`+07:00` → thẻ trong danh sách hiện `23:30 – 01:00` kèm nhãn `+1` và nằm dưới
tiêu đề ngày 20/11 → panel chi tiết hiện đủ hai ngày và "1 giờ 30 phút" → tạo
lịch 00:30–01:30 (sau nửa đêm) bị **409** nêu đúng lịch đêm → 01:00–02:00 (liền
kề) được **201** → chuyển múi giờ xem sang Tokyo thì chính lịch đó hiện thành
01:30–03:00 và **nhãn `+1` biến mất** vì ở Tokyo nó không còn qua nửa đêm.

### Vấn đề còn tồn tại / lưu ý

1. **Lịch qua đêm chỉ xuất hiện dưới ngày bắt đầu.** Người xem lịch ngày 21/11 sẽ
   không thấy lịch đêm 20→21/11 trong nhóm ngày đó. Đây là lựa chọn có chủ ý,
   nhưng một giao diện dạng lưới tuần/tháng sau này sẽ cần vẽ nó trải qua hai ngày.
2. **Không giới hạn độ dài lịch.** Có thể tạo lịch dài nhiều tháng; chưa rõ đó là
   tính năng hay lỗ hổng, nên chưa chặn.
3. **Form chỉ dời giờ kết thúc khi đổi giờ bắt đầu**, không tự cuộn ngày khi người
   dùng đặt giờ kết thúc sớm hơn giờ bắt đầu — trường hợp đó vẫn báo lỗi. Cố đoán
   ý ở chiều này dễ sai hơn là giúp.
4. Các mục tồn đọng từ Round 1–4 vẫn giữ nguyên.

---

## Round 6 — Add scheduling notifications

**Ngày:** 2026-08-25
**Commit:** `round 06: add scheduling notifications`

### Yêu cầu

Bổ sung cơ chế notification: xác định được thời điểm cần gửi thông báo dựa trên
thời gian của lịch. Đủ rõ ràng và chạy được để demo, không cần hệ thống
production. Phải đúng theo thời điểm thực, không sai khi lịch dùng múi giờ khác,
lịch qua nửa đêm vẫn hoạt động, và khi lịch bị sửa/xóa thì notification liên quan
được xử lý hợp lý.

### Notification hiện hoạt động như thế nào

**Quyết định cốt lõi: thời điểm nhắc được _suy ra_, không lưu thành bản ghi riêng.**

```
notify_at = start_time - reminder_minutes
```

`start_time` đang lưu là instant UTC (từ Round 3), nên `notify_at` cũng là một
instant. Đây chính là thứ đáp ứng đồng thời cả bốn yêu cầu, và không phải bằng
bốn đoạn code khác nhau:

| Yêu cầu | Vì sao đúng |
| --- | --- |
| Đúng thời điểm thực | `notify_at` là instant, tính từ instant |
| Không sai với múi giờ khác | Không dùng wall-clock ở bất kỳ đâu; hai lịch cùng giờ địa phương ở hai múi giờ có `notify_at` khác nhau, đúng như instant của chúng |
| Lịch qua nửa đêm | Không có logic nào theo ngày; mốc nhắc có thể nằm ở ngày hôm trước (00:15 nhắc trước 30 phút → 23:45 hôm trước) |
| Sửa/xóa lịch | Sửa → `notify_at` tự dịch theo vì nó là hàm của `start_time`; xóa → mốc nhắc mất cùng dòng dữ liệu. **Không có bảng nào cần đồng bộ.** |

Đã cân nhắc phương án bảng `notifications` riêng và loại: nó buộc phải re-sync
mỗi lần lịch đổi giờ hoặc bị xóa, tức là tự tạo ra đúng loại lỗi mà yêu cầu này
đang muốn tránh — và tốn nhiều máy móc hơn cho một bản demo.

Chỉ một thứ được **lưu**: `notified_at` (lúc đã gửi), để không gửi trùng.

**Cửa sổ thời gian.** Một nhắc "đang chờ" khi chưa gửi *và* lịch chưa bắt đầu;
nó "đến hạn" khi `notify_at <= now < start_time`. Nhắc của lịch đã bắt đầu tự rơi
ra khỏi danh sách chứ không gửi muộn — nhắc người ta về cuộc họp họ đang dự thì vô
nghĩa. Nhờ định nghĩa này không cần thêm trạng thái "hết hạn" hay job dọn dẹp.

**Nạp lại khi bị dời.** Nếu một nhắc đã gửi mà lịch bị dời, hoặc đổi
`reminder_minutes`, hoặc đổi múi giờ khiến instant thay đổi, thì `notified_at`
được xóa để nhắc lại cho mốc mới. Sửa mỗi tiêu đề thì **không** gửi lại. Quy tắc
nằm trong `notifications.reset_if_rescheduled()`, router gọi trước khi ghi đè
giá trị cũ.

**Kênh gửi (demo):** một dòng log phía server —
`INFO: app.notifications - Reminder: 'Họp nhóm' starts at ... (in 30 minutes)`.
Hàm `deliver()` là chỗ duy nhất cần thay khi muốn gắn email/push.

**Hai cách kích hoạt, dùng chung một `dispatch_due()`:**
* **poller nền** trong app, mặc định 30 giây (`NOTIFICATIONS_ENABLED`,
  `NOTIFICATION_POLL_SECONDS`);
* **`POST /api/notifications/dispatch`** để demo ngay, không phải đợi tick.

Thêm `GET /api/notifications` (đang chờ) và `GET /api/notifications/due`.

**Frontend:** form có ô "Nhắc trước" (mặc định 15 phút cho lịch mới), panel chi
tiết hiện dòng `30 phút trước · 10/05/2026 08:30 · chưa gửi`, với mốc nhắc quy
đổi sang **múi giờ đang xem**.

### Một lỗi thật gặp khi làm

Poller chạy đúng ngay từ đầu (`notified_at` được đặt sau 3 giây) nhưng **dòng log
không hiện ra ở đâu cả**: uvicorn chỉ cấu hình logger của chính nó, còn logger
`app.*` không có handler nào nên INFO rơi vào hư không. Với một tính năng mà "cái
gửi đi" chính là dòng log, đó là lỗi làm demo vô nghĩa. Đã thêm
`_configure_logging()` trong lifespan để logger `app` luôn có handler bất kể server
được khởi động bằng cách nào.

### Đã thay đổi

**Backend**
- `app/notifications.py` (mới) — `pending()`, `due()`, `deliver()`,
  `dispatch_due()`, `reset_if_rescheduled()`.
- `app/models.py` — thêm `reminder_minutes`, `notified_at`, và property
  `notify_at` (nơi duy nhất định nghĩa mốc nhắc).
- `app/schemas.py` — `reminder_minutes` ở input (1…40320 phút);
  `reminder_minutes`/`notify_at`/`notified_at` ở output; thêm `NotificationRead`.
- `app/routers/schedules.py` — gọi `reset_if_rescheduled()` khi cập nhật.
- `app/routers/notifications.py` (mới) — 3 endpoint.
- `app/main.py` — poller nền trong `lifespan` (huỷ gọn khi tắt app) và
  `_configure_logging()`.
- `app/config.py`, `.env.example` — `NOTIFICATIONS_ENABLED`,
  `NOTIFICATION_POLL_SECONDS`.
- `migrate.py`, `app/db.py` — bước migration thứ ba và schema guard cho hai cột mới.
- `tests/conftest.py` — tắt poller trong test; test tự gọi dispatch.

**Frontend**
- `src/types.ts`, `src/api.ts` — các trường mới.
- `src/format.ts` — tách `formatMinutes()` (dùng chung với `formatDuration`, và
  nay đọc được "1 ngày").
- `src/views.ts` — `reminderSelect()`, `reminderSummary()`, ô "Nhắc trước" trong
  form, dòng nhắc trong panel chi tiết.

### Các check đã chạy

| Check | Lệnh | Kết quả |
| --- | --- | --- |
| Backend lint | `ruff check backend` | All checks passed |
| Backend test | `pytest` | **141 passed** (108 cũ + 33 test notification) |
| Regression timezone/conflict/holiday/overnight | `pytest` 4 file đó | **92 passed**, không sửa gì |
| Frontend test | `npm test` | **96 passed** (84 cũ + 12 mới) |
| Frontend typecheck / build | `npm run typecheck`, `npm run build` | Sạch / Built OK |
| Migration | `migrate.py` trên database thật | thêm hai cột, lần hai là no-op |
| **Poller nền thật** | server thật, `NOTIFICATION_POLL_SECONDS=2` | `notified_at` được đặt sau 3 giây và log hiện đúng dòng `Reminder: 'Nhắc thử' ...` |
| **End-to-end thật** | UI thật trong jsdom → backend `:8001` → SQLite | **1 passed** (chi tiết bên dưới) |

33 test backend phủ: suy ra `notify_at` (kể cả lead 2 ngày), không nhắc thì không
có mốc, cửa sổ pending/due (tương lai, đúng thời khắc, lịch đã bắt đầu, đã gửi),
thứ tự, dispatch đánh dấu và không gửi trùng, có ghi log, cùng lead ở hai múi giờ
cho hai instant khác nhau, mốc nhắc quy đổi theo múi giờ của lịch, mốc nhắc rơi
sang ngày hôm trước, lịch qua nửa đêm, qua mốc DST, dời lịch/đổi lead/đổi múi giờ
thì nạp lại, sửa mỗi tiêu đề thì không, bỏ nhắc, xóa lịch, validate ngoài khoảng,
và cả ba endpoint.

Nội dung bài E2E: form mặc định 15 phút → tạo lịch cách 2 giờ với nhắc 30 phút,
kiểm tra `notify_at` đúng **chênh chính xác 30 phút so với start theo instant**,
panel hiện "30 phút trước · … · chưa gửi", lịch nằm trong `pending`, chưa `due`,
dispatch không gửi gì → đổi múi giờ xem thì dòng nhắc đổi giờ hiển thị nhưng vẫn
"30 phút trước" → dời lịch sang 5 giờ sau và đổi lead thành 60 phút thì
`notified_at` về null và khoảng cách thành đúng 60 phút → tạo lịch bắt đầu sau 5
phút với lead 30 phút thì nó **đến hạn ngay**, dispatch gửi đúng nó một lần, lần
hai không gửi gì → xóa lịch thì mốc nhắc biến khỏi danh sách.

### Giới hạn hiện tại

1. **Chỉ ghi log ở server.** Chưa có email, push hay hiển thị realtime trên
   frontend — frontend cho *đặt* và *xem* mốc nhắc, nhưng không tự nổi thông báo.
2. **Poller nằm trong tiến trình app.** Chạy nhiều worker/nhiều instance sẽ gửi
   trùng vì không có khóa. Production cần một worker riêng (cron, Celery beat…).
3. **Lọc `due` trong Python**, không phải trong SQL: đơn giản và dễ đọc nhưng
   duyệt toàn bộ lịch còn nhắc chưa gửi, không phù hợp với lượng dữ liệu lớn.
4. **Mỗi lịch chỉ một mốc nhắc.** Muốn "nhắc trước 1 ngày *và* trước 15 phút" thì
   phải chuyển sang danh sách lead time (hoặc bảng riêng).
5. **Nhắc bị bỏ qua khi server tắt sẽ không gửi bù** nếu lúc bật lại lịch đã bắt
   đầu — đúng theo định nghĩa cửa sổ, nhưng nghĩa là không có bảo đảm gửi.
6. **`notified_at` chỉ ghi lúc gửi**, không ghi kết quả gửi (thành công/thất bại)
   vì kênh hiện tại không thể thất bại.
7. Các mục tồn đọng từ Round 1–5 vẫn giữ nguyên.

---

## Round 7 — Add scheduling duration limits

**Ngày:** 2026-08-25
**Commit:** `round 07: add scheduling duration limits`

### Yêu cầu

Thêm giới hạn thời lượng tối thiểu và tối đa cho một lịch. Hai giá trị phải nằm ở
vị trí rõ ràng, dễ thay đổi, không hard-code rải rác. Backend thực thi rule.
Frontend hỗ trợ validation và hiển thị lỗi rõ khi quá ngắn/quá dài. Thời lượng
phải tính đúng với timezone, lịch qua nửa đêm và lịch vắt qua hai ngày. Không làm
hỏng conflict detection hay notification.

### Quyết định

- **Giới hạn nằm trong `Settings`** (`app/config.py`), override bằng
  `MIN_DURATION_MINUTES` / `MAX_DURATION_MINUTES`. Đây đã là chỗ chứa mọi tham số
  cấu hình khác của dự án nên không phát sinh cơ chế mới. Có validator bảo đảm
  `1 <= min < max` để cấu hình sai bị chặn ngay lúc khởi động.
- **Frontend không lặp lại hai con số**: thêm `GET /api/config` trả về giới hạn
  (và múi giờ mặc định). Frontend đọc lúc khởi động để hiện gợi ý trong form và
  chặn sớm trước khi gửi. Backend vẫn là bên quyết định — có test gửi thẳng vào
  API bỏ qua UI để chứng minh.
- **Mặc định 15 phút – 7 ngày.** 15 phút là slot họp tối thiểu quen thuộc; 7 ngày
  giữ được lịch nhiều ngày mà Round 5 đã cố tình hỗ trợ (nếu chọn 24 giờ thì hoá
  ra đi ngược lại tính năng vừa làm), đồng thời vẫn chặn được lịch dài vô lý.
- **Trả `422`, không phải `409`.** Độ dài chỉ phụ thuộc vào chính request, không
  phụ thuộc dữ liệu đang có — đúng nghĩa "well-formed nhưng không xử lý được".
  `409` vẫn dành cho xung đột với trạng thái hiện có (trùng lịch, ngày nghỉ).
  Body vẫn có cấu trúc (`code`, `message`, `duration_minutes`, `min_minutes`,
  `max_minutes`) như hai loại từ chối kia, nên frontend xử lý thống nhất.
- **Thứ tự kiểm tra: thời lượng → ngày nghỉ → trùng lịch.** Thời lượng đứng trước
  vì nó chỉ cần chính request, và lịch sai độ dài thì không khung giờ nào cứu được.
- **Đo giữa hai instant**, tức thời lượng thực. Điều này khiến rule tự đúng với
  timezone, lịch qua nửa đêm và lịch vắt hai ngày — không cần code riêng cho từng
  trường hợp. Quanh DST thì đồng hồ treo tường nói dối: 01:50 → 03:00 ngày
  spring-forward ở New York đọc như 70 phút nhưng chỉ **10 phút** thực trôi qua và
  bị từ chối.

### Đã sửa ba test cũ — có chủ ý

Bất kỳ giá trị min nào có ý nghĩa cũng làm một số test cũ trở thành không hợp lệ,
vì chúng dùng dải 1–2 phút để dò biên overlap:

| Test | Trước | Sau | Ý đồ giữ nguyên |
| --- | --- | --- | --- |
| `test_conflicts` | 08:59–09:01 | 08:45–09:01 | vẫn chồng đúng 1 phút ở đầu |
| `test_overnight` | 23:59–00:01 | 23:50–00:10 | vẫn là khoảng ngắn ôm nửa đêm |
| `test_overnight` | 00:00–00:01 | 00:00–00:20 | vẫn bắt đầu đúng thời khắc nửa đêm |

Đây là thay đổi hành vi có chủ ý, không phải test bị hỏng.

### Một lỗi thật phát hiện khi chạy E2E

Bài E2E lộ ra rằng sau khi lịch bị từ chối, form **mất sạch dữ liệu đã nhập** —
nhưng chỉ trong một cửa sổ hẹp ngay sau khi trang tải xong. Nguyên nhân:
`refresh()` khi thành công xoá cả `state.error` **và `state.draft`**; nếu lần tải
nền kết thúc đúng lúc người dùng vừa bị từ chối thì bản nháp bị xoá theo. Bản
nháp thuộc về form chứ không thuộc về lần tải, nên đã bỏ dòng xoá `state.draft`
trong `refresh()` (`setView()` vẫn xoá khi chuyển màn hình).

### Đã thay đổi

**Backend**
- `app/config.py` — `min_duration_minutes`, `max_duration_minutes` + validator.
- `app/schemas.py` — `DurationDetail`, `LimitsRead`.
- `app/routers/schedules.py` — `_reject_bad_duration()` dùng chung cho `POST` và
  `PUT`, chạy trước hai rule kia; khai báo `422` trong OpenAPI.
- `app/routers/config.py` (mới) — `GET /api/config`.
- Đổi `HTTP_422_UNPROCESSABLE_ENTITY` sang `HTTP_422_UNPROCESSABLE_CONTENT` (hằng
  cũ đã deprecated trong Starlette).

**Frontend**
- `src/types.ts`, `src/api.ts` — kiểu `Limits`, `fetchLimits()`, thêm nhánh
  `duration` vào `RefusalDetail`.
- `src/views.ts` — `renderError()` xử lý lỗi thời lượng; gợi ý dưới ô "Kết thúc"
  nêu đúng giới hạn backend đang áp dụng.
- `src/main.ts` — nạp giới hạn lúc khởi động, `checkDuration()` chặn sớm trước
  khi gửi, và không còn xoá bản nháp trong `refresh()`.

### Các check đã chạy

| Check | Lệnh | Kết quả |
| --- | --- | --- |
| Backend lint | `ruff check backend` | All checks passed |
| Backend test | `pytest` | **175 passed** (141 cũ + 34 test thời lượng) |
| Regression conflict/notification/timezone/overnight/holiday | `pytest` 5 file đó | **125 passed** |
| Frontend test | `npm test` | **103 passed** (96 cũ + 7 mới) |
| Frontend typecheck / build | `npm run typecheck`, `npm run build` | Sạch / Built OK |
| **End-to-end thật** | UI thật trong jsdom → backend `:8001` → SQLite | **1 passed** (chi tiết bên dưới) |
| Kiểm chứng bằng curl | 4 request + `/api/config` | 15 phút → **201**; 14 phút → **422** kèm `duration_out_of_range`; 7 ngày → **201**; 7 ngày 1 phút → **422** |

Bốn trường hợp yêu cầu nêu rõ đều có test riêng:

* **đúng minimum** — `test_exactly_the_minimum_is_accepted` (201);
* **đúng maximum** — `test_exactly_the_maximum_is_accepted` (201);
* **dưới minimum** — `test_one_minute_under_the_minimum_is_rejected` cùng
  parametrize 1 phút / 2 phút / `MIN-1`;
* **trên maximum** — `test_one_minute_over_the_maximum_is_rejected` cùng
  parametrize `MAX+1` / `MAX*2` / một năm.

Ngoài ra: không ghi gì khi bị từ chối, thu hẹp/kéo dài quá giới hạn khi sửa lịch,
`end < start` vẫn là lỗi validation thường chứ không phải lỗi thời lượng, và ba
test khẳng định conflict / holiday / notification vẫn hoạt động nguyên vẹn.

Nội dung bài E2E: form nêu sẵn "Thời lượng từ 15 phút đến 7 ngày" → gửi lịch 5
phút thì hiện "Lịch quá ngắn: 5 phút." kèm khoảng cho phép, database vẫn rỗng và
dữ liệu đã nhập được giữ lại → gửi lịch 19 ngày thì hiện "Lịch quá dài" → lịch
đúng 15 phút được tạo, panel hiện "15 phút" → lịch đúng 7 ngày được tạo, panel
hiện "7 ngày" → gọi thẳng API bỏ qua UI với lịch 10 phút vẫn nhận **422** → lịch
01:50→03:00 đêm DST ở New York bị **422** với `duration_minutes = 10`.

### Vấn đề còn tồn tại / lưu ý

1. **Kiểm tra sớm ở frontend so sánh theo giờ treo tường**, nên quanh mốc DST nó
   có thể lệch với thời lượng thực: đêm lùi giờ, một lịch 01:55 → 02:00 đọc là 5
   phút (frontend chặn) nhưng thực tế dài 65 phút và backend sẽ chấp nhận. Backend
   vẫn là nguồn quyết định; chấp nhận đánh đổi này thay vì đưa phép tính offset
   vào frontend.
2. **Giới hạn là toàn cục**, không theo loại lịch hay theo người dùng.
3. **Đổi giới hạn không ảnh hưởng lịch đã lưu**: lịch cũ nằm ngoài khoảng mới vẫn
   tồn tại, chỉ không sửa được nếu không đưa độ dài về trong khoảng.
4. **`GET /api/config` đọc lúc tải trang**; đổi cấu hình khi tab đang mở thì
   frontend chưa biết cho tới khi tải lại.
5. Các mục tồn đọng từ Round 1–6 vẫn giữ nguyên.
