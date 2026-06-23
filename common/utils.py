import math
import pandas as pd


def safe_div(n, d):
    if d is None or pd.isna(d) or d == 0:
        return 0.0
    if n is None or pd.isna(n):
        return 0.0
    if isinstance(n, (str, bool)) or isinstance(d, (str, bool)):
        return 0.0
    try:
        n_f = float(n)
        d_f = float(d)
        if not math.isfinite(n_f) or not math.isfinite(d_f):
            return 0.0
        return n_f / d_f
    except:
        return 0.0


def format_large_number(n, decimals=2):
    try:
        n_f = float(n)
    except:
        return "—"
    if pd.isna(n_f) or not math.isfinite(n_f):
        return "—"
    if abs(n_f) >= 1e8:
        return f"{n_f/1e8:.{decimals}f} 億元"
    if abs(n_f) >= 1e4:
        return f"{n_f/1e4:.0f} 萬元"
    return f"{n_f:,.0f} 元"


def fmt_pct(v, decimals=1):
    try:
        return f"{float(v)*100:.{decimals}f}%"
    except:
        return "—"
