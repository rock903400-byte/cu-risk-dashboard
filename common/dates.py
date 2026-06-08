import pandas as pd


def convert_minguo_date(val):
    try:
        s = str(int(float(str(val).strip())))
        if len(s) == 5:
            yr, mo = int(s[:3]) + 1911, int(s[3:])
        elif len(s) == 4:
            yr, mo = int(s[:2]) + 1911, int(s[2:])
        else:
            return pd.NaT
        return pd.to_datetime(f"{yr}-{mo:02d}-01")
    except:
        return pd.NaT


def get_value(df, col, d):
    if df.empty:
        return 0.0
    sub = df[df["年月"] <= d]
    return float(sub[col].iloc[-1]) if not sub.empty else float(df[col].iloc[0])
