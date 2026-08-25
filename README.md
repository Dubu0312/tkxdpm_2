# tkxdpm_2

Ứng dụng đặt lịch (scheduling) chạy local: backend Python + SQLite, frontend TypeScript.

Chức năng hiện có: tạo lịch, xem danh sách, xem chi tiết, chỉnh sửa và xóa lịch.
Mỗi lịch gồm tiêu đề, thời gian bắt đầu / kết thúc, múi giờ, quốc gia, địa điểm
và mô tả (ba trường sau không bắt buộc), kèm mốc `created_at` / `updated_at`.
Lịch có thể được tạo ở bất kỳ múi giờ nào và xem lại ở múi giờ khác mà không đổi
thời điểm thực, và có thể kéo dài qua nửa đêm. Backend từ chối lịch bị trùng khung
giờ với lịch đã có, và từ chối lịch rơi vào ngày nghỉ chính thức của quốc gia được
chọn. Mỗi lịch có thể đặt một mốc nhắc trước (`reminder_minutes`), phải dài trong
khoảng cho phép (mặc định 15 phút – 7 ngày), và có thể đồng bộ sang Google
Calendar (tùy chọn, mặc định tắt).

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
│   │   ├── schemas.py      # Pydantic schemas + request/response shapes
│   │   ├── timezones.py    # zone naming + wall-clock <-> instant conversion
│   │   ├── holiday_calendar.py # public-holiday lookup (single source)
│   │   ├── notifications.py    # when a reminder is due, and dispatching it
│   │   ├── google_calendar.py  # Google Calendar integration (single source)
│   │   ├── routers/
│   │   │   ├── schedules.py# CRUD endpoints under /api/schedules
│   │   │   ├── countries.py# GET /api/countries
│   │   │   ├── config.py   # GET /api/config (rules served to the frontend)
│   │   │   └── notifications.py # /api/notifications
│   │   └── main.py         # FastAPI app: GET /, GET /health, router
│   ├── migrate.py          # one-off upgrade of older databases
│   ├── google_auth.py      # one-off Google OAuth consent flow
│   ├── tests/              # pytest
│   ├── run.py              # dev entry point (reads host/port from .env)
│   ├── requirements.in     # direct runtime deps
│   ├── requirements.txt    # pinned runtime lock file
│   ├── requirements-dev.in # direct dev deps
│   └── requirements-dev.txt# pinned dev lock file
├── frontend/               # Vite + TypeScript app
│   ├── src/
│   │   ├── api.ts          # typed fetch client
│   │   ├── types.ts        # Schedule types
│   │   ├── format.ts       # timezone-aware datetime helpers
│   │   ├── views.ts        # list / detail / form rendering
│   │   └── main.ts         # app state + wiring
│   ├── e2e/                # Playwright specs (real browser)
│   └── playwright.config.ts# starts a throwaway backend + Vite for e2e
├── data/                   # local SQLite files (contents not committed)
├── secrets/                # Google credentials (contents not committed)
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
npm run test:e2e             # Playwright (real browser, starts its own servers)
npm run build                # type check + production build into frontend/dist
npm run preview              # serve the production build
```

`test:e2e` cần tải browser một lần: `npx playwright install chromium`. Nó tự khởi
động backend (cổng 8917, database tạm trong `frontend/.e2e/`) và Vite (cổng 5917),
nên không đụng tới `data/app.db` hay server đang chạy của bạn.

## API

Base URL: `http://127.0.0.1:8001`.

