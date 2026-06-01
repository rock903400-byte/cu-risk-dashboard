import pandas as pd
import streamlit as st

from data.utils import format_large_number
from services.finance_service import calc_yoy_pct


def render_kpi_cards(annual_agg: pd.DataFrame, prev_agg: pd.DataFrame | None):
    """頂部 KPI 卡片：總收入 / 總支出 / 本期損益（含 YoY delta）"""
    income  = annual_agg[annual_agg["會計科目"].str.match(r"^4")]["當月金額"].sum()
    expense = annual_agg[annual_agg["會計科目"].str.match(r"^5")]["當月金額"].sum()
    profit  = income - expense

    def get_prev_value(prev_df, pattern):
        if prev_df is None or prev_df.empty:
            return 0.0
        return prev_df[prev_df["會計科目"].str.match(pattern)]["當月金額"].sum()

    prev_income  = get_prev_value(prev_agg, r"^4")
    prev_expense = get_prev_value(prev_agg, r"^5")
    prev_profit  = prev_income - prev_expense

    yoy_inc = calc_yoy_pct(income, prev_income) if prev_agg is not None and not prev_agg.empty else None
    yoy_exp = calc_yoy_pct(expense, prev_expense) if prev_agg is not None and not prev_agg.empty else None
    yoy_prf = calc_yoy_pct(profit, prev_profit) if prev_agg is not None and not prev_agg.empty else None

    fmt_yoy = lambda val: f"{val:.1%}" if val is not None else None

    c1, c2, c3 = st.columns(3)
    c1.metric("💵 年度總收入（新台幣）", format_large_number(income),  fmt_yoy(yoy_inc),
              help="▲ 綠代表收入成長")
    c2.metric("💸 年度總支出（新台幣）", format_large_number(expense), fmt_yoy(yoy_exp),
              delta_color="inverse",
              help="▲ 紅代表支出惡化（支出越低越好）")
    c3.metric("📊 本期損益（新台幣）",   format_large_number(profit),  fmt_yoy(yoy_prf),
              help="▲ 綠代表淨利成長")
