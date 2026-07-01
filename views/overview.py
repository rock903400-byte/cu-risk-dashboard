from typing import Optional

import pandas as pd
import streamlit as st

from common.utils import safe_div, format_large_number
from components.risk_matrix import render_risk_matrix
from components.radar_cards import render_radar_cards
from components.health_check import render_health_check
from components.trend_tracker import render_trend_tracker


def render_overview_page(
    data: pd.DataFrame,
    df_m: pd.DataFrame,
    df_l: pd.DataFrame,
    region_data: Optional[pd.DataFrame],
    config: dict,
    assigned_union: Optional[str] = None,
    is_district_office: bool = False,
):
    THEME = config["THEME_BG"]
    T = config["THRESHOLDS"]

    if df_m is None or df_m.empty or df_m["年月"].dropna().empty:
        st.info(
            "📭 目前無「社務及資金運用情形」資料，"
            "請由側邊欄上傳 Excel 資料庫或透過分享連結載入。"
        )
        return

    latest_date = df_m["年月"].max()
    st.caption(f"📅 資料更新至 {latest_date.year} 年 {latest_date.month} 月")

    tab_ov, tab_mx, tab_hc, tab_rp, tab_tr = st.tabs(
        ["📊 經營總覽", "🎯 風險矩陣", "🏥 個社健檢", "📋 報表匯出", "📈 趨勢追蹤"]
    )

    # ── 經營總覽 ──────────────────────────────────────────
    with tab_ov:
        c1, c2, c3, c4 = st.columns(4)

        is_individual = assigned_union and not is_district_office

        if is_individual:
            avg_src = data
            avg_label = "本社"
        else:
            avg_src = region_data if region_data is not None else data
            avg_label = "區域平均" if region_data is not None else "全台平均"

        total_mem = avg_src["現有社員"].sum()
        total_shr = avg_src["現有股金"].sum()
        prev_mem = avg_src["_sM"].sum()
        prev_shr = avg_src["_sS"].sum()

        # 開支比 / 逾放比 YoY（方向性著色：inverse）
        if df_l.empty:
            max_d = pd.NaT
            T_12M = pd.NaT
            prev_逾放比_avg = float("nan")
            prev_開支比_avg = float("nan")
        else:
            max_d = df_l["年月"].max()
            T_12M = max_d - pd.DateOffset(months=12)
            prev_逾放比_avg = df_l[df_l["年月"] == T_12M]["逾放比"].mean()
            prev_開支比_avg = (
                df_l[df_l["年月"] == T_12M]["開支比"].mean()
                if pd.notna(T_12M)
                else float("nan")
            )
        curr_開支比_avg = avg_src["開支比(年)"].mean()
        curr_逾放比_avg = avg_src["逾放比"].mean()

        def _yoy_str(curr, prev):
            if pd.isna(prev) or prev == 0:
                return None
            return f"{(curr - prev) / abs(prev):.2%}"

        c1.metric(
            "社員總數（人）",
            f"{int(total_mem):,}",
            f"{safe_div(total_mem - prev_mem, prev_mem):.2%}",
            delta_color="inverse",
            help="與去年同期相比的變化。正值＝增加,負值＝減少。\n對社員人數而言,增加是好事。",
        )
        c2.metric(
            "股金總額",
            format_large_number(total_shr),
            f"{safe_div(total_shr - prev_shr, prev_shr):.2%}",
            delta_color="inverse",
            help="與去年同期相比的變化。正值＝增加,負值＝減少。\n對股金而言,增加是好事。",
        )
        c3.metric(
            f"{avg_label}開支比",
            f"{curr_開支比_avg:.2%}",
            _yoy_str(curr_開支比_avg, prev_開支比_avg),
            help="與去年同期相比的變化。開支比越低代表財務越健康。",
        )
        c4.metric(
            f"{avg_label}逾放比",
            f"{curr_逾放比_avg:.2%}",
            _yoy_str(curr_逾放比_avg, prev_逾放比_avg),
            help="與去年同期相比的變化。逾放比越低代表放款品質越好。",
        )

        render_radar_cards(data, T, assigned_union, is_district_office)

    # ── 風險矩陣 ──────────────────────────────────────────
    with tab_mx:
        show_labels = st.checkbox("🏷️ 在圖表上直接顯示社名", value=False)
        render_risk_matrix(data, T, THEME, show_labels=show_labels)

    with tab_hc:
        render_health_check(data, df_m, df_l, region_data, THEME)

    # ── 報表匯出 ──────────────────────────────────────────
    with tab_rp:
        fmt = {
            "現有社員": "{:,}",
            "社員成長數(12M)": "{:+,.0f}",
            "現有股金": "{:,.0f}",
            "社員成長率(12M)": "{:.2%}",
            "股金成長率(12M)": "{:.2%}",
            "貸放比": "{:.1%}",
            "儲蓄率": "{:.1%}",
            "逾放比(12M)": "{:.2%}",
            "逾放比": "{:.2%}",
            "開支比": "{:.2%}",
            "提撥率": lambda x: "無逾期" if x == -1 else f"{x:.2%}",
        }

        # 4 狀態對應 4 色（cell-level，僅標 診斷狀態 欄；一般狀態不上色）
        HIGHLIGHT_STATUS = {
            "🚨 特別關懷": "background-color: #FEF2F2; color: #991B1B; font-weight: bold",
            "⚠️ 流動性緊繃": "background-color: #FFFBEB; color: #92400E; font-weight: bold",
            "💤 資金閒置": "background-color: #EFF6FF; color: #1E40AF; font-weight: bold",
            "✅ 穩健模範": "background-color: #F0FDF4; color: #166534; font-weight: bold",
        }

        def highlight_status(val):
            return HIGHLIGHT_STATUS.get(str(val), "")

        cols_order = [
            "社號",
            "社名",
            "區域",
            "診斷狀態",
            "建議留意事項",
            "現有社員",
            "社員成長數(12M)",
            "社員成長率(12M)",
            "現有股金",
            "股金成長率(12M)",
            "貸放比",
            "儲蓄率",
            "逾放比(12M)",
            "逾放比",
            "開支比",
            "提撥率",
        ]
        df_export = data.drop(columns=["_sM", "_sS"])
        styled = (
            df_export[cols_order]
            .style.map(highlight_status, subset=["診斷狀態"])
            .format(fmt)
            .set_properties(**{"font-size": "18px", "padding": "10px"})
        )
        st.dataframe(styled, use_container_width=True, height=600)

        df_dl = df_export[cols_order].copy()
        for col, pattern in fmt.items():
            if col in df_dl.columns:
                if callable(pattern):
                    df_dl[col] = df_dl[col].apply(pattern)
                else:
                    df_dl[col] = df_dl[col].apply(
                        lambda x: pattern.format(x) if pd.notnull(x) else ""
                    )
        st.download_button(
            "📥 匯出 CSV",
            df_dl.to_csv(index=False).encode("utf-8-sig"),
            "report.csv",
            "text/csv",
        )

    # ── 趨勢追蹤 ──────────────────────────────────────────
    with tab_tr:
        render_trend_tracker(
            data,
            df_m,
            df_l,
            region_data,
            THEME,
            st.session_state["preloaded_data"],
        )