| Method | Path                   | Mô tả                                       |
| ------ | ---------------------- | ------------------------------------------- |
| GET    | `/api/schedules`       | Danh sách lịch, sắp xếp theo thời gian bắt đầu |
| POST   | `/api/schedules`       | Tạo lịch (201)                              |
| GET    | `/api/schedules/{id}`  | Chi tiết một lịch                           |
| PUT    | `/api/schedules/{id}`  | Cập nhật toàn bộ một lịch                   |
| DELETE | `/api/schedules/{id}`  | Xóa lịch (204)                              |
| GET    | `/api/countries`       | Danh sách quốc gia kiểm tra được ngày nghỉ  |
| GET    | `/api/config`          | Giới hạn thời lượng, múi giờ mặc định, bảng tên múi giờ |
| GET    | `/api/config/google`   | Trạng thái tích hợp Google Calendar         |
| POST   | `/api/schedules/{id}/google`   | Tạo/cập nhật event Google cho lịch  |
| DELETE | `/api/schedules/{id}/google`   | Xóa event Google, giữ lại lịch      |
| GET    | `/api/notifications`   | Nhắc đang chờ (chưa gửi, lịch chưa bắt đầu) |
| GET    | `/api/notifications/due` | Nhắc đã đến lúc gửi nhưng chưa gửi        |
| POST   | `/api/notifications/dispatch` | Gửi ngay các nhắc đang đến hạn      |

Schedule fields: `title` (bắt buộc, được trim hai đầu, ≤200 ký tự sau khi trim —
title chỉ gồm khoảng trắng bị từ chối), `start_time`, `end_time` (bắt
buộc, `end_time` phải sau `start_time`), `timezone` (tên IANA, mặc định
`DEFAULT_TIMEZONE`), `country` (mã ISO 3166-1 alpha-2, tùy chọn), `location` và
`description` (tùy chọn), cùng `id`,
`created_at`, `updated_at` do server sinh ra. Dữ liệu không hợp lệ trả về `422`
kèm thông báo, id không tồn tại trả về `404`.

### Múi giờ

Quy ước xử lý thời gian:

| Tầng | Cách xử lý |
| --- | --- |
| SQLite | `start_time` / `end_time` / `created_at` / `updated_at` lưu **UTC** (naive, vì SQLite không có kiểu aware); `timezone` lưu tên IANA riêng |
| Backend | Chuyển input về UTC lúc validate, so sánh và sắp xếp bằng UTC, dựng response về múi giờ của từng lịch |
| API | ISO-8601 kèm offset tường minh, ví dụ `2026-09-01T09:00:00+09:00`. **Mọi** datetime của một lịch — kể cả `notified_at`, `google_synced_at`, `created_at`, `updated_at` — đều dựng theo múi giờ của chính lịch đó |
| Frontend | Hiển thị mọi thời điểm theo *múi giờ đang xem* bằng `Intl.DateTimeFormat`; ô nhập gửi giờ wall-clock kèm `timezone`, không tự tính offset |

Input `start_time` / `end_time` chấp nhận hai dạng:

* **kèm offset** (`2026-09-01T09:00:00+09:00`) — offset quyết định thời điểm,
  trường `timezone` chỉ dùng để hiển thị lại;
* **không offset** (`2026-09-01T09:00:00`) — được hiểu là giờ địa phương của
  `timezone` trong cùng request. Đây là dạng frontend gửi.

Vì mọi so sánh diễn ra trên UTC, phát hiện xung đột hoạt động đúng giữa các múi
giờ khác nhau và qua các mốc đổi giờ DST. Một `timezone` không hợp lệ trả về `422`.

**Một múi giờ, một tên.** Cùng một vùng có thể có nhiều tên (`Asia/Saigon` và
`Asia/Ho_Chi_Minh` là một), và các runtime không thống nhất tên nào là chuẩn —
trình duyệt ở đây báo `Asia/Saigon`, còn IANA/Python dùng `Asia/Ho_Chi_Minh`.
Backend quyết định tên khi nhận request (`app/timezones.py`) nên mọi lịch mới
đều lưu cùng một tên bất kể client nào tạo. Bảng đổi tên được `GET /api/config`
trả về (`timezone_aliases`) để frontend gọi tên giống hệt backend thay vì giữ
một bản sao riêng. Bản ghi cũ vẫn đọc và hiển thị bình thường; `python
migrate.py` sẽ đổi tên chúng khi bạn muốn.

**Giờ không tồn tại do DST.** Khi đồng hồ vặn nhanh, những giờ nằm trong khoảng
bị nhảy không hề tồn tại — ở `America/New_York` ngày 2026-03-08, đồng hồ đi
thẳng từ 02:00 sang 03:00. Backend **từ chối** giá trị như vậy thay vì tự dời
sang 03:30 (việc dời sẽ làm sai cả thời điểm lẫn thời lượng):

