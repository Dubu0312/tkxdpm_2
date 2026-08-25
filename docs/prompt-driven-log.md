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

---

## Round 8 — Integrate Google Calendar

**Ngày:** 2026-08-25
**Commit:** `round 08: integrate Google Calendar`

### Yêu cầu

Cho phép lịch trong ứng dụng đồng bộ với Google Calendar: authentication, tạo
event, liên kết event với lịch trong SQLite, cập nhật khi lịch thay đổi, xử lý
khi lịch bị xóa, và tránh tạo duplicate khi sync nhiều lần. Thời gian gửi sang
Google phải giữ đúng timezone và thời điểm thực. Nếu chưa có credential thật thì
project vẫn phải chạy local. Không commit secret, OAuth token hay credential.

### Thiết kế

**Một interface, ba chế độ** (`GOOGLE_CALENDAR_MODE`):

| Chế độ | Vai trò |
| --- | --- |
| `disabled` (mặc định) | Không tích hợp. App chạy đầy đủ; endpoint sync trả `503` kèm đúng câu cần làm gì để bật. Đây là trạng thái của một lần clone sạch. |
| `memory` | Bản mô phỏng trong tiến trình, **cùng luật** insert/update/delete với API thật. Nhờ nó toàn bộ luồng demo được và test được mà không cần credential. Được gọi tên trung thực trong `/api/config/google`: "không phải Google Calendar thật". |
| `google` | Google Calendar API thật, OAuth. |

**Chống trùng event — hai lớp.** Lớp một: lịch lưu `google_event_id`, sync lần
sau là *update*. Lớp hai, quan trọng hơn: **id event được suy ra từ id lịch**
(`tkdpm{id}`), nên ngay cả khi liên kết ở local bị mất thì lệnh insert cũng va
chạm với event cũ và được chuyển thành update — không thể sinh ra event thứ hai.
Chiều ngược lại cũng được xử lý: nếu event bị xóa bên Google thì update báo
"không tìm thấy" và nó được tạo lại. Cả hai nhánh đều có test.

Google chỉ chấp nhận id gồm ký tự base32hex (`0-9`, `a-v`) — nên tiền tố mặc định
là `tkdpm` chứ không phải `tkxdpm` (`x` không hợp lệ), và có validate báo lỗi rõ
nếu ai đó đổi tiền tố thành chuỗi không hợp lệ.

**Thời gian.** Event gửi đi mang `dateTime` kèm offset **và** `timeZone` là tên
IANA — cùng thứ mà API của app vẫn trả về. Google vì thế nhận đủ cả thời điểm
thực lẫn múi giờ gốc. Có test cho múi giờ khác nhau, lịch qua nửa đêm, và đêm
DST (hai đầu mang hai offset khác nhau).

**Sync là opt-in theo từng lịch**, nhưng **lịch đã liên kết thì tự cập nhật** khi
bị sửa. Sửa một lịch chưa liên kết thì không tự đẩy lên Google — người dùng chưa
yêu cầu điều đó.

**Khi đẩy thất bại**: bản sửa ở local vẫn đứng vững, chỉ có `google_out_of_date`
bật lên (suy ra từ `updated_at > google_synced_at`) để giao diện mời đồng bộ lại.
Lệch nhau nhưng **nhìn thấy được**, thay vì im lặng.

**Khi xóa lịch**: xóa event Google trước, nhưng nếu không gọi được Google thì vẫn
xóa ở local và ghi cảnh báo — không được để một dịch vụ ngoài chặn người dùng xóa
lịch của chính họ. Đánh đổi: có thể còn event mồ côi bên Google.

**Credential**: OAuth Desktop app. `google_auth.py` chạy consent flow một lần và
ghi token vào `secrets/`. Cả `secrets/*` đều bị git-ignore (chỉ giữ lại
`secrets/README.md` giải thích chỗ đó chứa gì), cộng thêm `*token*.json` và
`client_secret*.json` ở mọi vị trí. Thư viện Google được import **lazy** để app
vẫn khởi động khi thiếu chúng.

### Một lỗi thật gặp khi làm

Sau khi sync xong, lịch lập tức bị đánh dấu `google_out_of_date`. Nguyên nhân:
chính thao tác ghi các cột liên kết cũng kích hoạt `onupdate` của `updated_at`,
nên `updated_at` luôn mới hơn `google_synced_at` vài micro giây. Về mặt ngữ nghĩa
thì sync **không phải** là thay đổi nội dung lịch, nên lời giải là ghi lại giá
trị `updated_at` cũ. Nhưng gán lại **cùng một giá trị** thì SQLAlchemy coi là
không đổi và `onupdate` vẫn chạy — phải `flag_modified()` để buộc cột đó vào câu
UPDATE. Chi tiết nhỏ nhưng nếu không xử lý thì mọi lịch vừa sync đều hiện "cần
đồng bộ lại".

Ngoài ra một lần `str.replace` sửa `views.ts` không khớp (chuỗi neo nằm trên
nhiều dòng) nên **im lặng không làm gì** — dòng "Google Calendar" không xuất hiện
trong panel. Bài E2E bắt được; từ đó có kiểm tra lại kết quả replace.

### Đã thay đổi

**Backend**
- `app/google_calendar.py` (mới) — protocol `CalendarClient`, ba client, ngoại lệ
  riêng, `event_id_for()`, `event_body()`, `push()`, `remove()`.
- `app/models.py` — `google_event_id`, `google_calendar_id`, `google_synced_at`,
  property `google_out_of_date`.
- `app/schemas.py` — các trường trên trong `ScheduleRead`, thêm `GoogleStatusRead`.
- `app/routers/schedules.py` — `POST`/`DELETE /{id}/google`, tự đẩy khi sửa lịch
  đã liên kết, xóa event khi xóa lịch, `_save_google_link()` giữ `updated_at`.
- `app/routers/config.py` — `GET /api/config/google`.
- `app/config.py` — 5 setting mới; `google_auth.py` — consent flow một lần.
- `migrate.py`, `app/db.py` — bước migration thứ tư và schema guard.
- `requirements` — `google-api-python-client`, `google-auth-oauthlib`.
- `.gitignore` — `secrets/*`, `*token*.json`, `client_secret*.json`.

**Frontend**
- `src/types.ts`, `src/api.ts` — trường liên kết, `GoogleStatus`,
  `fetchGoogleStatus()`, `syncToGoogle()`, `unlinkFromGoogle()`.
- `src/views.ts` — `googleSummary()`, dòng "Google Calendar" trong panel, nút
  "Đồng bộ Google" / "Đồng bộ lại" / "Bỏ liên kết", và ghi chú giải thích khi
  tích hợp đang tắt (thay vì ẩn tính năng đi không nói gì).
- `src/main.ts` — nạp trạng thái Google lúc khởi động, nối hai hành động.

### Các check đã chạy

| Check | Lệnh | Kết quả |
| --- | --- | --- |
| Backend lint | `ruff check backend` | All checks passed |
| Backend test | `pytest` | **206 passed** (175 cũ + 31 test Google) |
| Regression 6 file của các round trước | `pytest` | **159 passed**, không sửa gì |
| Frontend test | `npm test` | **113 passed** (103 cũ + 10 mới) |
| Frontend typecheck / build | `npm run typecheck`, `npm run build` | Sạch / Built OK |
| Migration | `migrate.py` trên database thật | thêm ba cột, lần hai no-op |
| Chạy không có credential | mặc định `disabled` | app hoạt động đầy đủ; `/api/config/google` báo `enabled: false` kèm hướng dẫn; sync trả **503** |
| `google_auth.py` khi thiếu client secret | chạy thử | báo đúng đường dẫn cần đặt file và cách tạo OAuth client, thoát mã 1 |
| **End-to-end thật** | UI thật → backend `:8001` (mode `memory`) → SQLite | **1 passed** (chi tiết bên dưới) |

