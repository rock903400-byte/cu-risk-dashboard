import pandas as pd
import pytest
from data.utils import convert_minguo_date, safe_div


class TestConvertMinguoDate:
    def test_5digit(self):
        result = convert_minguo_date(11201)
        assert result == pd.Timestamp("2023-01-01")

    def test_5digit_december(self):
        result = convert_minguo_date(11212)
        assert result == pd.Timestamp("2023-12-01")

    def test_4digit(self):
        # 民國99年1月 (4位數格式) → 2010-01-01
        result = convert_minguo_date(9901)
        assert result == pd.Timestamp("2010-01-01")

    def test_invalid_returns_nat(self):
        result = convert_minguo_date("abc")
        assert pd.isna(result)

    def test_none_returns_nat(self):
        result = convert_minguo_date(None)
        assert pd.isna(result)


class TestSafeDiv:
    def test_normal(self):
        assert safe_div(10, 2) == pytest.approx(5.0)

    def test_zero_denominator(self):
        assert safe_div(10, 0) == 0.0

    def test_nan_denominator(self):
        assert safe_div(10, float("nan")) == 0.0

    def test_zero_numerator(self):
        assert safe_div(0, 5) == 0.0