```bash
curl -X POST http://127.0.0.1:8001/api/schedules -H 'Content-Type: application/json' \
  -d '{"title":"DST","start_time":"2026-03-08T02:30:00","end_time":"2026-03-08T04:00:00","timezone":"America/New_York"}'
# -> 422, type "nonexistent_local_time", ctx kèm gap_minutes và next_valid
```

Chiều ngược lại (đồng hồ vặn chậm, một giờ lặp lại hai lần) được hiểu là **lần
xuất hiện đầu tiên**; offset trong response cho biết lần nào đã được chọn. Lịch
chạy *xuyên qua* mốc đổi giờ vẫn hợp lệ, và thời lượng được tính bằng thời gian
thực: 01:50 → 03:00 ngày 2026-03-08 ở New York chỉ dài 10 phút, không phải 70.

Ví dụ — hai lịch dưới đây xung đột dù giờ hiển thị khác nhau (cùng là 09:00 UTC):

```bash
curl -X POST http://127.0.0.1:8001/api/schedules -H 'Content-Type: application/json' \
  -d '{"title":"Tokyo","start_time":"2026-12-15T18:00:00","end_time":"2026-12-15T19:00:00","timezone":"Asia/Tokyo"}'

curl -X POST http://127.0.0.1:8001/api/schedules -H 'Content-Type: application/json' \
  -d '{"title":"Saigon","start_time":"2026-12-15T16:30:00","end_time":"2026-12-15T17:30:00","timezone":"Asia/Saigon"}'
# -> 409 Conflict
```

### Danh sách lịch: sắp tới và đã qua

Danh sách chia làm hai phần, dựa trên **thời điểm kết thúc**:

* **Sắp tới** — lịch chưa kết thúc, sắp xếp theo thời gian tăng dần. Lịch đang
  chạy (`bắt đầu <= bây giờ < kết thúc`) nằm ở đây kèm nhãn **Đang diễn ra**;
  xếp nó vào "đã qua" chỉ vì đã bắt đầu thì sai hơn nhiều.
* **Đã qua** — lịch đã kết thúc, gộp trong một khối thu gọn kèm số lượng, mới
  nhất trước. Thu gọn vì phần này chỉ dài thêm theo thời gian và không phải lý do
  người dùng mở trang.

Nếu chưa có lịch nào thì hiện empty state như cũ; nếu chỉ còn lịch quá khứ thì
phần "Sắp tới" nói rõ "Không có lịch nào sắp tới." Việc phân loại này hoàn toàn ở
frontend và dựa trên instant thật, nên đúng ở mọi múi giờ đang xem; backend không
đổi.

### Giới hạn thời lượng

Một lịch phải dài trong khoảng cho phép, mặc định **15 phút – 7 ngày**. Hai giá
trị này nằm ở **một chỗ duy nhất** là `Settings` trong
[`app/config.py`](backend/app/config.py), đổi được bằng biến môi trường:

```bash
MIN_DURATION_MINUTES=15
MAX_DURATION_MINUTES=10080   # 7 ngày
```

Backend là nơi thực thi rule. Frontend **không hard-code** hai con số này mà đọc
từ `GET /api/config` để hiện gợi ý trong form và chặn sớm trước khi gửi request —
nhưng backend vẫn là bên quyết định.

Thời lượng được đo **giữa hai instant**, nên đúng với mọi múi giờ, với lịch qua
nửa đêm và lịch bắt đầu/kết thúc ở hai ngày khác nhau. Quanh mốc đổi giờ DST thì
đồng hồ treo tường nói dối còn thời lượng thực thắng: 01:50 → 03:00 ngày
spring-forward ở New York đọc như 70 phút nhưng chỉ có **10 phút** thực trôi qua,
nên bị từ chối.

Vượt giới hạn trả `422` kèm body có cấu trúc:

```json
{
  "detail": {
    "code": "duration_out_of_range",
    "message": "Schedule lasts 14 minutes, below the minimum of 15",
    "duration_minutes": 14,
    "min_minutes": 15,
    "max_minutes": 10080
  }
}
```

