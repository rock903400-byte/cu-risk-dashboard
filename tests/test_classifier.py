import pytest
from data.classifier import classify, classify_code

THRESHOLDS = {
    "high_risk_income_ratio": 1.0,
    "high_risk_loan_ratio":   0.1,
    "high_risk_ovd_ratio":    0.5,
    "liquidity_loan":         0.9,
    "idle_loan":              0.3,
    "stable_loan_min":        0.4,
    "stable_loan_max":        0.8,
    "ovd_safe_line":          0.02,
    "high_risk_ovd":          0.1,
}

def _base():
    return dict(
        M0=100, M1=95, M2=90, M3=85,
        S0=1000, S1=950, S2=900, S3=850,
        R0=0.8, R1=0.8,
        O0=50, O1=60,
        eOvd=0.01, sOvd=0.01, eLoan=0.6,
        memG=0.05, shrG=0.05,
    )


class TestClassify:
    def test_重點輔導_c1_c2(self):
        p = _base()
        p.update(R0=1.1, R1=1.1, eLoan=0.05)  # c1 + c2
        status, reason = classify(p, THRESHOLDS)
        assert status == "🚨 特別關懷"
        assert "連兩年虧損" in reason
        assert "貸放比過低" in reason

    def test_重點輔導_c1_c3(self):
        p = _base()
        p.update(R0=1.1, R1=1.1, eOvd=0.6, O0=100, O1=50)  # c1 + c3
        status, reason = classify(p, THRESHOLDS)
        assert status == "🚨 特別關懷"
        assert "高逾放且惡化" in reason

    def test_重點輔導_c4_c5(self):
        p = _base()
        p.update(M0=80, M1=90, M2=100, M3=110,   # c4: 連三年社員衰退
                 S0=80, S1=90, S2=100, S3=110)    # c5: 連三年股金衰退
        status, reason = classify(p, THRESHOLDS)
        assert status == "🚨 特別關懷"
        assert "人數連兩年衰退" in reason
        assert "股金連兩年衰退" in reason

    def test_邊界_一個條件不觸發重點輔導(self):
        p = _base()
        p.update(R0=1.1, R1=1.1)  # 只有 c1，不足兩項
        status, _ = classify(p, THRESHOLDS)
        assert status != "🚨 特別關懷"

    def test_流動性緊繃(self):
        p = _base()
        p.update(eLoan=0.95, shrG=-0.1)
        status, reason = classify(p, THRESHOLDS)
        assert status == "⚠️ 流動性緊繃"
        assert reason == "貸放比偏高且股金衰退"

    def test_資金閒置(self):
        p = _base()
        p.update(eLoan=0.2, eOvd=0.01)
        status, reason = classify(p, THRESHOLDS)
        assert status == "💤 資金閒置"
        assert reason == "貸放比偏低且逾放安全"

    def test_穩健模範(self):
        p = _base()
        p.update(eLoan=0.6, eOvd=0.01, memG=0.05, shrG=0.05)
        status, reason = classify(p, THRESHOLDS)
        assert status == "✅ 穩健模範"
        assert reason == "各項指標均達標"

    def test_一般狀態(self):
        p = _base()
        p.update(eLoan=0.35, eOvd=0.05, memG=-0.01, shrG=-0.01)
        status, reason = classify(p, THRESHOLDS)
        assert status == "📊 一般狀態"
        assert "逾放比偏高" in reason  # eOvd=0.05 > ovd_safe_line=0.02
        assert "社員、股金雙降" in reason  # memG<0 and shrG<0

    def test_一般狀態_平穩(self):
        p = _base()
        p.update(eLoan=0.35, eOvd=0.01, memG=0.01, shrG=0.01)
        status, reason = classify(p, THRESHOLDS)
        assert status == "📊 一般狀態"
        assert reason == "各指標平穩"


class TestClassifyCode:
    @pytest.mark.parametrize("code,expected", [
        ("1101", "資產"),
        ("2201", "負債"),
        ("3101", "權益"),
        ("4101", "收入"),
        ("5101", "支出"),
        ("",     "其他"),
        ("9999", "其他"),
    ])
    def test_mapping(self, code, expected):
        assert classify_code(code) == expected
