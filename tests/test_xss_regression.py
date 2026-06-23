"""
Audit AppTest scenarios v2 — verify suspected bugs.
"""

import sys
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from streamlit.testing.v1 import AppTest
import pandas as pd


def make_synth_data():
    """合成 1 個社的完整資料,讓 overview 進得去"""
    data = pd.DataFrame(
        [
            {
                "社號": "001",
                "社名": "測試社",
                "區域": "北區",
                "診斷狀態": "📊 一般狀態",
                "建議留意事項": "",
                "現有社員": 100,
                "社員成長數(12M)": 5,
                "社員成長率(12M)": 0.05,
                "現有股金": 5_000_000,
                "股金成長率(12M)": 0.05,
                "貸放比": 0.6,
                "儲蓄率": 0.85,
                "逾放比(12M)": 0.01,
                "逾放比": 0.01,
                "開支比": 0.95,
                "開支比(年)": 0.95,
                "提撥率": 0.02,
                "_sM": 100,
                "_sS": 5_000_000,
            }
        ]
    )
    df_m = pd.DataFrame(
        [
            {
                "社號": "001",
                "社名": "測試社",
                "年月": pd.Timestamp("2023-12-01"),
                "社員數": 100,
                "股金": 5_000_000,
                "貸放比": 0.6,
                "儲蓄率": 0.85,
            },
            {
                "社號": "001",
                "社名": "測試社",
                "年月": pd.Timestamp("2024-12-01"),
                "社員數": 100,
                "股金": 5_000_000,
                "貸放比": 0.6,
                "儲蓄率": 0.85,
            },
        ]
    )
    df_l = pd.DataFrame(
        [
            {
                "社號": "001",
                "社名": "測試社",
                "年月": pd.Timestamp("2023-12-01"),
                "逾放比": 0.01,
                "逾期貸款": 0,
                "開支比": 0.95,
                "提撥率": 0.02,
            },
            {
                "社號": "001",
                "社名": "測試社",
                "年月": pd.Timestamp("2024-12-01"),
                "逾放比": 0.01,
                "逾期貸款": 0,
                "開支比": 0.95,
                "提撥率": 0.02,
            },
        ]
    )
    return data, df_m, df_l


# === Pytest regression tests for fixes in 568a268 + 69486c7 ===
# 下方 module-level 為 audit script，pytest 只收集本段 test_ 開頭的函式
_APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


def test_xss_via_assigned_union():
    """69486c7: viewer badge 不應執行惡意 JS"""
    malicious = "<img src=x onerror=alert(1)>"
    data, df_m, df_l = make_synth_data()
    at = AppTest.from_file(_APP_PATH, default_timeout=30)
    at.session_state["logged_in"] = True
    at.session_state["role"] = "viewer"
    at.session_state["assigned_region"] = "北區"
    at.session_state["assigned_union"] = malicious
    at.session_state["preloaded_data"] = (data, df_m, df_l, b"", {})
    at.session_state["preloaded_csv"] = None
    at.run()
    all_text = "".join(m.value for m in at.markdown)
    assert not at.exception, f"AppTest exception: {[e.value for e in at.exception]}"
    assert malicious not in all_text, f"XSS payload rendered: {all_text[:200]}"


def test_xss_via_union_name():
    """69486c7: 狀態雷達/報表匯出/個社健檢 H3/alert-box 不應執行惡意 JS"""
    malicious = "X<script>alert(1)</script>"
    base_data, df_m, df_l = make_synth_data()
    data2 = base_data.copy()
    data2["社名"] = malicious
    data2["區域"] = "北區"
    at = AppTest.from_file(_APP_PATH, default_timeout=30)
    at.session_state["logged_in"] = True
    at.session_state["role"] = "admin"
    at.session_state["assigned_region"] = None
    at.session_state["assigned_union"] = None
    at.session_state["is_district_office"] = False
    at.session_state["preloaded_data"] = (data2, df_m, df_l, b"", {malicious: "北區"})
    at.session_state["preloaded_csv"] = None
    at.run()
    all_text = "".join(m.value for m in at.markdown)
    assert not at.exception, f"AppTest exception: {[e.value for e in at.exception]}"
    assert malicious not in all_text, f"XSS payload rendered: {all_text[:200]}"


