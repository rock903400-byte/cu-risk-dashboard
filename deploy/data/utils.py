import pandas as pd


def safe_div(n, d):
    return n / d if d and not pd.isna(d) else 0.0


def format_large_number(n):
    """將大額數字轉為 億 或 萬 單位，縮短顯示長度"""
    if abs(n) >= 1e8:
        return f"{n/1e8:.2f} 億元"
    elif abs(n) >= 1e4:
        return f"{n/1e4:.0f} 萬元"
    else:
        return f"{n:,.0f} 元"


def convert_minguo_date(val):
    try:
        s = str(int(val)).strip()
        if len(s) == 5:
            y, m = int(s[:3]) + 1911, int(s[3:])
        else:
            y, m = int(s[:2]) + 1911, int(s[2:])
        return pd.to_datetime(f"{y}-{m:02d}-01")
    except Exception:
        return pd.NaT
