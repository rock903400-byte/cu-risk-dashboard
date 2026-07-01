import html
from typing import Optional
import pandas as pd
import streamlit as st


def render_radar_cards(
    data: pd.DataFrame,
    thresholds: dict,
    assigned_union: Optional[str] = None,
    is_district_office: bool = False,
) -> None:
    """四色風險雷達卡（🚨 ⚠️ 💤 ✅）— 僅非個社模式呼叫"""
    # Guard to prevent rendering in individual mode
    if assigned_union and not is_district_office:
        return

    T = thresholds
    st.markdown("### 狀態雷達監控")

    def render_card(title, key, cls, criteria_text, show_reasons=False):
        subset = data[data["診斷狀態"].str.contains(key)]
        if show_reasons:
            items_html = ""
            for _, row in subset.iterrows():
                reason = row["建議留意事項"]
                reason_html = (
                    f'<div class="reason-text">→ {html.escape(str(reason))}</div>'
                    if reason
                    else ""
                )
                items_html += (
                    f'<div class="union-item">'
                    f'<span class="name-tag">{html.escape(str(row["社名"]))}</span>'
                    f"{reason_html}</div>"
                )
            body = items_html or "無"
        else:
            names = subset["社名"].tolist()
            body = (
                " ".join(
                    f'<span class="name-tag">{html.escape(str(n))}</span>'
                    for n in names
                )
                or "無"
            )
        st.markdown(
            f"<div class='stat-card'>"
            f"<div class='card-header {cls}'>{title}</div>"
            f"<div class='card-criteria'>{criteria_text}</div>"
            f"<div style='padding:10px;'>{body}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        render_card(
            "🚨 特別關懷",
            "特別關懷",
            "hdr-red",
            f"以下 5 項觸發任 2 項：<br>① 連兩年虧損 ② 貸放比＜{T['high_risk_loan_ratio']:.0%} 且較去年減少<br>③ 高逾放且惡化 ④ 人數連三年衰退 ⑤ 股金連三年衰退",
            show_reasons=False,
        )
    with sc2:
        render_card(
            "⚠️ 緊繃",
            "流動性",
            "hdr-orange",
            f"貸放比 ＞{T['liquidity_loan']:.0%} 且股金成長率為負",
        )
    with sc3:
        render_card(
            "💤 閒置",
            "資金閒置",
            "hdr-blue",
            f"貸放比 ＜{T['idle_loan']:.0%} 且逾放比 ＜{T['ovd_safe_line']:.0%}",
        )
    with sc4:
        render_card(
            "✅ 穩健",
            "穩健",
            "hdr-green",
            f"社員、股金均成長，{T['stable_loan_min']:.0%}＜貸放比＜{T['stable_loan_max']:.0%}，逾放比 ＜{T['ovd_safe_line']:.0%}",
        )
