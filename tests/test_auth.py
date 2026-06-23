import pytest
import streamlit as st
from unittest.mock import patch, MagicMock
from services.auth import handle_login


@pytest.fixture(autouse=True)
def reset_session_state():
    for k in list(st.session_state.keys()):
        del st.session_state[k]


def _init_state():
    st.session_state["login_attempts"] = 0
    st.session_state["locked"] = False
    st.session_state["logged_in"] = False


def _mock_secrets(admin_pw: str = ""):
    return patch(
        "services.auth.safe_secrets",
        return_value=MagicMock(get=MagicMock(return_value=admin_pw)),
    )


class TestHandleLogin:

    def test_viewer_login_success(self):
        st.session_state["pwd_input"] = "abc"
        st.session_state["preloaded_passwords"] = {
            "abc": {"name": "測試社", "region": "北區"}
        }
        handle_login(5)
        assert st.session_state["logged_in"] is True
        assert st.session_state["role"] == "viewer"
        assert st.session_state["assigned_union"] == "測試社"
        assert st.session_state["assigned_region"] == "北區"

    def test_admin_login_success(self):
        st.session_state["pwd_input"] = "admin123"
        st.session_state["preloaded_passwords"] = {}
        with _mock_secrets("admin123"):
            handle_login(5)
        assert st.session_state["logged_in"] is True
        assert st.session_state["role"] == "admin"
        assert st.session_state["assigned_region"] is None

    def test_viewer_takes_priority_over_admin(self):
        """密碼同時存在於 pws 和 admin_pw 時，應為 viewer 而非 admin"""
        st.session_state["pwd_input"] = "shared"
        st.session_state["preloaded_passwords"] = {
            "shared": {"name": "測試社", "region": "北區"}
        }
        with _mock_secrets("shared"):
            handle_login(5)
        assert st.session_state["role"] == "viewer"
        assert st.session_state["assigned_union"] == "測試社"

    def test_wrong_password_increments_attempts(self):
        _init_state()
        st.session_state["pwd_input"] = "wrong"
        st.session_state["preloaded_passwords"] = {}
        with _mock_secrets("admin"):
            handle_login(5)
        assert st.session_state["logged_in"] is False
        assert st.session_state["login_attempts"] == 1

    def test_max_attempts_locks(self):
        _init_state()
        st.session_state["pwd_input"] = "wrong"
        st.session_state["preloaded_passwords"] = {}
        with _mock_secrets("admin"):
            for _ in range(5):
                handle_login(5)
        assert st.session_state["locked"] is True

    def test_no_admin_password_blocks_admin(self):
        _init_state()
        st.session_state["pwd_input"] = ""
        st.session_state["preloaded_passwords"] = {}
        with _mock_secrets(""):
            handle_login(5)
        assert st.session_state["logged_in"] is False

    def test_empty_input_does_not_match(self):
        _init_state()
        st.session_state["pwd_input"] = ""
        st.session_state["preloaded_passwords"] = {}
        with _mock_secrets("admin"):
            handle_login(5)
        assert st.session_state["logged_in"] is False
