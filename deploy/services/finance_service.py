import pandas as pd


def get_annual_snapshot(df: pd.DataFrame, year_str: str) -> pd.DataFrame:
    """取得指定年度的年化累計資料（資產負債取年底，損益取全年累計）"""
    y_df = df[df["年度"] == year_str].copy()
    if y_df.empty:
        return pd.DataFrame()
    latest_m = y_df["年月"].max()
    bs = y_df[y_df["會計科目"].str.match(r"^[123]") & (y_df["年月"] == latest_m)]
    pl = y_df[y_df["會計科目"].str.match(r"^[45]")]
    pl_sum = pl.groupby(["會計科目", "會科名稱"]).agg({"當月金額": "sum"}).reset_index()
    return pd.concat([bs[["會計科目", "會科名稱", "當月金額"]], pl_sum])


def calc_yoy_pct(current: float, previous: float) -> float | None:
    """計算 YoY 變動率；分母為 0 時回傳 None"""
    if previous == 0:
        return None
    return (current - previous) / abs(previous)


def prepare_waterfall_data(annual_agg: pd.DataFrame) -> dict:
    """
    準備瀑布圖所需資料。
    回傳 dict 含 labels, values, measures, net。
    net 採 Bug B 修復版：values[0] + sum(relative values)。
    """
    biz = annual_agg[annual_agg["會計科目"].str.match(r"^53")].sort_values("當月金額", ascending=False)
    top5_codes = biz.head(5)["會計科目"].tolist()
    top5_map   = dict(zip(biz.head(5)["會計科目"], biz.head(5)["會科名稱"]))

    def _group(code: str) -> str:
        c = str(code)
        if c.startswith("4"):  return "1.總收入"
        if c.startswith("51"): return "2.利息支出"
        if c.startswith("52"): return "3.用人費用"
        if c in top5_codes:    return f"4.{top5_map[c]}"
        if c.startswith("53"): return "5.其他業務費"
        if c.startswith("54"): return "6.管理費用"
        if c.startswith("55"): return "7.呆帳提列"
        if c.startswith("5"):  return "8.其他支出"
        return "其他"

    agg = annual_agg.copy()
    agg["WGroup"] = agg["會計科目"].apply(_group)
    w_data = agg.groupby("WGroup")["當月金額"].sum().sort_index()

    labels, values, measures = [], [], []
    labels.append("總收入")
    values.append(w_data.get("1.總收入", 0))
    measures.append("absolute")

    for g_name in w_data.index:
        if g_name.startswith(("2", "3", "4.", "5.", "6", "7", "8")):
            clean = g_name.split(".", 1)[1] if "." in g_name else g_name
            labels.append(clean)
            values.append(-w_data[g_name])
            measures.append("relative")

    labels.append("年度損益")
    values.append(0)
    measures.append("total")

    net = values[0] + sum(v for v, m in zip(values[1:], measures[1:]) if m == "relative")
    return {"labels": labels, "values": values, "measures": measures, "net": net}


def detect_yoy_anomalies(
    annual_agg: pd.DataFrame,
    prev_agg: pd.DataFrame,
    threshold_amount: float = 5000,
    threshold_pct: float = 5,
) -> pd.DataFrame:
    """
    找出 YoY 異常科目（同時滿足：|變動金額| > threshold_amount 且 |變動率| > threshold_pct%）。
    回傳排序後的 DataFrame（最多 10 筆），不含任何 st.* 呼叫。
    """
    ann = annual_agg.groupby("會計科目", as_index=False).agg({"會科名稱": "first", "當月金額": "sum"})
    prv = prev_agg.groupby("會計科目", as_index=False).agg({"當月金額": "sum"})

    comp = pd.merge(
        ann[["會計科目", "會科名稱", "當月金額"]],
        prv[["會計科目", "當月金額"]],
        on="會計科目", how="left", suffixes=("_今", "_前"),
    ).fillna(0)
    comp["變動金額"] = comp["當月金額_今"] - comp["當月金額_前"]
    comp["變動率 (%)"] = comp["變動金額"] / comp["當月金額_前"].replace(0, 1) * 100

    return (
        comp[
            (comp["變動金額"].abs() > threshold_amount) &
            (comp["變動率 (%)"].abs() > threshold_pct)
        ]
        .sort_values("變動金額", key=abs, ascending=False)
        .head(10)
        .reset_index(drop=True)
    )
