# TravelAdvisor — 自動化旅遊行程排定服務

> 輸入「去哪裡、幾天、想玩什麼」，自動產生一份對接**真實最新資訊**的每日行程；
> 遇到臨時突發狀況（景點關閉、下雨、延誤、交通取消）時，能重新計算並更新整條行程。

這是專案的第一個里程碑：**核心排程引擎 + 資料模型**，並以真實的開放資料 API
（天氣、地點、路線）作為資料來源。

---

## 專案目標的三個層次

| 層次 | 說明 | 對應程式 |
| --- | --- | --- |
| **規劃層** | 依條件（目的地、天數、預算、興趣、人數、節奏）自動排出每日行程 | `engine/` |
| **真實資訊層** | 行程內容對接真實且最新的資料，而非虛構 | `providers/` |
| **動態調整層** | 突發狀況發生時，重新計算並更新對應行程 | `engine/rescheduler.py` |

設計原則：**引擎不依賴任何特定外部 API**。所有外部資料都藏在
`providers/base.py` 定義的小型 `Protocol` 之後，未來要換成商用 API
（Google Places、航班 GDS…）只需寫一個滿足相同介面的類別，引擎完全不動。

---

## 架構

```
travel_advisor/
├── models/            # 領域資料模型（純資料，可序列化，不含任何邏輯）
│   ├── place.py       #   Coordinates / OpeningHours / PointOfInterest / PlaceCategory
│   ├── trip.py        #   TripRequest / Interest / Pace
│   ├── weather.py     #   DayWeather / WeatherCondition
│   ├── itinerary.py   #   Itinerary / DayPlan / ScheduledItem
│   └── disruption.py  #   Disruption / RescheduleResult
├── providers/         # 對接真實外部資料的轉接器（皆為免金鑰開放服務）
│   ├── base.py        #   Protocol 介面：Geocoding / Poi / Weather / Routing
│   ├── geocoding.py   #   OpenStreetMap Nominatim
│   ├── poi.py         #   OpenStreetMap Overpass
│   ├── weather.py     #   Open-Meteo
│   └── routing.py     #   OSRM（含 haversine 離線後備）
├── engine/            # 排程與重排的核心邏輯
│   ├── timeline.py    #   單日時間軸鋪排（開放時間、交通、用餐、天氣）
│   ├── scheduler.py   #   從請求 + 候選地點建立完整行程
│   ├── rescheduler.py #   吸收突發狀況並重排，附上「變更說明」
│   └── planner.py     #   端到端：把真實 providers 接上 scheduler
├── db/                # 持久化層（SQLAlchemy）
│   ├── models.py      #   ORM 資料表：UserRow / ItineraryRow
│   ├── session.py     #   Database（引擎/連線管理，可注入測試用記憶體 DB）
│   └── repository.py  #   UserRepository / ItineraryRepository（ORM ↔ 領域模型）
├── routers/           # HTTP 路由（依資源分組）
│   ├── auth.py        #   註冊 / 登入 / 目前使用者
│   └── itineraries.py #   行程 CRUD + 重排並存檔
├── security.py        # 密碼雜湊（PBKDF2）與 JWT 權杖
├── deps.py            # FastAPI 相依：DB session、目前使用者、planner
├── schemas.py         # API 請求/回應模型
├── demo.py            # 離線示範用 planner（用內建資料規劃，不需連外）
├── api.py             # FastAPI 應用工廠（組裝 DB + planner + routers + 前端）
├── static/
│   └── index.html     # 單頁前端（原生 HTML/CSS/JS，無需建置工具）
├── cli.py             # 命令列介面（demo / plan）
├── render.py          # 行程的文字化輸出
└── samples.py         # 離線示範/測試用的內建資料
```

---

## 快速開始

### 0. GitHub Codespaces（開啟即用，零設定）

本專案已內建 [Dev Container](.devcontainer/devcontainer.json) 設定，直接在
GitHub 上點 **Code → Codespaces → Create codespace** 即可：

