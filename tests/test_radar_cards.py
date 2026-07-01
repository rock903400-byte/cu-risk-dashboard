import sys
from pathlib import Path
from streamlit.testing.v1 import AppTest
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.test_xss_regression import make_synth_data, _APP_PATH


def test_individual_mode_hides_radar_cards():
    """個社模式進入經營總覽不應渲染雷達卡（語意：雷達卡為「全台/區域分布」用）"""
    data, df_m, df_l = make_synth_data()
    at = AppTest.from_file(_APP_PATH, default_timeout=30)
    at.session_state["logged_in"] = True
    at.session_state["role"] = "viewer"
    at.session_state["assigned_region"] = "北區"
    at.session_state["assigned_union"] = "測試社"
    at.session_state["preloaded_data"] = (data, df_m, df_l, b"", {"測試社": "北區"})
    at.session_state["preloaded_csv"] = None
    at.run()
    assert not at.exception, f"AppTest exception: {[e.value for e in at.exception]}"
    all_text = "".join(m.value for m in at.markdown)
    assert (
        "狀態雷達監控" not in all_text
    ), f"個社模式不應渲染雷達卡,實際 markdown 含: '狀態雷達監控'"


def test_admin_mode_shows_radar_cards():
    """管理員全台模式仍應渲染雷達卡（與個社模式對照）"""
    data, df_m, df_l = make_synth_data()
    at = AppTest.from_file(_APP_PATH, default_timeout=30)
    at.session_state["logged_in"] = True
    at.session_state["role"] = "admin"
    at.session_state["assigned_region"] = None
    at.session_state["assigned_union"] = None
    at.session_state["is_district_office"] = False
    at.session_state["preloaded_data"] = (data, df_m, df_l, b"", {"測試社": "北區"})
    at.session_state["preloaded_csv"] = None
    at.run()
    assert not at.exception, f"AppTest exception: {[e.value for e in at.exception]}"
    all_text = "".join(m.value for m in at.markdown)
    assert (
        "狀態雷達監控" in all_text
    ), f"管理員全台模式應渲染雷達卡,實際 markdown 不含 '狀態雷達監控'"
