import io
import pandas as pd
import pytest
from data.csv_processor import process_csv_final


def _make_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


class TestProcessCsvFinal:

    def test_returns_dataframe(self):
        df_in = pd.DataFrame(
            {
                "年月": ["11201", "11202"],
                "會計科目": ["4101", "5101"],
                "會科名稱": ["利息收入", "利息支出"],
                "當月金額": [500, 300],
            }
        )
        df_out = process_csv_final(_make_csv_bytes(df_in))
        assert isinstance(df_out, pd.DataFrame)
        assert len(df_out) == 2

    def test_drops_rows_without_ym(self):
        df_in = pd.DataFrame(
            {
                "年月": ["11201", None, "11203"],
                "會計科目": ["4101", "5101", "4101"],
                "會科名稱": ["利息收入", "利息支出", "利息收入"],
                "當月金額": [500, 300, 400],
            }
        )
        df_out = process_csv_final(_make_csv_bytes(df_in))
        assert len(df_out) == 2

    def test_converts_ym_to_string(self):
        df_in = pd.DataFrame(
            {
                "年月": [11201, 11202],
                "會計科目": ["4101", "5101"],
                "會科名稱": ["利息收入", "利息支出"],
                "當月金額": [500, 300],
            }
        )
        df_out = process_csv_final(_make_csv_bytes(df_in))
        assert df_out["年月"].dtype in (object, "string")

    def test_fills_missing_account_name(self):
        df_in = pd.DataFrame(
            {
                "年月": ["11201"],
                "會計科目": ["4101"],
                "會科名稱": [None],
                "當月金額": [500],
            }
        )
        df_out = process_csv_final(_make_csv_bytes(df_in))
        assert df_out["會科名稱"].iloc[0] == "(未分類)"

    def test_coerces_invalid_amount(self):
        df_in = pd.DataFrame(
            {
                "年月": ["11201"],
                "會計科目": ["4101"],
                "會科名稱": ["利息收入"],
                "當月金額": ["abc"],
            }
        )
        df_out = process_csv_final(_make_csv_bytes(df_in))
        assert df_out["當月金額"].iloc[0] == 0.0

    def test_raises_on_invalid_bytes(self):
        with pytest.raises(ValueError, match="CSV 解析失敗"):
            process_csv_final(b"not a csv \xff\xfe")

    def test_no_account_name_column(self):
        df_in = pd.DataFrame(
            {
                "年月": ["11201"],
                "會計科目": ["4101"],
                "當月金額": [500],
            }
        )
        df_out = process_csv_final(_make_csv_bytes(df_in))
        assert "會科名稱" not in df_out.columns or df_out["當月金額"].iloc[0] == 500