1. 容器建立時會自動執行 `pip install -e ".[dev]"` 安裝所有相依套件。
2. 附加（attach）後會自動在背景啟動 `uvicorn`（`0.0.0.0:8000`）。
3. 連接埠 8000 會自動轉發並開啟預覽視窗——**開啟 Codespace 就能直接看到網頁介面。**

啟動記錄可用 `cat /tmp/uvicorn.log` 查看；若要手動重跑：

```bash
uvicorn travel_advisor.api:app --host 0.0.0.0 --port 8000 --reload
```

> 網頁預設走「離線示範模式」（內建京都資料），因此就算 Codespace 的出站網路政策
> 擋掉開放資料主機也能完整體驗；取消勾選離線模式才會連外。

### 本機安裝

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### 1. 離線示範（不需網路，最快看到成果）

用內建的京都資料排一趟三天行程，接著模擬「第二天下雨」自動重排：

```bash
travel-advisor demo
```

會先印出行程，再印出重排後的版本——下雨的那天會自動把戶外景點換成室內景點。

### 2. 真實行程（串接即時開放資料）

```bash
travel-advisor plan \
  --destination "Kyoto, Japan" \
  --start 2026-09-01 --end 2026-09-03 \
  --interests history,art,nature \
  --pace balanced
```

> ⚠️ 這條路徑需要對外連到開放資料服務（Nominatim / Overpass / Open-Meteo / OSRM）。
> 若你的執行環境有 egress 網路政策封鎖這些主機，會回報連線錯誤——這是環境政策，
> 不是程式問題；請改用 `demo`，或在允許這些主機的環境執行。
> 所有 provider 對真實 API 回應格式的解析都有單元測試覆蓋（`tests/test_providers.py`）。

### 3. 網頁介面（最直觀）

```bash
uvicorn travel_advisor.api:app --reload
# 用瀏覽器開啟 http://localhost:8000
```

在網頁上即可：註冊/登入 → 填表規劃行程 → 檢視每日行程 →
點按鈕模擬突發狀況（下雨、景點關閉、延誤、交通取消）並**即時看到重排結果與變更說明**。
預設勾選「離線示範模式」用內建京都資料，不需連外即可完整體驗；
取消勾選則走即時開放資料（需對外網路）。

### 4. 以 API 服務執行（含帳號與行程儲存）

```bash
uvicorn travel_advisor.api:app --reload
```

| 方法 | 路徑 | 說明 | 需登入 |
| --- | --- | --- | --- |
| POST | `/auth/register` | 建立帳號 | |
| POST | `/auth/token` | 登入，回傳 JWT bearer token | |
| GET  | `/auth/me` | 目前使用者 | ✔ |
| POST | `/itineraries` | 依 TripRequest 規劃並存檔（加 `?sample=true` 用離線資料） | ✔ |
| GET  | `/itineraries` | 列出使用者的所有行程 | ✔ |
| GET  | `/itineraries/{id}` | 取得單一行程（含完整每日計畫） | ✔ |
| POST | `/itineraries/{id}/reschedule` | 套用突發狀況重排，存為新版本 | ✔ |
| DELETE | `/itineraries/{id}` | 刪除行程 | ✔ |
| POST | `/reschedule` | 無狀態、離線的重排工具 | |
| GET  | `/health` | 健康檢查 | |

典型流程：

```bash
# 註冊並登入取得 token
curl -X POST localhost:8000/auth/register -H 'content-type: application/json' \
  -d '{"email":"me@example.com","password":"password123"}'
TOKEN=$(curl -s -X POST localhost:8000/auth/token -H 'content-type: application/json' \
  -d '{"email":"me@example.com","password":"password123"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# 規劃並儲存一趟行程（即時資料）
curl -X POST localhost:8000/itineraries -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"destination":"Kyoto, Japan","start_date":"2026-09-01","end_date":"2026-09-03","interests":["history","art"]}'

# 之後遇到下雨，對已存行程重排（離線、存為新版本）
curl -X POST localhost:8000/itineraries/<id>/reschedule -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"type":"weather_rain","date":"2026-09-02"}'
```

行程與候選地點一併存入資料庫，因此對已儲存行程的重排是**離線且可預測**的
（不需再次連外）。互動式 API 文件在服務啟動後見 `http://localhost:8000/docs`。

