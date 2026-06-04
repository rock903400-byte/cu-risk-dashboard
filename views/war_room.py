import pandas as pd
import streamlit as st

from components.charts import render_ranking_tabs, render_waterfall, render_yearly_trend, render_yoy_anomalies
from components.metrics import render_kpi_cards
from data.classifier import classify_code
from data.utils import safe_div, format_large_number
from services.finance_service import get_annual_snapshot


def render_war_room_page(df_csv: pd.DataFrame, selected_unions: list[str],
                         is_admin: bool, config: dict):
    THEME = config["THEME_BG"]

    tab_bs, tab_is, tab_analysis, tab_raw = st.tabs(
        ["⚖️ 資產負債表", "📉 綜合損益表", "📈 營運分析", "📑 原始資料"]
    )

    with st.sidebar:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<span class="sidebar-label">🔍 戰情室過濾</span>', unsafe_allow_html=True)
        all_months = sorted(df_csv["年月"].unique())
        selected_month = st.selectbox("選擇年月", all_months, index=len(all_months) - 1)
        all_unions = sorted(df_csv["社名"].unique())
        selected_unions = st.multiselect("選擇查看互助社", all_unions, default=all_unions)

    filtered = df_csv[(df_csv["年月"] == selected_month) & (df_csv["社名"].isin(selected_unions))]

    st.markdown(f"### 📅 {selected_month} 財務概況快照 (Balance Sheet Snapshot)")

    total_assets = filtered[filtered["會計科目"].str.startswith("1")]["當月金額"].sum()
    total_liabs  = filtered[filtered["會計科目"].str.startswith("2")]["當月金額"].sum()
    total_equity = filtered[filtered["會計科目"].str.startswith("3")]["當月金額"].sum()

    ck1, ck2, ck3, ck4 = st.columns(4)
    ck1.metric("總資產規模", format_large_number(total_assets))
    ck2.metric("總負債規模", format_large_number(total_liabs))
    ck3.metric("淨值總額 (自有資金)", format_large_number(total_equity))
    ck4.metric("淨值佔資產比", f"{safe_div(total_equity, total_assets):.1%}")
    st.divider()

    # ── 資產負債表 ────────────────────────────────────────
    with tab_bs:
        st.subheader("📋 資產負債表 (Balance Sheet)")
        target_bs = st.selectbox("選擇互助社", selected_unions, key="bs_select", index=0 if selected_unions else None)
        if not selected_unions:
            st.info("請先選擇互助社")
        else:
            bs_df = filtered[filtered["社名"] == target_bs].copy()
            bs_df["類別"] = bs_df["會計科目"].apply(classify_code)

            col_a, col_le = st.columns(2)
            with col_a:
                st.markdown("#### 【 資產部 】")
                assets = bs_df[bs_df["類別"] == "資產"].sort_values("會計科目")[
                    ["會計科目", "會科名稱", "當月金額"]
                ]
                total_a = assets["當月金額"].sum()
                disp_a = pd.concat([assets,
                                     pd.DataFrame([{"會計科目": "", "會科名稱": "資產總計", "當月金額": total_a}])])
                st.dataframe(
                    disp_a.style.format({"當月金額": "{:,.0f}"})
                    .apply(lambda x: ["font-weight: bold; background-color: #f0f2f6"
                                       if x.name == len(disp_a) - 1 else "" for _ in x], axis=1)
                    .set_properties(**{"font-size": "18px"}),
                    use_container_width=True, hide_index=True,
                )

            with col_le:
                st.markdown("#### 【 負債與權益部 】")
                liabs  = bs_df[bs_df["類別"] == "負債"].sort_values("會計科目")[
                    ["會計科目", "會科名稱", "當月金額"]]
                equity = bs_df[bs_df["類別"] == "權益"].sort_values("會計科目")[
                    ["會計科目", "會科名稱", "當月金額"]]
                total_l, total_e = liabs["當月金額"].sum(), equity["當月金額"].sum()
                le_disp = pd.concat([
                    liabs,
                    pd.DataFrame([{"會計科目": "", "會科名稱": "負債小計",      "當月金額": total_l}]),
                    equity,
                    pd.DataFrame([{"會計科目": "", "會科名稱": "權益小計",      "當月金額": total_e}]),
                    pd.DataFrame([{"會計科目": "", "會科名稱": "負債與權益總計", "當月金額": total_l + total_e}]),
                ]).reset_index(drop=True)
                st.dataframe(
                    le_disp.style.format({"當月金額": "{:,.0f}"})
                    .apply(lambda x: ["font-weight: bold; background-color: #f0f2f6"
                                       if "計" in str(x["會科名稱"]) else "" for _ in x], axis=1)
                    .set_properties(**{"font-size": "18px"}),
                    use_container_width=True, hide_index=True,
                )
                diff = total_a - (total_l + total_e)
                if abs(diff) > 0.01:
                    st.error(f"⚠️ 報表不平衡！差額: {diff:,.2f}")

    # ── 綜合損益表 ────────────────────────────────────────
    with tab_is:
        st.subheader("📊 綜合損益表 (Income Statement)")
        target_is = st.selectbox("選擇互助社", selected_unions, key="is_select", index=0 if selected_unions else None)
        if not selected_unions:
            st.info("請先選擇互助社")
        else:
            is_df = filtered[filtered["社名"] == target_is].copy()
            is_df["類別"] = is_df["會計科目"].apply(classify_code)

            incomes  = is_df[is_df["類別"] == "收入"].sort_values("會計科目")[
                ["會計科目", "會科名稱", "當月金額"]]
            expenses = is_df[is_df["類別"] == "支出"].sort_values("會計科目")[
                ["會計科目", "會科名稱", "當月金額"]]
            rev_total  = incomes["當月金額"].sum()
            exp_total  = expenses["當月金額"].sum()
            net_profit = rev_total - exp_total

            is_disp = pd.concat([
                pd.DataFrame([{"會計科目": "", "會科名稱": "-- 營業收入 --",    "當月金額": None}]),
                incomes,
                pd.DataFrame([{"會計科目": "", "會科名稱": "營業收入合計",      "當月金額": rev_total}]),
                pd.DataFrame([{"會計科目": "", "會科名稱": "",                  "當月金額": None}]),
                pd.DataFrame([{"會計科目": "", "會科名稱": "-- 營業支出 --",    "當月金額": None}]),
                expenses,
                pd.DataFrame([{"會計科目": "", "會科名稱": "營業支出合計",      "當月金額": exp_total}]),
                pd.DataFrame([{"會計科目": "", "會科名稱": "",                  "當月金額": None}]),
                pd.DataFrame([{"會計科目": "", "會科名稱": "本期淨利（淨損）",  "當月金額": net_profit}]),
            ]).reset_index(drop=True)

            def style_is(row):
                if "合計" in str(row["會科名稱"]):
                    return ["font-weight: bold; background-color: #f0f2f6"] * len(row)
                if "淨利" in str(row["會科名稱"]):
                    bg = "#DCFCE7" if net_profit >= 0 else "#FEE2E2"
                    return [f"font-weight: bold; background-color: {bg}; border-top: 2px solid black"] * len(row)
                if "--" in str(row["會科名稱"]):
                    return ["color: #64748B; font-style: italic"] * len(row)
                return [""] * len(row)

            st.dataframe(
                is_disp.style.format({"當月金額": "{:,.0f}"}, na_rep="")
                .apply(style_is, axis=1)
                .set_properties(**{"font-size": "18px"}),
                use_container_width=True, hide_index=True,
            )

    # ── 營運分析 ──────────────────────────────────────────
    with tab_analysis:
        st.subheader("📈 年度營運分析 (Annual Analysis)")
        target_an = st.selectbox("選擇分析對象", selected_unions, key="analysis_select", index=0 if selected_unions else None)
        if not selected_unions:
            st.info("請先選擇社別")
        else:
            analysis_df = df_csv[df_csv["社名"] == target_an].copy()
            analysis_df["年度"] = analysis_df["年月"].apply(
                lambda x: x[:-2] if len(x) >= 3 else x
            )
            all_years = sorted(analysis_df["年度"].unique(), reverse=True)

            if not all_years:
                st.warning("無資料可供展示。")
            else:
                col_y1, col_y2 = st.columns([1.5, 2.5])
                with col_y1:
                    selected_year = st.selectbox("📅 選擇分析年度", all_years)
                with col_y2:
                    compare_options = ["（不比較）"] + [y for y in all_years if y != selected_year]
                    compare_choice = st.selectbox("📅 對比年度（選填）", compare_options)
                    compare_year = None if compare_choice == "（不比較）" else compare_choice

                annual_agg = get_annual_snapshot(analysis_df, selected_year)
                compare_agg = get_annual_snapshot(analysis_df, compare_year) if compare_year else None

                curr_idx  = all_years.index(selected_year)
                prev_year = all_years[curr_idx + 1] if curr_idx < len(all_years) - 1 else None
                prev_agg  = get_annual_snapshot(analysis_df, prev_year) if prev_year else None

                if not annual_agg.empty:
                    render_kpi_cards(annual_agg, prev_agg)

                st.divider()

                render_waterfall(annual_agg, selected_year, THEME)

                st.divider()

                st.markdown(f"#### 【 {selected_year} 年度會計科目變動偵測 (YoY) 與科目排名 】")
                col_left, col_right = st.columns([4, 6])

                with col_left:
                    if prev_year and prev_agg is not None and not prev_agg.empty:
                        render_yoy_anomalies(annual_agg, prev_agg, selected_year, prev_year)
                    else:
                        st.info("這是系統紀錄的第一個年度，無前期資料可供比較。")

                with col_right:
                    st.markdown("**關鍵科目金額排名（各類 Top 10）**")
                    if not annual_agg.empty:
                        render_ranking_tabs(
                            annual_agg, THEME,
                            compare_agg=compare_agg,
                            year_label=selected_year,
                            compare_label=compare_year or "",
                        )
                    else:
                        st.info("本年度無排名資料。")

                st.divider()

                if not analysis_df.empty:
                    render_yearly_trend(analysis_df, THEME)

    # ── 原始資料 ──────────────────────────────────────────
    with tab_raw:
        st.subheader("篩選後的原始數據")
        st.dataframe(
            filtered.style
            .format({"當月金額": "{:,.0f}"})
            .set_properties(**{"font-size": "16px"}),
            use_container_width=True,
        )
