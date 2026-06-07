"""
全域配置與常數
"""
import streamlit as st
from pydantic import BaseModel, field_validator


class ThresholdsConfig(BaseModel):
    high_risk_ovd:          float
    liquidity_loan:         float
    idle_loan:              float
    stable_loan_min:        float
    stable_loan_max:        float
    ovd_safe_line:          float
    high_risk_income_ratio: float
    high_risk_loan_ratio:   float
    high_risk_ovd_ratio:    float

    @field_validator(
        "high_risk_ovd", "liquidity_loan", "idle_loan",
        "stable_loan_min", "stable_loan_max", "ovd_safe_line",
        "high_risk_income_ratio", "high_risk_loan_ratio", "high_risk_ovd_ratio",
    )
    @classmethod
    def must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"門檻值必須 > 0，收到: {v}")
        return v


ACCOUNT_CODES = {
    "shares": "3101",
    "loans":  "1311",
    "profit": "3319",
}

def safe_secrets():
    """Return st.secrets as a dict-like, or empty dict if no secrets file."""
    try:
        return st.secrets
    except Exception:
        return {}


def get_config():
    _secrets = safe_secrets()
    _thr = _secrets.get("thresholds", {})
    _thr_defaults = {
        "high_risk_ovd": 0.1, "liquidity_loan": 0.9, "idle_loan": 0.3,
        "stable_loan_min": 0.4, "stable_loan_max": 0.8, "ovd_safe_line": 0.02,
        "high_risk_income_ratio": 1.0, "high_risk_loan_ratio": 0.1, "high_risk_ovd_ratio": 0.5,
    }
    raw = {
        "BUCKET_NAME":  _secrets.get("BUCKET_NAME", "excel-reports"),
        "APP_BASE_URL": "https://cu-analysis-v1-vizgphhwjwmfkvrrktdjte.streamlit.app",
        "MAX_ATTEMPTS": 5,
        "THEME_BG":     "#F0F4F8",
        "SHEETS": {
            "MAIN":   "社務及資金運用情形",
            "LOAN":   "放款及逾期放款",
            "REGION": "區域分類表",
        },
        "THRESHOLDS": {k: _thr.get(k, d) for k, d in _thr_defaults.items()},
    }
    ThresholdsConfig(**raw["THRESHOLDS"])  # 型別與正數校驗
    return raw
APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {{
    font-family: 'Noto Sans TC', sans-serif !important;
    background-color: {theme_bg} !important;
    color: #1A202C !important;
    font-size: 18px !important;
}}
[data-testid="stMainBlockContainer"] {{
    max-width: 100% !important;
    padding-top: 4rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    padding-bottom: 1.5rem !important;
}}
.responsive-h1 {{ font-size: 2.5rem; font-weight: 700; margin-bottom: 2rem !important; color: #1E293B; }}
.responsive-h2 {{ font-size: 2rem;   font-weight: 700; margin-bottom: 1.5rem !important; color: #1E293B; }}
.stButton > button {{
    min-height: 52px !important; font-size: 18px !important;
    border-radius: 12px !important; font-weight: 600 !important;
}}
.stTextInput input {{
    min-height: 52px !important; font-size: 18px !important; border-radius: 12px !important;
}}
[data-baseweb="select"] {{ min-height: 52px !important; font-size: 18px !important; }}
.stTabs [data-baseweb="tab"] {{
    font-size: 18px !important; font-weight: 600 !important; padding: 10px 20px !important;
}}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] > div {{ font-size: 2.2rem !important; font-weight: 700 !important; word-break: break-all !important; overflow-wrap: anywhere !important; white-space: normal !important; line-height: 1.2 !important; text-overflow: clip !important; overflow: visible !important; }}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] > div {{ font-size: 1.1rem !important; font-weight: 600 !important; word-break: break-word !important; white-space: normal !important; text-overflow: clip !important; overflow: visible !important; }}
[data-testid="metric-container"] {{ overflow: visible !important; }}
[data-testid="stDataFrame"] {{ font-size: 18px !important; }}
[data-testid="stDataFrame"] td {{ font-size: 18px !important; padding: 10px 8px !important; }}
[data-testid="stDataFrame"] th {{ font-size: 18px !important; padding: 10px 8px !important; }}
@media (max-width: 640px) {{
    html, body, [data-testid="stAppViewContainer"] {{ font-size: 18px !important; }}
    [data-testid="stMainBlockContainer"] {{
        padding-left: 1rem !important; padding-right: 1rem !important; padding-top: 3.5rem !important;
    }}
    .stat-card {{ min-height: auto !important; }}
    .responsive-h1 {{ font-size: 2rem !important; }}
    .responsive-h2 {{ font-size: 1.6rem !important; }}
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] > div {{ font-size: 2rem !important; word-break: break-all !important; white-space: normal !important; text-overflow: clip !important; overflow: visible !important; }}
    .stButton > button {{ min-height: 56px !important; font-size: 18px !important; }}
    [data-baseweb="select"] {{ min-height: 56px !important; font-size: 18px !important; }}
    .stTabs [data-baseweb="tab"] {{ font-size: 16px !important; padding: 12px 16px !important; }}
    .card-criteria {{ font-size: 1.1rem !important; padding: 10px 14px !important; }}
    .reason-text {{ font-size: 1.1rem !important; }}
    .name-tag {{ font-size: 1.1rem !important; padding: 6px 14px !important; }}
    [data-testid="stDataFrame"] {{ font-size: 18px !important; }}
    [data-testid="stCheckboxContainer"] {{ min-height: 56px !important; }}
    [data-testid="stExpander"] summary {{ min-height: 56px !important; padding: 14px 16px !important; }}
    .stDownloadButton > button {{ min-height: 56px !important; }}
}}
[data-testid="stSidebar"] {{ background-color: #1E293B !important; min-width: 280px !important; }}
[data-testid="stSidebar"] * {{ color: #E2E8F0 !important; }}
[data-testid="stSidebar"] hr {{ border-color: #334155 !important; margin: 1.5rem 0 !important; }}
[data-testid="stSidebar"] .stButton > button {{
    background: #334155; color: #E2E8F0 !important; border: 1px solid #475569;
    border-radius: 10px; padding: 0.5rem 1rem; font-weight: 600;
    width: 100%; min-height: 52px !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: #475569; border-color: #64748B; transform: translateY(-1px);
}}
[data-testid="stSidebar"] [data-baseweb="select"] {{ min-height: 52px !important; font-size: 18px !important; }}
[data-testid="stSidebar"] .stCheckboxContainer {{ min-height: 52px !important; }}
[data-testid="stSidebar"] .stCheckboxContainer label {{ font-size: 18px !important; }}
.stCodeBlock {{ border-radius: 10px !important; background: #0F172A !important; border: 1px solid #334155 !important; }}
[data-testid="stVerticalBlockBorderWrapper"] {{
    border-radius: 20px !important; background: white !important;
    padding: 1.5rem !important; box-shadow: 0 10px 25px rgba(0,0,0,0.05) !important;
}}
.stat-card {{
    background: white; border-radius: 14px; border: 1px solid #E2E8F0;
    margin-bottom: 1rem; min-height: 200px; display: flex; flex-direction: column; overflow: hidden;
}}
.card-header {{ padding: 12px; color: #FFF !important; font-weight: 700; text-align: center; font-size: 1.2rem; }}
.hdr-red    {{ background: linear-gradient(135deg, #EF4444, #991B1B); }}
.hdr-orange {{ background: linear-gradient(135deg, #F59E0B, #92400E); }}
.hdr-blue   {{ background: linear-gradient(135deg, #3B82F6, #1E40AF); }}
.hdr-green  {{ background: linear-gradient(135deg, #10B981, #065F46); }}
.name-tag {{
    display: inline-block; background: #F1F5F9; color: #1A202C !important;
    padding: 5px 12px; border-radius: 10px; margin: 4px;
    font-size: 1.1rem; border: 1px solid #CBD5E1; font-weight: 600;
}}
.card-criteria {{
    font-size: 1.1rem; color: #475569; background: #F8FAFC;
    border-bottom: 1px solid #E2E8F0; padding: 8px 14px; line-height: 1.6;
}}
.union-item {{ margin: 4px 0; }}
.reason-text {{
    font-size: 1.1rem; color: #92400E; padding: 2px 4px 4px 14px;
}}
.badge-admin  {{ background: #DCFCE7; color: #166534 !important; border-radius: 8px; padding: 10px; text-align: center; font-size: 1.1rem; font-weight: 700; border: 1px solid #86EFAC; margin-bottom: 1rem; }}
.badge-viewer {{ background: #FEF3C7; color: #92400E !important; border-radius: 8px; padding: 10px; text-align: center; font-size: 1.1rem; font-weight: 700; border: 1px solid #FCD34D; margin-bottom: 1rem; }}
.sidebar-label {{ font-size: 1.1rem; font-weight: 600; color: #94A3B8; margin-bottom: 0.5rem; display: block; }}
.alert-box   {{ padding: 15px; border-radius: 10px; margin-bottom: 1rem; font-size: 1.1rem; font-weight: 600; border: 1px solid transparent; }}
.alert-error   {{ background-color: #FEF2F2; color: #991B1B; border-color: #FEE2E2; }}
.alert-warning {{ background-color: #FFFBEB; color: #92400E; border-color: #FEF3C7; }}
[data-testid="stCaption"], .stCaption {{ font-size: 1rem !important; color: #475569 !important; }}
.stAlert {{ font-size: 1.1rem !important; }}
.stAlert p {{ font-size: 1.1rem !important; }}
[data-testid="stCheckboxContainer"] {{ min-height: 48px !important; }}
[data-testid="stCheckboxContainer"] label {{ font-size: 1.1rem !important; }}
[data-testid="stExpander"] {{ min-height: 48px !important; }}
[data-testid="stExpander"] summary {{ font-size: 1.1rem !important; padding: 12px 16px !important; min-height: 48px !important; }}
[data-baseweb="tag"] {{ font-size: 1rem !important; padding: 4px 10px !important; }}
.stDownloadButton > button {{ min-height: 52px !important; font-size: 18px !important; }}
</style>
"""
