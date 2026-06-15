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
    "responsive": True,
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
        dragmode=False, font=dict(size=18),
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True),
    )
    st.plotly_chart(fig, use_container_width=True, config=_DOWNLOAD_CONFIG)


def render_yoy_anomalies(annual_agg: pd.DataFrame, prev_agg: pd.DataFrame,
                          selected_year: str, prev_year: str):
    """YoY 異常偵測"""
    anomalies = detect_yoy_anomalies(annual_agg, prev_agg)

    if anomalies.empty:
        st.success("✅ 本年度各科目變動平穩，未發現顯著異常。")
        return

    total_increase = anomalies[anomalies["變動金額"] > 0]["變動金額"].sum()
    total_decrease = anomalies[anomalies["變動金額"] < 0]["變動金額"].abs().sum()
    net_change = total_increase - total_decrease

    st.info(f"📊 與 **{prev_year}年** 相比，共 **{len(anomalies)}** 個科目有顯著變動\n\n"
            f"- 增加合計：**{format_large_number(total_increase)}**\n"
            f"- 減少合計：**{format_large_number(total_decrease)}**\n"
            f"- 淨變動：**{format_large_number(abs(net_change))}** {'↑' if net_change > 0 else '↓'}")

    _GOOD_CATS = {"收入", "資產", "權益"}

    def _build_result(df: pd.DataFrame) -> pd.DataFrame:
        r = df[["會計科目", "會科名稱", "當月金額_前", "當月金額_今"]].copy()
        r.columns = ["科目代號", "科目名稱", "去年金額", "今年金額"]
        r.insert(2, "類別", r["科目代號"].apply(classify_code))
        r["增減金額"] = df["變動金額"].values
        r["增減率"] = df["變動率 (%)"].values
        return r

    def _style_row(row):
        styles = [""] * len(row)
        cols = list(row.index)
        inc_i = cols.index("增減金額")
        rate_i = cols.index("增減率")
        val = row["增減金額"]
        if pd.isna(val) or val == 0:
            return styles
        good_up = row["類別"] in _GOOD_CATS
        color = "#10B981" if (val > 0) == good_up else "#EF4444"
        styles[inc_i] = f"color: {color}; font-weight: bold"
        styles[rate_i] = f"color: {color}; font-weight: bold"
        return styles

    _FMT = {
        "去年金額": "{:,.0f}", "今年金額": "{:,.0f}",
        "增減金額": "{:+,.0f}", "增減率": "{:+.1f}%",
    }

    st.markdown("**變動前 10 大科目**")
    st.dataframe(
        _build_result(anomalies.head(10)).style
        .format(_FMT)
        .apply(_style_row, axis=1)
        .set_properties(**{"font-size": "16px", "padding": "8px"}),
        use_container_width=True, hide_index=True,
    )

    if len(anomalies) > 10:
        st.markdown(f"**其餘 {len(anomalies) - 10} 個變動科目**")
        st.dataframe(
            _build_result(anomalies.iloc[10:]).style
            .format(_FMT)
            .apply(_style_row, axis=1)
            .set_properties(**{"font-size": "16px", "padding": "8px"}),
            use_container_width=True, hide_index=True,
        )


def render_ranking_tabs(annual_agg: pd.DataFrame, theme_bg: str,
                        compare_agg: pd.DataFrame | None = None,
                        year_label: str = "", compare_label: str = ""):
    """
    Bug C 修復：改用 st.tabs 取代 facet_col，每個 tab 各自繪製單類別 Top 10。
    compare_agg 提供時，切換為雙年分組橫條圖。
    """
    annual_agg = annual_agg.copy()
    annual_agg["類別"] = annual_agg["會計科目"].apply(classify_code)
    rank_df = annual_agg[annual_agg["當月金額"].abs() > 0].copy()
    rank_df["顯示金額"] = rank_df["當月金額"].abs()

    comp_rank = None
    if compare_agg is not None and not compare_agg.empty:
        comp_df = compare_agg.copy()
        comp_df["類別"] = comp_df["會計科目"].apply(classify_code)
        comp_rank = comp_df[comp_df["當月金額"].abs() > 0].copy()
        comp_rank["顯示金額"] = comp_rank["當月金額"].abs()

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

            cat_color = CATEGORY_COLORS.get(cat_name, "#94A3B8")

            # Plotly horizontal bar: categories render bottom-to-top, so reverse to put rank-1 at top
            y_order = list(reversed(cat_df["會科名稱"].tolist()))

            if comp_rank is not None:
                top_accounts = cat_df["會科名稱"].tolist()
                comp_cat = (
                    comp_rank[
                        (comp_rank["類別"] == cat_name) &
                        (comp_rank["會科名稱"].isin(top_accounts))
                    ][["會科名稱", "顯示金額"]]
                )
                combined = pd.concat([
                    cat_df[["會科名稱", "顯示金額"]].assign(年度=year_label),
                    comp_cat.assign(年度=compare_label),
                ], ignore_index=True)
                combined["金額標籤"] = combined["顯示金額"].apply(format_large_number)
                max_val = combined["顯示金額"].max()
                fig = px.bar(
                    combined, x="顯示金額", y="會科名稱",
                    color="年度", barmode="group", orientation="h",
                    text="金額標籤",
                    color_discrete_map={year_label: cat_color, compare_label: "#94A3B8"},
                    labels={"顯示金額": "金額", "會科名稱": "科目"},
                )
                fig.update_traces(textposition="outside", textfont=dict(size=16))
                fig.update_layout(
                    plot_bgcolor=theme_bg, paper_bgcolor=theme_bg,
                    margin=dict(t=10, b=30, l=10, r=30),
                    dragmode=False, showlegend=True, height=430,
                    font=dict(size=18),
                    xaxis=dict(range=[0, max_val * 1.5], fixedrange=True),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
            else:
                max_val = cat_df["顯示金額"].max()
                fig = px.bar(
                    cat_df, x="顯示金額", y="會科名稱",
                    orientation="h",
                    color_discrete_sequence=[cat_color],
                    labels={"顯示金額": "金額", "會科名稱": "科目"},
                )
                fig.update_traces(
                    text=[format_large_number(v) for v in cat_df["顯示金額"]],
                    textposition="outside",
                    textfont=dict(size=17),
                )
                fig.update_layout(
                    plot_bgcolor=theme_bg, paper_bgcolor=theme_bg,
                    margin=dict(t=30, b=30, l=10, r=30),
                    dragmode=False, showlegend=False, height=380,
                    font=dict(size=18),
                    xaxis=dict(range=[0, max_val * 1.35], fixedrange=True),
                )
            fig.update_yaxes(fixedrange=True, categoryorder="array", categoryarray=y_order)
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
        dragmode=False, font=dict(size=18),
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True),
        yaxis2=dict(fixedrange=True),
    )
    st.plotly_chart(fig, use_container_width=True, config=_DOWNLOAD_CONFIG)
