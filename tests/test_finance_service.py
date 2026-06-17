import pandas as pd
import pytest

from services.finance_service import (
    calc_yoy_pct,
    detect_yoy_anomalies,
    get_annual_snapshot,
    prepare_waterfall_data,
)


def _make_analysis_df() -> pd.DataFrame:
    """合成 2 年 × 12 月的會計明細 DataFrame"""
    rows = []
    for year_str in ["112", "111"]:
        for m in range(1, 13):
            period = f"{year_str}{m:02d}"
            rows.append(
                {
                    "年度": year_str,
                    "年月": period,
                    "會計科目": "1101",
                    "會科名稱": "現金",
                    "當月金額": 10000 + m * 100,
                }
            )
            rows.append(
                {
                    "年度": year_str,
                    "年月": period,
                    "會計科目": "2101",
                    "會科名稱": "存款負債",
                    "當月金額": 8000,
                }
            )
            rows.append(
                {
                    "年度": year_str,
                    "年月": period,
                    "會計科目": "4101",
                    "會科名稱": "利息收入",
                    "當月金額": 500,
                }
            )
            rows.append(
                {
                    "年度": year_str,
                    "年月": period,
                    "會計科目": "5101",
                    "會科名稱": "利息支出",
                    "當月金額": 200,
                }
            )
    return pd.DataFrame(rows)


def _make_agg_df() -> pd.DataFrame:
    """合成 annual_agg DataFrame（真實下載工具 CSV 格式：費用為負值）"""
    return pd.DataFrame(
        [
            {"會計科目": "4101", "會科名稱": "利息收入", "當月金額": 10000},
            {"會計科目": "5101", "會科名稱": "利息支出", "當月金額": -3000},
            {"會計科目": "5201", "會科名稱": "薪資費用", "當月金額": -2000},
        ]
    )


def _make_multi_expense_df() -> pd.DataFrame:
    """模擬完整損益場景：收入 + 5 類費用（回歸測試 waterfall net bug）"""
    return pd.DataFrame(
        [
            {"會計科目": "4101", "會科名稱": "利息收入", "當月金額": 247000},
            {"會計科目": "4201", "會科名稱": "其他收入", "當月金額": 63000},
            {"會計科目": "5101", "會科名稱": "利息支出", "當月金額": -91000},
            {"會計科目": "5201", "會科名稱": "用人費用", "當月金額": -61000},
            {"會計科目": "5301", "會科名稱": "業務費", "當月金額": -30500},
            {"會計科目": "5401", "會科名稱": "管理費用", "當月金額": -15000},
            {"會計科目": "5501", "會科名稱": "呆帳提列", "當月金額": -6000},
        ]
    )


class TestGetAnnualSnapshot:
    def test_balance_sheet_uses_last_month(self):
        result = get_annual_snapshot(_make_analysis_df(), "112")
        asset = result[result["會計科目"] == "1101"]["當月金額"].iloc[0]
        assert asset == pytest.approx(10000 + 12 * 100)  # 11200

    def test_pl_sums_all_months(self):
        result = get_annual_snapshot(_make_analysis_df(), "112")
        income = result[result["會計科目"] == "4101"]["當月金額"].iloc[0]
        assert income == pytest.approx(500 * 12)  # 6000

    def test_empty_year_returns_empty_df(self):
        result = get_annual_snapshot(_make_analysis_df(), "999")
        assert result.empty

    def test_same_months_filters_both_pl_and_bs(self):
        """same_months 應同時篩選損益與資產負債科目，確保公平對比"""
        df = _make_analysis_df()
        result = get_annual_snapshot(df, "112", same_months=["11201", "11202", "11203"])
        income = result[result["會計科目"] == "4101"]["當月金額"].iloc[0]
        assert income == pytest.approx(500 * 3)
        asset = result[result["會計科目"] == "1101"]["當月金額"].iloc[0]
        assert asset == pytest.approx(10000 + 3 * 100)  # 11203 的快照值

    def test_same_months_cross_year(self):
        """same_months 傳入今年月份，應自動比對去年同期月份"""
        df = _make_analysis_df()
        # 傳入 112 年的月份，但查詢 111 年，應比對 11101, 11102, 11103
        result = get_annual_snapshot(df, "111", same_months=["11201", "11202", "11203"])
        income = result[result["會計科目"] == "4101"]["當月金額"].iloc[0]
        assert income == pytest.approx(500 * 3)

    def test_same_months_non_contiguous(self):
        """same_months 可處理非連續月份（如 5-8 月）"""
        df = _make_analysis_df()
        result = get_annual_snapshot(
            df, "112", same_months=["11205", "11206", "11207", "11208"]
        )
        income = result[result["會計科目"] == "4101"]["當月金額"].iloc[0]
        assert income == pytest.approx(500 * 4)


class TestCalcYoyPct:
    def test_positive_growth(self):
        assert calc_yoy_pct(110, 100) == pytest.approx(0.10)

    def test_decline(self):
        assert calc_yoy_pct(90, 100) == pytest.approx(-0.10)

    def test_zero_previous_returns_none(self):
        assert calc_yoy_pct(50, 0) is None

    def test_no_change(self):
        assert calc_yoy_pct(100, 100) == pytest.approx(0.0)


