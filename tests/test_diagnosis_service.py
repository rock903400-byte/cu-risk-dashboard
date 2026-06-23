import math
import pandas as pd
import pytest
from services.diagnosis_service import rate_ratio, calc_ratios, calc_trend
from services.finance_service import get_annual_snapshot


class TestRateRatio:

    def test_green_for_safe_value(self):
        assert rate_ratio(0.5, "debt_ratio") == "green"

    def test_yellow_for_warning_value(self):
        assert rate_ratio(0.85, "debt_ratio") == "yellow"

    def test_red_for_danger_value(self):
        assert rate_ratio(0.95, "debt_ratio") == "red"

    def test_gray_for_none(self):
        assert rate_ratio(None, "debt_ratio") == "gray"

    def test_gray_for_nan(self):
        assert rate_ratio(float("nan"), "debt_ratio") == "gray"

    def test_equity_ratio_logic(self):
        assert rate_ratio(0.25, "equity_ratio") == "green"
        assert rate_ratio(0.15, "equity_ratio") == "yellow"
        assert rate_ratio(0.05, "equity_ratio") == "red"

    def test_expense_ratio_logic(self):
        assert rate_ratio(0.9, "expense_ratio") == "green"
        assert rate_ratio(1.0, "expense_ratio") == "yellow"
        assert rate_ratio(1.1, "expense_ratio") == "red"

    def test_avg_rate_logic(self):
        assert rate_ratio(0.04, "avg_rate") == "green"
        assert rate_ratio(0.025, "avg_rate") == "yellow"
        assert rate_ratio(0.01, "avg_rate") == "red"


class TestCalcRatios:

    def _sample_annual_agg(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "會計科目": ["1101", "2101", "3101", "4101", "5101"],
                "會科名稱": ["現金", "存款負債", "股金", "利息收入", "利息支出"],
                "當月金額": [1000, 600, 400, 500, 300],
            }
        )

    def test_debt_ratio(self):
        r = calc_ratios(self._sample_annual_agg())
        assert r["debt_ratio"] == pytest.approx(0.6)

    def test_equity_ratio(self):
        r = calc_ratios(self._sample_annual_agg())
        assert r["equity_ratio"] == pytest.approx(0.4)

    def test_expense_ratio(self):
        r = calc_ratios(self._sample_annual_agg())
        assert r["expense_ratio"] == pytest.approx(0.6)

    def test_net_income(self):
        r = calc_ratios(self._sample_annual_agg())
        assert r["net_income"] == 200

    def test_empty_df_returns_zeros(self):
        r = calc_ratios(pd.DataFrame(columns=["會計科目", "當月金額"]))
        assert r["debt_ratio"] == 0.0
        assert r["equity_ratio"] == 0.0
        assert r["expense_ratio"] == 0.0
        assert r["net_income"] == 0.0

    def test_nan_amounts_does_not_propagate(self):
        """當月金額含 NaN 時，sum 不應傳出 NaN（導致下游 safe_div 失效）"""
        df = pd.DataFrame(
            {
                "會計科目": ["1101", "2101", "3101", "4101", "5101"],
                "會科名稱": ["現金", "存款負債", "股金", "利息收入", "利息支出"],
                "當月金額": [1000.0, float("nan"), 400.0, 500.0, 300.0],
            }
        )
        r = calc_ratios(df)
        assert not math.isnan(r["debt_ratio"])
        assert not math.isnan(r["equity_ratio"])
        assert not math.isnan(r["expense_ratio"])
        assert not math.isnan(r["net_income"])
        assert not math.isnan(r["total_assets"])
        assert not math.isnan(r["total_income"])
        assert not math.isnan(r["total_expense"])
        assert r["net_income"] == 200


class TestCalcTrend:

    def _make_multi_year_df(self) -> pd.DataFrame:
        rows = []
        for year in ["111", "112"]:
            for m in [1, 12]:
                ym = f"{year}{m:02d}"
                rows.append(
                    {
                        "年度": year,
                        "年月": ym,
                        "會計科目": "1101",
                        "會科名稱": "現金",
                        "當月金額": 1000,
                    }
                )
                rows.append(
                    {
                        "年度": year,
                        "年月": ym,
                        "會計科目": "2101",
                        "會科名稱": "存款負債",
                        "當月金額": 600,
                    }
                )
                rows.append(
                    {
                        "年度": year,
                        "年月": ym,
                        "會計科目": "3101",
                        "會科名稱": "股金",
                        "當月金額": 400,
                    }
                )
                rows.append(
                    {
                        "年度": year,
                        "年月": ym,
                        "會計科目": "4101",
                        "會科名稱": "利息收入",
                        "當月金額": 500,
                    }
                )
                rows.append(
                    {
                        "年度": year,
                        "年月": ym,
                        "會計科目": "5101",
                        "會科名稱": "利息支出",
                        "當月金額": 300,
                    }
                )
        return pd.DataFrame(rows)

    def test_returns_trend_for_multiple_years(self):
        df = self._make_multi_year_df()
        trend = calc_trend(df, ["111", "112"])
        assert len(trend) == 2
        assert list(trend["年度"]) == ["111", "112"]

    def test_empty_years_returns_empty(self):
        df = self._make_multi_year_df()
        trend = calc_trend(df, [])
        assert trend.empty

    def test_nonexistent_year_skipped(self):
        df = self._make_multi_year_df()
        trend = calc_trend(df, ["999"])
        assert trend.empty
