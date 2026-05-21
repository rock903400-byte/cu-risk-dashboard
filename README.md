# 儲互社分析系統 (Credit Union Analysis System)

專為台灣**儲蓄互助社**量身打造的風險管理與財務分析平台，目標使用者為高齡長輩，所有 UI 設計以直覺、清晰、防誤觸為第一優先。

## 核心功能

### 1. 經營總覽與風險診斷
- **自動化風險判定**：2/5 原則（連兩年虧損、貸放比過低、高逾放惡化、人數/股金連三年衰退，符合兩項 → 🚨 重點輔導）
- **狀態雷達監控**：四色卡片一覽重點輔導/流動性緊繃/資金閒置/穩健模範社
- **風險矩陣**：泡泡散佈圖 + 下方純文字社別一覽（不需 hover）
- **個社健檢**：與區域/全台平均對比柱狀圖
- **趨勢追蹤**：單欄垂直排列六大指標（逾放比優先），高度 450px，方便長輩閱讀
- **報表匯出**：CSV 下載，高風險社別自動標紅（正確判斷「重點輔導」）

### 2. 財務戰情室
- **資產負債表**：雙欄對照，自動勾稽（資產 = 負債 + 權益）
- **綜合損益表**：收入/支出分段，本期損益自動顯示紅/綠背景
- **年度營運分析**：KPI 卡片（YoY delta）+ 瀑布圖 + YoY 異常偵測 + 科目排名
- **歷年趨勢**：雙 Y 軸收支比折線/柱狀圖

### 3. 高齡友善設計
- 基礎字體 18px（手機 16px），按鈕高度 52px
- 圖表禁止誤觸縮放，工具列只保留「截圖下載」
- 金額統一中文單位（萬元 / 億元），不使用 `$` 符號
- 登出按鈕有二次確認，防止誤觸
- 上傳訊息持久顯示於側邊欄，不會自動消失

## 技術架構

| 層次 | 技術 |
|------|------|
| 前端框架 | Streamlit |
| 資料處理 | Pandas |
| 圖表 | Plotly |
| 雲端存儲 | Supabase Storage |
| 設定校驗 | Pydantic |
| 測試 | pytest（44 個測試） |

## 模組結構

```
app.py                  主入口（路由、session state、登入關卡）
config.py               CONFIG + ThresholdsConfig + APP_CSS
services/
  auth.py               登入頁面與驗證
  cloud.py              Supabase 初始化與下載
  finance_service.py    財務純函數（YoY、瀑布圖、損益快照）
data/
  classifier.py         風險診斷 2/5 門檻
  excel_processor.py    Excel 解析
  csv_processor.py      CSV 解析
  utils.py              safe_div, format_large_number, convert_minguo_date
components/
  charts.py             戰情室圖表（瀑布圖、YoY、排名、趨勢）
  metrics.py            KPI 卡片
pages/
  overview.py           經營總覽與風險診斷
  war_room.py           財務戰情室
charts/
  style.py              Plotly 全域樣式
tests/                  pytest 單元測試
tools/data_fetcher/     自動化資料抓取工具
raw_data/               原始資料（已 gitignore）
```

## 快速上手

```bash
pip install -r requirements.txt
streamlit run app.py
```

**線上部署網址**：https://cu-analysis-cz3xuj9tu52zsfxchmky4y.streamlit.app

資料來源：
- **Excel**（社務及資金運用 / 放款及逾期 / 區域分類表）→ 風險診斷
- **CSV**（會計科目明細）→ 財務戰情室

## 權限說明

| 身份 | 可見範圍 | 上傳權限 |
|------|---------|---------|
| Admin | 全台 | 有 |
| 區會 | 所屬區域 | 無 |
| 個社 | 自身社別 | 無 |

## 隱私與安全
- 本系統不直接儲存敏感個資
- 分享連結產生的檔案儲存於 Supabase，僅持有連結者可存取
- 敏感資料已透過 `.gitignore` 排除，請勿將真實資料庫上傳至 GitHub
