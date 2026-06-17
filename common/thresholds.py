DEFAULT_THRESHOLDS = {
    "high_risk_ovd": 0.1,
    "liquidity_loan": 0.9,
    "idle_loan": 0.3,
    "stable_loan_min": 0.4,
    "stable_loan_max": 0.8,
    "ovd_safe_line": 0.02,
    "high_risk_income_ratio": 1.0,
    "high_risk_loan_ratio": 0.1,
    "high_risk_ovd_ratio": 0.5,
    "savings_good": 0.6,
    "provision_good": 0.01,
}


def load_thresholds(secrets=None):
    thr = (secrets or {}).get("thresholds", {}) if secrets else {}
    return {k: thr.get(k, d) for k, d in DEFAULT_THRESHOLDS.items()}
