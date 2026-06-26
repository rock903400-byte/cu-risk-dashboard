import html

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from charts.style import apply_chart_style
from common.utils import safe_div, format_large_number

_DOWNLOAD_CONFIG = {
    "displayModeBar": True,
    "modeBarButtons": [["toImage"]],
    "displaylogo": False,
    "toImageButtonOptions": {"format": "png", "scale": 3},
    "responsive": True,
}


from typing import Optional


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

        if not is_individual:
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

    # ── 風險矩陣 ──────────────────────────────────────────
    with tab_mx:
        show_labels = st.checkbox("🏷️ 在圖表上直接顯示社名", value=False)
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
        fig.add_shape(
            x0=x_th, x1=x_max, y0=0, y1=y_th, fillcolor="#F59E0B", **quadrant_kw
        )
        fig.add_shape(x0=0, x1=x_th, y0=0, y1=y_th, fillcolor="#3B82F6", **quadrant_kw)
        fig.add_shape(
            x0=0, x1=x_th, y0=y_th, y1=y_max, fillcolor="#94A3B8", **quadrant_kw
        )

        apply_chart_style(fig, theme_bg=THEME)
        fig.update_xaxes(tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True, config=_DOWNLOAD_CONFIG)

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

    # ── 個社健檢 ──────────────────────────────────────────
    with tab_hc:
        # 預設選取第一個社別
        target = st.selectbox("請選擇儲互社", data["社名"].unique(), index=0)
        if target:
            row = data[data["社名"] == target].iloc[0]
            st.markdown(
                f"#### 【{html.escape(str(target))}】 狀態：`{html.escape(str(row['診斷狀態']))}`"
            )
            if row["建議留意事項"]:
                st.markdown(
                    f'<div class="alert-box alert-error">🚩 觸發項目：{html.escape(str(row["建議留意事項"]))}</div>',
                    unsafe_allow_html=True,
                )
            KEYS = [
                "貸放比",
                "儲蓄率",
                "逾放比",
                "開支比",
                "社員成長率(12M)",
                "股金成長率(12M)",
            ]
            avg_src = region_data if region_data is not None else data
            avg_label = "區域平均" if region_data is not None else "全台平均"
            y_target = [row[k] if k != "開支比" else row["開支比(年)"] for k in KEYS]
            y_avg = [
                avg_src[k].mean() if k != "開支比" else avg_src["開支比(年)"].mean()
                for k in KEYS
            ]
            fig_bar = go.Figure(
                [
                    go.Bar(name=target, x=KEYS, y=y_target, marker_color="#3B82F6"),
                    go.Bar(name=avg_label, x=KEYS, y=y_avg, marker_color="#CBD5E1"),
                ]
            )
            apply_chart_style(
                fig_bar, title=f"指標對比 ({avg_label})", is_pct=False, theme_bg=THEME
            )
            st.plotly_chart(fig_bar, use_container_width=True, config=_DOWNLOAD_CONFIG)
            cols = st.columns(4)
            for i, (k, v) in enumerate(
                [
                    ("現有社員（人）", f"{int(row['現有社員']):,}"),
                    ("現有股金", format_large_number(row["現有股金"])),
                    ("逾放比（%）", f"{row['逾放比']:.2%}"),
                    ("開支比（年）", f"{row['開支比(年)']:.2%}"),
                ]
            ):
                cols[i].metric(k, v)

            st.markdown("---")
            st.markdown("#### 近年指標趨勢（年底基準）")

            union_sno = row["社號"]
            m_hist = df_m[df_m["社號"] == union_sno].sort_values("年月")
            l_hist = df_l[df_l["社號"] == union_sno].sort_values("年月")

            m_yr = m_hist[m_hist["年月"].dt.month == 12].copy()
            l_yr = l_hist[l_hist["年月"].dt.month == 12].copy()
            hist_df = pd.merge(
                m_yr[["年月", "社員數", "貸放比", "儲蓄率"]],
                l_yr[["年月", "逾放比", "開支比", "提撥率"]],
                on="年月",
                how="outer",
            ).sort_values("年月")
            hist_df["年度"] = hist_df["年月"].dt.year

            if len(hist_df) >= 2:

                def small_trend(metric, title, is_pct=True):
                    df_plot = hist_df[["年度", metric]].dropna()
                    if df_plot.empty:
                        return
                    fig = px.line(df_plot, x="年度", y=metric, markers=True)
                    apply_chart_style(
                        fig, title, is_pct=is_pct, theme_bg=THEME, interactive=False
                    )
                    fig.update_layout(height=280, margin=dict(t=40, b=20, l=5, r=5))
                    st.plotly_chart(
                        fig, use_container_width=True, config=_DOWNLOAD_CONFIG
                    )

                col_a, col_b = st.columns(2)
                with col_a:
                    small_trend("開支比", "📈 開支比（年度）")
                    small_trend("逾放比", "⚠️ 逾放比")
                with col_b:
                    small_trend("貸放比", "💰 貸放比")
                    small_trend("社員數", "👥 社員數（人）", is_pct=False)
            else:
                st.info("歷史資料不足，無法繪製趨勢圖。")

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
        if region_data is not None:
            _, raw_df_m, raw_df_l, _ = st.session_state["preloaded_data"][:4]
            reg_snos = region_data["社號"].unique()
            df_all_full = pd.merge(
                raw_df_m[raw_df_m["社號"].isin(reg_snos)],
                raw_df_l[raw_df_l["社號"].isin(reg_snos)][
                    ["年月", "社號", "逾放比", "開支比", "提撥率"]
                ],
                on=["年月", "社號"],
                how="left",
            )
            avg_label = "區域平均"
        else:
            df_all_full = pd.merge(
                df_m,
                df_l[["年月", "社號", "逾放比", "開支比", "提撥率"]],
                on=["年月", "社號"],
                how="left",
            )
            avg_label = "全台平均"

        # 日期篩選器移至最上方
        all_yms = sorted(df_all_full["年月"].unique())
        all_ym_labels = [pd.Timestamp(ym).strftime("%Y-%m") for ym in all_yms]

        if not all_ym_labels:
            st.warning("尚無可顯示的月份資料。")
            return
        st.caption("💡 預設顯示近 36 個月；可自行調整起訖")
        default_start_idx = max(0, len(all_ym_labels) - 36)
        col_s, col_e = st.columns(2)
        with col_s:
            start_label = st.selectbox(
                "📅 起始月份", all_ym_labels, index=default_start_idx
            )
        with col_e:
            end_label = st.selectbox(
                "📅 結束月份", all_ym_labels, index=len(all_ym_labels) - 1
            )

        filtered_df_all = df_all_full[
            df_all_full["年月"].dt.strftime("%Y-%m").between(start_label, end_label)
        ]

        col1, col2 = st.columns([3, 1])
        with col1:
            # 預設選取第一個社別進行比較
            all_union_names = data["社名"].unique()
            default_sel = [all_union_names[0]] if len(all_union_names) > 0 else []
            sel = st.multiselect("加入比較社別", all_union_names, default=default_sel)

        with col2:
            st.write("")
            show_avg = st.checkbox(f"📈 顯示{avg_label}", value=True)

        if sel or show_avg:
            plot_dfs = []
            if sel:
                # 從 filtered_df_all 中選取特定社
                sel_df = filtered_df_all[filtered_df_all["社名"].isin(sel)]
                plot_dfs.append(sel_df)
            if show_avg:
                avg_df = (
                    filtered_df_all.groupby("年月")[
                        ["社員數", "貸放比", "儲蓄率", "逾放比", "開支比", "提撥率"]
                    ]
                    .mean()
                    .reset_index()
                )
                avg_df["社名"] = avg_label
                plot_dfs.append(avg_df)

            if plot_dfs:
                plot_df = pd.concat(plot_dfs, ignore_index=True)

                def trend(col, title, is_pct=True):
                    # 開支比僅顯示 12 月年度數據
                    curr_df = (
                        plot_df[plot_df["年月"].dt.month == 12]
                        if col == "開支比"
                        else plot_df
                    )
                    if col == "提撥率":
                        curr_df = curr_df.copy()
                        curr_df.loc[curr_df["提撥率"] == -1.0, "提撥率"] = None

                    fig = px.line(
                        curr_df,
                        x="年月",
                        y=col,
                        color="社名",
                        markers=True,
                        color_discrete_map={avg_label: "#1E293B"},
                    )
                    for trace in fig.data:
                        if trace.name == avg_label:
                            trace.line.dash = "dash"
                            trace.line.width = 3
                    apply_chart_style(
                        fig, title, is_pct, theme_bg=THEME, interactive=False
                    )
                    fig.update_layout(height=450)
                    st.plotly_chart(
                        fig, use_container_width=True, config=_DOWNLOAD_CONFIG
                    )

                trend("逾放比", "⚠️ 逾放比趨勢")
                trend("貸放比", "💰 貸放比趨勢")
                trend("社員數", "👥 社員數趨勢（人）", is_pct=False)
                trend("儲蓄率", "🏦 儲蓄率趨勢")
                trend("開支比", "📈 開支比趨勢")
                trend("提撥率", "🛡️ 提撥率趨勢")
            else:
                st.info("請選取社別或勾選顯示平均值以查看趨勢圖。")
