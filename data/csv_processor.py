import io
import pandas as pd
import streamlit as st


@st.cache_data(show_spinner="📑 正在解析 CSV 明細...")
def process_csv_final(file_bytes: bytes) -> pd.DataFrame:
    try:
        df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8-sig")
        df = df.dropna(subset=["年月"])
        df["年月"] = df["年月"].astype(int).astype(str)
        df["當月金額"] = pd.to_numeric(df["當月金額"], errors="coerce").fillna(0)
        df["會計科目"] = (
            pd.to_numeric(df["會計科目"], errors="coerce")
            .fillna(0)
            .astype(int)
            .astype(str)
        )
        if "會科名稱" in df.columns:
            df["會科名稱"] = df["會科名稱"].fillna("(未分類)")
            df["會科名稱"] = df["會科名稱"].replace({0: "(未分類)", "0": "(未分類)", "": "(未分類)"})
        return df
    except Exception as e:
        raise ValueError(f"CSV 解析失敗: {e}")
