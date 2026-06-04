import io
import pandas as pd
import streamlit as st

from data.utils import safe_div, convert_minguo_date
from data.classifier import classify


def _get_value(df: pd.DataFrame, col: str, d) -> float:
    """取得 df 中 年月 <= d 的最後一筆 col 值；無匹配時取第一筆；df 為空時回傳 0.0"""
    if df.empty:
        return 0.0
    sub = df[df["年月"] <= d]
    return float(sub[col].iloc[-1]) if not sub.empty else float(df[col].iloc[0])


_CACHE_VER = "v3"  # spinner 顯示用；真正 bust cache 的是函式內的 _VER，兩者都要 bump


@st.cache_data(show_spinner=f"🚀 正在執行智慧分析 ({_CACHE_VER})...")
def process_excel_final(file_bytes: bytes, thresholds: dict, sheets: dict):
    _VER = "v6"  # bump when classifier.py logic changes; this string IS in bytecode
    try:
        with pd.ExcelFile(io.BytesIO(file_bytes)) as xls:
            if not all(s in xls.sheet_names for s in sheets.values()):
                raise ValueError("Excel 缺少必要工作表，請檢查分頁名稱。")
            df_m_raw = pd.read_excel(xls, sheet_name=sheets["MAIN"],   dtype={"社號": str, "年月": str})
            df_l_raw = pd.read_excel(xls, sheet_name=sheets["LOAN"],   dtype={"社號": str, "年月": str})
            df_r_raw = pd.read_excel(xls, sheet_name=sheets["REGION"], dtype={"社名": str, "區域": str, "密碼": str})
            df_l_raw = df_l_raw.rename(columns={"收支比": "開支比"})
    except Exception as e:
        raise ValueError(f"解析失敗: {e}")

    region_map = dict(zip(df_r_raw["社名"], df_r_raw["區域"]))
    pw_to_info = {
        str(p).strip().replace(".0", ""): {"name": str(n).strip(), "region": str(r).strip()}
        for n, r, p in zip(df_r_raw["社名"], df_r_raw["區域"], df_r_raw["密碼"])
        if pd.notna(n) and pd.notna(r) and pd.notna(p)
    }

    df_m_raw["年月"] = df_m_raw["年月"].apply(convert_minguo_date)
    df_l_raw["年月"] = df_l_raw["年月"].apply(convert_minguo_date)
    for col in ["社員數", "股金", "貸放比"]:
        df_m_raw[col] = pd.to_numeric(df_m_raw[col], errors="coerce").fillna(0)
    
    # 儲蓄率防禦性讀取：大於 1.0 視為原始百分比（如 85.4%），自動除以 100
    df_m_raw["儲蓄率"] = pd.to_numeric(df_m_raw["儲蓄率"], errors="coerce").fillna(0)
    df_m_raw["儲蓄率"] = df_m_raw["儲蓄率"].apply(lambda x: x / 100 if abs(x) > 1.0 else x)

    df_l_raw["逾放比"]  = pd.to_numeric(df_l_raw["逾放比"],  errors="coerce").fillna(0)
    df_l_raw["逾期貸款"] = pd.to_numeric(df_l_raw["逾期貸款"], errors="coerce").fillna(0)
    
    # 開支比防禦性讀取：收支比容許大於 100% (1.0)，因此若已清洗為小數 (e.g. 1.6661)，不應再除以 100
    # 只有當數值大於 5.0 (500%) 時，才視為尚未清洗的百分比格式 (e.g. 166.61)
    df_l_raw["開支比"]  = pd.to_numeric(df_l_raw["開支比"],  errors="coerce").fillna(0)
    df_l_raw["開支比"]  = df_l_raw["開支比"].apply(lambda x: x / 100 if abs(x) > 5.0 else x)

    # 提撥率：update_database.py 下載時已將 HTML 的 % 值 ÷100，直接讀入即可
    df_l_raw["提撥率"]  = pd.to_numeric(df_l_raw.get("提撥率", 0), errors="coerce").fillna(0)

    df_m = df_m_raw.dropna(subset=["年月"]).sort_values(["社號", "年月"])
    df_l = df_l_raw.dropna(subset=["年月"]).sort_values(["社號", "年月"])

    max_d   = df_m["年月"].max()
    dec_dates = df_m[df_m["年月"].dt.month == 12]["年月"]
    T0 = dec_dates.max() if not dec_dates.empty else max_d
    T1, T2, T3 = (T0 - pd.DateOffset(years=i) for i in range(1, 4))
    T_12M = max_d - pd.DateOffset(months=12)

    rows = []
    for s_no in df_m["社號"].unique():
        ms = df_m[df_m["社號"] == s_no]
        ls = df_l[df_l["社號"] == s_no]
        if ms.empty:
            continue
        name = ms["社名"].iloc[0]

        M0, M1, M2, M3 = (_get_value(ms, "社員數", t) for t in (T0, T1, T2, T3))
        S0, S1, S2, S3 = (_get_value(ms, "股金",   t) for t in (T0, T1, T2, T3))
        R0, R1 = _get_value(ls, "開支比",  T0), _get_value(ls, "開支比",  T1)
        O0, O1 = _get_value(ls, "逾期貸款", T0), _get_value(ls, "逾期貸款", T1)
        eOvd   = _get_value(ls, "逾放比",  T0)
        eLoan  = _get_value(ms, "貸放比",  T0)
        sLoan  = _get_value(ms, "貸放比",  T1)
        memG   = safe_div(M0 - M1, M1)
        shrG   = safe_div(S0 - S1, S1)

        p = dict(M0=M0, M1=M1, M2=M2, M3=M3,
                 S0=S0, S1=S1, S2=S2, S3=S3,
                 R0=R0, R1=R1, O0=O0, O1=O1,
                 eOvd=eOvd, sOvd=_get_value(ls, "逾放比", T1),
                 eLoan=eLoan, sLoan=sLoan, memG=memG, shrG=shrG)
        status, reason = classify(p, thresholds)

        curr_M    = _get_value(ms, "社員數", max_d)
        curr_S    = _get_value(ms, "股金",   max_d)
        curr_eLoan = _get_value(ms, "貸放比",  max_d)
        curr_eOvd  = _get_value(ls, "逾放比",  max_d)
        curr_R     = _get_value(ls, "開支比",  max_d)
        eOvd_12m   = _get_value(ls, "逾放比",  T_12M)
        memG_curr  = safe_div(curr_M - M0, M0)
        shrG_curr  = safe_div(curr_S - S0, S0)

        rows.append({
            "社號": s_no, "社名": name, "區域": region_map.get(name, "未分類"),
            "診斷狀態": status, "建議留意事項": reason,
            "現有社員": curr_M,
            "社員成長數(12M)": curr_M - M0,
            "社員成長率(12M)": memG_curr,
            "現有股金": curr_S,
            "股金成長率(12M)": shrG_curr,
            "貸放比": curr_eLoan,
            "儲蓄率": float(ms.iloc[-1]["儲蓄率"]),
            "逾放比(12M)": eOvd_12m,
            "逾放比": curr_eOvd,
            "開支比": curr_R,
            "開支比(年)": R0,
            "提撥率": float(ls.iloc[-1]["提撥率"]) if not ls.empty else 0.0,
            "_sM": M0, "_sS": S0,
        })

    return pd.DataFrame(rows).fillna(0), df_m, df_l, pw_to_info, region_map
