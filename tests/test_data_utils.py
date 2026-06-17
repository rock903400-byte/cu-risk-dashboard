import pandas as pd
import pytest
from common.dates import convert_minguo_date
from common.utils import format_large_number, safe_div


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


class TestFormatLargeNumber:
    def test_yi(self):
        assert "億" in format_large_number(2e8)

    def test_wan(self):
        assert "萬" in format_large_number(50000)

    def test_small(self):
        result = format_large_number(999)
        assert "億" not in result and "萬" not in result

    def test_negative_yi(self):
        result = format_large_number(-2e8)
        assert "億" in result and "-" in result

    def test_boundary_yi(self):
        assert "億" in format_large_number(1e8)

    def test_boundary_wan(self):
        result = format_large_number(1e4)
        assert "萬" in result and "億" not in result