31 test backend phủ: chạy được khi tắt tích hợp, `503` với thông điệp hữu ích,
trạng thái ba chế độ, tạo event và lưu liên kết, các trường tùy chọn, không gửi
key rỗng, offset + tên vùng, hai múi giờ khác nhau, lịch qua nửa đêm, đêm DST,
sync hai lần / năm lần không sinh event mới, **mất liên kết vẫn không tạo trùng**,
event bị xóa bên Google thì tạo lại, hai lịch thì hai event, id không hợp lệ báo
lỗi, sửa lịch đã liên kết thì event đổi theo (tiêu đề, giờ, múi giờ), sửa lịch
chưa liên kết thì không tạo gì, đẩy thất bại thì bản sửa vẫn đứng và cờ
`google_out_of_date` bật, xóa lịch thì xóa event, xóa được cả khi Google hỏng,
bỏ liên kết rồi sync lại dùng đúng id cũ.

Nội dung bài E2E: tạo lịch giờ Tokyo qua form → panel hiện "Chưa đồng bộ" và chỉ
có nút "Đồng bộ Google" → bấm sync, panel chuyển sang "Đã đồng bộ" và hiện thêm
"Đồng bộ lại" + "Bỏ liên kết", `google_event_id` = `tkdpm{id}` → bấm đồng bộ lại
thì id **không đổi** → sửa lịch qua form (đổi tiêu đề và giờ) thì cùng event được
cập nhật, `google_out_of_date` vẫn `false`, giờ mới trả về `+09:00` đúng Tokyo →
bấm "Bỏ liên kết" thì quay lại "Chưa đồng bộ" và `google_event_id` là `null` →
sync lại rồi xóa lịch thì xóa được (204).

### Giới hạn hiện tại

1. **Nhánh `google` thật chưa được chạy tự động.** Toàn bộ test dùng bản mô
   phỏng `memory`; code gọi API thật đã viết đủ và có hướng dẫn cấu hình, nhưng
   chưa được chạy với credential thật trong round này. Đây là giới hạn cần nói
   thẳng, không phải "đã kiểm chứng".
2. **Đồng bộ một chiều** (app → Google). Sửa event bên Google không quay ngược
   về app; muốn hai chiều cần webhook/watch channel và xử lý xung đột.
3. **Không có hàng đợi hay retry.** Đẩy thất bại thì chỉ bật cờ `google_out_of_date`
   và chờ người dùng bấm lại.
4. **Xóa lịch có thể để lại event mồ côi** nếu lúc đó không gọi được Google —
   đánh đổi có chủ ý để không chặn thao tác xóa.
5. **Một tài khoản Google cho cả app**, chưa có khái niệm người dùng, nên chưa
   phân biệt được ai sync sang calendar nào.
6. **Reset database làm id lịch chạy lại từ 1**, nên id event suy ra có thể trùng
   với event cũ trên cùng calendar và sẽ *cập nhật* event cũ thay vì tạo mới.
   Chấp nhận được với ứng dụng local; nếu cần chắc chắn thì thêm một mã cài đặt
   ngẫu nhiên vào tiền tố.
7. Các mục tồn đọng từ Round 1–7 vẫn giữ nguyên.

---

## Round 9 — Review and stabilize

**Ngày:** 2026-08-25
**Commit:** `round 09: review and stabilize scheduling application`

### Yêu cầu

Review toàn bộ ứng dụng như một sản phẩm hoàn chỉnh: tìm bug, regression, logic
không nhất quán giữa các tính năng, lỗi tích hợp frontend/backend, lỗi database,
lỗi runtime ở các luồng chính. Chỉ sửa những gì thực sự phát hiện được; không
thêm feature, không đổi scope, không refactor lớn.

### Cách review

Không chỉ đọc code mà **chạy để dò**. Bốn nhóm probe (đều là script tạm, đã xóa
sau khi dùng):

1. **So sánh schema** giữa database do `create_all` tạo và database đi qua
   `migrate.py` từng bước — cột, kiểu, index, CHECK constraint.
2. **Probe biên và liên tính năng** trên API thật: thời lượng ở mức giây, xung
   đột ở mức giây, PUT bị từ chối có ghi một phần không, country lạ, tiêu đề
   quá dài, timezone không hợp lệ.
3. **Đối chiếu contract** giữa `frontend/src/types.ts` và `openapi.json`.
4. **Probe luồng hỏng ở frontend** trong jsdom: backend chết lúc khởi động,
   server trả 500, server trả body không phải JSON.

### Lỗi phát hiện và đã sửa

**1. Database migrate thiếu index (`ix_schedules_start_time`)**
`ALTER TABLE` chỉ thêm cột, nên database nâng cấp dần qua các round **không bao
giờ** có index trên `start_time` — đúng cột mà mọi truy vấn kiểm tra xung đột và
sắp xếp danh sách dựa vào. Hai cách dựng schema cho ra hai kết quả khác nhau.
→ `migrate.py` thêm bước tạo index còn thiếu (`CREATE INDEX IF NOT EXISTS`), và
có test so sánh **cột + index** giữa hai đường dựng schema.

**2. Giới hạn thời lượng so sánh trên số phút đã làm tròn**
`round(seconds/60)` khiến lịch **14 phút 31 giây** làm tròn thành 15 và lọt qua
mức tối thiểu 15 phút; tương tự **7 ngày + 30 giây** lọt qua mức tối đa. Rule
được quảng cáo là 15 phút nhưng thực tế là 14,5 phút.
→ So sánh trực tiếp trên `timedelta`. Con số báo về được làm tròn **xuống** khi
quá ngắn và **lên** khi quá dài, nên thông báo không bao giờ tự mâu thuẫn kiểu
"15 minutes, below the minimum of 15".

**3. Gửi notification làm lịch đã sync bị báo nhầm "cần đồng bộ lại"**
Đánh dấu `notified_at` cũng kích hoạt `onupdate` của `updated_at`, mà
`google_out_of_date` lại suy ra từ `updated_at > google_synced_at`. Kết quả:
cứ mỗi lần nhắc được gửi, lịch đã đồng bộ lại hiện "cần đồng bộ lại" dù không ai
sửa gì. Đúng loại lỗi đã sửa ở Round 8 nhưng đi qua đường khác.
→ Tách thành helper dùng chung `preserve_updated_at()` trong `models.py`, dùng cả
ở `notifications.dispatch_due()` lẫn `_save_google_link()`. Ghi cột bookkeeping
không phải là sửa nội dung lịch.

**4. Backend chết lúc khởi động thì danh sách kẹt ở "Đang tải…" vĩnh viễn**
Trong `refresh()`, `fail()` render lại **trước khi** `finally` kịp tắt cờ
`loading`, nên danh sách đứng nguyên ở placeholder trong khi banner lỗi hiện ở
trên. Người dùng thấy hai thông điệp mâu thuẫn và không có cách nào thoát ngoài
tải lại trang.
→ Tắt cờ `loading` trước khi render lỗi.

