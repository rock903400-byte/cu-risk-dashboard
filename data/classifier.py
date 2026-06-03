"""
風險分類引擎與會計科目分類
"""


def classify(p: dict, thresholds: dict) -> tuple[str, str]:
    """
    p 包含各項指標：M0-M3 (社員), S0-S3 (股金), R0-R1 (開支比),
    O0-O1 (逾期貸款金額), eOvd (逾放比), eLoan (貸放比), shrG, memG
    回傳 (診斷狀態, 建議留意事項)
    """
    T = thresholds

    c1 = p["R0"] > T["high_risk_income_ratio"] and p["R1"] > T["high_risk_income_ratio"]
    c2 = p["eLoan"] < T["high_risk_loan_ratio"]
    c3 = p["eOvd"] > T["high_risk_ovd_ratio"] and p["O0"] > p["O1"]
    c4 = p["M0"] < p["M1"] < p["M2"] < p["M3"]
    c5 = p["S0"] < p["S1"] < p["S2"] < p["S3"]

    reasons = []
    if c1: reasons.append("連兩年虧損")
    if c2: reasons.append("貸放比過低")
    if c3: reasons.append("高逾放且惡化")
    if c4: reasons.append("人數連三年衰退")
    if c5: reasons.append("股金連三年衰退")

    if len(reasons) >= 2:
        return "🚨 特別關懷", "、".join(reasons)

    if p["eLoan"] > T["liquidity_loan"] and p["shrG"] < 0:
        return "⚠️ 流動性緊繃", ""
    if p["eLoan"] < T["idle_loan"] and p["eOvd"] < T["ovd_safe_line"]:
        return "💤 資金閒置", ""
    if (p["memG"] > 0 and p["shrG"] > 0
            and T["stable_loan_min"] < p["eLoan"] < T["stable_loan_max"]
            and p["eOvd"] < T["ovd_safe_line"]):
        return "✅ 穩健模範", ""

    return "📊 一般狀態", ""


def classify_code(code: str) -> str:
    if not str(code).strip():
        return "其他"
    mapping = {"1": "資產", "2": "負債", "3": "權益", "4": "收入", "5": "支出"}
    return mapping.get(str(code)[0], "其他")