#### 環境變數

| 變數 | 預設 | 說明 |
| --- | --- | --- |
| `TRAVELADVISOR_DATABASE_URL` | `sqlite:///./traveladvisor.db` | 資料庫連線；可換成 PostgreSQL |
| `TRAVELADVISOR_SECRET` | （開發用預設值） | JWT 簽章密鑰，正式環境務必自行設定 |

### 5. 執行測試

```bash
pytest            # 37 個測試：模型、引擎、重排、provider 解析、持久化、認證 API、前端
```

---

## 動態調整：目前支援的突發狀況

`Rescheduler` 針對每種狀況重排當日（或後續）行程，並回傳一份人類可讀的變更說明
（`RescheduleResult.changes`），讓旅客清楚知道行程如何被調整。

| 狀況 | `DisruptionType` | 處理方式 |
| --- | --- | --- |
| 景點臨時關閉 | `POI_CLOSED` | 移除該點，從候選池挑同類替代點補上，重排當日 |
| 當天下雨 | `WEATHER_RAIN` | 將當日導向室內景點，換掉塞不下的戶外點 |
| 行程延誤 | `DELAY` | 把後續行程整體往後推，超出當日時間的自動捨去 |
| 交通取消 | `TRANSPORT_CANCELLED` | 清空受影響當日供改訂，並將受困景點嘗試移到後續日期 |

重排是**純函式且不觸網**：不會改動原行程（回傳新的副本），給定相同輸入就得到相同結果。

---

## 真實資料來源（皆免金鑰）

| 資料 | 服務 | 授權/限制 |
| --- | --- | --- |
| 地理編碼（地名→座標） | [Nominatim](https://nominatim.org/) | OSM 使用規範，需 User-Agent（已設定） |
| 景點/地點 | [Overpass API](https://overpass-api.de/) | OpenStreetMap 資料 |
| 天氣預報 | [Open-Meteo](https://open-meteo.com/) | 免費，約 16 天預報視窗 |
| 交通時間 | [OSRM](http://project-osrm.org/) | 公用路由，失敗時自動退回 haversine 估計 |

選用免金鑰開放服務的用意：**即時、真實、且不需你先申請一堆 API 金鑰就能跑**。
要換成商用資料源時，實作對應的 `Protocol` 即可。

---

## 里程碑與後續規劃

**里程碑一：核心排程引擎 + 資料模型**
- ✅ 完整領域資料模型（行程請求、地點、開放時間、行程、突發狀況）
- ✅ 排程引擎：興趣配對、地理鄰近路線、開放時間、交通時間、用餐、節奏、天氣感知
- ✅ 動態重排：四類突發狀況 + 變更說明
- ✅ 真實開放資料 providers（皆有解析測試）
- ✅ CLI（離線 demo + 即時 plan）與 FastAPI 服務骨架

**里程碑二：行程持久化 + 使用者帳號**
- ✅ 資料庫層（SQLAlchemy，SQLite 預設，可換 PostgreSQL）
- ✅ 使用者帳號：註冊、登入、密碼雜湊（PBKDF2）、JWT 認證
- ✅ 行程 CRUD API，含所有權隔離（使用者只能看到自己的行程）
- ✅ 對已儲存行程套用突發狀況並存為新版本（離線、可預測）

**里程碑三：前端網頁介面**
- ✅ 單頁前端（原生 HTML/CSS/JS，由 FastAPI 直接服務，無需建置工具）
- ✅ 註冊/登入、填表規劃、每日行程檢視
- ✅ 一鍵模擬四類突發狀況並即時看到重排結果與變更說明
- ✅ 離線示範模式（`?sample=true`），沙箱環境也能完整體驗

**下一步（尚未實作）**
- ⏳ 真正的訂位/訂票整合（航班、住宿、門票）與價格
- ⏳ 完整的 OSM `opening_hours` 解析（目前簡化處理，見 `providers/poi.py`）
- ⏳ 天氣以外的即時事件來源（航班狀態、交通告警）自動觸發重排
