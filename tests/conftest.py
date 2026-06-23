import pytest
import streamlit as st


@pytest.fixture(autouse=True)
def reset_st_cache():
    """每次測試後清除 st.cache_data，避免跨測試快取干擾"""
    yield
    st.cache_data.clear()
