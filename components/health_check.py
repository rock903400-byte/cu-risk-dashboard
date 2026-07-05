import html
from typing import Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from charts.style import apply_chart_style, DOWNLOAD_CONFIG
from common.utils import format_large_number


def render_health_check(
    data: pd.DataFrame,
    df_m: pd.DataFrame,
    df_l: pd.DataFrame,
    region_data: Optional[pd.DataFrame],
    theme_bg: str,
) -> None:
    """個社健檢：selectbox → 柱狀圖對比 + 4 個 metric + 近年趨勢"""
    unique_names = data["社名"].unique()
    if len(unique_names) == 0:
        st.info("📭 目前無社別資料")
        return

    target = st.selectbox("請選擇儲互社", unique_names, index=0)
    if target:
        row = data[data["社名"] == target].iloc[0]
        st.markdown(
            f"#### 【{html.escape(str(target))}】 狀態：`{html.escape(str(row['診斷狀態']))}`"
        )
        if row["建議留意事項"]:
            st.markdown(
                f'<div class="alert-box alert-error">🚩 觸發項目：{html.escape(str(row["建議留意事項"]))}</div>',
                unsafe_allow_html=True,
            )
        KEYS = [
            "貸放比",
            "儲蓄率",
            "逾放比",
            "開支比",
            "社員成長率(12M)",
            "股金成長率(12M)",
        ]
        avg_src = region_data if region_data is not None else data
        avg_label = "區域平均" if region_data is not None else "全台平均"
        y_target = [row[k] if k != "開支比" else row["開支比(年)"] for k in KEYS]
        y_avg = [
            avg_src[k].mean() if k != "開支比" else avg_src["開支比(年)"].mean()
            for k in KEYS
        ]
        fig_bar = go.Figure(
            [
                go.Bar(name=target, x=KEYS, y=y_target, marker_color="#3B82F6"),
                go.Bar(name=avg_label, x=KEYS, y=y_avg, marker_color="#CBD5E1"),
            ]
        )
        apply_chart_style(
            fig_bar, title=f"指標對比 ({avg_label})", is_pct=False, theme_bg=theme_bg
        )
        st.plotly_chart(fig_bar, use_container_width=True, config=DOWNLOAD_CONFIG)
        cols = st.columns(4)
        for i, (k, v) in enumerate(
            [
                ("現有社員（人）", f"{int(row['現有社員']):,}"),
                ("現有股金", format_large_number(row["現有股金"])),
                ("逾放比（%）", f"{row['逾放比']:.2%}"),
                ("開支比（年）", f"{row['開支比(年)']:.2%}"),
            ]
        ):
            cols[i].metric(k, v)

        st.markdown("---")
        st.markdown("#### 近年指標趨勢（年底基準）")

        union_sno = row["社號"]
        m_hist = df_m[df_m["社號"] == union_sno].sort_values("年月")
        l_hist = df_l[df_l["社號"] == union_sno].sort_values("年月")

        m_yr = m_hist[m_hist["年月"].dt.month == 12].copy()
        l_yr = l_hist[l_hist["年月"].dt.month == 12].copy()
        hist_df = pd.merge(
            m_yr[["年月", "社員數", "貸放比", "儲蓄率"]],
            l_yr[["年月", "逾放比", "開支比", "提撥率"]],
            on="年月",
            how="outer",
        ).sort_values("年月")
        hist_df["年度"] = hist_df["年月"].dt.year

        if len(hist_df) >= 2:

            def small_trend(metric, title, is_pct=True):
                df_plot = hist_df[["年度", metric]].dropna()
                if df_plot.empty:
                    return
                fig = px.line(df_plot, x="年度", y=metric, markers=True)
                apply_chart_style(
                    fig, title, is_pct=is_pct, theme_bg=theme_bg, interactive=False
                )
                fig.update_layout(height=280, margin=dict(t=40, b=20, l=5, r=5))
                st.plotly_chart(fig, use_container_width=True, config=DOWNLOAD_CONFIG)

            col_a, col_b = st.columns(2)
            with col_a:
                small_trend("開支比", "📈 開支比（年度）")
                small_trend("逾放比", "⚠️ 逾放比")
            with col_b:
                small_trend("貸放比", "💰 貸放比")
                small_trend("社員數", "👥 社員數（人）", is_pct=False)
        else:
            st.info("歷史資料不足，無法繪製趨勢圖。")