**5. Phản hồi 200 nhưng không phải JSON làm lộ lỗi parser thô**
Nếu `VITE_API_BASE_URL` trỏ nhầm (ví dụ vào chính dev server của Vite) thì client
nhận HTML kèm 200 và người dùng thấy `SyntaxError: Unexpected token '<'`.
→ Bọc bước parse ở nhánh thành công, báo đúng nguyên nhân và nhắc kiểm tra
`VITE_API_BASE_URL`.

**Cách kiểm chứng:** cả 5 lỗi đều có test hồi quy, và tôi đã **tạm gỡ phần sửa
rồi chạy lại** để chắc chắn test thật sự bắt được lỗi: 8/16 test backend mới và
2/5 test frontend mới fail trên code chưa sửa, tất cả pass sau khi sửa.

### Những chỗ đã kiểm tra và **không** có vấn đề

Ghi lại để lần sau không phải dò lại:

* Cột và kiểu dữ liệu giữa `create_all` và `migrate.py` khớp nhau; CHECK
  constraint `end_time > start_time` có ở cả hai; chạy migrate lần hai là no-op.
* Contract frontend/backend: mọi field trong `types.ts` đều tồn tại trong
  `openapi.json` và ngược lại, không thừa không thiếu; 11 route đều đúng.
* PUT bị từ chối (thời lượng, ngày nghỉ, trùng lịch) **không** ghi một phần vào
  database và **không** đẩy gì lên Google.
* Xóa lịch dọn sạch cả nhắc lẫn event Google.
* Sync hai lần không tạo event thứ hai; sync được cả lịch trong quá khứ.
* Lịch đã gửi nhắc rồi bị dời thì được nạp lại để nhắc cho mốc mới.
* Xung đột ở mức giây (chồng đúng 1 giây) vẫn bị bắt.
* `country` chấp nhận chữ thường, tiêu đề 200 ký tự unicode qua được, 201 ký tự
  bị chặn, timezone rỗng hoặc dạng offset thuần bị chặn.
* Không có unhandled promise rejection nào trong các luồng hỏng ở frontend; form
  vẫn giữ dữ liệu khi server trả 500.

### Các check đã chạy

| Check | Lệnh | Kết quả |
| --- | --- | --- |
| Backend lint | `ruff check backend` | All checks passed |
| Backend test | `pytest` | **222 passed** (206 cũ + 16 test hồi quy) |
| Frontend test | `npm test` | **118 passed** (113 cũ + 5 test hồi quy) |
| Frontend typecheck / build | `npm run typecheck`, `npm run build` | Sạch / Built OK |
| Kiểm chứng test bắt được lỗi | tạm gỡ fix rồi chạy lại | 8 backend + 2 frontend test fail đúng như mong đợi |
| Migration trên database thật | `migrate.py` | tạo nốt index còn thiếu, chạy lần hai no-op |
| **Smoke end-to-end 9 bước** | server thật, `memory` + poller 2s | CRUD/timezone, trùng chéo múi giờ **409**, 14m31s **422** với số liệu đúng, Tết **409**, qua nửa đêm **201**, sync hai lần cùng một event, poller gửi nhắc mà `out_of_date` **vẫn false**, xóa **204**, database sạch |

### Vấn đề còn tồn tại

Những điều dưới đây đã biết và **có chủ ý không sửa trong round này**, vì sửa
chúng là thêm feature hoặc đổi kiến trúc:

1. **Khi backend không kết nối được lúc khởi động**, form vẫn mở được nhưng danh
   sách quốc gia rỗng và không có gợi ý giới hạn thời lượng; không có nút thử
   lại, phải tải lại trang. Đã hết kẹt ở "Đang tải…" nhưng trải nghiệm vẫn nghèo.
2. **Kiểm tra thời lượng sớm ở frontend vẫn so theo giờ treo tường**, nên quanh
   mốc DST có thể lệch với backend (đã ghi từ Round 7). Backend vẫn là bên quyết
   định — và giờ đã chính xác tới từng giây.
3. **Race condition lý thuyết** khi kiểm tra trùng lịch (Round 2) vẫn còn: kiểm
   tra và ghi không nằm trong một khóa.
4. **Poller nhắc nằm trong tiến trình app**, chạy nhiều worker sẽ gửi trùng.
5. **Nhánh Google thật vẫn chưa được chạy với credential thật**; chỉ nhánh
   `memory` được phủ test.
6. **Không có phân trang** cho `GET /api/schedules`, và `notifications.pending()`
   lọc trong Python — cùng một giới hạn về quy mô dữ liệu.
7. **Cảnh báo deprecation** của Starlette TestClient (`httpx` → `httpx2`) vẫn còn.
8. Danh sách chọn múi giờ (~420 mục) và quốc gia (250 mục) vẫn chưa có tìm kiếm.

---

## Round 10 — Improve application UI and UX

**Ngày:** 2026-08-25
**Commit:** `round 10: improve application UI and UX`

### Yêu cầu

Cải thiện frontend cho hiện đại, chuyên nghiệp, rõ ràng, dễ dùng: bố cục, typography,
spacing, hierarchy, form, danh sách, chi tiết, các action, trạng thái loading/empty/
success/error, thông báo lỗi thân thiện, responsive, interaction vừa phải. Không đổi
business logic, không đổi API contract, không thêm feature, không over-engineer.

### Review UI/UX hiện trạng

Đọc lại toàn bộ frontend rồi liệt kê điểm yếu cụ thể, không sửa theo cảm tính:

1. **Không có phản hồi thành công nào.** Tạo, sửa, xóa, đồng bộ đều im lặng; kênh
   phản hồi duy nhất là banner lỗi.
2. **`window.confirm` cho thao tác xóa** — hộp thoại hệ điều hành, lạc lõng.
3. **Panel chi tiết là một `<dl>` phẳng 7 dòng cùng trọng số**, kể cả các dòng "—"
   cho trường rỗng; thời gian (thứ quan trọng nhất) chỉ là một dòng chữ thường.
4. **Form 8 trường xếp thẳng**, không nhóm, dấu `*` gõ thẳng vào nhãn.
5. **Empty state một câu**, không có lối đi tiếp.
6. **Loading chỉ là chữ "Đang tải…"**; nút bấm không có trạng thái đang xử lý.
7. **Một số thông báo lỗi còn là tiếng Anh của backend** (`Schedule not found`,
   `Value error, end_time must be after start_time`).
8. **Chỉ một breakpoint**, và trên màn hình hẹp chọn lịch không đưa panel vào tầm nhìn.
9. **Thẻ lịch không thể hiện** lịch có nhắc / có quốc gia / đã đồng bộ Google.
10. Không có hover/focus/transition nào.

### Đã cải thiện

**Hệ thống thị giác** — viết lại `style.css` thành một design system nhỏ: token màu
(neutral, brand, success/danger/warning), thang spacing, radius, shadow, type scale;
đủ cả light và dark. Mọi component dùng chung token, nên giao diện nhất quán.

**App shell** — header dính (sticky) có brand mark, tiêu đề và một dòng mô tả app;
ô chọn múi giờ và nút "Tạo lịch" nằm cùng hàng; cột danh sách có tiêu đề riêng và
số lượng; vùng toast riêng có `role="status"`.

**Danh sách** — thẻ lịch chuyển sang bố cục hai cột: cột giờ cố định bề rộng (giờ
thẳng hàng suốt danh sách, có vạch ngăn) và cột nội dung; thêm hàng badge cho
nhắc trước / quốc gia / trạng thái Google (badge cảnh báo khi lịch đã đổi sau lần
đồng bộ cuối). Nhãn `+1` cho lịch qua nửa đêm thành chip.

