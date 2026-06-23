import html

import streamlit as st

from config import safe_secrets


def handle_login(max_attempts: int):
    entered = st.session_state.get("pwd_input", "").strip()
    admin_pw = str(safe_secrets().get("admin_password", "")).strip()
    pws = st.session_state.get("preloaded_passwords", {})

    if entered in pws:
        info = pws[entered]
        st.session_state.update(
            logged_in=True,
            role="viewer",
            assigned_union=info["name"],
            assigned_region=info["region"],
        )
    elif entered == admin_pw and admin_pw:
        st.session_state.update(
            logged_in=True, role="admin", assigned_region=None, assigned_union=None
        )
    else:
        st.session_state["login_attempts"] += 1
        if st.session_state["login_attempts"] >= max_attempts:
            st.session_state["locked"] = True


def render_login_page(max_attempts: int):
    _, col, _ = st.columns([0.8, 2.4, 0.8])
    with col:
        with st.container(border=True):
            st.markdown(
                "<h2 class='responsive-h2' style='text-align:center;'>🏦 儲互社分析系統</h2>",
                unsafe_allow_html=True,
            )
            if st.session_state.get("preload_err"):
                _msg = html.escape(str(st.session_state["preload_err"]))
                st.markdown(
                    f'<div class="alert-box alert-error">⚠️ 無法讀取雲端 Excel 資料，請確認連結。<br><small>錯誤訊息: {_msg}</small></div>',
                    unsafe_allow_html=True,
                )
            if st.session_state.get("preload_csv_err"):
                _msg = html.escape(str(st.session_state["preload_csv_err"]))
                st.markdown(
                    f'<div class="alert-box alert-error">⚠️ 無法讀取雲端 CSV 資料，請確認連結或聯絡管理員。<br><small>錯誤訊息: {_msg}</small></div>',
                    unsafe_allow_html=True,
                )
            if st.session_state["locked"]:
                st.markdown(
                    '<div class="alert-box alert-error">🔒 嘗試次數過多，請稍後再試。</div>',
                    unsafe_allow_html=True,
                )
            else:
                attempts = st.session_state["login_attempts"]
                if attempts > 0:
                    st.markdown(
                        f'<div class="alert-box alert-warning">❌ 密碼錯誤 ({attempts}/{max_attempts})</div>',
                        unsafe_allow_html=True,
                    )
                st.text_input(
                    "密碼",
                    type="password",
                    key="pwd_input",
                    label_visibility="collapsed",
                    placeholder="請輸入密碼",
                )
                st.button(
                    "🔓 登入系統",
                    use_container_width=True,
                    on_click=handle_login,
                    args=(max_attempts,),
                )
