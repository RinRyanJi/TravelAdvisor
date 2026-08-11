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
├── api.py             # FastAPI 服務層（/plan, /reschedule, /health）
├── cli.py             # 命令列介面（demo / plan）
├── render.py          # 行程的文字化輸出
└── samples.py         # 離線示範/測試用的內建資料
```

---

## 快速開始

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

### 3. 以 API 服務執行

```bash
uvicorn travel_advisor.api:app --reload
# POST /plan        —— 依 TripRequest 規劃（即時資料）
# POST /reschedule  —— 對既有行程套用突發狀況重排（離線、可預測）
# GET  /health
```

### 4. 執行測試

```bash
pytest            # 23 個測試，涵蓋模型、引擎、重排、provider 解析
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

**本次已完成（MVP：核心排程引擎 + 資料模型）**
- ✅ 完整領域資料模型（行程請求、地點、開放時間、行程、突發狀況）
- ✅ 排程引擎：興趣配對、地理鄰近路線、開放時間、交通時間、用餐、節奏、天氣感知
- ✅ 動態重排：四類突發狀況 + 變更說明
- ✅ 真實開放資料 providers（皆有解析測試）
- ✅ CLI（離線 demo + 即時 plan）與 FastAPI 服務骨架

**下一步（尚未實作）**
- ⏳ 真正的訂位/訂票整合（航班、住宿、門票）與價格
- ⏳ 行程持久化（資料庫）與使用者帳號
- ⏳ 完整的 OSM `opening_hours` 解析（目前簡化處理，見 `providers/poi.py`）
- ⏳ 前端網頁介面
- ⏳ 天氣以外的即時事件來源（航班狀態、交通告警）自動觸發重排