**Chi tiết** — tiêu đề, hàng chip tóm tắt (múi giờ, quốc gia, nhắc, Google), rồi
**khối "khi nào"** nổi bật vì đó là thứ người ta cần trước tiên, sau đó mới tới các
dòng chi tiết. **Chỉ hiện dòng nào có nội dung** — một cột toàn "—" là nhiễu chứ
không phải thông tin. Nút xóa tách sang phải, khỏi nhóm hành động thường.

**Form** — chia thành nhóm "Thời gian" và "Chi tiết" có tiêu đề; hai ô bắt đầu/kết
thúc đặt cạnh nhau; dấu bắt buộc thành phần tử riêng có tooltip thay vì gõ vào nhãn;
thêm dòng dẫn nhập dưới tiêu đề form.

**Trạng thái** — skeleton khi tải lần đầu (thay chữ "Đang tải…"), empty state có
icon + lời mời + nút "Tạo lịch", toast xác nhận sau mỗi thao tác thành công (tự tắt
sau 4 giây), nút bị vô hiệu hóa khi thao tác đang chạy.

**Xóa** — hỏi ngay trong panel bằng một khối cảnh báo có "Xóa lịch này" / "Giữ lại",
bỏ hẳn `window.confirm`.

**Thông báo lỗi** — thêm `friendlyMessage()` dịch các cách diễn đạt đã biết của
backend sang tiếng Việt hành động được ("Thời gian kết thúc phải sau thời gian bắt
đầu.", "Lịch này không còn tồn tại…"), giữ chi tiết kỹ thuật làm dòng phụ cho lỗi
5xx và 503. Thông điệp vốn đã viết cho người dùng thì đi thẳng qua, không bị dịch lại.

**Responsive** — hai breakpoint (900px gộp cột, 560px thu gọn header, ẩn nhãn phụ,
facts xuống một cột, nút hành động giãn đều); trên màn hình hẹp, chọn một lịch sẽ
cuộn panel vào tầm nhìn.

### Ba lỗi giao diện phát hiện **nhờ chụp màn hình thật**

Chrome có sẵn trên máy nên tôi chụp giao diện thật và tự xem, thay vì chỉ đọc CSS:

1. **Panel rỗng có hai khung viền lồng nhau** — `.panel--placeholder` và
   `.emptystate` bên trong đều vẽ viền.
2. **Ô "Bắt đầu" cao gấp đôi ô "Kết thúc"** — ô bên cạnh có hint 2 dòng, mà grid
   item mặc định `stretch` nên input bị kéo giãn theo.
3. **Banner lỗi co lại theo nội dung rồi tự căn giữa** thay vì thẳng hàng với layout
   — `#app` là flex column, `margin: auto` trên flex item làm co item lại.

Không lỗi nào trong ba lỗi này lộ ra qua test hay qua đọc code; chỉ nhìn mới thấy.
Ảnh sau khi sửa xác nhận cả ba đã hết. Ngoài ra ảnh mobile lộ một lỗi nội dung:
placeholder ghi "danh sách **bên trái**" trong khi ở màn hình hẹp panel nằm **bên
dưới** — đã sửa thành câu không nói hướng.

### Các check đã chạy

| Check | Lệnh | Kết quả |
| --- | --- | --- |
| Frontend typecheck | `npm run typecheck` | Sạch (strict) |
| Frontend test | `npm test` | **139 passed** (120 cũ + 19 mới cho các hành vi UI mới) |
| Frontend build | `npm run build` | Built OK (CSS 11.6 kB / 3.1 kB gzip, JS 20.5 kB / 7.2 kB gzip) |
| Backend lint | `ruff check backend` | All checks passed |
| Backend test | `pytest` | **222 passed** — không đụng tới backend, không regression |
| **Luồng chính trên markup thật** | UI thật (đọc từ `index.html`) → backend thật | **1 passed**: empty state → mở form (đúng 2 nhóm, 4 dấu bắt buộc) → tạo lịch → toast "Đã tạo lịch" → thẻ hiện giờ + badge nhắc → panel hiện khối "khi nào" và **không** hiện dòng rỗng → đồng bộ Google → toast + chip "đã đồng bộ" → lưu lịch quá ngắn bị chặn, thông báo rõ, form giữ nguyên dữ liệu → sửa lại và lưu được → xóa hỏi trong panel, "Giữ lại" hủy được, "Xóa lịch này" xóa thật |
| **Kiểm tra bằng mắt** | Chrome headless, ảnh thật | desktop 1280×900 (sáng và tối), form, panel chi tiết, hộp xác nhận xóa, mobile 390×844 |

Test frontend mới phủ: empty state có/không có CTA, skeleton ẩn khỏi screen reader,
badge trên thẻ (không có gì / nhắc + quốc gia + Google / cảnh báo lệch), xác nhận
xóa trong panel (hiện đúng lúc, đúng nội dung, hai nút tách biệt), nút bị khóa khi
bận, `friendlyMessage` cho từng nhóm lỗi, toast, và bốn luồng chạy qua `main.ts`
thật (skeleton lúc tải, xóa không dùng hộp thoại trình duyệt, hủy xác nhận, toast
sau khi đồng bộ Google).

### Giới hạn và vấn đề còn tồn tại

1. **Không có bộ test tự động cho phần nhìn** (visual regression). Ảnh chụp là kiểm
   tra thủ công một lần trong round này, không được giữ lại để so sánh về sau.
2. **Ô chọn múi giờ (~420 mục) và quốc gia (250 mục) vẫn là `<select>` thuần**, chưa
   có tìm kiếm — làm combobox có lọc là thêm hẳn một component, vượt mức "không
   over-engineer" của round này.
3. **Chưa có chế độ xem lịch dạng lưới tuần/tháng** — vẫn là danh sách theo ngày.
   Lịch qua nửa đêm vì thế vẫn chỉ nằm ở ngày bắt đầu (đã ghi từ Round 5).
4. **Toast chỉ hiện một thông báo tại một thời điểm**; thao tác dồn dập sẽ ghi đè
   thông báo trước.
5. **Người dùng không đổi được light/dark** — giao diện đi theo thiết lập hệ thống.
6. Các mục tồn đọng về chức năng từ Round 1–9 vẫn giữ nguyên.

---

## Round 11 — Fix validation and reminder edge cases

**Ngày:** 2026-08-25
**Commit:** `round 11: fix validation and reminder edge cases`

Hai lỗi do người dùng báo sau khi chạy thử API thật.

---

### BUG-01 — Title chỉ có khoảng trắng vẫn được chấp nhận

**Tái hiện.** `POST` với `title` là `"   "`, `"\t\t"` hay `" \t \n "` đều trả **201**
và lưu nguyên văn; `PUT` cũng vậy. Frontend có `.trim()` trước khi gửi nên form
không bao giờ lộ ra, nhưng API là contract công khai và phải tự đứng vững.

**Nguyên nhân.** `title: str = Field(min_length=1, max_length=200)` — `"   "` dài 3
ký tự nên qua được `min_length`. Không có bước chuẩn hóa nào ở backend.

**Cách sửa.** Thêm `field_validator("title", mode="before")` trong `ScheduleFields`,
trim rồi mới để pydantic áp ràng buộc độ dài. Chọn `mode="before"` chứ không phải
`after` vì hai lý do:

* title toàn khoảng trắng biến thành `""` và trượt `min_length` — đúng thứ ta muốn;
* ràng buộc độ dài áp lên **title thật**. Trước đây `" " + "x"*200 + " "` bị **422**
  vì `max_length` đếm cả khoảng trắng người dùng không hề gõ; giờ được chấp nhận và
  lưu đúng 200 ký tự. Giới hạn vẫn là 200, chỉ là đo trên phần có nghĩa.

`ScheduleCreate` và `ScheduleUpdate` đều kế thừa `ScheduleFields` nên **create và
update dùng chung đúng một rule**, không phải lặp lại.

Chỉ trim `title`; `location` và `description` không nằm trong phạm vi báo lỗi nên
giữ nguyên (ghi ở phần tồn tại bên dưới).

**Test.** `tests/test_title_validation.py`, 22 test ở tầng API: 5 dạng khoảng trắng
× cả `POST` lẫn `PUT`, chuỗi rỗng, không ghi gì khi bị từ chối, bản ghi cũ không đổi
khi `PUT` bị từ chối, trim hai đầu nhưng **không** đụng khoảng trắng ở giữa, và bốn
test cho ranh giới độ dài (đúng 200, 201, 200 + đệm, 201 + đệm).

---

### BUG-03 — Reminder của lịch quá khứ kẹt ở "chưa gửi"

**Tái hiện.** Tạo lịch trong quá khứ kèm `reminder_minutes`: `notify_at` nằm ở quá
khứ, `pending` = 0, `due` = 0, `dispatch` = 0, và `notified_at` = `null` vĩnh viễn.
Giao diện đọc `notified_at == null` thành "chưa gửi" nên hứa một thông báo không bao
giờ đến.

**Nguyên nhân.** Cửa sổ gửi (`notify_at <= now < start_time`, từ Round 6) là **đúng**
— nhắc một cuộc họp đã bắt đầu thì vô nghĩa. Vấn đề nằm ở chỗ hệ thống **không nói
ra điều đó**: API chỉ có `notified_at`, mà `null` bị hiểu là "đang chờ". Không phân
biệt được "sắp gửi" và "đã lỡ, sẽ không gửi".

**Các phương án đã cân nhắc.**

| Phương án | Vì sao không chọn |
| --- | --- |
| Gửi bù dù lịch đã bắt đầu | Nhắc về cuộc họp đang diễn ra hoặc đã xong là phiền, không phải hữu ích |
| Từ chối tạo nhắc cho lịch quá khứ (422) | Ứng dụng vốn cho phép tạo lịch quá khứ (Round 9); và không giải quyết được lịch **trở thành** quá khứ sau khi bị dời |
| Tự xóa `reminder_minutes` | Xóa dữ liệu người dùng đã nhập |
| Thêm cột trạng thái vào database | Phải cập nhật hàng loạt theo thời gian trôi; trạng thái này vốn suy ra được |

**Cách sửa — đặt tên cho trạng thái, suy ra chứ không lưu.** Thêm
`models.reminder_status(schedule, now)` trả về một trong bốn giá trị:

| Giá trị | Nghĩa |
| --- | --- |
| `none` | lịch không đặt nhắc |
| `scheduled` | nhắc vẫn sẽ được gửi |
| `sent` | đã gửi |
| `missed` | mốc nhắc đã trôi qua khi lịch đã bắt đầu — sẽ không bao giờ gửi |

`ScheduleRead` trả thêm trường `reminder_status` (bổ sung, không phá contract cũ),
và `notifications.pending()` được viết lại theo chính hàm này nên **hai nơi không
thể lệch nhau**. Không thêm cột, không migration: `missed` chỉ là hệ quả của
`start_time` so với hiện tại, nên dời lịch trở lại tương lai thì nhắc tự về
`scheduled` — đã kiểm chứng cả hai chiều.

**Frontend.** `reminderSummary` và chip trong panel đọc theo `reminder_status`:
`sent` → "đã gửi", `scheduled` → "chưa gửi", `missed` → "đã qua, không nhắc nữa"
(chip hiện "Nhắc trước 30 phút · đã qua").

**Test.** `tests/test_reminder_status.py`, 17 test: bốn trạng thái (kể cả lịch bắt
đầu đúng thời điểm hiện tại → `missed`, và `sent` không bị "mất hiệu lực" khi lịch
đã qua), `pending` chỉ chứa `scheduled`, nhắc `missed` không bao giờ được dispatch,
bốn test qua API, và bốn test cho việc dời lịch qua lại giữa quá khứ/tương lai.

---

### Các check đã chạy

| Check | Lệnh | Kết quả |
| --- | --- | --- |
| Backend lint | `ruff check backend` | All checks passed |
| Backend test | `pytest` | **261 passed** (222 cũ + 39 mới) |
| Regression các vùng liên quan | 9 file test của các round trước | **220 passed**, không sửa gì |
| Frontend typecheck / test / build | `tsc`, `npm test`, `npm run build` | Sạch / **142 passed** (139 + 3 mới) / Built OK |
| Kiểm chứng test bắt được lỗi | tạm gỡ `backend/app` rồi chạy lại | **17/22** test title fail; file test reminder thậm chí không import được vì hàm chưa tồn tại, và response cũ không có trường `reminder_status` nào |
| API thật | server riêng trên cổng 8002, database tạm | title `'   '` / `'\t\t'` / `''` → **422**; `'  Họp nhóm  '` → **201** lưu `'Họp nhóm'`; `PUT` khoảng trắng → **422** và bản ghi cũ không đổi; lịch quá khứ → `missed`, lịch tương lai → `scheduled`, `pending`=1, `dispatch`=0 |

### Vấn đề còn tồn tại

1. **`location` và `description` chưa được trim ở backend.** Cùng loại vấn đề với
   title nhưng không nằm trong phạm vi báo lỗi nên chưa đụng tới; hệ quả là
   `location = "   "` vẫn lưu được và hiện thành một dòng trắng ở panel chi tiết.
2. **`reminder_status` phụ thuộc đồng hồ lúc đọc**, nên một phản hồi được cache lâu
   có thể nói `scheduled` cho một nhắc vừa thành `missed`. Với ứng dụng local thì
   không đáng kể.
3. **Lịch quá khứ vẫn tạo được kèm nhắc** — có chủ ý: hệ thống nói thẳng là nhắc sẽ
   không gửi thay vì chặn người dùng nhập.
4. Các mục tồn đọng từ Round 1–10 vẫn giữ nguyên.

### Lưu ý vận hành

Trong lúc kiểm tra, tôi đã xóa các bản ghi trong `data/app.db` khi chưa nhận ra
server `python run.py` của bạn đang chạy trên cổng 8001 với dữ liệu thử nghiệm —
dữ liệu đó không khôi phục được. Các bước kiểm tra sau đó chuyển hẳn sang một
database tạm và cổng 8002, và server của bạn không bị dừng. Server đó vẫn đang chạy
**code cũ**, cần khởi động lại để nhận hai bản sửa này.

---

## Round 12 — Fix timezone and DST consistency

**Ngày:** 2026-08-25
**Commit:** `round 12: fix timezone and DST consistency`

Ba lỗi liên quan tới múi giờ, do người dùng báo. Cả ba đều là cùng một nguyên
nhân sâu hơn: **danh tính của một múi giờ và cách quy đổi thời gian chưa có một
chỗ duy nhất để quyết định**. Vì vậy round này gom cả hai việc đó vào module mới
`backend/app/timezones.py` thay vì vá riêng từng chỗ.

---

### BUG-05 — Giờ không tồn tại do DST bị đổi âm thầm

**Hiện tượng.** `2026-03-08 02:30` ở `America/New_York` không tồn tại (đồng hồ
nhảy thẳng 02:00 → 03:00), nhưng API vẫn nhận và lưu thành 03:30.

**Tái hiện trước khi sửa:**

```
2026-03-08T01:30 -> UTC 06:30 -> đọc lại 01:30-05:00   khớp
2026-03-08T02:30 -> UTC 07:30 -> đọc lại 03:30-04:00   KHÔNG khớp
```

**Nguyên nhân.** `to_utc()` gọi `value.replace(tzinfo=tz)`. Theo PEP 495, với
một giờ nằm trong khoảng bị nhảy, `fold=0` dùng offset *trước* mốc đổi, nên
02:30 EST = 07:30Z — mà 07:30Z ở New York lại là 03:30 EDT. Python không báo lỗi,
nó chỉ trả về một thời điểm khác. Hệ quả: lịch bắt đầu muộn hơn người dùng nhập
một tiếng, và thời lượng cũng lệch một tiếng — sai cả hai thứ quan trọng nhất
của một lịch hẹn.

**Cách sửa.** `app/timezones.to_utc()` kiểm tra bằng chính định nghĩa của
"tồn tại": một giờ wall-clock tồn tại khi đổi sang UTC rồi đổi ngược lại thì ra
đúng nó. Nếu không, ném `NonexistentLocalTime`.

```python
def _skipped(value, tz):
    landed = value.replace(tzinfo=tz).astimezone(UTC).astimezone(tz).replace(tzinfo=None)
    return None if landed == value else landed
```

Phép thử này chọn đúng thứ cần chọn: giờ **lặp lại** (khi đồng hồ vặn chậm) vẫn
round-trip được nên không bị chặn oan, còn giá trị `landed` chính là gợi ý cần
đưa cho người dùng.

**Vì sao từ chối chứ không tự chọn hộ.** Người dùng gõ 02:30 có thể muốn "trước
khi đổi giờ" hoặc "sau khi đổi giờ" — hai thời điểm cách nhau một tiếng và không
có cách nào đoán đúng. Tự dời là im lặng làm sai; hỏi lại là để người dùng quyết.

**Thông báo lỗi.** Ném `PydanticCustomError("nonexistent_local_time", …)` kèm
`ctx` có `timezone`, `local_time`, `gap_minutes`, `next_valid`. Đây là error có
mã máy đọc được như `schedule_conflict` / `holiday_conflict` / `duration_out_of_range`,
nên frontend giải thích bằng lời của nó thay vì lặp lại câu tiếng Anh:

> Giờ bắt đầu bạn chọn không tồn tại ở America/New_York: 02:30 ngày CN, 08/03/2026.
> Hôm đó đồng hồ ở múi giờ này được vặn nhanh 1 giờ để đổi sang giờ mùa hè (DST),
> nên quãng thời gian đó bị bỏ qua. Hãy chọn một giờ trước lúc đổi, hoặc từ
> 03:30 ngày CN, 08/03/2026 trở đi.

**Giờ lặp lại (chiều ngược lại).** Được hiểu là **lần xuất hiện đầu tiên** —
đúng thứ tự người ta nhìn thấy khi cuộn qua ngày hôm đó trên lịch — và offset
trong response nói rõ đã chọn lần nào. Không đổi hành vi, chỉ ghi lại thành quy
ước có chủ đích.

---

### BUG-06 — `Asia/Saigon` và `Asia/Ho_Chi_Minh` không nhất quán

**Hiện tượng.** Backend mặc định `Asia/Ho_Chi_Minh`, trình duyệt báo
`Asia/Saigon`. Lịch được lưu theo tên nào tùy nơi tạo ra nó.

**Nguyên nhân.** Không phải một bên sai — hai bên dùng **hai nguồn "tên chuẩn"
khác nhau**. Đo trực tiếp trên máy này:

```
Intl.DateTimeFormat().resolvedOptions().timeZone      -> Asia/Saigon
canonicalTimezone("Asia/Ho_Chi_Minh")  (ICU)          -> Asia/Saigon
ZoneInfo / IANA                                        -> Asia/Ho_Chi_Minh
```

`frontend/src/format.ts` trước đây hỏi ICU để so sánh, còn backend lưu tên client
gửi lên. Nên `sameZone()` vẫn *so sánh* đúng, nhưng **chuỗi lưu trong database**
thì không đồng nhất — đúng như báo cáo.

**Cách sửa.** Chọn một nguồn duy nhất: **backend**, vì backend là nơi ghi dữ liệu.

* `app/timezones.RENAMED_ZONES` — bảng tên cũ → tên chuẩn, dạng dữ liệu thuần.
* `ScheduleInput._known_timezone` trả về `canonical(value)`, nên tạo/sửa bằng
  tên nào cũng lưu ra cùng một tên.
* `Settings.default_timezone` cũng được chuẩn hóa, để cấu hình không tự tạo ra
  một tên thứ hai.
* `GET /api/config` trả bảng đó (`timezone_aliases`); frontend `setTimezoneAliases()`
  dùng chính bảng ấy và **bỏ hẳn** cách hỏi ICU. Một bảng, hai bên đọc chung —
  giữ bản sao thứ hai trong TypeScript chính là cách lỗi này quay lại.

**Chọn lọc bảng, không lấy hết link IANA.** Đo trên máy này có 30 tên mà ICU coi
là chuẩn nhưng IANA coi là link. Chỉ 19 trong số đó là **đổi tên cùng một nơi**
(`Asia/Calcutta` → `Asia/Kolkata`, `Europe/Kiev` → `Europe/Kyiv`,
`America/Jujuy` → `America/Argentina/Jujuy`, …). Số còn lại là link *gộp hai nơi
khác nhau* trùng luật giờ — `Europe/Vatican` → `Europe/Rome`,
`Arctic/Longyearbyen` → `Europe/Oslo`. Đưa nhóm sau vào bảng sẽ viết lại lịch của
người dùng ở Vatican thành Rome: đó là sửa dữ liệu họ đã nhập, không phải sửa
chính tả. Tiêu chí này được ghi ngay trong docstring của bảng để lần mở rộng sau
không lẫn.

**Dữ liệu cũ.** Bản ghi cũ vẫn đọc và hiển thị bình thường (không viết lại lén
lúc đọc), và `migrate.py` có thêm bước `_canonicalise_timezones()` để đổi tên
khi người dùng muốn — chỉ đổi nhãn, không dịch chuyển thời điểm nào.

**Frontend.** `listTimezones()` nay ánh xạ danh sách qua `canonicalTimezone` rồi
khử trùng lặp, nên ô chọn hiện `Asia/Ho_Chi_Minh` chứ không hiện `Asia/Saigon` —
nếu không, người dùng chọn một tên rồi thấy lịch trả về tên khác.
`main.ts` tách ra `bootstrap()`: nạp `/api/config` **trước**, rồi mới dựng ô chọn
múi giờ, để giao diện không có khoảnh khắc nào gọi một vùng bằng hai tên.

---

### BUG-07 — `notified_at` không cùng quy ước với các datetime khác

**Hiện tượng.** `start_time`, `end_time`, `notify_at` trả về theo múi giờ của
lịch; `notified_at`, `google_synced_at`, `created_at`, `updated_at` trả về UTC.

**Nguyên nhân.** Quy ước cũ chia datetime thành hai nhóm: "giờ người dùng nhập"
và "dấu thời gian hệ thống". Cách chia đó có lý khi viết ra, nhưng người đọc API
không nhìn thấy nó — và hai trường cạnh nhau, tên chỉ khác một chữ (`notify_at`
"sẽ gửi lúc" / `notified_at` "đã gửi lúc"), lại hiển thị theo hai đồng hồ khác
nhau. Không sai instant, nhưng đọc là hiểu nhầm.

**Cách sửa.** Bỏ ngoại lệ: **mọi datetime của một lịch đều dựng theo múi giờ của
chính lịch đó**. Một câu, không có "trừ". `ScheduleRead.from_model` và
`NotificationRead.from_model` dùng `from_utc(..., tz)` cho tất cả các trường.

**Vì sao chọn hướng này thay vì đưa tất cả về UTC.** Cả hai đều nhất quán, nhưng
hướng này giữ được điều có ích: đọc "đã gửi lúc 12:38" ngay cạnh "lịch bắt đầu
12:43" là so sánh được ngay, không phải tự cộng offset trong đầu. Instant không
đổi và offset luôn tường minh, nên client nào chỉ quan tâm instant vẫn không bị
ảnh hưởng.

**Đây là thay đổi hành vi có chủ ý**, nên hai test cũ ghi lại quy ước cũ đã được
viết lại chứ không phải sửa cho qua:
`test_schedules.py::test_create_returns_full_record` và
`test_timezones.py::test_timestamps_are_reported_in_utc` (đổi tên thành
`test_timestamps_use_the_schedule_timezone_like_every_other_datetime`). Cả hai
vẫn kiểm tra đúng instant như trước.

---

### Test đã chạy

| Kiểm tra | Kết quả |
| --- | --- |
| `pytest` (backend, toàn bộ) | **304 passed** (261 cũ + 43 mới) |
| `tests/test_dst.py` (mới) | 16 test — giờ không tồn tại, giờ lặp lại, lịch xuyên DST, thời lượng và xung đột qua mốc đổi giờ |
| `tests/test_timezone_naming.py` (mới) | 17 test — bảng đổi tên, tạo/sửa bằng tên cũ, `/api/config`, migrate |
| `tests/test_datetime_convention.py` (mới) | 10 test — mọi datetime của một lịch dùng chung một offset |
| Kiểm chứng test bắt được lỗi | tạm gỡ bản sửa (`git stash`): **20/43** test mới fail |
| `ruff check backend` | sạch |
| `tsc --noEmit`, `vitest`, `npm run build` | sạch — **149 passed** (142 cũ + 7 mới), build OK |
| API thật (cổng 8002, DB tạm) | 02:30 New York → **422** `nonexistent_local_time`; 23:00→04:00 xuyên DST → **201**, lưu `04:00Z–08:00Z`; tạo bằng `Asia/Saigon` → lưu và trả về `Asia/Ho_Chi_Minh`; sau khi dispatch, cả 6 datetime của lịch Tokyo đều `+09:00` |
| Frontend chạy thật với backend thật (jsdom, tạm) | runtime báo `Asia/Saigon` nhưng ô chọn hiện `Asia/Ho_Chi_Minh`; lịch lưu tên chuẩn không còn bị đánh dấu "khác múi giờ"; lỗi DST hiện đúng câu tiếng Việt kèm gợi ý |

**Một lỗi phát hiện nhờ chạy thật.** Lần chạy jsdom đầu tiên vẫn cho ô chọn là
`Asia/Saigon`. Nguyên nhân không nằm ở code mà ở chỗ `VITE_API_BASE_URL` chưa
được đặt, nên frontend đang gọi sang server cũ ở cổng 8001 (server đang chạy của
người dùng, chưa nạp code mới) — server đó chưa trả `timezone_aliases`. Cũng vì
vậy `setTimezoneAliases()` được viết để chấp nhận `undefined`: gặp backend cũ thì
lùi về gọi tên nguyên văn thay vì hỏng cả trang.

### Còn tồn tại

* Bảng `RENAMED_ZONES` chỉ có 19 cặp đổi tên đã đo được trên môi trường này. Một
  runtime khác báo về một tên cũ ngoài bảng thì tên đó được giữ nguyên — vẫn
  chạy đúng, chỉ là chưa gộp về một tên. Mở rộng bằng cách thêm cặp vào bảng.
* Giờ lặp lại khi đồng hồ vặn chậm luôn được hiểu là lần đầu; chưa có cách để
  người dùng chọn lần thứ hai. Cần thì phải thêm vào API (ví dụ cờ `fold`).
* `location` / `description` vẫn chưa được trim ở backend (đã ghi ở Round 11,
  ngoài phạm vi round này).

---

## Round 13 — Fix scheduling UI semantics

**Ngày:** 2026-08-25
**Commit:** `round 13: fix scheduling UI semantics`

Hai lỗi UI/UX do người dùng phát hiện khi test bằng Playwright. Điểm chung: cả
hai đều **vô hình với bộ test jsdom hiện có** — một cái là ý nghĩa của chữ trên
màn hình, một cái là thứ trình duyệt tự thêm vào. Vì vậy round này bổ sung luôn
một tầng test chạy trong browser thật.

---

### BUG-02 — "Lịch sắp tới" chứa cả lịch đã qua

**Hiện tượng.** Tiêu đề cột ghi "Lịch sắp tới" nhưng bên dưới render toàn bộ
schedules, kể cả lịch đã kết thúc từ lâu.

**Nguyên nhân.** Không có bug logic nào cả — `renderList` vốn chỉ nhóm theo ngày
rồi đổ ra hết. Cái sai nằm ở chỗ tiêu đề **hứa một việc mà danh sách không làm**.
Từ Round 1 tới giờ danh sách luôn là "tất cả lịch"; chữ "sắp tới" được thêm vào ở
Round 10 lúc làm lại giao diện và không ai đối chiếu lại với nội dung.

**Cách sửa.** Làm cho danh sách đúng như tiêu đề nói, thay vì đổi tiêu đề thành
"Tất cả lịch" — vì yêu cầu thật của người dùng là *phân biệt được* hai loại:

* **Sắp tới** — hiện luôn, xếp tăng dần.
* **Đã qua** — `<details>` thu gọn kèm số lượng, mới nhất trước.

Ranh giới là **thời điểm kết thúc**, không phải thời điểm bắt đầu:

```ts
export function standingOf(schedule: Schedule, now: Date): Standing {
  const moment = now.getTime();
  if (parseInstant(schedule.end_time).getTime() <= moment) return "past";
  return parseInstant(schedule.start_time).getTime() <= moment ? "ongoing" : "upcoming";
}
```

Lấy mốc kết thúc là điều giữ cho **cuộc họp đang ngồi trong đó** không bị đẩy
sang "đã qua" — lỗi này khó chịu hơn hẳn lỗi ban đầu. Lịch đang chạy nằm ở phần
"Sắp tới" kèm nhãn **Đang diễn ra**, nói thẳng ra bằng chữ thay vì để người dùng
tự suy.

**Vài quyết định nhỏ:**

* Thu gọn phần "Đã qua" vì nó chỉ dài thêm theo thời gian và không phải lý do
  người ta mở trang. Dùng `<details>/<summary>` nên có sẵn hành vi bàn phím và
  screen reader, không phải tự dựng.
* Quá khứ xếp **ngược** (mới nhất trước): thứ vừa xảy ra là thứ đáng tìm nhất.
* Chỉ còn lịch quá khứ → phần "Sắp tới" ghi rõ "Không có lịch nào sắp tới.",
  khác hẳn empty state "Chưa có lịch nào" của lần đầu dùng.
* `renderList` nhận thêm tham số `now` (mặc định `new Date()`), để test cố định
  được thời gian thay vì phải giả lập đồng hồ.
* Tiêu đề cột đổi thành "Lịch của bạn" — giờ nó đứng đầu **cả hai** phần.
* Ngày (`h3.day`) hạ xuống `h4` vì đã có `h3` cho tên phần, giữ thứ bậc heading
  không nhảy cấp.

**Backend không đổi.** Việc phân loại dựa trên instant đã có trong response nên
đúng ở mọi múi giờ đang xem; không cần endpoint hay tham số mới.

---

### BUG-04 — Validation message tiếng Anh của trình duyệt

**Hiện tượng.** Trang tiếng Việt, nhưng submit title rỗng thì trình duyệt hiện
bong bóng `Please fill out this field.`

**Nguyên nhân.** Các input có `required` và form không tắt validation gốc, nên
trình duyệt chặn submit và tự hiện thông báo bằng ngôn ngữ của **nó**, không phải
của trang. Không thể dịch và cũng không thể style bong bóng đó.

**Cách sửa.** `form.noValidate = true` để tắt **giao diện** gốc, giữ nguyên
thuộc tính `required` trên từng control, rồi tự kiểm tra và tự hiển thị:

```ts
function checkRequired(): boolean {
  let firstBad: HTMLInputElement | null = null;
  for (const [control, message] of requiredFields) {
    const empty = control.value.trim() === "";
    setFieldError(control, empty ? message : null);
    if (empty && firstBad === null) firstBad = control;
  }
  if (firstBad) firstBad.focus();
  return firstBad === null;
}
```

**Không làm giảm accessibility** — đây là điều người dùng dặn riêng:

| | Trước (native) | Sau |
| --- | --- | --- |
| Thông báo | bong bóng tiếng Anh, tự biến mất | `.field__error` cạnh ô, ở lại tới khi sửa xong |
| Trạng thái ô | pseudo-class `:invalid` | `aria-invalid="true"` + viền đỏ |
| Liên kết message ↔ ô | ngầm | `aria-describedby` trỏ đúng id |
| "Bắt buộc" | `required` | **giữ nguyên** `required` |
| Focus | trình duyệt tự nhảy | tự focus ô sai đầu tiên |

Thông báo tự xóa ngay khi ô có nội dung, nên không treo trên ô đã sửa xong.

**Phạm vi kiểm tra giữ đúng bằng cái native đã làm** — chỉ "ô bắt buộc không được
rỗng", cộng thêm title toàn khoảng trắng tính là rỗng (khớp rule backend từ
Round 11, và đây chính là trường hợp `required` gốc *cho lọt*). Thời lượng, ngày
nghỉ, trùng giờ vẫn để backend trả lời qua panel lỗi như cũ: kiểm tra hai lần là
cách hai câu trả lời bắt đầu lệch nhau.

