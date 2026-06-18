# AGENTS.md — deploy/

工作目錄 `C:\Users\user\Desktop\穿透\deploy` 是 GitHub repo `rock903400-byte/CU-Analysis-v1` 的**唯一上線來源**。
線上 app: <https://cu-analysis-v1-vizgphhwjwmfkvrrktdjte.streamlit.app>

父層 `..\CLAUDE.md` 涵蓋全工作區（含獨立子系統 `..\下載工具\` 與歷史備份 `..\Credit-Union-Analysis new\`），本檔只談 deploy/。

---

## 指令

```bash
# 啟動 app
streamlit run app.py

# 跑全部測試（69 個 case）
pytest tests/ -v

# 單一檔案
pytest tests/test_excel_processor.py

# 單一 case
pytest tests/test_excel_processor.py::TestProcessExcelFinal::test_returns_five_tuple_with_correct_shapes
```

### 程式碼品質（format / lint / typecheck）

工具：`black` + `flake8` + `mypy`（dev-only，不進 `requirements.txt`）。
config 統一在 `pyproject.toml`（注意：flake8 透過 `Flake8-pyproject` 插件讀這檔，原本的 `.flake8` 已刪）。
dev 安裝：`pip install -r requirements-dev.txt`。

```bash
# Linux / macOS / 裝了 GNU make 的 Windows
make help       # 看所有 target
make fmt        # black 格式化
make fmt-check  # black --check（CI 用）
make lint       # flake8
make type       # mypy
make test       # pytest -v
make review     # git status + diff stat
make verify     # lint + type + test（一錯就停）
make all        # fmt + verify

# Windows 沒裝 make → 用 PowerShell scripts
pwsh scripts/all.ps1               # 一鍵跑全部
pwsh scripts/all.ps1 -SkipFmt      # 跳過格式化
pwsh scripts/all.ps1 -SkipType     # 跳過型別檢查
pwsh scripts/format.ps1            # 個別跑
pwsh scripts/lint.ps1
pwsh scripts/type.ps1
pwsh scripts/test.ps1
```

**mypy 寬鬆設定**（`pyproject.toml [tool.mypy]`）：`ignore_missing_imports=true`、`disallow_untyped_defs=false`，關閉 `var-annotated` / `call-overload` / `attr-defined`（Streamlit + plotly 噪音）。其餘錯誤（特別是 `arg-type`）要修。

---

## 模組地圖（兩條 pipeline + 共用層）

```
app.py                            主入口（路由、session state、登入）
 ├─ components/onboarding.py      歡迎頁 + 首次使用 tip 橫幅（components/onboarding.py:9, :178）
 ├─ views/overview.py             風險診斷（5 個 tab，吃 Excel）
 ├─ views/war_room.py             財務戰情室（6 個 tab，吃 CSV）
 ├─ components/charts.py          戰情室圖表（瀑布、YoY 異常、排名）
 ├─ components/metrics.py         KPI 卡
 ├─ services/
 │   ├─ auth.py                   登入（含 5 次鎖定；無 admin secret 時 fallback "666"）
 │   ├─ cloud.py                  Supabase init / download（@st.cache_resource / @st.cache_data）
 │   ├─ diagnosis_service.py      財報比率 + 燈號 + 同期月份公平比對
 │   └─ finance_service.py        YoY、瀑布、損益快照純函數
 ├─ data/
 │   ├─ excel_processor.py        ① Excel → 5-tuple（瓶頸函式,見下方高風險段）
 │   └─ csv_processor.py          CSV → DataFrame
 └─ common/                       共用底層（**所有 import 直接走 common/，不要 data/Utils 風格的 shim**）
     ├─ classifier.py             風險 2/5 分類引擎（classify, classify_code）
     ├─ cleaning.py               defensive 清洗（給歷史 Excel 用）
     ├─ constants.py              顏色 / 工作表名 / 會計科目常數
     ├─ dates.py                  convert_minguo_date（4/5 位數）、get_value（年底取數）
     ├─ thresholds.py             門檻預設值 + 從 secrets 載入
     └─ utils.py                  safe_div, format_large_number, fmt_pct

