# 專案核心指南 (Credit Union Analysis System)

本文件為系統開發與維護的最高準則，涵蓋設計哲學、業務邏輯、UI/UX 規範及技術架構。

---

## 📌 目錄
1. [設計哲學與目標受眾](#1-設計哲學與目標受眾)
2. [UI/UX 工程規範 (手機與高齡友善)](#2-uiux-工程規範)
3. [系統權限與導覽邏輯](#3-系統權限與導覽邏輯)
4. [財務戰情室 (War Room) 特有規範](#4-財務戰情室-特有規範)
5. [風險診斷與業務邏輯](#5-風險診斷與業務邏輯)
6. [技術基礎設施與穩定性](#6-技術基礎設施與穩定性)

---

## 1. 設計哲學與目標受眾
*   **目標受眾**：儲互社管理階層、區域管理者（區會）及高齡（銀髮族）使用者。
*   **設計理念**：
    *   **手機優先 (Mobile-First)**：所有功能必須在小螢幕上操作流暢且不裁切。
    *   **直覺化視覺**：減少文字敘述，優先使用大字體、顏色警示及縮減後的單位。
    *   **專業嚴謹**：報表邏輯需符合互助社財務規範。

## 2. UI/UX 工程規範
### 2.1 視覺與字體
*   **基礎字體**：桌機版 `18px` / 手機版 `16px`。
*   **指標放大**：`st.metric` 數值需加粗並進一步放大。
*   **防裁切機制**：數值容器應設為 `overflow: visible`，並在必要時自動折行。
*   **智慧單位縮減**：
    *   金額 >= 1 億：轉換為「**億元**」（保留兩位小數）。
    *   金額 >= 1 萬：轉換為「**萬元**」（無小數）。
    *   禁止使用 `$` 符號；統一使用中文單位，對長輩更直覺。
    *   實作位置：`data/utils.py` 的 `format_large_number`，所有金額顯示須經此函式。

### 2.2 操作體驗
*   **觸控熱區**：所有點擊元素（按鈕、選單）高度需達 `48px - 52px`。
*   **日期選擇**：捨棄滑桿，統一使用兩個 `st.selectbox` 分別選擇「起月」與「迄月」。
*   **圖表禁止縮放**：Plotly 圖表預設 `interactive=False`（`dragmode=False`、`fixedrange=True`），防止長輩誤觸縮放；工具列僅保留「下載圖片」按鈕。實作位置：`charts/style.py` 的 `apply_chart_style`。
*   **登出確認**：登出按鈕需二次確認（透過 `confirm_logout` session state），防止長輩誤觸。
*   **訊息持久化**：上傳成功/失敗訊息不可依賴 `st.success/st.error` 的短暫顯示；必須寫入 session state（`xl_msg` / `csv_msg`）保持持久顯示，直到下次操作覆寫。
*   **重要資訊不得隱藏**：禁止將關鍵資訊放入 `expander` 或 hover tooltip；長輩不一定知道這些元件可以互動。風險矩陣散佈圖下方須附加純文字社別一覽。
*   **趨勢圖排版**：禁用雙欄版面，改為單欄垂直排列；欄位順序以重要性排序（逾放比 → 貸放比 → 社員數 → 儲蓄率 → 開支比 → 提撥率），圖表高度固定 `450px`。

## 3. 系統權限與導覽邏輯
*   **導覽結構**：單一入口，側邊欄切換「📊 經營總覽」與「⚖️ 財務戰情室」。
*   **權限分級**：
    *   **Admin**：全台數據，具備檔案上傳權限。
    *   **District (區會)**：登入者具區域標籤時，標題顯示「[區域]區會」，僅限看該區。
    *   **Individual (個社)**：僅限查看自身互助社，標題顯示社名。
*   **預設行為**：戰情室多選器預設「全選」，單選器預設「第一個社別」。

## 4. 財務戰情室 (War Room) 特有規範
*   **概況快照 (Snapshot)**：頁面頂部四大核心指標。
    *   **總資產規模**、**總負債規模**、**淨值總額 (自有資金)**、**淨值佔資產比**。
*   ** terminology (術語)**：所有相關報表統一使用「**開支比**」取代舊有的「收支比」。
*   **勾稽檢查**：資產負債表必須自動檢查 `資產 = 負債 + 權益`，若不平衡需顯示錯誤警示。

## 5. 風險診斷與業務邏輯
*   **年度結算基準**：判定邏輯強制以「**年度 12 月年底數據**」為準。
*   **🚨 高風險觸發 (2/5 原則)**：滿足以下任兩項即列管。
    1.  **連兩年虧損**：開支比連續兩個年底 > 100%。
    2.  **貸放比過低**：低於設定門檻（預設 10%）。
    3.  **高逾放且惡化**：逾放比 > 50% 且逾期金額較前一年底增加。
    4.  **人數連三年衰退**。
    5.  **股金連三年衰退**。

## 6. 技術基礎設施與穩定性

### 6.1 模組架構
```
app.py              主入口（路由控管）
config.py           全域設定、ThresholdsConfig、ACCOUNT_CODES、APP_CSS
services/           核心服務層
  auth.py           登入頁面渲染與權限驗證邏輯
  cloud.py          Supabase 雲端客戶端初始化與檔案下載
  finance_service.py 財務分析核心邏輯（損益、YoY、瀑布圖準備）
data/               資料解析引擎
  classifier.py      風險診斷 2/5 門檻判定
  excel_processor.py Excel 財務指標解析
  csv_processor.py   CSV 財務明細解析
  utils.py           通用工具（民國年轉換、大額數字格式化）
components/         Streamlit UI 組件
  charts.py          戰情室圖表（瀑布圖、YoY 偵測、趨勢、排名）
  metrics.py         戰情室 KPI 卡片
pages/              頁面入口
  overview.py        經營總覽與風險診斷（含雷達監控與風險矩陣）
  war_room.py        財務戰情室（資產負債表、損益表、營運分析）
charts/style.py     Plotly 全域圖表樣式與主題配置
tools/data_fetcher/ 自動化資料抓取工具（原穿透協會）
tests/              pytest 自動化單元測試
```

### 6.2 雲端整合
*   使用 Supabase Storage 作為報表存儲中心。

### 6.3 資料解析
*   `excel_processor.py`：解析 Excel，以 12 月為年度基準點。
*   `csv_processor.py`：統一使用 `utf-8-sig` 編碼。

### 6.4 穩定性防護
*   所有 `selectbox` 前必須檢查 List 是否為空。
*   使用 `safe_div` 防止分母為 0 的崩潰。
*   標題自動去贅詞（避免「儲互社儲互社」重複顯示）。
*   `ThresholdsConfig` 在啟動時自動校驗門檻值，若為 0 或負數會立即報錯。

### 6.5 Session State 鍵值（勿任意增刪）

| 鍵值 | 預設值 | 用途 |
|------|--------|------|
| `logged_in` | `False` | 登入狀態 |
| `role` | `None` | `admin` / `viewer` |
| `assigned_region` | `None` | 登入者所屬區域 |
| `assigned_union` | `None` | 登入者所屬社名 |
| `login_attempts` | `0` | 連續登入失敗次數 |
| `locked` | `False` | 帳號鎖定狀態 |
| `preloaded_data` | `None` | Excel 解析結果 `(data, df_m, df_l, raw_bytes, region_map)` |
| `preloaded_csv` | `None` | CSV 解析結果 `(df, raw_bytes)` |
| `preloaded_passwords` | `{}` | 各區域密碼對照表 |
| `nav_selection` | `"📊 經營總覽..."` | 目前選取的導覽頁面 |
| `is_district_office` | `False` | 是否為區會模式 |
| `confirm_logout` | `False` | 登出二次確認暫存 |
| `xl_msg` | `None` | Excel 上傳結果 `("success"\|"error", 訊息文字)` |
| `csv_msg` | `None` | CSV 上傳結果 `("success"\|"error", 訊息文字)` |
