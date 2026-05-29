import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from charts.style import apply_chart_style
from data.utils import safe_div, format_large_number

_DOWNLOAD_CONFIG = {
    "displayModeBar": True,
    "modeBarButtons": [["toImage"]],
    "displaylogo": False,
}


def render_overview_page(data: pd.DataFrame, df_m: pd.DataFrame, df_l: pd.DataFrame,
                         region_data: pd.DataFrame | None, config: dict):
    THEME = config["THEME_BG"]
    T = config["THRESHOLDS"]

    latest_date = df_m["年月"].max()
    st.caption(f"📅 資料更新至 {latest_date.year} 年 {latest_date.month} 月")

    tab_ov, tab_mx, tab_hc, tab_rp, tab_tr = st.tabs(
        ["📊 經營總覽", "🎯 風險矩陣", "🏥 個社健檢", "📋 報表匯出", "📈 趨勢追蹤"]
    )

    # ── 經營總覽 ──────────────────────────────────────────
    with tab_ov:
        c1, c2, c3, c4 = st.columns(4)
        total_mem = data["現有社員"].sum()
        total_shr = data["現有股金"].sum()
        prev_mem  = data["_sM"].sum()
        prev_shr  = data["_sS"].sum()

        avg_src   = region_data if region_data is not None else data
        avg_label = "區域平均" if region_data is not None else "全台平均"

        c1.metric("社員總數（人）",  f"{int(total_mem):,}",
                  f"{safe_div(total_mem - prev_mem, prev_mem):.2%}")
        c2.metric("股金總額",  format_large_number(total_shr),
                  f"{safe_div(total_shr - prev_shr, prev_shr):.2%}")
        c3.metric(f"{avg_label}開支比", f"{avg_src['開支比(年)'].mean():.2%}")
        c4.metric(f"{avg_label}逾放比", f"{avg_src['逾放比'].mean():.2%}")

        st.markdown("### 狀態雷達監控")

        def render_card(title, key, cls):
            names = data[data["診斷狀態"].str.contains(key)]["社名"].tolist()
            tags = " ".join(f'<span class="name-tag">{n}</span>' for n in names) or "無"
            st.markdown(
                f"<div class='stat-card'>"
                f"<div class='card-header {cls}'>{title}</div>"
                f"<div style='padding:10px;'>{tags}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1: render_card("🚨 重點輔導", "重點輔導", "hdr-red")
        with sc2: render_card("⚠️ 緊繃",    "流動性",   "hdr-orange")
        with sc3: render_card("💤 閒置",    "資金閒置", "hdr-blue")
        with sc4: render_card("✅ 穩健",    "穩健",     "hdr-green")

    # ── 風險矩陣 ──────────────────────────────────────────
    with tab_mx:
        show_labels = st.checkbox("🏷️ 在圖表上直接顯示社名", value=False)
        fig = px.scatter(
            data, x="貸放比", y="逾放比",
            color="診斷狀態", size="現有社員",
            hover_name="社名", hover_data=["建議留意事項"],
            text="社名" if show_labels else None,
            height=600,
            color_discrete_map={
                "🚨 重點輔導": "#EF4444", "⚠️ 流動性緊繃": "#F59E0B",
                "💤 資金閒置": "#3B82F6", "✅ 穩健模範":   "#10B981",
                "📊 一般狀態": "#94A3B8",
            },
        )
        trace_kw = dict(marker=dict(
            sizeref=2 * data["現有社員"].max() / (40 ** 2),
            line=dict(width=1, color="DarkSlateGrey"),
        ))
        if show_labels:
            trace_kw.update(textposition="top center", textfont=dict(size=14))
        fig.update_traces(**trace_kw)
        fig.add_hline(y=T["high_risk_ovd"],  line_dash="dot", line_color="red")
        fig.add_vline(x=T["liquidity_loan"], line_dash="dot", line_color="orange")
        apply_chart_style(fig, theme_bg=THEME)
        st.plotly_chart(fig, use_container_width=True, config=_DOWNLOAD_CONFIG)

        st.markdown("---")
        st.markdown("#### 各狀態社別一覽")
        status_order = ["🚨 重點輔導", "⚠️ 流動性緊繃", "💤 資金閒置", "✅ 穩健模範", "📊 一般狀態"]
        for _s in status_order:
            _group = data[data["診斷狀態"] == _s]["社名"].tolist()
            if _group:
                st.markdown(f"**{_s}**（{len(_group)} 社）：{'、'.join(_group)}")

    # ── 個社健檢 ──────────────────────────────────────────
    with tab_hc:
        # 預設選取第一個社別
        target = st.selectbox("請選擇儲互社", data["社名"].unique(), index=0)
        if target:
            row = data[data["社名"] == target].iloc[0]
            st.markdown(f"#### 【{target}】 狀態：`{row['診斷狀態']}`")
            if row["建議留意事項"]:
                st.markdown(
                    f'<div class="alert-box alert-error">🚩 觸發項目：{row["建議留意事項"]}</div>',
                    unsafe_allow_html=True,
                )
            KEYS = ["貸放比", "儲蓄率", "逾放比", "開支比", "社員成長率(12M)", "股金成長率(12M)"]
            avg_src   = region_data if region_data is not None else data
            avg_label = "區域平均" if region_data is not None else "全台平均"
            y_target = [row[k] if k != "開支比" else row["開支比(年)"] for k in KEYS]
            y_avg    = [avg_src[k].mean() if k != "開支比" else avg_src["開支比(年)"].mean() for k in KEYS]
            fig_bar = go.Figure([
                go.Bar(name=target,    x=KEYS, y=y_target, marker_color="#3B82F6"),
                go.Bar(name=avg_label, x=KEYS, y=y_avg,    marker_color="#CBD5E1"),
            ])
            apply_chart_style(fig_bar, title=f"指標對比 ({avg_label})", theme_bg=THEME)
            st.plotly_chart(fig_bar, use_container_width=True, config=_DOWNLOAD_CONFIG)
            cols = st.columns(4)
            for i, (k, v) in enumerate([
                ("現有社員（人）", f"{int(row['現有社員']):,}"),
                ("現有股金",      format_large_number(row['現有股金'])),
                ("逾放比（%）",   f"{row['逾放比']:.2%}"),
                ("開支比（年）",  f"{row['開支比(年)']:.2%}"),
            ]):
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
                on="年月", how="outer",
            ).sort_values("年月")
            hist_df["年度"] = hist_df["年月"].dt.year

            if len(hist_df) >= 2:
                def small_trend(metric, title, is_pct=True):
                    df_plot = hist_df[["年度", metric]].dropna()
                    if df_plot.empty:
                        return
                    fig = px.line(df_plot, x="年度", y=metric, markers=True)
                    apply_chart_style(fig, title, is_pct=is_pct, theme_bg=THEME, interactive=False)
                    fig.update_layout(height=280, margin=dict(t=40, b=20, l=5, r=5))
                    st.plotly_chart(fig, use_container_width=True, config=_DOWNLOAD_CONFIG)

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
            "現有社員": "{:,}", "社員成長數(12M)": "{:+,.0f}",
            "現有股金": "{:,.0f}", "社員成長率(12M)": "{:.2%}",
            "股金成長率(12M)": "{:.2%}", "貸放比": "{:.1%}", "儲蓄率": "{:.1%}",
            "逾放比(12M)": "{:.2%}", "逾放比": "{:.2%}",
            "開支比": "{:.2%}", "提撥率": "{:.2%}",
        }

        def highlight(row):
            style = "background-color: #FEF2F2; color: #991B1B; font-weight: bold"
            return [style if "重點輔導" in str(row["診斷狀態"]) else "" for _ in row]

        cols_order = [
            "社號", "社名", "區域", "診斷狀態", "建議留意事項",
            "現有社員", "社員成長數(12M)", "社員成長率(12M)",
            "現有股金", "股金成長率(12M)",
            "貸放比", "儲蓄率", "逾放比(12M)", "逾放比", "開支比", "提撥率",
        ]
        df_export = data.drop(columns=["_sM", "_sS"])
        styled = (
            df_export[cols_order]
            .style.apply(highlight, axis=1)
            .format(fmt)
            .set_properties(**{"font-size": "18px", "padding": "10px"})
        )
        st.dataframe(styled, use_container_width=True, height=600)

        df_dl = df_export[cols_order].copy()
        for col, pattern in fmt.items():
            if col in df_dl.columns:
                df_dl[col] = df_dl[col].apply(
                    lambda x: pattern.format(x) if pd.notnull(x) else ""
                )
        st.download_button("📥 匯出 CSV",
                           df_dl.to_csv(index=False).encode("utf-8-sig"),
                           "report.csv", "text/csv")

    # ── 趨勢追蹤 ──────────────────────────────────────────
    with tab_tr:
        if region_data is not None:
            _, raw_df_m, raw_df_l, _ = st.session_state["preloaded_data"][:4]
            reg_snos = region_data["社號"].unique()
            df_all_full = pd.merge(
                raw_df_m[raw_df_m["社號"].isin(reg_snos)],
                raw_df_l[raw_df_l["社號"].isin(reg_snos)][
                    ["年月", "社號", "逾放比", "開支比", "提撥率"]],
                on=["年月", "社號"], how="left",
            )
            avg_label = "區域平均"
        else:
            df_all_full = pd.merge(
                df_m, df_l[["年月", "社號", "逾放比", "開支比", "提撥率"]],
                on=["年月", "社號"], how="left",
            )
            avg_label = "全台平均"

        # 日期篩選器移至最上方
        all_yms = sorted(df_all_full["年月"].unique())
        all_ym_labels = [pd.Timestamp(ym).strftime("%Y-%m") for ym in all_yms]
        
        col_s, col_e = st.columns(2)
        with col_s:
            start_label = st.selectbox("📅 起始月份", all_ym_labels, index=0)
        with col_e:
            end_label = st.selectbox("📅 結束月份", all_ym_labels, index=len(all_ym_labels) - 1)
        
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
                    filtered_df_all
                    .groupby("年月")[["社員數", "貸放比", "儲蓄率", "逾放比", "開支比", "提撥率"]]
                    .mean()
                    .reset_index()
                )
                avg_df["社名"] = avg_label
                plot_dfs.append(avg_df)
            
            if plot_dfs:
                plot_df = pd.concat(plot_dfs, ignore_index=True)

                def trend(col, title, is_pct=True):
                    # 開支比僅顯示 12 月年度數據
                    curr_df = plot_df[plot_df["年月"].dt.month == 12] if col == "開支比" else plot_df
                    fig = px.line(curr_df, x="年月", y=col, color="社名", markers=True,
                                  color_discrete_map={avg_label: "#1E293B"})
                    for trace in fig.data:
                        if trace.name == avg_label:
                            trace.line.dash  = "dash"
                            trace.line.width = 3
                    apply_chart_style(fig, title, is_pct, theme_bg=THEME, interactive=True)
                    fig.update_layout(height=450)
                    st.plotly_chart(fig, use_container_width=True, config=_DOWNLOAD_CONFIG)

                trend("逾放比", "⚠️ 逾放比趨勢")
                trend("貸放比", "💰 貸放比趨勢")
                trend("社員數", "👥 社員數趨勢（人）", is_pct=False)
                trend("儲蓄率", "🏦 儲蓄率趨勢")
                trend("開支比", "📈 開支比趨勢")
                trend("提撥率", "🛡️ 提撥率趨勢")
            else:
                st.info("請選取社別或勾選顯示平均值以查看趨勢圖。")
