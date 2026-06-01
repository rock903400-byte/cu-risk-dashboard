import logging
import streamlit as st
from supabase import create_client, Client

from config import safe_secrets

logger = logging.getLogger(__name__)


@st.cache_resource
def init_supabase() -> Client | None:
    try:
        _secrets = safe_secrets()
        if "supabase" in _secrets:
            return create_client(_secrets["supabase"]["url"], _secrets["supabase"]["key"])
    except Exception as e:
        logger.warning(f"Supabase 初始化失敗: {e}")
    return None


@st.cache_data(show_spinner="📥 正在同步數據...")
def download_file_from_storage(_supabase: Client, bucket: str, fname: str) -> bytes:
    if not _supabase:
        raise ValueError("雲端服務未設定，無法下載檔案。")
    return _supabase.storage.from_(bucket).download(fname)
