import pytest
from pydantic import ValidationError

from config import ThresholdsConfig

_VALID = dict(
    high_risk_ovd=0.1, liquidity_loan=0.9, idle_loan=0.3,
    stable_loan_min=0.4, stable_loan_max=0.8, ovd_safe_line=0.02,
    high_risk_income_ratio=1.0, high_risk_loan_ratio=0.1, high_risk_ovd_ratio=0.5,
    savings_good=0.6, provision_good=0.01,
)


class TestThresholdsConfig:
    def test_valid_defaults_load(self):
        cfg = ThresholdsConfig(**_VALID)
        assert cfg.high_risk_ovd == pytest.approx(0.1)
        assert cfg.liquidity_loan == pytest.approx(0.9)

    def test_negative_value_raises(self):
        bad = {**_VALID, "high_risk_ovd": -0.1}
        with pytest.raises(ValidationError):
            ThresholdsConfig(**bad)

    def test_zero_value_raises(self):
        bad = {**_VALID, "ovd_safe_line": 0}
        with pytest.raises(ValidationError):
            ThresholdsConfig(**bad)

    def test_all_fields_present(self):
        cfg = ThresholdsConfig(**_VALID)
        assert cfg.stable_loan_min == pytest.approx(0.4)
        assert cfg.stable_loan_max == pytest.approx(0.8)
        assert cfg.high_risk_income_ratio == pytest.approx(1.0)
        assert cfg.savings_good == pytest.approx(0.6)
        assert cfg.provision_good == pytest.approx(0.01)
