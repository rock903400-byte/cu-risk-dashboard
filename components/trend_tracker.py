from typing import Optional
import pandas as pd
import plotly.express as px
import streamlit as st

from charts.style import apply_chart_style, DOWNLOAD_CONFIG


def render_trend_tracker(
    data: pd.DataFrame,
    df_m: pd.DataFrame,
    df_l: pd.DataFrame,
    region_data: Optional[pd.DataFrame],
    theme_bg: str,
    preloaded_data: tuple,
) -> None:
    """趨勢追蹤：日期篩選 + 社別比較 + 6 張折線圖"""
    if region_data is not None:
        raw_df_m = preloaded_data[1]
        raw_df_l = preloaded_data[2]
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
                    fig, title, is_pct, theme_bg=theme_bg, interactive=False
                )
                fig.update_layout(height=450)
                st.plotly_chart(fig, use_container_width=True, config=DOWNLOAD_CONFIG)

            trend("逾放比", "⚠️ 逾放比趨勢")
            trend("貸放比", "💰 貸放比趨勢")
            trend("社員數", "👥 社員數趨勢（人）", is_pct=False)
            trend("儲蓄率", "🏦 儲蓄率趨勢")
            trend("開支比", "📈 開支比趨勢")
            trend("提撥率", "🛡️ 提撥率趨勢")
        else:
            st.info("請選取社別或勾選顯示平均值以查看趨勢圖。")