class TestPrepareWaterfallData:
    def test_returns_required_keys(self):
        result = prepare_waterfall_data(_make_agg_df())
        assert {"labels", "values", "measures", "net"} <= result.keys()

    def test_net_equals_income_minus_expenses(self):
        result = prepare_waterfall_data(_make_agg_df())
        # 10000 - 3000 - 2000 = 5000
        assert result["net"] == pytest.approx(5000)

    def test_first_measure_is_absolute(self):
        result = prepare_waterfall_data(_make_agg_df())
        assert result["measures"][0] == "absolute"

    def test_last_label_is_annual_profit(self):
        result = prepare_waterfall_data(_make_agg_df())
        assert result["labels"][-1] == "年度損益"
        assert result["measures"][-1] == "total"

    def test_first_label_is_total_income(self):
        result = prepare_waterfall_data(_make_agg_df())
        assert result["labels"][0] == "總收入"
        assert result["values"][0] == pytest.approx(10000)

    def test_net_with_realistic_negative_expenses(self):
        """回歸測試：真實下載工具 CSV 格式（費用為負），net 須等於 收入 + Σ負費用"""
        result = prepare_waterfall_data(_make_multi_expense_df())
        income = 247000 + 63000
        expected_net = income - 91000 - 61000 - 30500 - 15000 - 6000
        assert result["net"] == pytest.approx(expected_net)

    def test_expense_bars_are_negative_for_waterfall(self):
        """瀑布圖支出 bar 必須是負值，圖形才會正確往下減"""
        result = prepare_waterfall_data(_make_multi_expense_df())
        relative_values = [
            v for v, m in zip(result["values"], result["measures"]) if m == "relative"
        ]
        assert all(
            v < 0 for v in relative_values
        ), f"支出 bars 應全為負,實際:{relative_values}"

    def test_net_with_zero_income(self):
        """邊界：無收入時,瀑布圖 net 應為負（純虧損）"""
        df = pd.DataFrame(
            [
                {"會計科目": "5101", "會科名稱": "利息支出", "當月金額": -3000},
                {"會計科目": "5201", "會科名稱": "用人費用", "當月金額": -2000},
            ]
        )
        result = prepare_waterfall_data(df)
        assert result["net"] == pytest.approx(-5000)


class TestDetectYoyAnomalies:
    def _make_pair(self, curr_amount, prev_amount):
        curr = pd.DataFrame(
            [{"會計科目": "4101", "會科名稱": "利息收入", "當月金額": curr_amount}]
        )
        prev = pd.DataFrame(
            [{"會計科目": "4101", "會科名稱": "利息收入", "當月金額": prev_amount}]
        )
        return curr, prev

    def test_large_change_detected(self):
        curr = pd.DataFrame(
            [
                {"會計科目": "4101", "會科名稱": "利息收入", "當月金額": 20000},
                {"會計科目": "5101", "會科名稱": "利息支出", "當月金額": 5000},
            ]
        )
        prev = pd.DataFrame(
            [
                {"會計科目": "4101", "會科名稱": "利息收入", "當月金額": 10000},
                {"會計科目": "5101", "會科名稱": "利息支出", "當月金額": 4500},
            ]
        )
        result = detect_yoy_anomalies(curr, prev)
        # 4101: +10000 (100%) → detected; 5101: +500 (11%) → 500 < 5000, not detected
        assert "4101" in result["會計科目"].values
        assert "5101" not in result["會計科目"].values

    def test_no_anomaly_returns_empty(self):
        curr, prev = self._make_pair(10100, 10000)  # +100 (1%) — below both thresholds
        assert detect_yoy_anomalies(curr, prev).empty

    def test_custom_thresholds(self):
        curr, prev = self._make_pair(10500, 10000)  # +500 (5%)
        assert detect_yoy_anomalies(curr, prev).empty  # default: 500 < 5000
        result = detect_yoy_anomalies(curr, prev, threshold_amount=100, threshold_pct=4)
        assert len(result) == 1  # lowered: 500>100, 5%>4%

    def test_zero_previous_year_not_in_results(self):
        """前年金額為 0 時，變動率為 NaN，不應出現在異常清單（迴歸：修復前會算出天文數字）"""
        curr, prev = self._make_pair(50000, 0)
        result = detect_yoy_anomalies(curr, prev, threshold_amount=1, threshold_pct=1)
        assert result.empty

    def test_negative_change_detected(self):
        """大額負成長應被偵測"""
        curr, prev = self._make_pair(1000, 100000)
        result = detect_yoy_anomalies(
            curr, prev, threshold_amount=1000, threshold_pct=5
        )
        assert len(result) == 1
        assert result.iloc[0]["變動金額"] < 0

    def test_result_sorted_by_absolute_change(self):
        curr = pd.DataFrame(
            [
                {"會計科目": "4101", "會科名稱": "收入A", "當月金額": 30000},
                {"會計科目": "4201", "會科名稱": "收入B", "當月金額": 25000},
            ]
        )
        prev = pd.DataFrame(
            [
                {"會計科目": "4101", "會科名稱": "收入A", "當月金額": 10000},
                {"會計科目": "4201", "會科名稱": "收入B", "當月金額": 10000},
            ]
        )
        result = detect_yoy_anomalies(curr, prev)
        assert result.iloc[0]["會計科目"] == "4101"  # +20000 > +15000