---

### Thêm tầng test Playwright

Cả hai lỗi này lọt qua 149 test jsdom vì jsdom **không có** validation gốc của
form, không có layout, không có focus thật. Nên round này thêm `frontend/e2e/`
chạy trong Chromium thật:

* `playwright.config.ts` tự khởi động backend (cổng **8917**, SQLite tạm trong
  `frontend/.e2e/`) và Vite (cổng **5917**). Chọn cổng lạ có chủ đích: 5173 và
  8001 thường đã có server đang chạy, và một lần chạy test không được tranh cổng
  với chúng.
* Không đụng `data/app.db`; mỗi lần chạy xóa và tạo lại database tạm.
* Artefacts (`test-results/`, `.e2e/`, `playwright-report/`) đã cho vào
  `.gitignore`.

### Test đã chạy

| Kiểm tra | Kết quả |
| --- | --- |
| `npm run test:e2e` (Playwright, Chromium) | **19 passed** |
| — empty state | 1 test: "Chưa có lịch nào", không có phần Sắp tới/Đã qua |
| — upcoming/past | 5 test: chỉ lịch chưa xong ở "Sắp tới", "Đã qua (2)" thu gọn, nhãn Đang diễn ra, trường hợp chỉ còn quá khứ, mở được lịch cũ |
| — form validation | 7 test: thông báo tiếng Việt, `noValidate` + `required`, `aria-invalid`/`aria-describedby`/focus, ô sai được cuộn ra khỏi header dính, title toàn khoảng trắng, tự xóa message, submit hợp lệ vẫn chạy |
| — responsive & a11y | 6 test: 390px và 1280px không tràn ngang, một `h1` và heading không nhảy cấp, mở "Đã qua" bằng bàn phím, mọi control có tên đọc được, `role="alert"` / `aria-live` |
| Kiểm chứng test bắt được lỗi | tạm gỡ bản sửa: **9/11** test của hai bug fail |
| `npm test` (vitest) | **164 passed** (149 + 15 mới) |
| Kiểm chứng test unit bắt được lỗi | tạm gỡ `views.ts`: **13/15** test mới fail |
| `npm run typecheck` / `npm run build` | sạch / OK |
| `pytest` + `ruff` (backend) | **304 passed** / sạch — round này không đổi backend |