Thứ tự kiểm tra: payload hợp lệ (`end` sau `start`) → **thời lượng** → ngày nghỉ
→ trùng lịch. Thời lượng đứng trước vì nó chỉ phụ thuộc vào chính request, và một
lịch sai độ dài thì không giờ nào cứu được.

### Ngày nghỉ theo quốc gia

Nếu lịch có `country`, backend từ chối lịch rơi vào **ngày nghỉ chính thức** của
quốc gia đó và trả về `409 Conflict`. Bỏ trống `country` nghĩa là không kiểm tra.

Dữ liệu ngày nghỉ lấy từ package [`holidays`](https://pypi.org/project/holidays/):
nó **tính** ngày nghỉ từ luật của từng nước (kể cả ngày lễ trôi như Tết Nguyên
đán hay Easter) thay vì tra bảng cố định. Nhờ vậy repo không chứa dữ liệu ngày
nghỉ nào, chạy hoàn toàn offline, và không cần cập nhật theo từng năm. Toàn bộ
phần này nằm gọn trong [`app/holiday_calendar.py`](backend/app/holiday_calendar.py);
danh sách quốc gia được lấy từ chính package qua `GET /api/countries` nên frontend
không hard-code quốc gia nào.

Ngày được xét là **ngày địa phương theo `timezone` của lịch**, không phải theo
UTC — 08:00 ngày 01/01 giờ Tokyo vẫn là 01/01 dù theo UTC còn là 31/12. Khoảng
thời gian là nửa mở: lịch kết thúc đúng 00:00 không tính sang ngày hôm sau. Lịch
trải nhiều ngày sẽ báo mọi ngày nghỉ mà nó chạm vào.

Body của `409`:

```json
{
  "detail": {
    "code": "holiday_conflict",
    "message": "VN observes 1 public holiday in this time range",
    "country": "VN",
    "holidays": [{ "date": "2026-02-17", "name": "Lunar New Year" }]
  }
}
```

Ví dụ:

```bash
curl -X POST http://127.0.0.1:8001/api/schedules -H 'Content-Type: application/json' \
  -d '{"title":"Họp Tết","start_time":"2026-02-17T09:00:00","end_time":"2026-02-17T10:00:00","timezone":"Asia/Ho_Chi_Minh","country":"VN"}'
# -> 409 Conflict (Lunar New Year)
```

### Nhắc trước (notification)

Thời điểm nhắc **được suy ra**, không lưu thành bản ghi riêng:

```
notify_at = start_time - reminder_minutes
```

`start_time` đang lưu là instant UTC, nên `notify_at` cũng là một instant — đúng
dù lịch nhập ở múi giờ nào và dù lịch vắt qua nửa đêm. Chỉ có `notified_at` (lúc
đã gửi) được lưu, để không gửi trùng.

Vì thời điểm nhắc là suy ra chứ không lưu, **sửa lịch thì mốc nhắc tự dịch theo,
xóa lịch thì mốc nhắc mất theo** — không có bảng nào cần đồng bộ. Nếu một nhắc đã
gửi rồi mà lịch bị dời (hoặc đổi `reminder_minutes`, hoặc đổi múi giờ khiến
instant thay đổi) thì nhắc đó được **nạp lại** để gửi cho mốc mới; sửa mỗi tiêu đề
thì không gửi lại.

Một nhắc "đang chờ" khi chưa gửi **và** lịch chưa bắt đầu; nó "đến hạn" khi
`notify_at <= now < start_time`. Nhắc của lịch đã bắt đầu tự rơi ra khỏi danh sách
thay vì gửi muộn — không cần dọn gì.

Trường `reminder_status` trên mỗi lịch cho biết nhắc đó đã đi tới đâu:

| Giá trị | Nghĩa |
| --- | --- |
| `none` | lịch không đặt nhắc |
| `scheduled` | nhắc vẫn sẽ được gửi |
| `sent` | đã gửi (`notified_at` có giá trị) |
| `missed` | mốc nhắc đã trôi qua trong khi lịch đã bắt đầu — sẽ không bao giờ gửi |

`missed` được **suy ra**, không lưu: dời lịch trở lại tương lai thì nhắc tự trở
lại `scheduled`.

Kênh gửi hiện tại là **một dòng log** ở phía server:

```
INFO:     app.notifications - Reminder: 'Họp nhóm' starts at 2026-05-10 02:00:00 UTC (in 30 minutes)
```

Có hai cách kích hoạt, dùng chung một hàm `dispatch_due()`:

* **Poller nền** chạy trong app, mặc định mỗi 30 giây
  (`NOTIFICATIONS_ENABLED`, `NOTIFICATION_POLL_SECONDS`);
* **`POST /api/notifications/dispatch`** để demo ngay, không phải đợi tick.

Giới hạn hiện tại: chỉ log ra server (chưa có email/push), poller nằm trong tiến
trình app nên nhiều worker sẽ gửi trùng, và danh sách đến hạn được lọc trong
Python nên không phù hợp với lượng lịch rất lớn.

### Lịch qua nửa đêm

Lịch bắt đầu 23:30 và kết thúc 01:00 hôm sau là hợp lệ — không có ràng buộc nào
theo ngày, chỉ có `end_time` phải sau `start_time`. Vì mọi thứ so sánh theo thời
điểm (UTC) chứ không theo ngày, phát hiện xung đột hoạt động bình thường ở cả hai
phía nửa đêm, và một lịch dài nhiều ngày cũng chỉ là một khoảng dài hơn.

"Qua nửa đêm" là **thuộc tính hiển thị, không phải thuộc tính lưu trữ**: lịch
23:30–01:00 giờ Việt Nam được lưu là `16:30–18:00` UTC, thậm chí không chạm nửa
đêm; còn khi xem ở `Asia/Tokyo` thì nó hiện thành 01:30–03:00 trong cùng một ngày.
Vì vậy frontend đánh dấu `+1` trên thẻ trong danh sách theo **múi giờ đang xem**,
và lịch được xếp vào ngày mà nó *bắt đầu*.

Trong form, đổi giờ bắt đầu sẽ dời giờ kết thúc theo để giữ nguyên độ dài — đặt
giờ bắt đầu 23:30 thì giờ kết thúc tự chuyển sang ngày hôm sau.

### Xung đột thời gian

`POST` và `PUT` từ chối lịch có khung giờ chồng lấn lịch đã tồn tại và trả về
`409 Conflict`. Hai khoảng thời gian được coi là chồng lấn khi mỗi khoảng bắt đầu
trước khi khoảng kia kết thúc — nên hai lịch **liền kề** (một lịch kết thúc đúng
lúc lịch kia bắt đầu) vẫn hợp lệ. Khi cập nhật, lịch đang sửa không tự xung đột
với chính nó.

Kiểm tra này nằm ở backend và là nguồn duy nhất quyết định hợp lệ hay không;
frontend chỉ hiển thị lại kết quả, không kiểm tra trùng lịch riêng. Ngày nghỉ
được kiểm tra **trước** xung đột thời gian, vì ngày nghỉ chặn cả ngày nên đó là
thông báo hữu ích hơn.

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

## Google Calendar (tùy chọn)

Tích hợp **mặc định tắt** — clone về là chạy được ngay, không cần credential nào.

Ba chế độ, đặt bằng `GOOGLE_CALENDAR_MODE`:

| Chế độ | Ý nghĩa |
| --- | --- |
| `disabled` (mặc định) | Không tích hợp. Các endpoint sync trả `503` kèm hướng dẫn bật. |
| `memory` | Bản mô phỏng chạy trong tiến trình, cùng luật insert/update/delete với API thật. Dùng để **demo và test luồng mà không cần credential**. Đây **không** phải đồng bộ thật. |
| `google` | Google Calendar API thật, dùng OAuth. |

### Cấu hình credential thật

1. Vào [Google Cloud Console](https://console.cloud.google.com/), tạo project và
   bật **Google Calendar API**.
2. Tạo **OAuth client ID** loại **Desktop app**, tải file JSON về và lưu thành
   `secrets/google_client_secret.json`.
3. Chạy consent flow một lần — nó mở trình duyệt và ghi token:

   ```bash
   source .venv/bin/activate
   cd backend && python google_auth.py
   ```

4. Bật tích hợp trong `.env`:

   ```bash
   GOOGLE_CALENDAR_MODE=google
   GOOGLE_CALENDAR_ID=primary          # hoặc id của một calendar khác
   ```

Cả `secrets/google_client_secret.json` lẫn `secrets/google_token.json` đều nằm
trong `.gitignore` và **không bao giờ được commit**.

### Cách đồng bộ hoạt động

* **Opt-in theo từng lịch**: bấm "Đồng bộ Google" ở panel chi tiết, hoặc gọi
  `POST /api/schedules/{id}/google`.
* **Liên kết**: id event Google được lưu trên chính dòng lịch trong SQLite
  (`google_event_id`, `google_calendar_id`, `google_synced_at`).
* **Không tạo trùng**: id event được **suy ra từ id lịch**, nên gọi sync bao
  nhiêu lần cũng chỉ tác động đúng một event. Nếu liên kết bị mất ở phía local,
  lệnh insert va chạm và được chuyển thành update thay vì tạo event thứ hai; nếu
  event bị xóa ở phía Google thì nó được tạo lại.
* **Thời gian**: gửi `dateTime` kèm offset **và** `timeZone` là tên IANA, nên
  Google nhận đủ cả thời điểm thực lẫn múi giờ gốc của lịch.
* **Khi lịch thay đổi**: lịch **đã liên kết** được đẩy cập nhật ngay sau khi sửa.
  Nếu đẩy thất bại thì bản sửa vẫn được lưu và `google_out_of_date` bật lên để
  giao diện mời đồng bộ lại, thay vì lệch nhau trong im lặng.
* **Khi lịch bị xóa**: event Google được xóa theo. Nếu không gọi được Google thì
  vẫn xóa lịch ở local (không chặn người dùng) và ghi cảnh báo vào log.
* **Bỏ liên kết**: `DELETE /api/schedules/{id}/google` xóa event nhưng giữ lịch.

Giới hạn hiện tại: đồng bộ **một chiều** (app → Google), chưa đọc ngược thay đổi
từ Google; và nhánh `google` thật chưa được chạy tự động trong CI vì cần
credential — chỉ nhánh `memory` được phủ bằng test.

## Tests and linting

```bash
# Backend
source .venv/bin/activate
cd backend && pytest && ruff check .

# Frontend
cd frontend && npm run typecheck && npm test

# Frontend, trong browser thật (cần `npx playwright install chromium` một lần)
cd frontend && npm run test:e2e
```

Hai tầng test frontend làm hai việc khác nhau: **vitest (jsdom)** kiểm tra các hàm
render tạo ra cái gì, còn **Playwright** kiểm tra những thứ chỉ trình duyệt thật
mới có — validation gốc của form, bố cục ở một chiều rộng cụ thể, focus và bàn phím.

## Database

SQLite is used by default; the database file and the `schedules` table are
created automatically at `data/app.db` when the app starts.

Nếu database được tạo bằng phiên bản cũ hơn, app sẽ báo lỗi khi khởi động vì bảng
`schedules` thiếu cột (`timezone` từ Round 3, `country` từ Round 4). Nâng cấp bằng:

```bash
cd backend
python migrate.py --timezone Asia/Ho_Chi_Minh   # múi giờ các bản ghi cũ đã nhập
```

Các cột được thêm qua nhiều round (`timezone`, `country`, `reminder_minutes`,
`notified_at`, `google_event_id`, …) đều do script này bổ sung.

Script này thêm các cột còn thiếu, đổi các mốc thời gian cũ (giờ địa phương)
sang UTC, và đổi tên múi giờ cũ về tên chuẩn (`Asia/Saigon` → `Asia/Ho_Chi_Minh`)
— việc đổi tên không làm dịch chuyển bất kỳ thời điểm nào. Chạy lại lần nữa là no-op. The `data/` directory is tracked but its
`*.db` contents are ignored by Git. Point `DATABASE_URL` elsewhere in `.env` to
use a different location or engine.

## Environment variables

All variables are documented in [`.env.example`](.env.example). Copy it to
`.env` and fill in real values there — `.env` and any credential files are
git-ignored and must never be committed. Only variables prefixed with `VITE_`
are exposed to browser code.
