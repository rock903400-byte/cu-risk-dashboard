import numpy as np
import pandas as pd
from .constants import PERCENTAGE_FIELDS


def normalize_html_percentage(val, col_name):
    """Process raw HTML cell value for database storage.
    Used by 下載工具 during HTML scraping."""
    s = str(val).strip().replace(",", "").replace("NT$", "")
    if s in ("&nbsp;", "", "nan"):
        return np.nan
    if col_name == "提撥率" and "無逾期" in s:
        return "無逾期"
    try:
        raw_f = float(s.replace("%", ""))
        if col_name in PERCENTAGE_FIELDS:
            return round(raw_f / 100, 6)
        return int(raw_f)
    except:
        return s


def defensive_clean_value(val, col_name):
    """Defensive re-cleaning for numeric values read from legacy Excel.
    Used by deploy/報告工具 when reading old database files."""
    try:
        if pd.isna(val):
            return val
    except:
        pass
    if col_name in ("逾放比", "提撥率"):
        return val
    try:
        f_val = float(val)
        if col_name in ("貸放比", "儲蓄率"):
            return f_val / 100 if abs(f_val) > 1.0 else f_val
        if col_name in ("收支比", "開支比"):
            return f_val / 100 if abs(f_val) > 5.0 else f_val
    except:
        pass
    return val


def defensive_clean_series(series, col_name):
    return series.apply(lambda x: defensive_clean_value(x, col_name))
