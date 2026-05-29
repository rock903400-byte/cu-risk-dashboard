import logging
import streamlit as st
from supabase import create_client, Client

logger = logging.getLogger(__name__)


@st.cache_resource
def init_supabase() -> Client | None:
    try:
        if "supabase" in st.secrets:
            return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception as e:
        logger.warning(f"Supabase 初始化失敗: {e}")
    return None


@st.cache_data(show_spinner="📥 正在同步數據...")
def download_file_from_storage(_supabase: Client, bucket: str, fname: str) -> bytes:
    if not _supabase:
        raise ValueError("雲端服務未設定，無法下載檔案。")
    return _supabase.storage.from_(bucket).download(fname)
