import pandas as pd
import streamlit as st

from components.charts import render_ranking_tabs, render_waterfall, render_yearly_trend, render_yoy_anomalies
from components.metrics import render_kpi_cards
from data.classifier import classify_code
from data.utils import format_large_number
from services.finance_service import get_annual_snapshot
from services.diagnosis_service import calc_ratios, rate_ratio, calc_trend


def render_war_room_page(df_csv: pd.DataFrame, is_admin: bool, config: dict):
    THEME = config["THEME_BG"]

    tab_bs, tab_is, tab_overview, tab_deep, tab_diag, tab_raw = st.tabs(
        ["⚖️ 資產負債表", "📉 綜合損益表", "📈 年度概覽", "🔍 深度分析", "🏥 財務診斷", "📑 原始資料"]
    )

    union_df = df_csv.copy()
    union_df["年度"] = union_df["年月"].apply(lambda x: x[:-2] if len(x) >= 3 else x)

    with st.sidebar:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<span class="sidebar-label">🔍 財報篩選</span>', unsafe_allow_html=True)
        all_unions = sorted(union_df["社名"].unique())
        selected_union = st.selectbox("選擇社別", all_unions, index=0)

        union_data = union_df[union_df["社名"] == selected_union]
        all_years = sorted(union_data["年度"].unique(), reverse=True)
        selected_year = st.selectbox("選擇年度", all_years, index=0) if all_years else None

        year_months = sorted(union_data[union_data["年度"] == selected_year]["年月"].unique()) if selected_year else []
        selected_month = st.selectbox("選擇月份", year_months, index=len(year_months) - 1) if year_months else None

        if selected_year:
            total_months = union_data[union_data["年度"] == selected_year]["年月"].nunique()
            st.caption(f"📊 {selected_year}年資料：{total_months}/12 月")

    filtered = union_df[(union_df["年月"] == selected_month) & (union_df["社名"] == selected_union)] if selected_month else pd.DataFrame()

    # ── 資產負債表 ────────────────────────────────────────
    with tab_bs:
        st.subheader("📋 資產負債表")
        if filtered.empty:
            st.warning("請選擇月份。")
        else:
            bs_df = filtered.copy()
            bs_df["類別"] = bs_df["會計科目"].apply(classify_code)

            show_compare = st.checkbox("📊 對比上月", value=False, key="bs_compare")
            prev_month_data = pd.DataFrame()
            if show_compare and year_months:
                curr_idx = year_months.index(selected_month)
                if curr_idx > 0:
                    prev_month = year_months[curr_idx - 1]
                    prev_month_data = union_df[(union_df["年月"] == prev_month) & (union_df["社名"] == selected_union)].copy()
                    prev_month_data["類別"] = prev_month_data["會計科目"].apply(classify_code)
                else:
                    st.info("無前期月份可對比。")

            if show_compare and not prev_month_data.empty:
                def _render_bs_with_compare(category_filter, title):
                    st.markdown(f"#### 【 {title} 】")
                    curr = bs_df[bs_df["類別"] == category_filter].sort_values("會計科目")[
                        ["會計科目", "會科名稱", "當月金額"]
                    ]
                    prev = prev_month_data[prev_month_data["類別"] == category_filter].sort_values("會計科目")[
                        ["會計科目", "當月金額"]
                    ].rename(columns={"當月金額": "上月金額"})
                    merged = pd.merge(curr, prev, on="會計科目", how="left").fillna(0)
                    merged["增減"] = merged["當月金額"] - merged["上月金額"]
                    total_curr = merged["當月金額"].sum()
                    total_prev = merged["上月金額"].sum()
                    total_delta = total_curr - total_prev
                    total_row = pd.DataFrame([{
                        "會計科目": "", "會科名稱": f"{title}總計",
                        "當月金額": total_curr, "上月金額": total_prev, "增減": total_delta
                    }])
                    disp = pd.concat([merged, total_row], ignore_index=True)

                    def _style_bs_compare(row):
                        if row.name == len(disp) - 1:
                            return ["font-weight: bold; background-color: #f0f2f6"] * len(row)
                        styles = [""] * len(row)
                        if row["增減"] > 0:
                            styles[4] = "color: #10B981; font-weight: bold"
                        elif row["增減"] < 0:
                            styles[4] = "color: #EF4444; font-weight: bold"
                        return styles

                    st.dataframe(
                        disp.style.format({"當月金額": "{:,.0f}", "上月金額": "{:,.0f}", "增減": "{:+,.0f}"})
                        .apply(_style_bs_compare, axis=1)
                        .set_properties(**{"font-size": "16px"}),
                        use_container_width=True, hide_index=True,
                    )

                _render_bs_with_compare("資產", "資產部")
                _render_bs_with_compare("負債", "負債部")
                _render_bs_with_compare("權益", "權益部")
            else:
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
                        .set_properties(**{"font-size": "16px"}),
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
                        .set_properties(**{"font-size": "16px"}),
                        use_container_width=True, hide_index=True,
                    )
                    diff = total_a - (total_l + total_e)
                    if abs(diff) > 0.01:
                        st.error(f"⚠️ 報表不平衡！差額: {diff:,.2f}")

    # ── 綜合損益表 ────────────────────────────────────────
    with tab_is:
        st.subheader("📊 年度綜合損益表")
        if not selected_year:
            st.warning("無資料可供展示。")
        else:
            is_df = union_df[union_df["社名"] == selected_union].copy()
            is_annual = get_annual_snapshot(is_df, selected_year)
            is_annual = is_annual[is_annual["會計科目"].astype(str).str.match(r"^[45]")].copy()
            is_annual["類別"] = is_annual["會計科目"].apply(classify_code)

            incomes  = is_annual[is_annual["類別"] == "收入"].sort_values("會計科目")[
                ["會計科目", "會科名稱", "當月金額"]]
            expenses = is_annual[is_annual["類別"] == "支出"].sort_values("會計科目")[
                ["會計科目", "會科名稱", "當月金額"]]
            rev_total  = incomes["當月金額"].sum()
            exp_total  = expenses["當月金額"].sum()
            net_profit = rev_total - exp_total

            show_compare = st.checkbox("📊 對比去年", value=False, key="is_compare")
            prev_is_annual = pd.DataFrame()
            if show_compare:
                curr_idx = all_years.index(selected_year) if selected_year in all_years else -1
                prev_year = all_years[curr_idx + 1] if curr_idx >= 0 and curr_idx < len(all_years) - 1 else None
                if prev_year:
                    curr_months_list = sorted(is_df[is_df["年度"] == selected_year]["年月"].unique())
                    prev_months_list = sorted(is_df[is_df["年度"] == prev_year]["年月"].unique())
                    prev_is_annual = get_annual_snapshot(is_df, prev_year, same_months=curr_months_list)
                    prev_is_annual = prev_is_annual[prev_is_annual["會計科目"].astype(str).str.match(r"^[45]")].copy()
                    prev_is_annual["類別"] = prev_is_annual["會計科目"].apply(classify_code)
                    if len(curr_months_list) < len(prev_months_list):
                        st.info(f"ℹ️ {selected_year}年僅有 {len(curr_months_list)} 個月資料，已自動取{prev_year}年同期 {len(curr_months_list)} 個月進行公平對比。")
                else:
                    st.info("無前期年度可對比。")

            def _fmt(v):
                return "" if v is None or (isinstance(v, float) and pd.isna(v)) else f"{v:,.0f}"

            if show_compare and not prev_is_annual.empty:
                prev_incomes = prev_is_annual[prev_is_annual["類別"] == "收入"].sort_values("會計科目")[
                    ["會計科目", "當月金額"]].rename(columns={"當月金額": "去年金額"})
                prev_expenses = prev_is_annual[prev_is_annual["類別"] == "支出"].sort_values("會計科目")[
                    ["會計科目", "當月金額"]].rename(columns={"當月金額": "去年金額"})

                inc_merged = pd.merge(incomes, prev_incomes, on="會計科目", how="outer").fillna(0)
                inc_merged["增減"] = inc_merged["當月金額"] - inc_merged["去年金額"]
                inc_merged["增減率"] = inc_merged.apply(
                    lambda r: r["增減"] / r["去年金額"] if r["去年金額"] != 0 else None, axis=1)

                exp_merged = pd.merge(expenses, prev_expenses, on="會計科目", how="outer").fillna(0)
                exp_merged["增減"] = exp_merged["當月金額"] - exp_merged["去年金額"]
                exp_merged["增減率"] = exp_merged.apply(
                    lambda r: r["增減"] / r["去年金額"] if r["去年金額"] != 0 else None, axis=1)

                prev_rev_total = prev_incomes["去年金額"].sum()
                prev_exp_total = prev_expenses["去年金額"].sum()
                prev_net = prev_rev_total - prev_exp_total
                rev_delta = rev_total - prev_rev_total
                exp_delta = exp_total - prev_exp_total
                net_delta = net_profit - prev_net

                is_disp = pd.concat([
                    pd.DataFrame([{"會計科目": "", "會科名稱": "-- 營業收入 --", "今年金額": "", "去年金額": "", "增減": "", "增減率": ""}]),
                    inc_merged.assign(今年金額=inc_merged["當月金額"].map(_fmt),
                                      去年金額=inc_merged["去年金額"].map(_fmt),
                                      增減=inc_merged["增減"].map(_fmt),
                                      增減率=inc_merged["增減率"].map(lambda x: f"{x:+.1%}" if x is not None else "")),
                    pd.DataFrame([{"會計科目": "", "會科名稱": "營業收入合計",
                                   "今年金額": _fmt(rev_total), "去年金額": _fmt(prev_rev_total),
                                   "增減": _fmt(rev_delta), "增減率": f"{rev_delta/prev_rev_total:+.1%}" if prev_rev_total else ""}]),
                    pd.DataFrame([{"會計科目": "", "會科名稱": "", "今年金額": "", "去年金額": "", "增減": "", "增減率": ""}]),
                    pd.DataFrame([{"會計科目": "", "會科名稱": "-- 營業支出 --", "今年金額": "", "去年金額": "", "增減": "", "增減率": ""}]),
                    exp_merged.assign(今年金額=exp_merged["當月金額"].map(_fmt),
                                      去年金額=exp_merged["去年金額"].map(_fmt),
                                      增減=exp_merged["增減"].map(_fmt),
                                      增減率=exp_merged["增減率"].map(lambda x: f"{x:+.1%}" if x is not None else "")),
                    pd.DataFrame([{"會計科目": "", "會科名稱": "營業支出合計",
                                   "今年金額": _fmt(exp_total), "去年金額": _fmt(prev_exp_total),
                                   "增減": _fmt(exp_delta), "增減率": f"{exp_delta/prev_exp_total:+.1%}" if prev_exp_total else ""}]),
                    pd.DataFrame([{"會計科目": "", "會科名稱": "", "今年金額": "", "去年金額": "", "增減": "", "增減率": ""}]),
                    pd.DataFrame([{"會計科目": "", "會科名稱": "本期淨利（淨損）",
                                   "今年金額": _fmt(net_profit), "去年金額": _fmt(prev_net),
                                   "增減": _fmt(net_delta), "增減率": ""}]),
                ]).reset_index(drop=True)

                def style_is_compare(row):
                    styles = [""] * len(row)
                    if "合計" in str(row["會科名稱"]):
                        styles = ["font-weight: bold; background-color: #f0f2f6"] * len(row)
                    elif "淨利" in str(row["會科名稱"]):
                        bg = "#DCFCE7" if net_profit >= 0 else "#FEE2E2"
                        styles = [f"font-weight: bold; background-color: {bg}; border-top: 2px solid black"] * len(row)
                    elif "--" in str(row["會科名稱"]):
                        styles = ["color: #64748B; font-style: italic"] * len(row)
                    if len(row) > 4 and row["增減"] not in ("", None):
                        try:
                            delta = float(str(row["增減"]).replace(",", ""))
                            if delta > 0:
                                styles[4] = "color: #10B981; font-weight: bold"
                            elif delta < 0:
                                styles[4] = "color: #EF4444; font-weight: bold"
                        except (ValueError, TypeError):
                            pass
                    return styles

                st.dataframe(
                    is_disp[["會計科目", "會科名稱", "今年金額", "去年金額", "增減", "增減率"]].style
                    .apply(style_is_compare, axis=1)
                    .set_properties(**{"font-size": "16px"}),
                    use_container_width=True, hide_index=True,
                )
            else:
                is_disp = pd.concat([
                    pd.DataFrame([{"會計科目": "", "會科名稱": "-- 營業收入 --",    "年度累計金額": ""}]),
                    incomes.rename(columns={"當月金額": "年度累計金額"}).assign(
                        年度累計金額=lambda d: d["年度累計金額"].map(_fmt)),
                    pd.DataFrame([{"會計科目": "", "會科名稱": "營業收入合計",      "年度累計金額": _fmt(rev_total)}]),
                    pd.DataFrame([{"會計科目": "", "會科名稱": "",                  "年度累計金額": ""}]),
                    pd.DataFrame([{"會計科目": "", "會科名稱": "-- 營業支出 --",    "年度累計金額": ""}]),
                    expenses.rename(columns={"當月金額": "年度累計金額"}).assign(
                        年度累計金額=lambda d: d["年度累計金額"].map(_fmt)),
                    pd.DataFrame([{"會計科目": "", "會科名稱": "營業支出合計",      "年度累計金額": _fmt(exp_total)}]),
                    pd.DataFrame([{"會計科目": "", "會科名稱": "",                  "年度累計金額": ""}]),
                    pd.DataFrame([{"會計科目": "", "會科名稱": "本期淨利（淨損）",  "年度累計金額": _fmt(net_profit)}]),
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
                    is_disp.style
                    .apply(style_is, axis=1)
                    .set_properties(**{"font-size": "16px"}),
                    use_container_width=True, hide_index=True,
                )

    # ── 年度概覽 ──────────────────────────────────────────
    with tab_overview:
        st.subheader("📈 年度營運概覽")
        if not selected_year:
            st.warning("無資料可供展示。")
        else:
            analysis_df = union_df[union_df["社名"] == selected_union].copy()
            annual_agg = get_annual_snapshot(analysis_df, selected_year)

            curr_idx  = all_years.index(selected_year) if selected_year in all_years else -1
            prev_year = all_years[curr_idx + 1] if curr_idx >= 0 and curr_idx < len(all_years) - 1 else None
            prev_agg  = get_annual_snapshot(analysis_df, prev_year) if prev_year else None

            if not annual_agg.empty:
                render_kpi_cards(annual_agg, prev_agg)

            st.divider()

            with st.spinner("繪製瀑布圖..."):
                render_waterfall(annual_agg, selected_year, THEME)

            st.divider()

            if not analysis_df.empty:
                render_yearly_trend(analysis_df, THEME)

    # ── 深度分析 ──────────────────────────────────────────
    with tab_deep:
        st.subheader("🔍 深度分析")
        if not selected_year:
            st.warning("無資料可供展示。")
        else:
            analysis_df = union_df[union_df["社名"] == selected_union].copy()

            compare_options = ["（不比較）"] + [y for y in all_years if y != selected_year]
            compare_choice = st.selectbox("📅 對比年度（選填）", compare_options, key="deep_compare")
            compare_year = None if compare_choice == "（不比較）" else compare_choice

            annual_agg = get_annual_snapshot(analysis_df, selected_year)
            compare_agg = get_annual_snapshot(analysis_df, compare_year) if compare_year else None

            if compare_year:
                _sel_months = sorted(analysis_df[analysis_df["年度"] == selected_year]["年月"].unique())
                _cmp_months = sorted(analysis_df[analysis_df["年度"] == compare_year]["年月"].unique())
                _sel_suffixes = {m[-2:] for m in _sel_months}
                _cmp_suffixes = {m[-2:] for m in _cmp_months}
                _common_suffixes = sorted(_sel_suffixes & _cmp_suffixes)
                _common_months = [m for m in _sel_months if m[-2:] in _common_suffixes]
                if len(_common_months) < len(_sel_months) or len(_common_months) < len(_cmp_months):
                    st.info(f"ℹ️ {selected_year}年有 {len(_sel_months)} 個月、{compare_year}年有 {len(_cmp_months)} 個月資料，已自動取同期 {len(_common_months)} 個月進行公平對比。")
                    annual_agg = get_annual_snapshot(analysis_df, selected_year, same_months=_common_months)
                    compare_agg = get_annual_snapshot(analysis_df, compare_year, same_months=_common_months)

            curr_idx  = all_years.index(selected_year) if selected_year in all_years else -1
            prev_year = all_years[curr_idx + 1] if curr_idx >= 0 and curr_idx < len(all_years) - 1 else None
            curr_months_list = sorted(analysis_df[analysis_df["年度"] == selected_year]["年月"].unique())
            prev_agg  = get_annual_snapshot(analysis_df, prev_year, same_months=curr_months_list) if prev_year else None
            yoy_annual_agg = get_annual_snapshot(analysis_df, selected_year, same_months=curr_months_list) if prev_year else annual_agg

            st.markdown(f"#### 📊 年度科目變動偵測")
            if prev_year and prev_agg is not None and not prev_agg.empty:
                prev_months_list = sorted(analysis_df[analysis_df["年度"] == prev_year]["年月"].unique())
                if len(curr_months_list) < len(prev_months_list):
                    st.info(f"ℹ️ {selected_year}年僅有 {len(curr_months_list)} 個月資料，已自動取{prev_year}年同期 {len(curr_months_list)} 個月進行公平對比。")
                with st.spinner("偵測年度變動..."):
                    render_yoy_anomalies(yoy_annual_agg, prev_agg, selected_year, prev_year)
            else:
                st.info("這是系統紀錄的第一個年度，無前期資料可供比較。")

            st.divider()

            st.markdown(f"#### 🏆 關鍵科目金額排名（各類 Top 10）")
            if not annual_agg.empty:
                render_ranking_tabs(
                    annual_agg, THEME,
                    compare_agg=compare_agg,
                    year_label=selected_year,
                    compare_label=compare_year or "",
                )
            else:
                st.info("本年度無排名資料。")

    # ── 財務診斷 ──────────────────────────────────────────
    with tab_diag:
        st.subheader("🏥 財務診斷")
        if not selected_year:
            st.warning("無資料可供診斷。")
        else:
            diag_df = union_df[union_df["社名"] == selected_union].copy()
            annual_agg = get_annual_snapshot(diag_df, selected_year)

            curr_idx  = all_years.index(selected_year) if selected_year in all_years else -1
            prev_year = all_years[curr_idx + 1] if curr_idx >= 0 and curr_idx < len(all_years) - 1 else None
            curr_months_list = sorted(diag_df[diag_df["年度"] == selected_year]["年月"].unique())
            prev_agg  = get_annual_snapshot(diag_df, prev_year, same_months=curr_months_list) if prev_year else None

            if annual_agg.empty:
                st.warning("本年度無資料。")
            else:
                ratios      = calc_ratios(annual_agg)
                prev_ratios = calc_ratios(prev_agg) if prev_agg is not None and not prev_agg.empty else None

                # ── 財務結構 ──────────────────────────────
                st.markdown("#### 💰 財務結構")
                col1, col2 = st.columns(2)

                with col1:
                    dr = ratios["debt_ratio"]
                    delta_dr = f"{(dr - prev_ratios['debt_ratio']):+.1%}" if prev_ratios else None
                    st.metric("負債比（總負債／總資產）", f"{dr:.1%}", delta=delta_dr,
                              delta_color="inverse")
                    lv = rate_ratio(dr, "debt_ratio")
                    if lv == "green":
                        st.success("✅ 負債比正常，財務結構穩健。")
                    elif lv == "yellow":
                        st.warning("⚠️ 負債比偏高（80–90%），建議控制新增舉債，逐步改善資本結構。")
                    else:
                        st.error("🚨 負債比過高（> 90%），自有資金嚴重不足，建議優先降低負債。")

                with col2:
                    er = ratios["equity_ratio"]
                    delta_er = f"{(er - prev_ratios['equity_ratio']):+.1%}" if prev_ratios else None
                    st.metric("淨值比（淨值／總資產）", f"{er:.1%}", delta=delta_er)
                    lv = rate_ratio(er, "equity_ratio")
                    if lv == "green":
                        st.success("✅ 自有資金充足，資本適足性良好。")
                    elif lv == "yellow":
                        st.warning("⚠️ 淨值比偏低（10–20%），建議減少股金退還，加強留存盈餘。")
                    else:
                        st.error("🚨 淨值比嚴重不足（< 10%），資本適足性警示，建議優先增資或盈餘轉增資。")

                st.divider()

                # ── 獲利能力 ──────────────────────────────
                st.markdown("#### 📊 獲利能力")
                col3, col4 = st.columns(2)

                with col3:
                    xr = ratios["expense_ratio"]
                    delta_xr = f"{(xr - prev_ratios['expense_ratio']):+.1%}" if prev_ratios else None
                    st.metric("開支比（總支出／總收入）", f"{xr:.1%}", delta=delta_xr,
                              delta_color="inverse")
                    lv = rate_ratio(xr, "expense_ratio")
                    if lv == "green":
                        st.success("✅ 開支比正常，收支控制良好。")
                    elif lv == "yellow":
                        st.warning("⚠️ 開支比偏高（95–105%），建議適度控制費用支出。")
                    else:
                        st.error("🚨 開支比超標（> 105%），本年度入不敷出，建議全面檢視收支。")

                with col4:
                    net = ratios["net_income"]
                    prev_net = prev_ratios["net_income"] if prev_ratios else None
                    delta_net = format_large_number(net - prev_net) if prev_net is not None else None
                    st.metric("本期損益", format_large_number(net), delta=delta_net)
                    consecutive_loss = (prev_ratios is not None and net < 0
                                        and prev_ratios["net_income"] < 0)
                    if consecutive_loss:
                        st.error("🚨 連續兩年虧損，財務壓力持續，建議緊急檢視業務結構。")
                    elif net < 0:
                        st.error("🚨 本年度虧損，建議檢視主要支出項目，評估增收節支方案。")
                    else:
                        st.success("✅ 本年度盈餘，獲利能力正常。")

                st.divider()

                # ── 歷年趨勢燈號 ──────────────────────────
                st.markdown("#### 📈 歷年趨勢燈號")
                with st.spinner("計算歷年趨勢..."):
                    trend_df = calc_trend(diag_df, all_years)
                if trend_df.empty:
                    st.info("歷史資料不足，無法顯示趨勢。")
                else:
                    def _cell_color(val, key):
                        lv = rate_ratio(val, key)
                        if lv == "green":  return "background-color: #DCFCE7; color: #166534"
                        if lv == "yellow": return "background-color: #FEF9C3; color: #854D0E"
                        return "background-color: #FEE2E2; color: #991B1B"

                    def _net_color(val):
                        return "color: #166534" if val >= 0 else "color: #991B1B; font-weight: bold"

                    st.dataframe(
                        trend_df.style
                        .map(lambda v: _cell_color(v, "expense_ratio"), subset=["開支比"])
                        .map(lambda v: _cell_color(v, "avg_rate"),      subset=["加權平均利率"])
                        .map(_net_color,                                subset=["損益"])
                        .format({
                            "開支比": "{:.1%}",
                            "加權平均利率": "{:.2%}",
                            "損益":   lambda x: format_large_number(x),
                        })
                        .set_properties(**{"font-size": "16px", "text-align": "center"})
                        .set_properties(**{"text-align": "left"}, subset=["年度"]),
                        use_container_width=True,
                        hide_index=True,
                    )
                    loss_years = trend_df[trend_df["開支比"] > 1.0]["年度"].tolist()
                    if len(loss_years) >= 2:
                        st.error(f"⚠️ 歷年中有 {len(loss_years)} 個年度開支比超過 100%（{', '.join(loss_years)}），請持續關注收支趨勢。")

    # ── 原始資料 ──────────────────────────────────────────
    with tab_raw:
        st.subheader("篩選後的原始數據")
        if filtered.empty:
            st.warning("請選擇月份。")
        else:
            st.dataframe(
                filtered.style
                .format({"當月金額": "{:,.0f}"})
                .set_properties(**{"font-size": "16px"}),
                use_container_width=True,
            )
