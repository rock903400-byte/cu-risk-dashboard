"""
儲互社分析系統 — 主入口
"""
import logging
import uuid

import streamlit as st

from services.auth import render_login_page, handle_login
from services.cloud import init_supabase, download_file_from_storage
from config import APP_CSS, get_config
from data.csv_processor import process_csv_final
from data.excel_processor import process_excel_final
from views.overview import render_overview_page
from views.war_room import render_war_room_page

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

CONFIG = get_config()

# ── 頁面設定 ──────────────────────────────────────────────
st.set_page_config(
    page_title="儲互社分析系統",
    layout="wide",
    page_icon="🏦",
    initial_sidebar_state="collapsed",
)
st.markdown(APP_CSS.format(theme_bg=CONFIG["THEME_BG"]), unsafe_allow_html=True)

# ── Session State 初始化 ──────────────────────────────────
_DEFAULTS = {
    "logged_in":          False,
    "role":               None,
    "assigned_region":    None,
    "assigned_union":     None,
    "login_attempts":     0,
    "locked":             False,
    "preloaded_data":     None,   # (data, df_m, df_l, raw_bytes, region_map)
    "preloaded_csv":      None,   # (df, raw_bytes)
    "preloaded_passwords": {},
    "nav_selection":      "📊 社務診斷",
    "is_district_office": False,
    "confirm_logout":     False,
    "xl_msg":             None,
    "csv_msg":            None,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── 雲端服務 ──────────────────────────────────────────────
supabase = init_supabase()

# ── 共享連結預載 ──────────────────────────────────────────
shared_file = st.query_params.get("file")
shared_csv  = st.query_params.get("csv")

if shared_file and st.session_state["preloaded_data"] is None:
    try:
        raw_bytes = download_file_from_storage(supabase, CONFIG["BUCKET_NAME"], shared_file)
        data, df_m, df_l, region_pws, region_map = process_excel_final(
            raw_bytes, CONFIG["THRESHOLDS"], CONFIG["SHEETS"]
        )
        st.session_state.update(
            preloaded_passwords=region_pws,
            preloaded_data=(data, df_m, df_l, raw_bytes, region_map),
        )
    except Exception as e:
        st.session_state["preload_err"] = str(e)

if shared_csv and st.session_state["preloaded_csv"] is None:
    try:
        raw_csv = download_file_from_storage(supabase, CONFIG["BUCKET_NAME"], shared_csv)
        st.session_state["preloaded_csv"] = (process_csv_final(raw_csv), raw_csv)
    except Exception as e:
        logger.error(f"CSV 載入失敗: {e}")

# ── 登入關卡 ──────────────────────────────────────────────
if not st.session_state["logged_in"]:
    render_login_page(CONFIG["MAX_ATTEMPTS"])
    st.stop()

# ── 資料載入與過濾 ────────────────────────────────────────
IS_ADMIN   = (st.session_state["role"] == "admin")
data_loaded = False
region_data = None

if st.session_state["preloaded_data"]:
    data, df_m, df_l, raw_bytes, region_map = st.session_state["preloaded_data"]
    region = st.session_state["assigned_region"]
    union  = st.session_state["assigned_union"]

    if region:
        # 取得該區域內所有實際有財報的社名
        region_data = data[data["區域"] == region].copy()
        actual_unions_in_reg = set(region_data["社名"].unique())

        if union in actual_unions_in_reg:
            # 【個社模式】：登入名稱是一個實際存在的社
            data = data[data["社名"] == union].copy()
            st.session_state["is_district_office"] = False
        else:
            # 【區會模式】：登入名稱不在財報清單中，視為管理單位
            if region_data.empty:
                st.warning("該區目前尚無報表資料，請先上傳資料庫。")
                st.stop()
            data = region_data.copy()
            st.session_state["is_district_office"] = True
        
        target_snos = data["社號"].unique()
        df_m = df_m[df_m["社號"].isin(target_snos)].copy()
        df_l = df_l[df_l["社號"].isin(target_snos)].copy()
    else:
        # Admin 模式
        st.session_state["is_district_office"] = False
        region_map = region_map

    data_loaded = True

if st.session_state["preloaded_csv"]:
    df_csv_full, raw_csv_bytes = st.session_state["preloaded_csv"]
    union  = st.session_state["assigned_union"]
    region = st.session_state["assigned_region"]
    is_dist = st.session_state.get("is_district_office", False)

    if union and not is_dist:
        # 個社：僅顯示自身資料
        df_csv = df_csv_full[df_csv_full["社名"] == union].copy()
    elif region:
        # 區會或管理員：查看該區域內所有社
        _, _, _, _, rm = st.session_state["preloaded_data"]
        target_names = [n for n, r in rm.items() if r == region]
        df_csv = df_csv_full[df_csv_full["社名"].isin(target_names)].copy()
    else:
        df_csv = df_csv_full.copy()
    data_loaded = True

# ── 管理員側邊欄 ──────────────────────────────────────────
if IS_ADMIN:
    with st.sidebar:
        st.markdown('<span class="sidebar-label">📂 資料匯入</span>', unsafe_allow_html=True)
        uploaded_xl  = st.file_uploader("Excel (風險診斷)", type=["xlsx"], label_visibility="collapsed")
        uploaded_csv = st.file_uploader("CSV (財務明細)",  type=["csv"],  label_visibility="collapsed")

        if uploaded_xl:
            try:
                raw_bytes = uploaded_xl.getvalue()
                data, df_m, df_l, region_pws, region_map = process_excel_final(
                    raw_bytes, CONFIG["THRESHOLDS"], CONFIG["SHEETS"]
                )
                st.session_state.update(
                    preloaded_passwords=region_pws,
                    preloaded_data=(data, df_m, df_l, raw_bytes, region_map),
                )
                data_loaded = True
                st.session_state["xl_msg"] = ("success", "✅ Excel 解析成功，資料已載入。")
            except Exception as e:
                st.session_state["xl_msg"] = ("error", f"❌ Excel 解析失敗：{e}")

        if st.session_state["xl_msg"]:
            _t, _m = st.session_state["xl_msg"]
            if _t == "success":
                st.success(_m)
            else:
                st.error(_m)

        if uploaded_csv:
            try:
                raw_csv_bytes = uploaded_csv.getvalue()
                df_csv = process_csv_final(raw_csv_bytes)
                st.session_state["preloaded_csv"] = (df_csv, raw_csv_bytes)
                data_loaded = True
                st.session_state["csv_msg"] = ("success", "✅ CSV 解析成功，資料已載入。")
            except Exception as e:
                st.session_state["csv_msg"] = ("error", f"❌ CSV 解析失敗：{e}")

        if st.session_state["csv_msg"]:
            _t, _m = st.session_state["csv_msg"]
            if _t == "success":
                st.success(_m)
            else:
                st.error(_m)

        if st.session_state["preloaded_data"] or st.session_state["preloaded_csv"]:
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown('<span class="sidebar-label">🔗 分享功能</span>', unsafe_allow_html=True)
            if st.button("🚀 生成分享連結", use_container_width=True):
                if not supabase:
                    st.error("❌ 雲端服務未設定，無法產生分享連結。")
                else:
                    params = []
                    if st.session_state["preloaded_data"]:
                        f_xl = f"xl_{uuid.uuid4().hex[:8]}.xlsx"
                        supabase.storage.from_(CONFIG["BUCKET_NAME"]).upload(
                            f_xl, st.session_state["preloaded_data"][3],
                            file_options={"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
                        )
                        params.append(f"file={f_xl}")
                    if st.session_state["preloaded_csv"]:
                        f_csv = f"csv_{uuid.uuid4().hex[:8]}.csv"
                        supabase.storage.from_(CONFIG["BUCKET_NAME"]).upload(
                            f_csv, st.session_state["preloaded_csv"][1],
                            file_options={"content-type": "text/csv"},
                        )
                        params.append(f"csv={f_csv}")
                    if params:
                        st.session_state["latest_share_url"] = (
                            f"{CONFIG['APP_BASE_URL']}/?{'&'.join(params)}"
                        )
            if "latest_share_url" in st.session_state:
                st.code(st.session_state["latest_share_url"], language="text")

if not data_loaded:
    st.info("👋 歡迎使用分析系統！請由側邊欄上傳 Excel 檔案或點擊分享連結。")
    st.stop()

# ── 標題 ──────────────────────────────────────────────────
if st.session_state.get("is_district_office"):
    # 區會模式
    disp_title = f"{st.session_state['assigned_region']}區會"
elif st.session_state.get("assigned_union"):
    # 個社模式
    disp_title = st.session_state["assigned_union"]
else:
    # Admin 或未分配區域
    disp_title = st.session_state["assigned_region"] or "全台"

# 智能避開重複的「儲互社」字眼
if "儲互社" in disp_title:
    display_text = f"{disp_title} 分析系統"
else:
    display_text = f"{disp_title} 儲互社分析系統"

st.markdown(f"<h1 class='responsive-h1'>📊 {display_text}</h1>",
            unsafe_allow_html=True)

# ── 導覽側邊欄 ────────────────────────────────────────────
with st.sidebar:
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<span class="sidebar-label">🧭 系統導覽</span>', unsafe_allow_html=True)

    nav_options = []
    if st.session_state["preloaded_data"]:
        nav_options.append("📊 社務診斷")
    if st.session_state["preloaded_csv"]:
        nav_options.append("⚖️ 財報明細")
    if not nav_options:
        nav_options = ["👋 歡迎頁面"]

    if st.session_state["nav_selection"] not in nav_options:
        st.session_state["nav_selection"] = nav_options[0]

    st.session_state["nav_selection"] = st.radio(
        "選擇功能模組", nav_options,
        label_visibility="collapsed",
        index=nav_options.index(st.session_state["nav_selection"]),
    )

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<span class="sidebar-label">👤 帳號權限</span>', unsafe_allow_html=True)
    if IS_ADMIN:
        badge_cls, badge_txt = "badge-admin", "🔑 管理員模式"
    else:
        disp_name = st.session_state["assigned_union"] or st.session_state["assigned_region"]
        badge_cls, badge_txt = "badge-viewer", f"👁️ 訪客：{disp_name}"
    st.markdown(f'<div class="{badge_cls}">{badge_txt}</div>', unsafe_allow_html=True)
    if not st.session_state["confirm_logout"]:
        if st.button("🚪 登出系統", use_container_width=True):
            st.session_state["confirm_logout"] = True
            st.rerun()
    else:
        st.warning("⚠️ 確定要登出嗎？")
        _cy, _cn = st.columns(2)
        if _cy.button("✅ 確定登出", use_container_width=True):
            for k, v in _DEFAULTS.items():
                st.session_state[k] = v
            st.rerun()
        if _cn.button("❌ 取消", use_container_width=True):
            st.session_state["confirm_logout"] = False
            st.rerun()

# ── 頁面路由 ──────────────────────────────────────────────
if st.session_state["nav_selection"] == "📊 社務診斷":
    render_overview_page(data, df_m, df_l, region_data, CONFIG)

elif st.session_state["nav_selection"] == "⚖️ 財報明細":
    render_war_room_page(df_csv, IS_ADMIN, CONFIG)

else:
    st.info("👋 歡迎！請由左側上傳資料或選擇功能模組。")
