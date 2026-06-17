def classify(p, thresholds):
    T = thresholds

    c1 = p["R0"] > T["high_risk_income_ratio"] and p["R1"] > T["high_risk_income_ratio"]
    c2 = p["eLoan"] < T["high_risk_loan_ratio"] and p["eLoan"] < p["sLoan"]
    c3 = p["eOvd"] > T["high_risk_ovd_ratio"] and p["O0"] > p["O1"]
    c4 = p["M0"] < p["M1"] < p["M2"] < p["M3"]
    c5 = p["S0"] < p["S1"] < p["S2"] < p["S3"]

    reasons = []
    if c1:
        reasons.append("連兩年虧損")
    if c2:
        reasons.append("貸放比過低")
    if c3:
        reasons.append("高逾放且惡化")
    if c4:
        reasons.append("人數連三年衰退")
    if c5:
        reasons.append("股金連三年衰退")

    if len(reasons) >= 2:
        return "🚨 特別關懷", "、".join(reasons)

    if p["eLoan"] > T["liquidity_loan"] and p["shrG"] < 0:
        return "⚠️ 流動性緊繃", "貸放比偏高且股金衰退"
    if p["eLoan"] < T["idle_loan"] and p["eOvd"] < T["ovd_safe_line"]:
        return "💤 資金閒置", "貸放比偏低且逾放安全"
    if (
        p["memG"] > 0
        and p["shrG"] > 0
        and T["stable_loan_min"] < p["eLoan"] < T["stable_loan_max"]
        and p["eOvd"] < T["ovd_safe_line"]
    ):
        return "✅ 穩健模範", "各項指標均達標"

    notes = []
    if p["eOvd"] > T["ovd_safe_line"]:
        notes.append(f"逾放比偏高 {p['eOvd']:.1%}")
    if p["R0"] >= T["high_risk_income_ratio"]:
        notes.append(f"今年虧損 開支比 {p['R0']:.1%}")
    if p["memG"] < 0 and p["shrG"] < 0:
        notes.append("社員、股金雙降")
    elif p["memG"] < 0:
        notes.append("社員成長趨緩")
    elif p["shrG"] < 0:
        notes.append("股金成長趨緩")
    return "📊 一般狀態", "；".join(notes[:2]) if notes else "各指標平穩"


def classify_code(code):
    if not str(code).strip():
        return "其他"
    mapping = {"1": "資產", "2": "負債", "3": "權益", "4": "收入", "5": "支出"}
    return mapping.get(str(code)[0], "其他")
