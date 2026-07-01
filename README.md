# CU-Analysis-v1

> 儲互社分析系統 (Credit Union Analysis System) — 專為台灣儲蓄互助社打造的風險管理與財務分析平台

## 功能特色

- **自動化風險判定**：遵循 2/5 原則進行系統性風險指標判定與等級劃分。
- **狀態雷達監控**：提供多維度財務指標的狀態雷達圖，即時掌握營運態勢。
- **風險矩陣與個社健檢**：支援個社財務健康評估、風險等級判定及預警提示。
- **財務戰情室**：整合資產負債表、綜合損益表及年度營運數據的動態趨勢追蹤。
- **高齡友善 UI**：專為高齡使用者設計，採用 18px 大字體與 52px 大按鈕互動介面。

## 技術棧

- **Frontend**: Streamlit
- **Backend**: Python (Pandas, Plotly)
- **Database**: Supabase

## 快速開始

### 1. 安裝環境依賴
請確保本機已安裝 Python 3.8+：
```bash
pip install -r requirements.txt
```

### 2. 啟動 Streamlit 服務
```bash
streamlit run app.py
```

## 專案結構

```text
/
├── app.py              # 系統入口程式
├── views/              # 各業務頁面儀表板 (dashboard, risk, health 等)
├── services/           # 商業邏輯運算與 Supabase 資料庫介面
├── components/         # 封裝之可重複使用 UI 元件
├── charts/             # Plotly 數據視覺化圖表繪製邏輯
└── tests/              # pytest 單元與整合測試
```

## 相關專案

- [CU-Analysis](https://github.com/rock903400-byte/CU-Analysis)
- [Credit-Union-Analysis-2-](https://github.com/rock903400-byte/Credit-Union-Analysis-2-)

## License

MIT