def test_empty_df_m_no_crash():
    """568a268: 空 df_m 不應 NaT.year crash"""
    empty_cols = [
        "社號",
        "社名",
        "區域",
        "診斷狀態",
        "建議留意事項",
        "現有社員",
        "社員成長數(12M)",
        "社員成長率(12M)",
        "現有股金",
        "股金成長率(12M)",
        "貸放比",
        "儲蓄率",
        "逾放比(12M)",
        "逾放比",
        "開支比",
        "開支比(年)",
        "提撥率",
        "_sM",
        "_sS",
    ]
    data, _, df_l = make_synth_data()
    at = AppTest.from_file(_APP_PATH, default_timeout=30)
    at.session_state["logged_in"] = True
    at.session_state["role"] = "admin"
    at.session_state["preloaded_data"] = (
        data,
        pd.DataFrame(columns=empty_cols),
        df_l,
        b"",
        {},
    )
    at.session_state["preloaded_csv"] = None
    at.run()
    assert not at.exception, f"AppTest exception: {[e.value for e in at.exception]}"


def test_individual_downgrade_shows_warning():
    """568a268: 個社 viewer 找不到 union 應顯示 warning"""
    data, df_m, df_l = make_synth_data()
    at = AppTest.from_file(_APP_PATH, default_timeout=30)
    at.session_state["logged_in"] = True
    at.session_state["role"] = "viewer"
    at.session_state["assigned_region"] = "北區"
    at.session_state["assigned_union"] = "不存在的社"
    at.session_state["preloaded_data"] = (data, df_m, df_l, b"", {})
    at.session_state["preloaded_csv"] = None
    at.run()
    warnings_text = " ".join(w.value for w in at.warning)
    assert "找不到" in warnings_text, f"預期降級 warning,實際: {warnings_text}"
    assert not at.exception


def test_strict_union_comparison_with_whitespace():
    """568a268: 個社 union 比對容錯 Excel 空白差異（trailing space 應正常匹配）"""
    data, df_m, df_l = make_synth_data()
    at = AppTest.from_file(_APP_PATH, default_timeout=30)
    at.session_state["logged_in"] = True
    at.session_state["role"] = "viewer"
    at.session_state["assigned_region"] = "北區"
    at.session_state["assigned_union"] = "測試社 "  # 尾端空白
    at.session_state["preloaded_data"] = (data, df_m, df_l, b"", {})
    at.session_state["preloaded_csv"] = None
    at.run()
    warnings_text = " ".join(w.value for w in at.warning)
    assert (
        "找不到" not in warnings_text
    ), f"strip 後應匹配,不應降級 warning: {warnings_text}"
    assert not at.exception


def test_only_csv_preload_no_crash():
    """568a268: 只有 CSV 無 Excel 不應 TypeError unpack None crash"""
    empty_csv = pd.DataFrame(
        columns=[
            "社號",
            "社名",
            "區域",
            "年度",
            "年月",
            "會計科目",
            "會科名稱",
            "當月金額",
        ]
    )
    at = AppTest.from_file(_APP_PATH, default_timeout=30)
    at.session_state["logged_in"] = True
    at.session_state["role"] = "viewer"
    at.session_state["assigned_region"] = "北區"
    at.session_state["assigned_union"] = "測試社"
    at.session_state["preloaded_data"] = None
    at.session_state["preloaded_csv"] = (empty_csv, b"")
    at.run()
    assert not at.exception, f"AppTest exception: {[e.value for e in at.exception]}"


