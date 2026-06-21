# AGENTS.md — deploy/

**唯一上線來源**：GitHub `rock903400-byte/CU-Analysis-v1` → Streamlit Cloud 自動 rebuild（1–3 分）
線上 app: <https://cu-analysis-v1-vizgphhwjwmfkvrrktdjte.streamlit.app>

## 指令

```bash
streamlit run app.py                                          # 開發
pytest tests/ -v                                              # 全部（75 個）
python tests/sim_100_journeys.py                              # UI/UX 旅程模擬（AppTest）
python tests/probe_cloud.py                                   # 線上 HTTP 探測
```

```bash
# Linux / macOS
make fmt       # black
make lint      # flake8
make type      # mypy
make test      # pytest -v
make verify    # lint + type + test（一錯就停）
make all       # fmt + verify

# Windows (pwsh 7)
pwsh scripts/all.ps1
```

mypy 只掃 `app.py config.py common/ components/ data/ services/ views/ charts/`，跳過 `tests/`。
mypy 寬鬆：`ignore_missing_imports=true`、`disallow_untyped_defs=false`，關閉 `var-annotated` / `call-overload` / `attr-defined`。其餘 `arg-type` 型別錯誤要修。

## 架構

`app.py` 主入口，執行順序：
1. `_DEFAULTS` session state 初始化（**所有 key 都在這定義**）
2. 雲端預載：`?file=xxx` → `cloud.py` → `excel_processor.py` → `st.session_state.preloaded_data`
3. `?csv=xxx` → `csv_processor.py` → `st.session_state.preloaded_csv`
4. 登入關卡 → 資料過濾→ 路由（overview / war_room）

```
app.py
 ├─ components/    onboarding, charts, metrics
 ├─ views/         overview（風險診斷）, war_room（財務戰情室）
 ├─ services/      auth, cloud（Supabase）, diagnosis_service（燈號）, finance_service（YoY/瀑布）
 ├─ data/          excel_processor（Excel→5-tuple）, csv_processor（CSV→DataFrame）
 └─ common/        classifier, cleaning, constants, dates, thresholds, utils
```

## 業務規則（不可任意修改）

- 個社模式用「本社」標籤；區會/管理員用「區域平均」或「全台平均」
- 股市燈號：紅漲＝好、綠跌＝壞（社員/股金/收入/淨利/淨值比），綠漲＝壞、紅跌＝壞（開支/逾放/負債比/支出）
- 風險燈號字串在 `common/classifier.py` 與 `tests/test_classifier.py` **兩邊都要同步**（hardcode 字串）
- CSV 年月是字串 `YYYYMM`（非 datetime），`diagnosis_service.py` 自行 `pd.to_datetime(format="%Y%m")`
- `preloaded_data` 為 5-tuple：`(data, df_m, df_l, raw_bytes, region_map)`，索引 0‑4
- `df_l` 可能為空：過濾後先 guard 再算 YoY，否則 `NaT - DateOffset` 噴 TypeError
- `st.query_params.get("file")` 只讀第一個值（Streamlit 限制）
- MAX_ATTEMPTS = 5（`config.py`），admin 密碼 fallback `"666"`（無 secret 時）

## 易踩的坑

- **`excel_processor.py:process_excel_final`**：`_get_value` 是 `common.dates.get_value` 的 alias，**不要再寫巢狀同名函式**（過去 bug：誤用巢狀 `get_v` 導致共享連結全壞）。提撥率可能缺欄，先 `if "提撥率" in df_l_raw.columns` 檢查。百分比清洗（`defensive_clean_series`）每欄規則不同。Cache buster：函式內 `_VER` 與模組層 `_CACHE_VER` **兩處都要 bump**。合併鍵一律用「社號」。改完必跑 `pytest tests/test_excel_processor.py::TestProcessExcelFinal`
- **`views/` 資料 Guard**：所有使用 `df_m` 或 `df_l` 的地方必須先 `if x is None: return` 再呼叫 `.empty`，否則 AppTest 和正式環境都會 crash
- **`SafeSessionState` 沒有 `.get()`**：`tests/` 中 `at.session_state` 是 `SafeSessionState` 代理，不支援 `.get()`。必須用 `"key" in at.session_state and at.session_state["key"]` 或 `try/except KeyError`。誤用會噴 `AttributeError: get not found in session_state`，整趟旅程變 `completed=False`
- **`load_thresholds`**（`common/thresholds.py`）：從 `secrets["thresholds"]` 讀，缺欄 fallback 到 `DEFAULT_THRESHOLDS`
- **生成分享連結 debounce**：`app.py` 用 `share_generating` 鎖定 + disabled 按鈕 + `try/finally` 重置；測試注意 disabled button 無法被 AppTest click
- **`@st.cache_data`** 跨測試可能互相干擾，新增 case 後建議跑全套
- **`st.session_state` 內 `preload_err` 成功載入後會自動清空**（L112），若需手動 reset 可 `st.session_state.pop("preload_err", None)`
- **Streamlit `1.56`** 對 `use_container_width=True` 有 deprecation warning（不影響功能）
- **URL 參數長度驗證**：`_MAX_PARAM_LEN = 256`（`app.py:69`），超過則 `st.error` 並忽略

## 測試

| 檔案 | 性質 |
|------|------|
| `test_*.py`（6 個） | pytest 75 cases |
| `sim_100_journeys.py` | AppTest 70 旅程模擬，產 `sim_100_REPORT.md` |
| `sim_1000_users.py` / `sim_10k_users.py` | 服務層模擬，產 `sim_*_results.json` |
| `probe_cloud.py` | 線上 HTTP 探測（85 probes） |

- `tests/test_classifier.py` 硬編碼狀態字串，改 `common/classifier.py` 要同步
- 元素改動後更新 `manual_human_journey.py` 的預期計數

## 部署

1. `git add → commit → push main`
2. Streamlit Cloud 自動 rebuild
3. 勿 `--force` push
4. Secrets 在 Streamlit Cloud Dashboard 設定（模板 `.streamlit/secrets_template.toml`）