### Một lỗi chỉ ảnh chụp mới thấy

Chụp màn hình lại (như Round 10) cho thấy: khi bấm nút submit ở cuối form dài,
trang đã cuộn xuống, `focus()` kéo ô sai trở lại nhưng nó nằm **khuất sau topbar
dính** — người dùng thấy form nhảy mà không thấy lỗi. Sửa bằng
`scroll-margin-top: 6rem` đặt trên chính `input/select/textarea` (đặt trên
`.field` không có tác dụng: phần tử được cuộn tới là control, không phải wrapper).
Đã thêm test e2e so sánh `boundingBox()` của ô với đáy topbar.

Cùng lúc đó, ảnh chụp cho thấy tiêu đề phần "Sắp tới" ban đầu dùng đúng kiểu chữ
in hoa nhỏ như nhãn cột và như tiêu đề ngày, thành ba nhãn gần giống nhau chồng
lên nhau. Đã đổi sang cỡ lớn hơn, chữ thường, màu đậm — để nó đọc như một tiêu đề
thật, còn nhãn cột và tiêu đề ngày giữ vai trò phụ.

### Còn tồn tại

* Việc phân loại sắp tới/đã qua tính lại mỗi lần render, không có đồng hồ chạy
  nền. Một lịch kết thúc trong lúc trang đang mở chỉ chuyển sang "Đã qua" ở lần
  render kế tiếp (tạo/sửa/xóa/đổi múi giờ). Đủ cho demo; muốn chính xác từng
  phút thì cần một `setInterval` re-render.
* Playwright cần tải browser một lần (`npx playwright install chromium`, ~115MB),
  nên `npm run test:e2e` không nằm trong luồng test mặc định.
* Suite e2e chỉ chạy Chromium. Thêm Firefox/WebKit chỉ là thêm `projects`, nhưng
  chưa cần cho phạm vi hiện tại.
