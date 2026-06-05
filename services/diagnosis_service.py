import pandas as pd

from data.utils import safe_div, format_large_number
from services.finance_service import get_annual_snapshot

THRESHOLDS = {
    "debt_ratio":    {"green": 0.80, "red": 0.90},
    "equity_ratio":  {"green": 0.20, "red": 0.10},
    "expense_ratio": {"green": 0.95, "red": 1.05},
    "avg_rate":      {"green": 0.03, "red": 0.02},
}

_YOY_RULES = [
    (["利息支出"],               "increase", "建議檢視現有借款利率，評估是否有再融資機會以降低資金成本。"),
    (["薪資", "人事", "用人費"], "increase", "建議審視人事配置與薪資結構，評估效率提升空間。"),
    (["逾期", "催收", "呆帳"],  "increase", "建議加強催收作業，並評估是否需提高備抵呆帳提撥比率。"),
    (["放款", "信用"],           "decrease", "注意放款業務收縮趨勢，可能影響未來利息收入。"),
    (["利息收入"],               "decrease", "利息收入下滑，建議評估放款策略或定存配置調整。"),
    (["業務費", "交際", "廣告"], "increase", "業務費用顯著增加，建議評估其效益與必要性。"),
]


def calc_ratios(annual_agg: pd.DataFrame) -> dict:
    codes = annual_agg["會計科目"].astype(str)
    total_assets  = annual_agg[codes.str.startswith("1")]["當月金額"].sum()
    total_liabs   = annual_agg[codes.str.startswith("2")]["當月金額"].sum()
    total_equity  = annual_agg[codes.str.startswith("3")]["當月金額"].sum()
    total_income  = annual_agg[codes.str.startswith("4")]["當月金額"].sum()
    total_expense = annual_agg[codes.str.startswith("5")]["當月金額"].sum()
    interest_income = annual_agg[codes.str.startswith("4101")]["當月金額"].sum()
    loan_balance = annual_agg[codes.str.startswith("131")]["當月金額"].sum()
    return {
        "debt_ratio":    safe_div(total_liabs, total_assets),
        "equity_ratio":  safe_div(total_equity, total_assets),
        "expense_ratio": safe_div(total_expense, total_income),
        "net_income":    total_income - total_expense,
        "total_assets":  total_assets,
        "total_income":  total_income,
        "total_expense": total_expense,
        "avg_rate":      safe_div(interest_income, loan_balance),
    }


def rate_ratio(value: float, key: str) -> str:
    t = THRESHOLDS[key]
    if key == "equity_ratio":
        if value <= t["red"]:  return "red"
        if value < t["green"]: return "yellow"
        return "green"
    elif key == "avg_rate":
        if value >= t["green"]: return "green"
        if value >= t["red"]:   return "yellow"
        return "red"
    else:
        if value >= t["red"]:   return "red"
        if value >= t["green"]: return "yellow"
        return "green"


def get_yoy_advice(anomalies: pd.DataFrame) -> list[dict]:
    if anomalies.empty:
        return []
    advice = []
    for _, row in anomalies.head(5).iterrows():
        name = str(row["會科名稱"])
        chg  = row["變動金額"]
        pct  = row["變動率 (%)"]
        direction = "increase" if chg > 0 else "decrease"
        direction_zh = "暴增" if chg > 0 else "驟減"

        body = None
        for keywords, rule_dir, suggestion in _YOY_RULES:
            if rule_dir == direction and any(kw in name for kw in keywords):
                body = suggestion
                break
        if body is None:
            body = f"建議確認「{name}」{'大幅增加' if chg > 0 else '大幅減少'}的原因，評估是否屬正常業務波動。"

        advice.append({
            "level": "red" if abs(pct) >= 30 else "yellow",
            "title": f"{name} 較去年{direction_zh} {format_large_number(abs(chg))}（{pct:+.1f}%）",
            "body":  body,
        })
    return advice


def calc_trend(analysis_df: pd.DataFrame, all_years: list) -> pd.DataFrame:
    rows = []
    for yr in all_years:
        agg = get_annual_snapshot(analysis_df, yr)
        if agg.empty:
            continue
        r = calc_ratios(agg)
        rows.append({
            "年度":  yr,
            "開支比": r["expense_ratio"],
            "加權平均利率": r["avg_rate"],
            "損益":   r["net_income"],
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()
