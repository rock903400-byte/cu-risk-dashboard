import html
import pandas as pd
import plotly.express as px
import streamlit as st

from charts.style import apply_chart_style, DOWNLOAD_CONFIG


def render_risk_matrix(
    data: pd.DataFrame,
    thresholds: dict,
    theme_bg: str,
    show_labels: bool = False,
) -> None:
    """風險矩陣泡泡圖 + 四象限色塊 + 下方狀態列表"""
    T = thresholds
    fig = px.scatter(
        data,
        x="貸放比",
        y="逾放比",
        color="診斷狀態",
        size="現有社員",
        hover_name="社名",
        hover_data=["建議留意事項"],
        text="社名" if show_labels else None,
        height=600,
        color_discrete_map={
            "🚨 特別關懷": "#EF4444",
            "⚠️ 流動性緊繃": "#F59E0B",
            "💤 資金閒置": "#3B82F6",
            "✅ 穩健模範": "#10B981",
            "📊 一般狀態": "#94A3B8",
        },
    )
    trace_kw = dict(
        marker=dict(
            sizeref=2 * data["現有社員"].max() / (40**2),
            line=dict(width=1, color="DarkSlateGrey"),
        )
    )
    if show_labels:
        trace_kw.update(textposition="top center", textfont=dict(size=16))
    fig.update_traces(**trace_kw)
    fig.add_hline(y=T["high_risk_ovd"], line_dash="dot", line_color="red")
    fig.add_vline(x=T["liquidity_loan"], line_dash="dot", line_color="orange")

    # 四象限背景色塊（語意：高貸+高逾=雙高風險 / 高貸+低逾=流動性緊繃 / 低貸+低逾=資金閒置 / 低貸+高逾=逾期風險）
    x_th, y_th = T["liquidity_loan"], T["high_risk_ovd"]
    x_max = max(data["貸放比"].max() * 1.1, x_th * 1.1, 1.0)
    y_max = max(data["逾放比"].max() * 1.1, y_th * 1.1, 0.05)
    quadrant_kw = dict(opacity=0.08, line_width=0, layer="below", type="rect")
    fig.add_shape(
        x0=x_th, x1=x_max, y0=y_th, y1=y_max, fillcolor="#EF4444", **quadrant_kw
    )
    fig.add_shape(x0=x_th, x1=x_max, y0=0, y1=y_th, fillcolor="#F59E0B", **quadrant_kw)
    fig.add_shape(x0=0, x1=x_th, y0=0, y1=y_th, fillcolor="#3B82F6", **quadrant_kw)
    fig.add_shape(x0=0, x1=x_th, y0=y_th, y1=y_max, fillcolor="#94A3B8", **quadrant_kw)

    apply_chart_style(fig, theme_bg=theme_bg)
    fig.update_xaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True, config=DOWNLOAD_CONFIG)

    st.markdown("---")
    st.markdown("#### 各狀態社別一覽")
    status_order = [
        "🚨 特別關懷",
        "⚠️ 流動性緊繃",
        "💤 資金閒置",
        "✅ 穩健模範",
        "📊 一般狀態",
    ]
    for _s in status_order:
        _group = data[data["診斷狀態"] == _s]["社名"].tolist()
        if _group:
            _safe_names = [html.escape(str(n)) for n in _group]
            st.markdown(f"**{_s}**（{len(_group)} 社）：{'、'.join(_safe_names)}")