雲端分享路徑：
  ?file=xxx  → services/cloud.py → data/excel_processor.py ① → st.session_state["preloaded_data"]
  ?csv=xxx   → data/csv_processor.py                        → st.session_state["preloaded_csv"]
  上傳 Excel/CSV                                                  → 直接寫入 session_state
```

① `process_excel_final()` 是整個雲端預載路徑的瓶頸，被 `@st.cache_data` 包裝。pytest 內會印 "No runtime found" 警告，正常現象，無視即可。

---

## Session State 鍵值（app.py:40-59 附近）

完整清單見 `..\CLAUDE.md`；deploy/ 內特有的：

| Key | 用途 | 預設 |
|-----|------|------|
| `preloaded_data` | Excel 解析後的 5-tuple `(data, df_m, df_l, raw_bytes, region_map)` | `None` |
| `preloaded_csv` | CSV 解析後的 `(df, raw_bytes)` | `None` |
| `preloaded_passwords` | 從 Excel「區域分類表」讀出的 `{密碼: {name, region}}` | `{}` |
| `nav_selection` | 當前 tab 文字 | `"📊 社務診斷"` |
| `is_district_office` | True=區會模式 / False=個社或 admin | `False` |
| `confirm_logout` | 登出二次確認中 | `False` |
| `xl_msg` / `csv_msg` | 上傳成功/失敗訊息持久顯示 | `None` |
| `preload_err` | 雲端預載失敗訊息（render_login_page 內顯示） | — |

---

## 業務規則（不可任意修改）

- **個社模式經營總覽**：4 個核心指標（社員總數、股金總額、開支比、逾放比）顯示「本社」自身數值，標籤用「本社」；區會/管理員維持區域/全台平均（`views/overview.py:44-50` 附近）
- **股市紅綠燈**：紅漲＝好、綠跌＝壞（社員成長、股金增、收入增、淨利增、淨值比增）；綠漲＝壞、紅跌＝好（開支比升、逾放比升、負債比升、支出增）
- **風險燈號**：特別關懷=紅、流動性緊繃=橘、資金閒置=藍、穩健模範=綠、一般狀態=灰 — 變更要同步改 `tests/test_classifier.py`（硬編碼字串）
- **年月底線**：風險診斷的年度基準強制 12 月快照（`T0 = max(dec_dates)`，見 `data/excel_processor.py:83-86` 附近）
- **合併鍵一律用「社號」不用「社名」**（防更名）
- **「收支比」自動 rename 為「開支比」**（`data/excel_processor.py:39` 附近），後續邏輯只認「開支比」

---

## 部署

1. 改 `deploy/` 內檔案 → `git add` → `git commit` → `git push main`
2. Streamlit Cloud 自動 rebuild（1–3 分鐘）
3. **勿 `--force` push**；Windows 上設 `$env:GIT_EDITOR="true"` 跳過 vim

Secrets 在 Streamlit Cloud Dashboard 設定，模板見 `.streamlit/secrets_template.toml`。
所有門檻值統一放在 `[thresholds]` 區塊下 — `config.py:67` 的 `load_thresholds(_secrets)` 從 `secrets["thresholds"]` 讀，缺欄位時 fallback 到 `common/thresholds.py:DEFAULT_THRESHOLDS`。

`requirements.txt` **已 pin 死**（`streamlit==1.56.0` 等）。升級套件要手動改版號，不要讓 Streamlit Cloud 自動挑最新版。

---

## 測試

- 69 個 pytest 全部通過；每次改完跑 `pytest tests/ -v`
- `tests/test_excel_processor.py::TestProcessExcelFinal` 是 `process_excel_final` 的端對端驗證，**改該函式後必跑**
- `tests/test_classifier.py` 內狀態字串（如 `"🚨 特別關懷"`）是硬編碼，改 `common/classifier.py` 的 emoji / 文字要同步更新
- `@st.cache_data` 跨測試可能互相干擾，新增 case 後建議跑全套
- `tests/manual_human_journey.py` / `tests/manual_journey_tip.py` 是**手動 AppTest 腳本**（不以 `test_` 開頭，pytest 不會抓），用 `streamlit.testing.v1.AppTest` 模擬使用者視角；要跑就 `python tests/manual_*.py`
- Streamlit Cloud 可能用較舊 Python（3.10+），型別註解用 `Optional[X]` 而非 `X | None`
- 1.56 對 `use_container_width=True` 會 deprecation warning（2025-12-31 移除），目前不影響功能

---

## ★ 高風險函式：`process_excel_final`（`data/excel_processor.py:22`）

> 行號會隨改版漂移；`grep` 二次確認。

**過去 bug 實錄**：曾誤用巢狀 `get_v` 而非模組層 `_get_value`，導致共享連結全壞且錯誤訊息誤導。

**規則**：
- `common.dates.get_value`（被 import alias 成 `_get_value`，`common/dates.py:34` 附近，回傳 `float`）**不要**再寫巢狀同名函式
- 百分比欄位防禦性清洗（`data/excel_processor.py:57-66` 附近）每欄規則不同，改前先讀程式碼
- **提撥率**欄位可能缺失（`data/excel_processor.py:67` 附近）：`if "提撥率" in df_l_raw.columns` 先檢查，否則直接 assign 純量會被 `fillna(0)` 視為 Series 而 crash
- **cache buster**：函式內的 `_VER` 字串（`data/excel_processor.py:23`）與模組層 `_CACHE_VER`（`data/excel_processor.py:18`）**兩處都要 bump**，前者清 bytecode、後者清 spinner 顯示
- 修改後必跑 `pytest tests/test_excel_processor.py::TestProcessExcelFinal`

---

## 易踩的坑

- **`safe_secrets()`**（`config.py:48`）：**只是 `return st.secrets`**，不要再呼叫私有 `_parse()`（Streamlit 內部 API 會改）
- **`download_file_from_storage` 已接受 `Client | None`**（`services/cloud.py:24`）：若 `init_supabase()` 回 None 會自己 `raise ValueError`，呼叫端不需 guard
- **`st.query_params.get("file")` 是單值**（`app.py:65` 附近），`?file=a&file=b` 只讀到第一個；設計上只用單檔案
- **`df_l` 可能為空**（`views/overview.py:52`）：過濾後若無放款資料，先 guard 再算 YoY，否則 `NaT - DateOffset` 會噴 TypeError
- **CSV 年月是字串（`YYYYMM`）非 datetime**（`data/csv_processor.py:11` 轉 `str`），`services/diagnosis_service.py:21` 需自行 `pd.to_datetime(..., format="%Y%m")`
- **`st.columns(4)` 手機版會擠壓**：CSS `@media (max-width: 640px)` 強制 `width: 100%` 已在 `config.py:139-148` 處理
- **側邊欄手機版需抽屜式**：`config.py:155-198` 用 `position: fixed` + `transform` 切換，依賴 `aria-expanded="true"`
- **`st.session_state["preloaded_data"][3]`**（`app.py:204`）取的是 `raw_bytes`（4 號位）；別搞混 0-4 對應的 data/df_m/df_l/raw_bytes/region_map
- **不要寫 `data.utils` / `data.classifier` shim 檔**：這兩個檔已刪，所有 import 直接走 `common.*`
- **onboarding 模組**：新增 onboarding 元素時同步改 `tests/manual_journey_tip.py` 的預期數字（step/legend/cta 計數）
- **勿修改 `..\Credit-Union-Analysis new\`**（歷史備份）

---

## 其他參考

- **系統架構、術語規範、完整 session state 鍵值清單、`p` dict 鍵值定義** → `..\CLAUDE.md`
- **改版紀錄** → `CHANGELOG.md`（按時間倒序，新版在上）
- **給使用者看的訓練教材** → `docs/操作手冊.html` / `docs/training.html`
- **未來 OpenCode 接手提示**：本檔是給「還不熟 deploy/ 的 agent」看的,看完應能避免 80% 的踩坑;若發現新坑請補上
