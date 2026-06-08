import pandas as pd


def safe_div(n, d):
    try:
        if d and not pd.isna(d) and d != 0:
            return n / d
    except:
        pass
    return 0.0


def format_large_number(n, decimals=2):
    try:
        n = float(n)
        if abs(n) >= 1e8:
            return f"{n/1e8:.{decimals}f} 億元"
        if abs(n) >= 1e4:
            return f"{n/1e4:.0f} 萬元"
        return f"{n:,.0f} 元"
    except:
        return str(n)


def fmt_pct(v, decimals=1):
    try:
        return f"{float(v)*100:.{decimals}f}%"
    except:
        return "—"
