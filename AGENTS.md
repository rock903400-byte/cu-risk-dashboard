# AGENTS.md — deploy/

工作目錄 `C:\Users\user\Desktop\穿透\deploy` 是 GitHub repo `rock903400-byte/CU-Analysis-v1` 的**唯一上線來源**。
線上 app: <https://cu-analysis-v1-vizgphhwjwmfkvrrktdjte.streamlit.app>

父層 `..\CLAUDE.md` 涵蓋全工作區（含獨立子系統 `..\下載工具\` 與歷史備份 `..\Credit-Union-Analysis new\`），本檔只談 deploy/。

---

## 指令

```bash
# 啟動 app
streamlit run app.py

# 跑全部測試
pytest tests/ -v

# 單一檔案
pytest tests/test_excel_processor.py

# 單一 case
pytest tests/test_excel_processor.py::TestProcessExcelFinal::test_returns_five_tuple_with_correct_shapes
```

**無** lint / typecheck / formatter。要加之前先問使用者。

---

## 資料流（兩條獨立 pipeline）

```
app.py
 ├─ ?file=xxx  → services/cloud.py → data/excel_processor.py ①
 │                → st.session_state["preloaded_data"]
 ├─ ?csv=xxx   → data/csv_processor.py → st.session_state["preloaded_csv"]
 ├─ 上傳 Excel/CSV → 直接寫入 session_state
 └─ render:
      ├─ views/overview.py（風險診斷，吃 Excel）
      └─ views/war_room.py（財務戰情室，吃 CSV）
```

① `process_excel_final()` 是整個雲端預載路徑的瓶頸，被 `@st.cache_data` 包裝。pytest 內會印 "No runtime found" 警告，正常現象，無視即可。

---

## 關鍵行為變更（近期）

- **個社模式經營總覽**：四個指標（社員總數、股金總額、開支比、逾放比）改顯示該社自己的數值，標籤顯示「本社」；區會/管理員維持區域/全台平均
- **股市紅綠燈邏輯**：全站 metric 紅漲=好、綠跌=壞（社員成長、股金增、收入增、淨利增、淨值比增）；綠漲=壞、紅跌=好（開支比升、逾放比升、負債比升、支出增）
- **風險燈號顏色維持不變**：特別關懷=紅、穩健=綠、趨勢表風險著色

---

## 部署

1. 改 `deploy/` 內檔案 → `git add` → `git commit` → `git push main`
2. Streamlit Cloud 自動 rebuild（1–3 分鐘）
3. **勿 `--force` push**；Windows 上設 `$env:GIT_EDITOR="true"` 跳過 vim

Secrets 在 Streamlit Cloud Dashboard 設定，模板見 `.streamlit/secrets_template.toml`。
所有門檻值統一放在 `[thresholds]` 區塊下（`config.py:58` 用 `_secrets.get("thresholds", {}).get(k, d)` 統一讀取）。

---

## 測試（66 個 pytest）

- `tests/test_classifier.py` 內狀態字串（如 `"🚨 重點輔導"`）是硬編碼，改 `data/classifier.py` 的 emoji / 文字要同步更新
- `tests/test_excel_processor.py::TestProcessExcelFinal` 是 `process_excel_final` 的端對端驗證，改該函式後必跑
- `@st.cache_data` 跨測試可能互相干擾，新增 case 後建議跑全套
- Streamlit Cloud 可能用較舊 Python（3.10+），型別註解用 `Optional[X]` 而非 `X | None`

---

## ★ 高風險函式：`process_excel_final`（`data/excel_processor.py:21`）

**過去 bug 實錄**：曾誤用巢狀 `get_v` 而非模組層 `_get_value`，導致共享連結全壞且錯誤訊息誤導。

**規則**：
- 模組層已有 `_get_value(df, col, d)`（回傳 `float`），**不要**再寫巢狀同名函式
- 百分比欄位防禦性清洗（excel_processor.py:46-56）每欄規則不同，改前先讀註解
- **提撥率**欄位可能缺失（`excel_processor.py:59`），若不存在則 `.get("提撥率", 0)` 回傳純量導致 `.fillna(0)` crash → 先 `in columns` 檢查
- 修改後必跑 `pytest tests/test_excel_processor.py::TestProcessExcelFinal`

---

## 易踩的坑

- **合併鍵一律用「社號」不用「社名」**（防更名）
- **「收支比」→「開支比」**（`excel_processor.py:30` 自動 rename），後續邏輯只認「開支比」
- **年月底線強制 12 月**：風險診斷的年度基準是 12 月快照（`T0 = max(dec_dates)`）
- **`df_l` 可能為空**（`views/overview.py:41`）：過濾後若無放款資料，先 guard 再算 YoY，否則 `NaT - DateOffset` 會噴 TypeError
- **`safe_secrets()`**（`config.py:37`）不吃 `_parse()` 私有方法了，單純 `return st.secrets`
- **`st.query_params.get("file")` 是單值**，`?file=a&file=b` 只讀到第一個
- **勿修改 `..\Credit-Union-Analysis new\`**（歷史備份）
- **CSV 年月是字串（`YYYYMM`）非 datetime**：`csv_processor.py:11` 轉 `str`，`diagnosis_service.py` 需自行 `pd.to_datetime(..., format="%Y%m")`
- **`st.columns(4)` 手機版會擠壓**：CSS `@media (max-width: 640px)` 強制 `width: 100%` 已在 `config.py` 處理
- **側邊欄手機版需抽屜式**：`config.py` 有 `position: fixed` + `transform` 切換，依賴 `aria-expanded="true"`

---

## 其他參考

- 系統架構、術語規範、session state 鍵值清單、`p` dict 鍵值定義 → `..\CLAUDE.md`
- 版本號管理：`_CACHE_VER`（spinner 顯示）+ `_VER`（bytecode cache buster），兩處都要 bump
