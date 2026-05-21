# 穿透協會 - 自動化資料抓取工具

負責模擬登入穿透協會系統，自動化選取單位 / 會科 / 年月，並下載原始 CSV 財務數據。

## 檔案說明

- `download_data.py`：主要執行腳本，處理登入、表單操作與 CSV 下載。
- `exported_data.csv`：最近一次下載的結構化財務數據（本機暫存，勿上傳）。

## 技術規範

- **網路請求**：`urllib`（無第三方 HTTP 套件）
- **ASP.NET 表單**：所有 POST 請求必須攜帶完整隱藏欄位（`__VIEWSTATE` 等）；需處理 Cookieless 狀態下的 `form action` 導向
- **CSV 寫入**：指定 `newline=''` 防止 Windows 重複換行；統一 `utf-8-sig` 編碼確保 Excel 開啟不掉字
- **核心函式**：修改網頁解析邏輯時，優先更新 `get_aspset_payload_pairs`

## 下載後的資料去向

下載完的 CSV 上傳至主系統側邊欄（財務戰情室），由 `data/csv_processor.py` 負責解析。
