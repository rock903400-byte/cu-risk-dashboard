# AGENTS.md — deploy/

工作目錄 `C:\Users\user\Desktop\穿透\deploy` 是 GitHub repo `rock903400-byte/CU-Analysis-v1` 的**唯一上線來源**。線上 app: <https://cu-analysis-v1-vizgphhwjwmfkvrrktdjte.streamlit.app>。

> 父層 `..\CLAUDE.md` 涵蓋全工作區（含 `下載工具\` 與 `Credit-Union-Analysis new\` 兩個獨立子系統），本檔只談 deploy/ 本身。

---

## 1. Repo 邊界（必看）

| 路徑 | 狀態 | 動它會怎樣 |
|------|------|------------|
| `deploy/` | **唯一線上來源** | 改這裡就改線上 |
| `..\下載工具\` | 獨立工具（不在此 repo） | 改它不會影響 deploy |
| `..\Credit-Union-Analysis new\` | **歷史備份，勿修改** | CLAUDE.md 明令 |
| `..\_backup_pre_cleanup_20260601\` | 自動備份 | 勿手動編輯 |

---

## 2. 常用指令

```bash
# 啟動 app（本機）
streamlit run app.py

# 跑全部測試
pytest tests/

# 跑單一檔案
pytest tests/test_excel_processor.py

# 跑單一 case
pytest tests/test_excel_processor.py::TestProcessExcelFinal::test_returns_five_tuple_with_correct_shapes
```

**沒有** lint / typecheck / formatter 設定（無 `pyproject.toml`、無 `ruff`、無 `black`、無 `mypy`）。要加之前先問使用者。

---

## 3. 入口與資料流

```
app.py
 ├─ 共用連結 ?file=xxx  → services/cloud.py.download_file_from_storage
 │                      → data/excel_processor.py.process_excel_final  ★ 見 §5
 │                      → st.session_state["preloaded_data"]
 ├─ 共用連結 ?csv=xxx   → csv_processor.py → st.session_state["preloaded_csv"]
 ├─ 上傳 Excel/CSV      → 直接寫入 session_state
 └─ views/overview.py  (風險診斷) + views/war_room.py  (財務戰情室)
```

**兩條獨立資料流**，UI 上是分頁概念：
- **Excel**（3 分頁：社務/放款/區域分類表）→ 風險診斷
- **CSV**（PR019 會計科目明細）→ 財務戰情室

---

## 4. 部署流程

1. 改 `deploy/` 內任何檔
2. `git add` → `git commit` → `git push` 到 `main`
3. Streamlit Cloud 自動 rebuild（1–3 分鐘）
4. 若新 push 後行為沒變：到 <https://share.streamlit.io/> → 該 app → 「⋮」→「Reboot app」

**Secrets** 在 Streamlit Cloud Dashboard 設定，本機不要建 `.streamlit/secrets.toml`（會被 `.gitignore` 擋但避免混淆）。模板在 `.streamlit/secrets_template.toml`。

---

## 5. ★ `process_excel_final` 高風險函式

`data/excel_processor.py:18` 的 `process_excel_final()` 是整個雲端預載路徑的瓶頸。**過去 bug 實錄**：第 86 行曾誤用舊名 `get_v`（巢狀函式）而非模組層函式 `_get_value`，導致任何共享連結都壞，且錯誤訊息誤導為「無法讀取雲端資料」。

**規則**：
- 模組層已有 `_get_value(df, col, d)`（`data/excel_processor.py:9`），**不要**再寫新的 `get_v` / `get_value` 巢狀函式
- 修改 `process_excel_final` 後**必須**跑 `pytest tests/test_excel_processor.py::TestProcessExcelFinal` 驗證
- 函式本體被 `@st.cache_data` 包裝；在 pytest 內跑會印 "No runtime found" 警告，是正常的，無視即可

百分比欄位的「防禦性清洗」邏輯（`excel_processor.py:39-55`）每欄位規則不同，**改之前先讀註解**，別用統一公式整段重寫。

---

## 6. 測試

- 60 個 pytest，新增 case 後跑 `pytest tests/` 全套（`@st.cache_data` 跨測試可能互相干擾）
- `tests/test_classifier.py` 內狀態字串（如 `"🚨 重點輔導"`）是硬編碼，改 `data/classifier.py` 的 emoji / 文字要同步更新
- 風險診斷的 `p` dict 鍵值定義見 `..\CLAUDE.md` 的「`p` dict 的鍵值定義」表格

---

## 7. 易踩的坑

- **合併鍵一律用「社號」不用「社名」**（防社名更名導致資料遺失）
- **「收支比」欄位讀入時自動 rename 為「開支比」**（`excel_processor.py:26`），後續邏輯只認「開支比」
- **年月底線強制 12 月**——風險診斷的年度基準是 12 月快照（`T0 = max(dec_dates)`）
- **Streamlit `st.query_params` 是單值 dict**，多 `?file=...&csv=...` 是 OK 的，但 `?file=a&file=b` 只會讀到第一個
- **不要再用 git push --force**——本 repo 有 27 個歷史 commit，用 rebase merge 才是正路
- **Windows + Git Bash 的互動編輯器**：`git rebase --continue` / `git commit` 會跳 vim；本工作流統一加 `$env:GIT_EDITOR = "true"` 跳過

---

## 8. 其他參考

- 系統架構、術語規範、session state 鍵值清單：`..\CLAUDE.md`
- README（中文）：`README.md`
- 父層 CLAUDE.md 的「`p` dict 鍵值定義」與「Session State 鍵值」兩個表格是新增條件 / state key 時必查的
