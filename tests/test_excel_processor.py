import pandas as pd
import pytest

from data.excel_processor import _get_value


def _make_df(months, values, col="社員數"):
    return pd.DataFrame({
        "年月": [pd.Timestamp(f"20{m}-01-01") if isinstance(m, str) else m for m in months],
        col: values,
    })


class TestGetValue:
    def test_empty_df_returns_zero(self):
        df = pd.DataFrame(columns=["年月", "社員數"])
        assert _get_value(df, "社員數", pd.Timestamp("2023-01-01")) == 0.0

    def test_returns_last_value_before_date(self):
        df = _make_df(
            [pd.Timestamp("2023-01-01"), pd.Timestamp("2023-06-01"), pd.Timestamp("2023-12-01")],
            [100, 200, 300],
        )
        result = _get_value(df, "社員數", pd.Timestamp("2023-06-01"))
        assert result == pytest.approx(200.0)

    def test_returns_last_value_strictly_before(self):
        df = _make_df(
            [pd.Timestamp("2023-01-01"), pd.Timestamp("2023-06-01")],
            [100, 200],
        )
        result = _get_value(df, "社員數", pd.Timestamp("2023-03-01"))
        assert result == pytest.approx(100.0)

    def test_no_matching_date_falls_back_to_first(self):
        df = _make_df(
            [pd.Timestamp("2023-06-01"), pd.Timestamp("2023-12-01")],
            [500, 600],
        )
        # 查詢日期早於所有資料 → 落回第一筆
        result = _get_value(df, "社員數", pd.Timestamp("2023-01-01"))
        assert result == pytest.approx(500.0)

    def test_exact_date_match(self):
        df = _make_df([pd.Timestamp("2023-12-01")], [999])
        assert _get_value(df, "社員數", pd.Timestamp("2023-12-01")) == pytest.approx(999.0)
