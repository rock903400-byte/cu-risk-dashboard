import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from data.classifier import classify_code
from data.utils import format_large_number
from services.finance_service import detect_yoy_anomalies, prepare_waterfall_data

CATEGORY_COLORS = {
    "資產": "#10B981", "負債": "#EF4444", "權益": "#3B82F6",
    "收入": "#F59E0B", "支出": "#6366F1",
}
CATEGORY_TABS  = ["💰 資產", "📉 負債", "⚖️ 權益", "💵 收入", "💸 支出"]
CATEGORY_NAMES = ["資產", "負債", "權益", "收入", "支出"]

_DOWNLOAD_CONFIG = {
    "displayModeBar": True,
    "modeBarButtons": [["toImage"]],
    "displaylogo": False,
    "toImageButtonOptions": {"format": "png", "scale": 3},
}


def render_waterfall(annual_agg: pd.DataFrame, selected_year: str, theme_bg: str):
    """年度利潤流向瀑布圖"""
    st.markdown(f"#### 【 {selected_year} 年度利潤流向瀑布圖 】")
    if annual_agg.empty:
        st.warning(f"當前年度 ({selected_year}) 無資料。")
        return

    wf = prepare_waterfall_data(annual_agg)
    labels, values, measures, net = wf["labels"], wf["values"], wf["measures"], wf["net"]

    def _fmt(v):
        if abs(v) >= 1e8:
            return f"{v/1e8:.2f}億"
        elif abs(v) >= 1e4:
            return f"{v/1e4:.1f}萬"
        return f"{v:,.0f}"

    text_list = [
        _fmt(v) if m != "total" else _fmt(net)
        for v, m in zip(values, measures)
    ]

    fig = go.Figure(go.Waterfall(
        name="Profit Breakdown", orientation="v",
        measure=measures, x=labels,
        textposition="outside", text=text_list, y=values,
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#10B981"}},
        decreasing={"marker": {"color": "#EF4444"}},
        totals={"marker":   {"color": "#3B82F6"}},
    ))
    fig.update_layout(
        plot_bgcolor=theme_bg, paper_bgcolor=theme_bg,
        height=500, margin=dict(t=50, b=50, l=20, r=20),
        dragmode=False, font=dict(size=15),
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True),
    )
    st.plotly_chart(fig, use_container_width=True, config=_DOWNLOAD_CONFIG)


def render_yoy_anomalies(annual_agg: pd.DataFrame, prev_agg: pd.DataFrame,
                          selected_year: str, prev_year: str):
    """YoY 異常偵測：前 3 大用 st.error 置頂，其餘放 expander"""
    anomalies = detect_yoy_anomalies(annual_agg, prev_agg)

    if anomalies.empty:
        st.success("本年度各科目變動平穩，未發現顯著異常。")
        return

    st.write(f"與 **前一年度 ({prev_year})** 相比，最劇烈前 10 大科目：")

    for _, r in anomalies.head(3).iterrows():
        direction = "暴增" if r["變動金額"] > 0 else "驟減"
        st.error(
            f"🚨 **{r['會科名稱']}** 較去年{direction} "
            f"{format_large_number(abs(r['變動金額']))}（{r['變動率 (%)']:+.1f}%）"
        )

    st.markdown("**完整異常科目（前 10 名）**")

    def color_diff(val):
        return f"color: {'#EF4444' if val > 0 else '#10B981'}; font-weight: bold"

    st.dataframe(
        anomalies.style
        .format({
            "當月金額_前": "{:,.0f}", "當月金額_今": "{:,.0f}",
            "變動金額": "{:+,.0f}", "變動率 (%)": "{:+.2f}%",
        })
        .map(color_diff, subset=["變動金額", "變動率 (%)"])
        .set_properties(**{"font-size": "18px", "padding": "10px"}),
        use_container_width=True, hide_index=True,
    )


def render_ranking_tabs(annual_agg: pd.DataFrame, theme_bg: str):
    """
    Bug C 修復：改用 st.tabs 取代 facet_col，每個 tab 各自繪製單類別 Top 10。
    """
    annual_agg = annual_agg.copy()
    annual_agg["類別"] = annual_agg["會計科目"].apply(classify_code)
    rank_df = annual_agg[annual_agg["當月金額"].abs() > 0].copy()
    rank_df["顯示金額"] = rank_df["當月金額"].abs()

    tabs = st.tabs(CATEGORY_TABS)
    for tab, cat_name in zip(tabs, CATEGORY_NAMES):
        with tab:
            cat_df = (
                rank_df[rank_df["類別"] == cat_name]
                .sort_values("顯示金額", ascending=False)
                .head(10)
                .reset_index(drop=True)
            )
            if cat_df.empty:
                st.info(f"本年度無「{cat_name}」類資料。")
                continue
            fig = px.bar(
                cat_df, x="顯示金額", y="會科名稱",
                orientation="h",
                color_discrete_sequence=[CATEGORY_COLORS.get(cat_name, "#94A3B8")],
                labels={"顯示金額": "金額", "會科名稱": "科目"},
            )
            max_val = cat_df["顯示金額"].max()
            fig.update_traces(
                text=[format_large_number(v) for v in cat_df["顯示金額"]],
                textposition="outside",
                textfont=dict(size=13),
            )
            fig.update_layout(
                plot_bgcolor=theme_bg, paper_bgcolor=theme_bg,
                margin=dict(t=30, b=30, l=10, r=30),
                dragmode=False, showlegend=False, height=380,
                font=dict(size=14),
                xaxis=dict(range=[0, max_val * 1.35], fixedrange=True),
            )
            fig.update_yaxes(fixedrange=True, categoryorder="total ascending")
            st.plotly_chart(fig, use_container_width=True, config=_DOWNLOAD_CONFIG)


def render_yearly_trend(analysis_df: pd.DataFrame, theme_bg: str):
    """歷年開支比趨勢（全歷史）"""
    st.markdown("#### 【 歷年收支與開支比趨勢 (全歷史) 】")
    analysis_df = analysis_df.copy()
    analysis_df["類別"] = analysis_df["會計科目"].apply(classify_code)
    yearly = analysis_df.groupby(["年度", "類別"])["當月金額"].sum().unstack(fill_value=0)
    for cat in ["收入", "支出"]:
        if cat not in yearly.columns:
            yearly[cat] = 0
    yearly = yearly.reset_index()
    yearly["開支比 (%)"] = (yearly["支出"] / yearly["收入"] * 100).fillna(0)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(name="總收入", x=yearly["年度"], y=yearly["收入"],
                         marker_color="#10B981"), secondary_y=False)
    fig.add_trace(go.Bar(name="總支出", x=yearly["年度"], y=yearly["支出"],
                         marker_color="#EF4444"), secondary_y=False)
    fig.add_trace(go.Scatter(name="開支比 (%)", x=yearly["年度"], y=yearly["開支比 (%)"],
                             mode="lines+markers",
                             line=dict(color="#3B82F6", width=4)), secondary_y=True)
    fig.update_layout(
        height=400, barmode="group", hovermode="x unified",
        plot_bgcolor=theme_bg, paper_bgcolor=theme_bg,
        legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
        dragmode=False, font=dict(size=14),
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True),
        yaxis2=dict(fixedrange=True),
    )
    st.plotly_chart(fig, use_container_width=True, config=_DOWNLOAD_CONFIG)
