"""
Onboarding 引導元件 — 給第一次使用或沒有資料時的引導畫面。
"""
from typing import Optional

import streamlit as st


def render_welcome_page(
    is_admin: bool = False,
    is_district_office: bool = False,
    has_share_link: bool = False,
) -> None:
    """
    空狀態歡迎頁：取代舊版一行 st.info。
    包含 3 步驟視覺化引導 + 4 色狀態圖例 + 角色化 CTA。
    """
    st.markdown(
        """
        <div class="welcome-hero">
            <h1 class="welcome-title">🏦 儲互社分析系統</h1>
            <p class="welcome-subtitle">專為台灣儲蓄互助社設計的風險管理與財務分析平台</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if has_share_link:
        st.error(
            "⚠️ **無法讀取雲端資料**\n\n"
            "請確認分享連結是否正確,或聯絡管理員重新產生。",
            icon="🔗",
        )

    st.markdown("### 🚀 3 步驟開始使用")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            """
            <div class="step-card">
                <div class="step-num step-1">1</div>
                <div class="step-icon">📂</div>
                <h3>上傳資料</h3>
                <p>管理員從左側「資料匯入」上傳 Excel（風險診斷）或 CSV（財報明細）</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            """
            <div class="step-card">
                <div class="step-num step-2">2</div>
                <div class="step-icon">🔗</div>
                <h3>分享連結</h3>
                <p>按「🚀 生成分享連結」,把網址 LINE 傳給幹部或社員</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            """
            <div class="step-card">
                <div class="step-num step-3">3</div>
                <div class="step-icon">📊</div>
                <h3>開始分析</h3>
                <p>看到風險狀態、財務趨勢,做出更好的決策</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("### 🎨 狀態顏色說明")

    leg_a, leg_b, leg_c, leg_d, leg_e = st.columns(5)
    with leg_a:
        st.markdown(
            """
            <div class="legend-card legend-red">
                <div class="legend-emoji">🚨</div>
                <strong>特別關懷</strong>
                <p class="legend-desc">需立即關注</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with leg_b:
        st.markdown(
            """
            <div class="legend-card legend-orange">
                <div class="legend-emoji">⚠️</div>
                <strong>流動性緊繃</strong>
                <p class="legend-desc">資金較吃緊</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with leg_c:
        st.markdown(
            """
            <div class="legend-card legend-blue">
                <div class="legend-emoji">💤</div>
                <strong>資金閒置</strong>
                <p class="legend-desc">放款偏低</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with leg_d:
        st.markdown(
            """
            <div class="legend-card legend-green">
                <div class="legend-emoji">✅</div>
                <strong>穩健模範</strong>
                <p class="legend-desc">各項達標</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with leg_e:
        st.markdown(
            """
            <div class="legend-card legend-gray">
                <div class="legend-emoji">📊</div>
                <strong>一般狀態</strong>
                <p class="legend-desc">平穩無異常</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    if is_admin:
        st.markdown(
            """
            <div class="cta-box cta-admin">
                <div class="cta-icon">👤</div>
                <div>
                    <strong>您是管理員</strong><br>
                    從左側 <b>「📂 資料匯入」</b> 上傳 Excel 或 CSV 開始。
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif is_district_office:
        st.markdown(
            """
            <div class="cta-box cta-viewer">
                <div class="cta-icon">👥</div>
                <div>
                    <strong>您是區會管理</strong><br>
                    確認上方網址正確,或請總會管理員重傳分享連結。
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="cta-box cta-viewer">
                <div class="cta-icon">👤</div>
                <div>
                    <strong>您是訪客</strong><br>
                    請聯絡管理員索取分享連結,或確認上方的網址是否正確。
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def maybe_show_first_time_tip() -> None:
    """
    首次登入顯示 5 秒的「狀態顏色速覽」提示橫幅,使用者可永久關閉。
    透過 st.session_state["seen_color_tip"] 控制。
    """
    if st.session_state.get("seen_color_tip", False):
        return

    st.markdown(
        """
        <div class="first-time-tip">
            <div class="tip-title">💡 第一次使用？看這裡！</div>
            <div class="tip-body">
                全站狀態用 <b>4 種顏色</b> 標示風險：<br>
                <span class="tip-red">🚨 紅</span>＝特別關懷　
                <span class="tip-orange">⚠️ 橘</span>＝流動性緊繃　
                <span class="tip-blue">💤 藍</span>＝資金閒置　
                <span class="tip-green">✅ 綠</span>＝穩健模範
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns([1, 5])
    with col_a:
        if st.button("✅ 知道了,以後不再顯示", key="dismiss_tip", use_container_width=True):
            st.session_state["seen_color_tip"] = True
            st.rerun()
    with col_b:
        st.caption("點上方按鈕可永久關閉此提示")
