import math
import pandas as pd


def convert_minguo_date(val):
    if val is None:
        return pd.NaT
    try:
        if isinstance(val, float) and math.isnan(val):
            return pd.NaT
    except:
        pass
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    s = "".join(ch for ch in s if ch.isdigit() or ch == "-")
    if not s:
        return pd.NaT
    try:
        s_int = int(float(s))
    except:
        return pd.NaT
    s = str(s_int)
    if len(s) == 5:
        yr, mo = int(s[:3]) + 1911, int(s[3:])
    elif len(s) == 4:
        yr, mo = int(s[:2]) + 1911, int(s[2:])
    else:
        return pd.NaT
    try:
        return pd.to_datetime(f"{yr}-{mo:02d}-01")
    except:
        return pd.NaT


def get_value(df, col, d):
    if df.empty:
        return 0.0
    sub = df[df["年月"] <= d]
    if sub.empty:
        return 0.0
    return float(sub[col].iloc[-1])
