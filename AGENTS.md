# AGENTS.md — deploy/

**唯一上線來源**：GitHub `rock903400-byte/CU-Analysis-v1` → Streamlit Cloud 自動 rebuild（1–3 分）
線上 app: <https://cu-analysis-v1-vizgphhwjwmfkvrrktdjte.streamlit.app>

---

## 指令

```bash
streamlit run app.py                                          # 開發
pytest tests/ -v                                              # 全部（75 個）
pytest tests/test_excel_processor.py::TestProcessExcelFinal   # 端到端驗證
python tests/sim_100_journeys.py                              # UI/UX 旅程模擬 (本地 AppTest)
python tests/probe_cloud.py                                   # 線上環境探測 (HTTP probe)
```

### 程式碼品質（Windows/macOS/Linux）

```bash
# Linux / macOS / GNU make Windows：直接 make
make fmt       # black
make lint      # flake8
make type      # mypy
make test      # pytest -v
make verify    # lint + type + test（一錯就停）
make all       # fmt + verify

# Windows 無 make → pwsh scripts/
pwsh scripts/all.ps1               # 一鍵全跑
pwsh scripts/format.ps1            # 個別
pwsh scripts/lint.ps1
pwsh scripts/type.ps1
pwsh scripts/test.ps1
```

工具：`black` + `flake8`（透過 `Flake8-pyproject` 讀 `pyproject.toml`） + `mypy`（dev-only，`requirements-dev.txt`）。
mypy 寬鬆：`ignore_missing_imports=true`、`disallow_untyped_defs=false`，關閉 `var-annotated` / `call-overload` / `attr-defined`（Streamlit + plotly 噪音）。其余 `arg-type` 型別錯誤要修。

---

## 模組地圖

```
app.py                    主入口（路由、session state、登入 / 登出）
 ├─ components/            歡迎頁 + 戰情室圖表 + KPI 卡
 ├─ views/                 風險診斷（overview.py） + 財務戰情室（war_room.py）
 ├─ services/              auth（登入）、cloud（Supabase）、diagnosis_service（燈號）、finance_service（YoY/瀑布）
 ├─ data/                  excel_processor（Excel→5‑tuple）+ csv_processor（CSV→DataFrame）
 └─ common/                classifier（分類引擎） + cleaning + constants + dates + thresholds + utils
```

雲端預載：`?file=xxx` → `cloud.py` → `excel_processor.py` → `preloaded_data`，`?csv=xxx` → `csv_processor.py` → `preloaded_csv`。

---

## 高風險：`process_excel_final`（`data/excel_processor.py`）

- **`_get_value`**（alias of `common.dates.get_value`）：**不要**再寫巢狀同名函式（過去 bug：誤用巢狀 `get_v` 導致共享連結全壞）
- **提撥率**可能缺欄：先 `if "提撥率" in df_l_raw.columns` 檢查，否則 `fillna(0)` 崩潰
- **百分比清洗**（`defensive_clean_series`）每欄規則不同，改前讀程式碼
- **Cache buster**：函式內 `_VER` 與模組層 `_CACHE_VER` **兩處都要 bump**
- 年度基準強制 12 月快照（`T0 = max(dec_dates)`）
- 合併鍵一律用「社號」（防更名）
- 「收支比」自動 rename 為「開支比」，後續只認「開支比」
- 改完必跑 `pytest tests/test_excel_processor.py::TestProcessExcelFinal`

---

## 業務規則（不可任意修改）

- 個社模式 4 個核心指標標籤用「本社」；區會/管理員用「區域平均」或「全台平均」
- 股市紅綠燈：紅漲＝好、綠跌＝壞（社員/股金/收入/淨利/淨值比），綠漲＝壞、紅跌＝壞（開支/逾放/負債比/支出）
- 風險燈號字串在 classifier.py 與 test_classifier.py 都 hardcode，兩邊要同步
- CSV 年月是字串 `YYYYMM`（非 datetime），`diagnosis_service.py` 自行 `pd.to_datetime(..., format="%Y%m")`
- `df_l` 可能為空：過濾後先 guard 再算 YoY，否則 `NaT - DateOffset` 噴 TypeError
- `preloaded_data` 為 5-tuple：`(data, df_m, df_l, raw_bytes, region_map)`，索引 0‑4
- `st.query_params.get("file")` 只讀第一個值

---

## 易踩的坑

- **`auth.py`**：admin 密碼 fallback `"666"`（無 secret 時），最近已修登出時清 `pwd_input`
- **`safe_secrets()`**（`config.py`）：只是 `return st.secrets`，不要叫私有 `_parse()`
- **`download_file_from_storage`** 已接受 `Client | None`；`init_supabase()` 回 None 會自己 raise，呼叫端不需 guard
- **`config.py:48` `load_thresholds`** 從 `secrets["thresholds"]` 讀，缺欄 fallback 到 `common/thresholds.py:DEFAULT_THRESHOLDS`
- **「生成分享連結」** 連點會上傳多份到 Supabase（無 debounce）
- **`preload_err`** 成功載入後會自動清空（最近修復）；若需手動 reset 可設 `st.session_state.pop("preload_err", None)`
- **側邊欄手機版**：`.sidebar-overlay.visible` CSS 已存在但無 JS 觸發遮罩，暫時只靠 aria-expanded
- **Streamlit 1.56** 對 `use_container_width=True` 有 deprecation warning（2026，不影響功能）
- **資料 Guard**：`views/` 內所有使用 `df_m` 或 `df_l` 的地方必須先檢查 `is None` 再呼叫 `.empty`，否則會觸發 AttributeError 崩潰

---

## 測試文件說明

| 檔案 | 性質 |
|------|------|
| `test_*.py`（6 個） | pytest 自動抓，共 75 個 case |
| `manual_human_journey.py` | 手動 AppTest 腳本（`python tests/manual_human_journey.py`）|
| `sim_100_journeys.py` | UI/UX 旅程模擬（$\sim$100 cases），產出 `sim_100_REPORT.md` |
| `sim_1000_users.py` / `sim_10k_users.py` | 服務層模擬測試（`python tests/sim_1000_users.py`），會寫 `sim_*_results.json` |
| `probe_cloud.py` | 線上環境 HTTP 探測，驗證 XSS/Crash/效能 |

- `tests/test_classifier.py` 硬編碼狀態字串（如 `"🚨 特別關懷"`），改 `common/classifier.py` 要同步
- `@st.cache_data` 跨測試可能互相干擾，新增 case 後建議跑全套
- onboarding 元素改動後更新 `manual_human_journey.py` 的預期計數

---

## 部署

1. 改 `deploy/` → `git add` → `git commit` → `git push main`
2. Streamlit Cloud 自動 rebuild
3. 勿 `--force` push
4. `requirements.txt` 已 pin 死（`streamlit==1.56.0`），升級手動改版號
5. Secrets 在 Streamlit Cloud Dashboard 設定，模板 `.streamlit/secrets_template.toml`