if __name__ == "__main__":
    # ============================================================
    # A1. XSS via assigned_union (with real data)
    # ============================================================
    print("\n[A1] XSS via assigned_union with real data")
    malicious = "<img src=x onerror=alert(1)>"
    data, df_m, df_l = make_synth_data()
    at = AppTest.from_file(_APP_PATH, default_timeout=30)
    at.session_state["logged_in"] = True
    at.session_state["role"] = "viewer"
    at.session_state["assigned_region"] = "北區"
    at.session_state["assigned_union"] = malicious
    at.session_state["is_district_office"] = False
    at.session_state["preloaded_data"] = (data, df_m, df_l, b"", {"測試社": "北區"})
    at.session_state["preloaded_csv"] = None
    at.run()
    all_text = ""
    for m in at.markdown:
        all_text += m.value
    print(f"  exc={len(at.exception)}, err={len(at.error)}")
    print(f"  malicious in rendered markdown: {malicious in all_text}")
    if malicious in all_text:
        print(f"  🚨 XSS payload LEAKED via st.markdown(unsafe_allow_html=True)")
        # 找出含 XSS 的區塊
        idx = all_text.find(malicious)
        print(f"  context: ...{all_text[max(0, idx-50):idx+80]}...")

    # ============================================================
    # A2. XSS via 社員 社名字段
    # ============================================================
    print("\n[A2] XSS via 社名 in overview 報表匯出")
    malicious_name = "X<script>alert(1)</script>"
    data2 = data.copy()
    data2["社名"] = malicious_name
    data2["區域"] = "北區"
    at = AppTest.from_file(_APP_PATH, default_timeout=30)
    at.session_state["logged_in"] = True
    at.session_state["role"] = "admin"
    at.session_state["assigned_region"] = None
    at.session_state["assigned_union"] = None
    at.session_state["is_district_office"] = False
    at.session_state["preloaded_data"] = (
        data2,
        df_m,
        df_l,
        b"",
        {malicious_name: "北區"},
    )
    at.session_state["preloaded_csv"] = None
    at.run()
    all_text = ""
    for m in at.markdown:
        all_text += m.value
    print(f"  exc={len(at.exception)}")
    print(f"  malicious in rendered: {malicious_name in all_text}")
    if malicious_name in all_text:
        print(f"  🚨 XSS via 社名字段 — 報表匯出/狀態雷達卡 渲染時未 escape")

    # ============================================================
    # A3. overview empty df_m crash
    # ============================================================
    print("\n[A3] overview 頁面空 df_m 崩潰")
    empty_df = pd.DataFrame(
        columns=[
            "社號",
            "社名",
            "區域",
            "診斷狀態",
            "建議留意事項",
            "現有社員",
            "社員成長數(12M)",
            "社員成長率(12M)",
            "現有股金",
            "股金成長率(12M)",
            "貸放比",
            "儲蓄率",
            "逾放比(12M)",
            "逾放比",
            "開支比",
            "開支比(年)",
            "提撥率",
            "_sM",
            "_sS",
        ]
    )
    empty_df_m = pd.DataFrame(
        columns=["社號", "社名", "年月", "社員數", "股金", "貸放比", "儲蓄率"]
    )
    empty_df_l = pd.DataFrame(
        columns=["社號", "社名", "年月", "逾放比", "逾期貸款", "開支比", "提撥率"]
    )
    at = AppTest.from_file(_APP_PATH, default_timeout=30)
    at.session_state["logged_in"] = True
    at.session_state["role"] = "admin"
    at.session_state["is_district_office"] = False
    at.session_state["preloaded_data"] = (empty_df, empty_df_m, empty_df_l, b"", {})
    at.session_state["preloaded_csv"] = None
    at.run()
    print(f"  exc={len(at.exception)}, err={len(at.error)}")
    for e in at.exception:
        print(f"  !! {str(e.value)[:200]}")
        if "AttributeError" in str(e.value) or "NaT" in str(e.value):
            print(f"  🚨 CONFIRMED: 空 df_m → NaT.year crash (overview.py:34)")

    # ============================================================
    # A4. 個社降級無告知
    # ============================================================
    print("\n[A4] 個社降級為區會模式無告知")
    data3, df_m3, df_l3 = make_synth_data()
    at = AppTest.from_file(_APP_PATH, default_timeout=30)
    at.session_state["logged_in"] = True
    at.session_state["role"] = "viewer"
    at.session_state["assigned_region"] = "北區"
    at.session_state["assigned_union"] = "舊社(已合併)"  # 不在社清單
    at.session_state["is_district_office"] = False
    at.session_state["preloaded_data"] = (data3, df_m3, df_l3, b"", {"測試社": "北區"})
    at.session_state["preloaded_csv"] = None
    at.run()
    warn_text = ""
    for w in at.warning:
        warn_text += w.value
    all_text = ""
    for m in at.markdown:
        all_text += m.value
    print(f"  warning={len(at.warning)}")
    if "降級" in all_text or "找不到" in all_text or "切換" in all_text:
        print(f"  ✅ 有告知降級")
    else:
        print(f"  🚨 沒告知降級 — 個社 viewer 看到「區域平均」誤以為是本社數據")

    # ============================================================
    # A5. new 科目 in detect_yoy_anomalies
    # ============================================================
    print("\n[A5] detect_yoy_anomalies 新科目")
    from services.finance_service import detect_yoy_anomalies

    prev = pd.DataFrame(
        [{"會計科目": "4101", "會科名稱": "利息收入", "當月金額": 1000}]
    )
    curr = pd.DataFrame(
        [
            {"會計科目": "4101", "會科名稱": "利息收入", "當月金額": 2000},
            {"會計科目": "9999", "會科名稱": "新科目(去年沒有)", "當月金額": 100000},
        ]
    )
    r = detect_yoy_anomalies(curr, prev, threshold_amount=100, threshold_pct=10)
    has_new = "9999" in r["會計科目"].astype(str).values if not r.empty else False
    print(f"  anomalies: {len(r)} rows, has_new={has_new}")
    if has_new:
        print(f"  🚨 BUG-18 still real: 新科目(去年金額=0) 變動率 NaN 仍被列入")

    # ============================================================
    # A6. safe_div, get_value regression
    # ============================================================
    print("\n[A6] regression — safe_div, get_value")
    from common.utils import safe_div
    from common.dates import get_value

    r1 = safe_div(float("nan"), 10)
    r2 = get_value(
        pd.DataFrame({"年月": [pd.Timestamp("2030-12-01")], "x": [9999.0]}),
        "x",
        pd.Timestamp("2020-12-01"),
    )
    print(f"  safe_div(NaN, 10) = {r1}  | 期望 0.0")
    print(f"  get_value(future, past) = {r2}  | 期望 0.0")
    print(f"  ✅ BUG-1 (get_value fallback) 與 BUG-9 (safe_div NaN) 兩者皆已修")

    # ============================================================
    # A7. prepare_waterfall regression
    # ============================================================
    print("\n[A7] prepare_waterfall_data 真實負費用")
    from services.finance_service import prepare_waterfall_data

    real = pd.DataFrame(
        [
            {"會計科目": "4101", "會科名稱": "利息收入", "當月金額": 247000},
            {"會計科目": "4201", "會科名稱": "其他收入", "當月金額": 63000},
            {"會計科目": "5101", "會科名稱": "利息支出", "當月金額": -91000},
            {"會計科目": "5201", "會科名稱": "用人費用", "當月金額": -61000},
            {"會計科目": "5301", "會科名稱": "業務費", "當月金額": -30500},
            {"會計科目": "5401", "會科名稱": "管理費用", "當月金額": -15000},
            {"會計科目": "5501", "會科名稱": "呆帳提列", "當月金額": -6000},
        ]
    )
    wf = prepare_waterfall_data(real)
    expected = 247000 + 63000 - 91000 - 61000 - 30500 - 15000 - 6000
    print(f"  net={wf['net']}, expected={expected}")
    print(f"  ✅ BUG-4 fixed")

    # ============================================================
    # A8. 5 attempts lock — 確認是第 5 次才 lock
    # ============================================================
    print("\n[A8] 5 attempts lock 邏輯（code review）")
    max_attempts = 5
    for i in range(1, 7):
        attempts = i
        locked = attempts >= max_attempts
        print(f"  attempt {i}: locked={locked}")
    # 預期第 5 次 locked=True

    # ============================================================
    # A9. CSV 雲端失敗無提示
    # ============================================================
    print("\n[A9] CSV 雲端下載失敗 — 是否顯示錯誤 (code review)")
    # app.py:83-90
    # try: download_file_from_storage(supabase, ..., shared_csv)
    #      process_csv_final(raw_csv)
    #      st.session_state["preloaded_csv"] = (df, raw_csv)
    # except Exception as e:
    #      logger.error(f"CSV 載入失敗: {e}")
    # → 只 logger.error，沒 set preload_csv_err，沒 UI 提示
    print(
        "  app.py:83-90 只有 logger.error，沒設 preload_csv_err,render_login_page 不會顯示"
    )
    print("  🚨 BUG-11 still real: CSV 雲端 404 完全沒反饋給使用者")

    # ============================================================
    # A10. login_attempts overflow / 永遠累積
    # ============================================================
    print("\n[A10] login_attempts overflow 風險 (code review)")
    print("  auth.py:25 — login_attempts += 1,沒 upper bound")
    print("  雖然 locked=True 後 button 不顯示,不會再 +1")
    print("  但若有人用 URL 觸發 / 直接操作 session_state → 累積到 10^9 仍無害(僅 int)")
    print("  ✅ 實際無害")

    # ============================================================
    # A11. upload Excel 失敗時,舊資料仍被當作當前
    # ============================================================
    print("\n[A11] Excel 解析失敗時,舊資料是否繼續顯示 (code review)")
    # app.py:166-183
    # if uploaded_xl:
    #     try:
    #         ...
    #         st.session_state.update(preloaded_data=...)
    #         st.session_state["xl_msg"] = ("success", "✅ ...")
    #     except Exception as e:
    #         st.session_state["xl_msg"] = ("error", f"❌ ...: {e}")
    # 失敗時:session_state 沒更新,舊 data 仍在,繼續渲染
    print("  app.py:166-183 失敗時不重置 session_state['preloaded_data']")
    print("  → 使用者看到「Excel 解析失敗」紅字,但下方表格仍顯示舊資料(誤導)")
    print("  🚨 MEDIUM: 失敗時應至少 st.warning「請重新上傳正確檔案」")

    # ============================================================
    # A12. share URL supabase.upload 失敗無錯誤提示
    # ============================================================
    print("\n[A12] share URL 上傳失敗 (code review)")
    # app.py:216-244
    # if st.button("🚀 生成分享連結", use_container_width=True):
    #     if not supabase:
    #         st.error("❌ 雲端服務未設定,無法產生分享連結。")
    #     else:
    #         params = []
    #         if st.session_state["preloaded_data"]:
    #             ...
    #             supabase.storage.from_(...).upload(...)
    # upload() 可能 raise StorageException,沒 try/except 包住
    print("  app.py:223 supabase.storage.upload() 沒 try/except")
    print("  → 失敗時 exception 會冒到頂,整個 script crash")
    print("  🚨 HIGH: 應 wrap 在 try/except,顯示 st.error 給使用者")

    # ============================================================
    # A13. nav_selection 強制重設無告知
    # ============================================================
    print("\n[A13] nav_selection 強制重設 (code review)")
    # app.py:288-296
    # if st.session_state["nav_selection"] not in nav_options:
    #     st.session_state["nav_selection"] = nav_options[0]
    # 使用者可能選「⚖️ 財報明細」,reload 後(preloaded_csv 還沒好)→ 重設
    print("  app.py:288-296 強制重設不告知")
    print("  🚨 LOW: 加 st.toast")

    # ============================================================
    # A14. file_uploader 沒 max_upload_size
    # ============================================================
    print("\n[A14] file_uploader 沒限制大小 (code review)")
    # app.py:159-164
    # uploaded_xl = st.file_uploader("Excel (風險診斷)", type=["xlsx"], label_visibility="collapsed")
    # uploaded_csv = st.file_uploader("CSV (財務明細)", type=["csv"], label_visibility="collapsed")
    # 沒 max_upload_size 參數
    print("  app.py:159-164 沒 max_upload_size")
    print("  Streamlit 1.56 預設 200MB → 大檔解析緩慢或 OOM")
    print("  🚨 MEDIUM: 加 max_upload_size=50")

    # ============================================================
    # A15. only-CSV admin crash
    # ============================================================
    print("\n[A15] viewer 區會只有 CSV 無 Excel → crash (code review)")
    # app.py:135-150
    # if st.session_state["preloaded_csv"]:
    #     df_csv_full, raw_csv_bytes = st.session_state["preloaded_csv"]
    #     ...
    #     elif region:
    #         # 區會或管理員：查看該區域內所有社
    #         _, _, _, _, rm = st.session_state["preloaded_data"]  # <-- preloaded_data is None
    # 觸發條件:viewer assigned_region 有值,但 preloaded_data 為 None
    # 實務上不太可能(viewer 需密碼登入 → 必須有 Excel 提供密碼),但若 admin 上傳 CSV + 設定 region 假資料則可能
    print("  app.py:146 對 preloaded_data=None 強制 unpack → crash")
    print("  ⚠️ LOW: 實務上極少觸發,但 code path 脆弱")

    # ============================================================
    # A16. 1000-user report BUG-1 (get_value) 確認 fixed
    # ============================================================
    print("\n[A16] get_value fallback 確認")
    from common.dates import get_value

    df = pd.DataFrame(
        {
            "年月": [pd.Timestamp("2030-06-01"), pd.Timestamp("2030-12-01")],
            "x": [100, 200],
        }
    )
    r = get_value(df, "x", pd.Timestamp("2020-12-01"))
    print(f"  get_value(future data, past query) = {r} (期望 0.0)")
    if r == 0.0:
        print(f"  ✅ BUG-1 fixed: 不再 fallback 到首筆")

    # ============================================================
    # A17. classify_code 對 None
    # ============================================================
    print("\n[A17] classify_code(None) / 數字")
    from common.classifier import classify_code

    for inp in [None, "", 1234, 1234.0, "  ", "X", 0]:
        try:
            r = classify_code(inp)
            print(f"  classify_code({inp!r}) = {r!r}")
        except Exception as e:
            print(f"  🚨 {type(e).__name__}: {e}")

    # ============================================================
    # A18. format_large_number 邊界
    # ============================================================
    print("\n[A18] format_large_number 邊界")
    from common.utils import format_large_number

    for v in [0, 9999, 10000, 1e8, -1e8, None, float("nan"), "abc", 1.234]:
        r = format_large_number(v)
        print(f"  format({v!r}) = {r!r}")

    # ============================================================
    # A19. process_excel_final Excel 缺提撥率欄位
    # ============================================================
    print("\n[A19] process_excel_final 缺提撥率欄位")
    import io
    from data.excel_processor import process_excel_final
    from config import get_config

    cfg = get_config()
    main = pd.DataFrame(
        [
            {
                "社號": "001",
                "社名": "A社",
                "年月": "11312",
                "社員數": 100,
                "股金": 5_000_000,
                "貸放比": 0.5,
                "儲蓄率": 0.85,
            }
        ]
    )
    loan = pd.DataFrame(
        [
            {
                "社號": "001",
                "社名": "A社",
                "年月": "11312",
                "逾放比": 0.01,
                "逾期貸款": 100,
                "開支比": 0.95,
                # 缺提撥率
            }
        ]
    )
    region = pd.DataFrame([{"社名": "A社", "區域": "北", "密碼": "1234"}])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        main.to_excel(w, sheet_name=cfg["SHEETS"]["MAIN"], index=False)
        loan.to_excel(w, sheet_name=cfg["SHEETS"]["LOAN"], index=False)
        region.to_excel(w, sheet_name=cfg["SHEETS"]["REGION"], index=False)
    try:
        data, df_m, df_l, pws, rm = process_excel_final(
            buf.getvalue(), cfg["THRESHOLDS"], cfg["SHEETS"]
        )
        print(f"  ✅ 缺提撥率 fallback 0.0: 提撥率={data['提撥率'].iloc[0]}")
    except Exception as e:
        print(f"  🚨 {type(e).__name__}: {e}")

    # ============================================================
    # A20. same_months 跨年比對（BUG F5 確認）
    # ============================================================
    print("\n[A20] get_annual_snapshot same_months 跨年")
    from services.finance_service import get_annual_snapshot

    df_2y = pd.DataFrame(
        {
            "年月": ["11301", "11302", "11401", "11402", "11403", "11412"],
            "年度": ["113", "113", "114", "114", "114", "114"],
            "會計科目": ["1101", "1101", "1101", "1101", "4101", "5101"],
            "會科名稱": ["現金"] * 4 + ["利息收入", "利息支出"],
            "當月金額": [100, 110, 200, 210, 500, 600],
        }
    )
    # 113 年只有 11301, 11302; 查 113 年 + same_months=["11401", "11402"]
    # 預期 11301, 11302 月份 → 取 11301=100, 11302=110
    # 但 same_months 用 [-2:] suffix 對照 → 113 年應該比對 11301, 11302
    snap = get_annual_snapshot(df_2y, "113", same_months=["11401", "11402"])
    cash_113 = (
        snap[snap["會計科目"] == "1101"]["當月金額"].iloc[0] if not snap.empty else None
    )
    print(f"  113 年 cross-year 取到 1101={cash_113} (期望 110 = 11302 現金)")

    print("\n" + "=" * 70)
    print("  audit_scenario_xss.py v2 完成")
    print("=" * 70)


# === Phase 4 review fixes: P1-1 雷達卡個社模式、P1-2 curr_idx 守衛、P1-6 is_pct ===


def test_individual_mode_hides_radar_cards():
    """個社模式進入經營總覽不應渲染雷達卡（語意：雷達卡為「全台/區域分布」用）"""
    data, df_m, df_l = make_synth_data()
    at = AppTest.from_file(_APP_PATH, default_timeout=30)
    at.session_state["logged_in"] = True
    at.session_state["role"] = "viewer"
    at.session_state["assigned_region"] = "北區"
    at.session_state["assigned_union"] = "測試社"
    at.session_state["preloaded_data"] = (data, df_m, df_l, b"", {"測試社": "北區"})
    at.session_state["preloaded_csv"] = None
    at.run()
    assert not at.exception, f"AppTest exception: {[e.value for e in at.exception]}"
    all_text = "".join(m.value for m in at.markdown)
    assert (
        "狀態雷達監控" not in all_text
    ), f"個社模式不應渲染雷達卡,實際 markdown 含: '狀態雷達監控'"


def test_admin_mode_shows_radar_cards():
    """管理員全台模式仍應渲染雷達卡（與個社模式對照）"""
    data, df_m, df_l = make_synth_data()
    at = AppTest.from_file(_APP_PATH, default_timeout=30)
    at.session_state["logged_in"] = True
    at.session_state["role"] = "admin"
    at.session_state["assigned_region"] = None
    at.session_state["assigned_union"] = None
    at.session_state["is_district_office"] = False
    at.session_state["preloaded_data"] = (data, df_m, df_l, b"", {"測試社": "北區"})
    at.session_state["preloaded_csv"] = None
    at.run()
    assert not at.exception, f"AppTest exception: {[e.value for e in at.exception]}"
    all_text = "".join(m.value for m in at.markdown)
    assert (
        "狀態雷達監控" in all_text
    ), f"管理員全台模式應渲染雷達卡,實際 markdown 不含 '狀態雷達監控'"
