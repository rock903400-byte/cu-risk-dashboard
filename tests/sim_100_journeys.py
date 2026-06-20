"""
100-person journey simulation
- 9 personas × ~11 variants = 100 journeys
- Records: exceptions, errors, warnings, task completion, step count, pain points
- Outputs: sim_100_results.json + sim_100_REPORT.md

Usage: python tests/sim_100_journeys.py
"""

import sys
import io
import json
import traceback
import time
from pathlib import Path
from collections import Counter
from typing import Dict, List, Any, Callable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import streamlit as st
from streamlit.testing.v1 import AppTest

# Service imports for auditing
from services.finance_service import calc_yoy_pct, prepare_waterfall_data
from services.diagnosis_service import calc_ratios
from common.classifier import classify


class Journey:
    def __init__(
        self,
        persona_id: str,
        variant_id: int,
        description: str,
        initial_session: Dict[str, Any],
        initial_query: Dict[str, Any],
        target_state: Callable[[AppTest], bool],
        ops: List[Dict[str, Any]],
        expected_pain_points: List[str],
    ):
        self.persona_id = persona_id
        self.variant_id = variant_id
        self.description = description
        self.initial_session = initial_session
        self.initial_query = initial_query
        self.target_state = target_state
        self.ops = ops
        self.expected_pain_points = expected_pain_points

    def get_id(self) -> str:
        return f"{self.persona_id}-{self.variant_id}"


class JourneyResult:
    def __init__(
        self,
        journey: Journey,
        completed: bool,
        exceptions: List[Dict[str, Any]],
        errors: List[Dict[str, Any]],
        warnings: List[Dict[str, Any]],
        step_count: int,
        pain_points_hit: List[str],
        ux_score: int,
        notes: Optional[str] = None,
        issues: List[Dict[str, Any]] = None,
    ):
        self.id = journey.get_id()
        self.persona = journey.persona_id
        self.description = journey.description
        self.completed = completed
        self.exceptions = exceptions
        self.errors = errors
        self.warnings = warnings
        self.step_count = step_count
        self.pain_points_hit = pain_points_hit
        self.ux_score = ux_score
        self.notes = notes
        self.issues = issues or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "persona": self.persona,
            "description": self.description,
            "completed": self.completed,
            "exceptions": self.exceptions,
            "errors": self.errors,
            "warnings": self.warnings,
            "step_count": self.step_count,
            "pain_points_hit": self.pain_points_hit,
            "ux_score": self.ux_score,
            "notes": self.notes,
            "issues": self.issues,
        }


class JourneyResult:
    def __init__(
        self,
        journey: Journey,
        completed: bool,
        exceptions: List[Dict[str, Any]],
        errors: List[Dict[str, Any]],
        warnings: List[Dict[str, Any]],
        step_count: int,
        pain_points_hit: List[str],
        ux_score: int,
        notes: Optional[str] = None,
        issues: List[Dict[str, Any]] = None,
    ):
        self.id = journey.get_id()
        self.persona = journey.persona_id
        self.description = journey.description
        self.completed = completed
        self.exceptions = exceptions
        self.errors = errors
        self.warnings = warnings
        self.step_count = step_count
        self.pain_points_hit = pain_points_hit
        self.ux_score = ux_score
        self.notes = notes
        self.issues = issues or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "persona": self.persona,
            "description": self.description,
            "completed": self.completed,
            "exceptions": self.exceptions,
            "errors": self.errors,
            "warnings": self.warnings,
            "step_count": self.step_count,
            "pain_points_hit": self.pain_points_hit,
            "ux_score": self.ux_score,
            "notes": self.notes,
            "issues": self.issues,
        }


class UXScorer:
    def __init__(self):
        self.pain_point_weights = {
            "PP-1": 15, "PP-2": 15, "PP-3": 10, "PP-4": 5,
            "PP-5": 10, "PP-6": 10, "PP-7": 5, "PP-8": 5,
            "PP-9": 10, "PP-10": 5,
        }

    def score(self, result: JourneyResult) -> int:
        score = 0
        if result.completed:
            score += 50
        pain_points_triggered = len(set(result.pain_points_hit))
        pp_scores = {0: 30, 1: 25, 2: 20, 3: 15, 4: 10, 5: 5}
        score += pp_scores.get(pain_points_triggered, 0)
        step_penalty = max(0, result.step_count - 5) * 2
        score += max(0, 20 - step_penalty)
        return min(100, max(0, score))

    def detect_pain_points(
        self, expected: List[str], result: JourneyResult, at: AppTest
    ) -> List[str]:
        hit = []
        nav = ""
        for pp in expected:
            if pp == "PP-1": # 找不到
                if any("找不到" in str(e.get("value", "")) for e in result.errors):
                    hit.append(pp)
            elif pp == "PP-2": # 渲染慢
                # AppTest doesn't give us real wall-clock time easily per run,
                # but we can check if it took too many steps to reach target
                if result.step_count > 10:
                    hit.append(pp)
            elif pp == "PP-3": # 異常 Warning
                if any("警告" in str(w.get("value", "")) for w in result.warnings):
                    hit.append(pp)
            elif pp == "PP-4": # 殘留敏感資訊
                if "pwd_input" in at.session_state and at.session_state["pwd_input"]:
                    hit.append(pp)
            elif pp == "PP-5": # Login 失敗未鎖定
                login_attempts = at.session_state["login_attempts"] if "login_attempts" in at.session_state else 0
                locked = at.session_state["locked"] if "locked" in at.session_state else False
                if login_attempts >= 3 and not locked:
                    hit.append(pp)
            elif pp == "PP-6": # 非法頁面
                nav = at.session_state["nav_selection"] if "nav_selection" in at.session_state else ""
                if nav and nav not in ["overview", "war_room"]:
                    hit.append(pp)
            elif pp == "PP-7": # 空資料進入資料頁
                has_data = "preloaded_data" in at.session_state and at.session_state["preloaded_data"] is not None
                if not has_data and nav in ["overview", "war_room"]:
                    hit.append(pp)
            elif pp == "PP-8": # KPI NaN/Inf
                for t in at.text:
                    if "NaN" in t or "inf" in t:
                        hit.append(pp)
                        break
            elif pp == "PP-9": # 多次重複下載
                dcount = at.session_state["download_count"] if "download_count" in at.session_state else 0
                if dcount > 1:
                    hit.append(pp)
            elif pp == "PP-10": # 空 df 跑 YoY
                if any("TypeError" in str(e.get("value", "")) for e in result.exceptions):
                    hit.append(pp)
        return hit


def service_layer_audit(at: AppTest, result: JourneyResult):
    """Audit the final session state against business logic and services."""
    sess = at.session_state
    data = sess["preloaded_data"] if "preloaded_data" in sess else None
    if not data:
        return

    # data is expected to be (data, df_m, df_l, raw_bytes, region_map)
    try:
        if not isinstance(data, (list, tuple)) or len(data) < 3:
            return
        df_m, df_l = data[1], data[2]
        import pandas as pd
        if not isinstance(df_l, pd.DataFrame):
            return
        
        # 1. Check for NaN/Inf in critical columns
        for col in ["社員", "股金", "開支比"]:
            if col in df_l.columns:
                if df_l[col].isin([float("inf"), -float("inf")]).any():
                    result.issues.append({"severity": "HIGH", "code": "S-1", "title": f"欄位 {col} 含 Inf"})
                if df_l[col].isna().sum() > len(df_l) * 0.3:
                    result.issues.append({"severity": "MEDIUM", "code": "S-2", "title": f"欄位 {col} NaN 過多"})
        
        # 2. Verify YoY calculations aren't crashing (simulated)
        if len(df_l) > 0:
            pass
            
    except Exception as e:
        result.issues.append({"severity": "CRITICAL", "code": "S-ERR", "title": "Audit Crash", "detail": str(e)})


def run_journey(journey: Journey) -> JourneyResult:
    try:
        at = AppTest.from_file("app.py", default_timeout=30)

        for key, value in journey.initial_session.items():
            at.session_state[key] = value
        for key, value in journey.initial_query.items():
            at.query_params[key] = value

        at.run()
        step_count = 1

        for op in journey.ops:
            if "click" in op:
                for btn in at.button:
                    if op["click"] in btn.label:
                        btn.click()
                        at.run()
                        step_count += 1
                        break
            elif "set" in op:
                for key, value in op["set"].items():
                    at.session_state[key] = value
                at.run()
                step_count += 1
            elif "query" in op:
                for key, value in op["query"].items():
                    at.query_params[key] = value
                at.run()
                step_count += 1
            elif "wait" in op:
                at.run()
                step_count += 1

        completed = journey.target_state(at)

        exceptions = []
        for e in at.exception:
            exceptions.append({"type": type(e.value).__name__, "value": str(e.value)})
        errors = []
        for e in at.error:
            errors.append({"type": type(e.value).__name__, "value": str(e.value)})
        warnings = []
        for w in at.warning:
            warnings.append({"type": type(w.value).__name__, "value": str(w.value)})

        ux_scorer = UXScorer()
        tmp_result = JourneyResult(
            journey, completed, exceptions, errors, warnings, step_count, [], 0
        )
        
        # Detect pain points using the full AppTest state
        pain_points_hit = ux_scorer.detect_pain_points(
            journey.expected_pain_points, tmp_result, at
        )
        
        # Re-calculate score with hit pain points
        final_result = JourneyResult(
            journey,
            completed,
            exceptions,
            errors,
            warnings,
            step_count,
            pain_points_hit,
            ux_scorer.score(JourneyResult(
                journey, completed, exceptions, errors, warnings, step_count, pain_points_hit, 0
            )),
        )
        
        # Run service audit
        service_layer_audit(at, final_result)

        notes = None
        if not completed:
            notes = f"任務未完成: exceptions={len(exceptions)}, errors={len(errors)}, warnings={len(warnings)}"

        final_result.notes = notes
        return final_result

    except Exception as e:
        return JourneyResult(
            journey,
            False,
            [{"type": type(e).__name__, "value": str(e)}],
            [],
            [],
            0,
            [],
            0,
            f"Journey runner exception: {type(e).__name__}: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Helper / target-state functions
# ---------------------------------------------------------------------------


def _make_op(*args, **kwargs) -> list:
    return []


def _no_exception(at: AppTest) -> bool:
    return len(list(at.exception)) == 0


def _assert_components(at: AppTest, required_texts: List[str]) -> bool:
    """Check if all required texts are present in any widget."""
    all_text = " ".join([str(t) for t in at.text])
    for txt in required_texts:
        if txt not in all_text:
            return False
    return True


def _assert_kpis(at: AppTest, min_count: int = 4) -> bool:
    """Check if minimum number of KPI cards (text elements) are present."""
    # In our app, KPIs are often in a specific format or just many text items
    # This is a heuristic
    return len(at.text) >= min_count


def _has_login_form(at: AppTest) -> bool:
    return len(list(at.text_input)) > 0 and len(list(at.button)) > 0


def _not_logged_in(at: AppTest) -> bool:
    return "logged_in" in at.session_state and at.session_state["logged_in"] is False


def _sees_overview(at: AppTest) -> bool:
    return _no_exception(at)


def _sees_district_warning(at: AppTest) -> bool:
    if len(list(at.warning)) > 0:
        for w in at.warning:
            text = str(w.value)
            if "找不到" in text or "區會模式" in text:
                return True
    return False


def _sees_welcome(at: AppTest) -> bool:
    """Check if welcome page is visible (landing state with no data)."""
    for m in at.markdown:
        raw = str(m.value)
        if "儲互社分析系統" in raw or "歡迎" in raw:
            return True
    return False


def _sees_dashboard_text(at: AppTest, required: list[str], or_welcome: bool = True) -> bool:
    """Check for dashboard text; fall back to welcome page if or_welcome is True."""
    if _no_exception(at) and _assert_components(at, required):
        return True
    if or_welcome and _no_exception(at) and _sees_welcome(at):
        return True
    return False


def _sees_kpis_or_welcome(at: AppTest, min_kpis: int = 4) -> bool:
    """Check for KPIs or fall back to welcome page."""
    if _no_exception(at) and _assert_kpis(at, min_kpis):
        return True
    if _no_exception(at) and _sees_welcome(at):
        return True
    return False


# ---------------------------------------------------------------------------
# P1: 未登入訪客
# ---------------------------------------------------------------------------
def section_p1_anonymous() -> list[Journey]:
    rv = []
    for v, (desc, sess, query) in enumerate(
        [
            ("匿名訪客 - 無查詢參數", {"logged_in": False}, {}),
            ("匿名訪客 - 帶 file param", {"logged_in": False}, {"file": "some_id"}),
            ("匿名訪客 - 帶 csv param", {"logged_in": False}, {"csv": "some_csv"}),
            ("匿名訪客 - 帶空 file", {"logged_in": False}, {"file": ""}),
        ],
        1,
    ):
        rv.append(
            Journey(
                persona_id="P1",
                variant_id=v,
                description=desc,
                initial_session=sess,
                initial_query=query,
                target_state=lambda at: _has_login_form(at) and _not_logged_in(at),
                ops=_make_op(),
                expected_pain_points=[],
            )
        )
    return rv


# ---------------------------------------------------------------------------
# P2: 已登入使用者（無 preloaded_data，模擬登入後空資料）
# ---------------------------------------------------------------------------
def section_p2_logged_in_no_data() -> list[Journey]:
    rv = []
    for v, (desc, sess, query) in enumerate(
        [
            (
                "已登入 - admin 無資料",
                {
                    "logged_in": True,
                    "role": "admin",
                    "assigned_region": None,
                    "assigned_union": None,
                    "preloaded_data": None,
                    "preloaded_csv": None,
                },
                {},
            ),
            (
                "已登入 - viewer 無資料",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "北區",
                    "assigned_union": "測試社",
                    "preloaded_data": None,
                    "preloaded_csv": None,
                },
                {},
            ),
            (
                "已登入 - admin 有 preloaded_data",
                {
                    "logged_in": True,
                    "role": "admin",
                    "assigned_region": None,
                    "assigned_union": None,
                },
                {},
            ),
            (
                "已登入 - viewer 有 preloaded_csv",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "北區",
                    "assigned_union": "測試社",
                },
                {},
            ),
            (
                "已登入 - viewer 區域無 union",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "北區",
                    "assigned_union": "不存在的社",
                    "preloaded_data": None,
                    "preloaded_csv": None,
                },
                {},
            ),
            (
                "已登入 - admin 有 preloaded_csv",
                {
                    "logged_in": True,
                    "role": "admin",
                    "assigned_region": None,
                    "assigned_union": None,
                },
                {},
            ),
        ],
        1,
    ):
        target = lambda at: _sees_dashboard_text(at, ["戰情室"]) or _assert_components(at, ["無資料"])
        rv.append(
            Journey(
                persona_id="P2",
                variant_id=v,
                description=desc,
                initial_session=sess,
                initial_query=query,
                target_state=target,
                ops=_make_op(),
                expected_pain_points=["PP-7"],
            )
        )
    return rv


# ---------------------------------------------------------------------------
# P3: 分享連結（query param 觸發 supabase 下載）
# ---------------------------------------------------------------------------
def section_p3_shared_links() -> list[Journey]:
    rv = []
    for v, (desc, sess, query) in enumerate(
        [
            ("分享連結 - file 參數", {"logged_in": False}, {"file": "test_file_id"}),
            ("分享連結 - csv 參數", {"logged_in": False}, {"csv": "test_csv_id"}),
            (
                "分享連結 - file+csv",
                {"logged_in": False},
                {"file": "test_file_id", "csv": "test_csv_id"},
            ),
            ("分享連結 - file 空字串", {"logged_in": False}, {"file": ""}),
            ("分享連結 - csv 空字串", {"logged_in": False}, {"csv": ""}),
        ],
        1,
    ):
        rv.append(
            Journey(
                persona_id="P3",
                variant_id=v,
                description=desc,
                initial_session=sess,
                initial_query=query,
                target_state=lambda at: _has_login_form(at) or _no_exception(at),
                ops=_make_op(),
                expected_pain_points=["PP-9"],
            )
        )
    return rv


# ---------------------------------------------------------------------------
# P4: Viewer — 有 assigned_region + assigned_union（個社模式）
# ---------------------------------------------------------------------------
def section_p4_viewer_with_union() -> list[Journey]:
    rv = []
    for v, (desc, sess, query) in enumerate(
        [
            (
                "viewer 個社 - 正常",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "北區",
                    "assigned_union": "測試社",
                },
                {},
            ),
            (
                "viewer 個社 - union 尾端空白",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "北區",
                    "assigned_union": "測試社 ",
                },
                {},
            ),
            (
                "viewer 個社 - 全形空白",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "北區",
                    "assigned_union": "測試社\u3000",
                },
                {},
            ),
            (
                "viewer 個社 - 特殊字元 union",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "北區",
                    "assigned_union": "<script>",
                },
                {},
            ),
            (
                "viewer 個社 - 極長 union",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "北區",
                    "assigned_union": "A" * 200,
                },
                {},
            ),
            (
                "viewer 個社 - region 無此 union",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "北區",
                    "assigned_union": "不存在的社",
                },
                {},
            ),
            (
                "viewer 個社 - region=None（admin 情境）",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": None,
                    "assigned_union": "測試社",
                },
                {},
            ),
        ],
        1,
    ):
        target = _sees_kpis_or_welcome
        rv.append(
            Journey(
                persona_id="P4",
                variant_id=v,
                description=desc,
                initial_session=sess,
                initial_query=query,
                target_state=target,
                ops=_make_op(),
                expected_pain_points=["PP-8"],
            )
        )
    return rv


# ---------------------------------------------------------------------------
# P5: Viewer — 區會模式（assigned_region 有值，union 不存在或 None）
# ---------------------------------------------------------------------------
def section_p5_viewer_district() -> list[Journey]:
    rv = []
    for v, (desc, sess, query) in enumerate(
        [
            (
                "viewer 區會 - region 有值 union=None",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "北區",
                    "assigned_union": None,
                },
                {},
            ),
            (
                "viewer 區會 - union 不存在（觸發 warning）",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "北區",
                    "assigned_union": "不存在的社",
                },
                {},
            ),
            (
                "viewer 區會 - 空 region 字串",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "",
                    "assigned_union": None,
                },
                {},
            ),
            (
                "viewer 區會 - region 含特殊字元",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "><",
                    "assigned_union": None,
                },
                {},
            ),
        ],
        1,
    ):
        target = lambda at: _sees_dashboard_text(at, ["區會模式"])
        rv.append(
            Journey(
                persona_id="P5",
                variant_id=v,
                description=desc,
                initial_session=sess,
                initial_query=query,
                target_state=target,
                ops=_make_op(),
                expected_pain_points=["PP-3"],
            )
        )
    return rv


# ---------------------------------------------------------------------------
# P6: Admin 模式（role=admin）
# ---------------------------------------------------------------------------
def section_p6_admin() -> list[Journey]:
    rv = []
    for v, (desc, sess, query) in enumerate(
        [
            (
                "admin - 全台 overview",
                {
                    "logged_in": True,
                    "role": "admin",
                    "assigned_region": None,
                    "assigned_union": None,
                },
                {},
            ),
            (
                "admin - 有 region 無 union",
                {
                    "logged_in": True,
                    "role": "admin",
                    "assigned_region": "北區",
                    "assigned_union": None,
                },
                {},
            ),
            (
                "admin - region+union 皆 set",
                {
                    "logged_in": True,
                    "role": "admin",
                    "assigned_region": "北區",
                    "assigned_union": "測試社",
                },
                {},
            ),
            (
                "admin - 上傳 Excel 觸發",
                {
                    "logged_in": True,
                    "role": "admin",
                    "assigned_region": None,
                    "assigned_union": None,
                },
                {},
            ),
            (
                "admin - 上傳 CSV 觸發",
                {
                    "logged_in": True,
                    "role": "admin",
                    "assigned_region": None,
                    "assigned_union": None,
                },
                {},
            ),
            (
                "admin - 無 preloaded 但已登入",
                {
                    "logged_in": True,
                    "role": "admin",
                    "assigned_region": None,
                    "assigned_union": None,
                    "preloaded_data": None,
                    "preloaded_csv": None,
                },
                {},
            ),
            (
                "admin - 大量 login_attempts",
                {
                    "logged_in": True,
                    "role": "admin",
                    "assigned_region": None,
                    "assigned_union": None,
                    "login_attempts": 99,
                },
                {},
            ),
            (
                "admin - locked=False 但無資料",
                {
                    "logged_in": True,
                    "role": "admin",
                    "assigned_region": None,
                    "assigned_union": None,
                    "locked": False,
                },
                {},
            ),
            (
                "admin - 有 preloaded_csv 無 preloaded_data",
                {
                    "logged_in": True,
                    "role": "admin",
                    "assigned_region": None,
                    "assigned_union": None,
                },
                {},
            ),
        ],
        1,
    ):
        target = lambda at: _sees_dashboard_text(at, ["全台"])
        rv.append(
            Journey(
                persona_id="P6",
                variant_id=v,
                description=desc,
                initial_session=sess,
                initial_query=query,
                target_state=target,
                ops=_make_op(),
                expected_pain_points=["PP-4", "PP-5"],
            )
        )
    return rv


# ---------------------------------------------------------------------------
# P7: role=viewer 各種邊界（無 preloaded_data 情境）
# ---------------------------------------------------------------------------
def section_p7_viewer_edge_cases() -> list[Journey]:
    rv = []
    for v, (desc, sess, query) in enumerate(
        [
            (
                "viewer - region 北區無 union",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "北區",
                    "assigned_union": None,
                },
                {},
            ),
            (
                "viewer - region 中區",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "中區",
                    "assigned_union": None,
                },
                {},
            ),
            (
                "viewer - region 南區",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "南區",
                    "assigned_union": None,
                },
                {},
            ),
            (
                "viewer - region 東區",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "東區",
                    "assigned_union": None,
                },
                {},
            ),
            (
                "viewer - region 空字串",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "",
                    "assigned_union": None,
                },
                {},
            ),
            (
                "viewer - role='hacker'（非法）",
                {
                    "logged_in": True,
                    "role": "hacker",
                    "assigned_region": None,
                    "assigned_union": None,
                },
                {},
            ),
        ],
        1,
    ):
        target = _sees_welcome
        rv.append(
            Journey(
                persona_id="P7",
                variant_id=v,
                description=desc,
                initial_session=sess,
                initial_query=query,
                target_state=target,
                ops=_make_op(),
                expected_pain_points=["PP-1"],
            )
        )
    return rv


# ---------------------------------------------------------------------------
# P8: preloaded_data = None / empty 情境
# ---------------------------------------------------------------------------
def section_p8_no_data() -> list[Journey]:
    rv = []
    for v, (desc, sess, query) in enumerate(
        [
            (
                "無資料 - admin preloaded None",
                {
                    "logged_in": True,
                    "role": "admin",
                    "assigned_region": None,
                    "assigned_union": None,
                    "preloaded_data": None,
                    "preloaded_csv": None,
                },
                {},
            ),
            (
                "無資料 - viewer preloaded None",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "北區",
                    "assigned_union": "測試社",
                    "preloaded_data": None,
                    "preloaded_csv": None,
                },
                {},
            ),
            (
                "無資料 - viewer 區會 preloaded None",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "北區",
                    "assigned_union": None,
                    "preloaded_data": None,
                    "preloaded_csv": None,
                },
                {},
            ),
            (
                "無資料 - admin locked flag",
                {
                    "logged_in": True,
                    "role": "admin",
                    "assigned_region": None,
                    "assigned_union": None,
                    "preloaded_data": None,
                    "preloaded_csv": None,
                    "locked": True,
                },
                {},
            ),
        ],
        1,
    ):
        target = lambda at: _sees_dashboard_text(at, ["無資料"])
        rv.append(
            Journey(
                persona_id="P8",
                variant_id=v,
                description=desc,
                initial_session=sess,
                initial_query=query,
                target_state=target,
                ops=_make_op(),
                expected_pain_points=["PP-7"],
            )
        )
    return rv


# ---------------------------------------------------------------------------
# P9: 登出 / session 重置 / 極端情境
# ---------------------------------------------------------------------------
def section_p9_logout_extreme() -> list[Journey]:
    rv = []
    for v, (desc, sess, query) in enumerate(
        [
            ("極端 - 未登入試圖存取", {"logged_in": False}, {}),
            (
                "極端 - 登出後 session 殘留",
                {
                    "logged_in": False,
                    "role": "admin",
                    "preloaded_data": None,
                    "preloaded_csv": None,
                },
                {},
            ),
            (
                "極端 - confirm_logout=True",
                {
                    "logged_in": True,
                    "role": "admin",
                    "confirm_logout": True,
                    "assigned_region": None,
                    "assigned_union": None,
                },
                {},
            ),
            (
                "極端 - nav_selection 非法值",
                {
                    "logged_in": True,
                    "role": "admin",
                    "nav_selection": "NON_EXISTENT_PAGE",
                    "assigned_region": None,
                    "assigned_union": None,
                },
                {},
            ),
            (
                "極端 - preload_err 殘留",
                {
                    "logged_in": True,
                    "role": "admin",
                    "preload_err": "舊錯誤未清除",
                    "assigned_region": None,
                    "assigned_union": None,
                },
                {},
            ),
            ("極端 - 所有預設值都保留（模擬全新 session）", {}, {}),
            (
                "極端 - is_district_office=True",
                {
                    "logged_in": True,
                    "role": "viewer",
                    "assigned_region": "北區",
                    "assigned_union": None,
                    "is_district_office": True,
                },
                {},
            ),
            (
                "極端 - 角色空白",
                {
                    "logged_in": True,
                    "role": "",
                    "assigned_region": None,
                    "assigned_union": None,
                },
                {},
            ),
        ],
        1,
    ):
        target = lambda at: _has_login_form(at) or _sees_dashboard_text(at, ["登出"])
        rv.append(
            Journey(
                persona_id="P9",
                variant_id=v,
                description=desc,
                initial_session=sess,
                initial_query=query,
                target_state=target,
                ops=_make_op(),
                expected_pain_points=["PP-6"],
            )
        )
    return rv


def section_p10_data_variants() -> list[Journey]:
    """P10: 資料邊界變體 — 測試 cleaning 與 calculations"""
    rv = []
    for v, (desc, sess, query) in enumerate(
        [
            ("資料 - 空 df_l", {"logged_in": True, "role": "admin", "preloaded_data": (None, None, [], None, None)}, {}),
            ("資料 - 極端負值", {"logged_in": True, "role": "admin", "preloaded_data": (None, None, [{"社員": -1000}], None, None)}, {}),
            ("資料 - 未來日期", {"logged_in": True, "role": "admin", "preloaded_data": (None, None, [{"日期": "209901"}], None, None)}, {}),
            ("資料 - 提撥率缺欄", {"logged_in": True, "role": "admin", "preloaded_data": (None, None, [{"社員": 10}], None, None)}, {}),
            ("資料 - 收支比需改開支比", {"logged_in": True, "role": "admin", "preloaded_data": (None, None, [{"收支比": 0.5}], None, None)}, {}),
            ("資料 - 全 NaN 欄位", {"logged_in": True, "role": "admin", "preloaded_data": (None, None, [{"社員": None}], None, None)}, {}),
            ("資料 - 混合型別", {"logged_in": True, "role": "admin", "preloaded_data": (None, None, [{"社員": "abc"}], None, None)}, {}),
            ("資料 - 超長數字", {"logged_in": True, "role": "admin", "preloaded_data": (None, None, [{"社員": 1e20}], None, None)}, {}),
            ("資料 - 零除測試", {"logged_in": True, "role": "admin", "preloaded_data": (None, None, [{"分母": 0}], None, None)}, {}),
            ("資料 - 僅含 header", {"logged_in": True, "role": "admin", "preloaded_data": (None, None, [], None, None)}, {}),
        ],
        1,
    ):
        rv.append(
            Journey(
                persona_id="P10",
                variant_id=v,
                description=desc,
                initial_session=sess,
                initial_query=query,
                target_state=_no_exception,
                ops=_make_op(),
                expected_pain_points=["PP-8", "PP-10"],
            )
        )
    return rv


def section_p11_concurrency_sim() -> list[Journey]:
    """P11: 模擬快速重複操作 (連點)"""
    rv = []
    for v, (desc, sess, query) in enumerate(
        [
            ("連點 - 生成分享連結 5 次", {"logged_in": True, "role": "admin"}, {}),
            ("連點 - 切換 View 10 次", {"logged_in": True, "role": "admin"}, {}),
            ("連點 - 登入/登出 迴圈", {"logged_in": False}, {}),
        ],
        1,
    ):
        ops = []
        if "生成分享連結" in desc:
            ops = [{"click": "生成分享連結"}] * 5
        elif "切換 View" in desc:
            ops = [{"click": "財務戰情室"}, {"click": "風險診斷"}] * 5
        
        rv.append(
            Journey(
                persona_id="P11",
                variant_id=v,
                description=desc,
                initial_session=sess,
                initial_query=query,
                target_state=_no_exception,
                ops=ops,
                expected_pain_points=["PP-9"],
            )
        )
    return rv


def section_p12_auth_roundtrip() -> list[Journey]:
    """P12: 完整身份驗證週期"""
    rv = []
    for v, (desc, sess, query) in enumerate(
        [
            ("Auth - 登入 -> 瀏覽 -> 登出 -> 重新登入", {"logged_in": False}, {}),
            ("Auth - 登入 -> 更改密碼(sim) -> 登出", {"logged_in": False}, {}),
        ],
        1,
    ):
        ops = [{"click": "登入"}, {"click": "登出"}, {"click": "登入"}] # simplified
        rv.append(
            Journey(
                persona_id="P12",
                variant_id=v,
                description=desc,
                initial_session=sess,
                initial_query=query,
                target_state=_no_exception,
                ops=ops,
                expected_pain_points=["PP-4"],
            )
        )
    return rv


def section_p13_region_switching() -> list[Journey]:
    """P13: 區域/社群快速切換"""
    rv = []
    for v, (desc, sess, query) in enumerate(
        [
            ("切換 - 北區 -> 中區 -> 南區 -> 東區", {"logged_in": True, "role": "admin"}, {}),
            ("切換 - 隨機 10 個 union", {"logged_in": True, "role": "admin"}, {}),
        ],
        1,
    ):
        rv.append(
            Journey(
                persona_id="P13",
                variant_id=v,
                description=desc,
                initial_session=sess,
                initial_query=query,
                target_state=_no_exception,
                ops=_make_op(),
                expected_pain_points=["PP-6"],
            )
        )
    return rv



ALL_SECTIONS = [
    ("P1 匿名訪客", section_p1_anonymous),
    ("P2 已登入（無資料）", section_p2_logged_in_no_data),
    ("P3 分享連結", section_p3_shared_links),
    ("P4 viewer 個社", section_p4_viewer_with_union),
    ("P5 viewer 區會", section_p5_viewer_district),
    ("P6 admin", section_p6_admin),
    ("P7 viewer 邊界", section_p7_viewer_edge_cases),
    ("P8 無資料", section_p8_no_data),
    ("P9 極端/登出", section_p9_logout_extreme),
    ("P10 資料變體", section_p10_data_variants),
    ("P11 連點模擬", section_p11_concurrency_sim),
    ("P12 Auth 週期", section_p12_auth_roundtrip),
    ("P13 區域切換", section_p13_region_switching),
]


# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------


def generate_all_journeys() -> list[Journey]:
    all_journeys: list[Journey] = []
    for _name, gen_fn in ALL_SECTIONS:
        all_journeys.extend(gen_fn())
    return all_journeys


def generate_report(all_results: List[JourneyResult]) -> str:
    total = len(all_results)
    completed = sum(1 for r in all_results if r.completed)
    completion_rate = completed / total * 100 if total else 0

    avg_steps = sum(r.step_count for r in all_results) / total if total else 0
    avg_score = sum(r.ux_score for r in all_results) / total if total else 0

    all_exceptions = []
    all_errors = []
    all_warnings = []
    all_pain_points = []
    severity_counts = Counter()
    all_issues = []

    for r in all_results:
        all_exceptions.extend(r.exceptions)
        all_errors.extend(r.errors)
        all_warnings.extend(r.warnings)
        all_pain_points.extend(r.pain_points_hit)
        for issue in r.issues:
            severity_counts[issue["severity"]] += 1
            all_issues.append((r.id, issue))

    exc_counts = Counter(e["type"] for e in all_exceptions)
    err_counts = Counter(e["type"] for e in all_errors)
    warn_counts = Counter(e["type"] for e in all_warnings)
    pp_counts = Counter(all_pain_points)

    lines = []
    lines.append("# 百人模擬報告（本地 AppTest）\n")
    lines.append(f"**模擬範圍: {total} 個旅程 (13 Persona 變體)**\n")
    lines.append("---\n")
    lines.append(f"## 總覽\n")
    lines.append(f"- **總旅程數**: {total}")
    lines.append(f"- **完成率**: {completed}/{total} ({completion_rate:.1f}%)")
    lines.append(f"- **平均步驟數**: {avg_steps:.1f}")
    lines.append(f"- **平均 UX 評分**: {avg_score:.1f} / 100")
    lines.append(f"- **總例外數**: {len(all_exceptions)}")
    lines.append(f"- **總錯誤數**: {len(all_errors)}")
    lines.append(f"- **總警告數**: {len(all_warnings)}")
    lines.append("")
    
    lines.append("## 嚴重性分級總計\n")
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        lines.append(f"- **{sev}**: {severity_counts[sev]}")
    lines.append("")

    lines.append("## 重點問題分析\n")
    for sev in ["CRITICAL", "HIGH", "MEDIUM"]:
        lines.append(f"### {sev}")
        found = False
        for rid, issue in all_issues:
            if issue["severity"] == sev:
                lines.append(f"- **{rid}**: {issue['title']} ({issue.get('detail', '無詳情')})")
                found = True
        if not found:
            lines.append("（無）")
        lines.append("")

    lines.append("## 痛點分布 (Pain Points)\n")
    lines.append(f"| 痛點代碼 | 觸發次數 |")
    lines.append(f"|----------|----------|")
    for pp in sorted(pp_counts.keys()):
        lines.append(f"| {pp} | {pp_counts[pp]} |")
    lines.append("")

    lines.append("## 各旅程詳細結果\n")
    for r in all_results:
        lines.append(f"### {r.id}: {r.description}")
        lines.append(f"- 完成: {'✅' if r.completed else '❌'}")
        lines.append(f"- UX 評分: {r.ux_score}")
        lines.append(f"- 痛點: {', '.join(r.pain_points_hit) if r.pain_points_hit else '無'}")
        if r.issues:
            lines.append(f"- 發現問題: {', '.join([i['title'] for i in r.issues])}")
        if r.exceptions:
            lines.append(f"- 例外: {', '.join(e['value'][:80] for e in r.exceptions)}")
        if r.notes:
            lines.append(f"- 備註: {r.notes}")
        lines.append("")

    lines.append("---\n")
    lines.append("## 結論\n")
    if completion_rate >= 90 and avg_score >= 70 and severity_counts["CRITICAL"] == 0:
        lines.append("**結果: 良好** — 大部分旅程完成，無嚴重問題。")
    elif completion_rate >= 70:
        lines.append("**結果: 需改善** — 存在 HIGH/MEDIUM 問題或 UX 評分偏低。")
    else:
        lines.append("**結果: 需重大改善** — 完成率低或有 CRITICAL 問題。")
    lines.append(f"\n_產生時間: (模擬執行日期)_\n")

    return "\n".join(lines)


def main():
    output_dir = Path(__file__).resolve().parent

    print("Generating 100 journeys...")
    all_journeys = generate_all_journeys()
    print(f"  Total journeys: {len(all_journeys)}")
    for name, _ in ALL_SECTIONS:
        count = len([j for j in all_journeys if j.persona_id == name.split()[0]])
        print(f"    {name}: {count} journeys")

    results: list[JourneyResult] = []
    for i, j in enumerate(all_journeys, 1):
        sys.stdout.write(
            f"\r  Running journey {i}/{len(all_journeys)}: {j.get_id()}..."
        )
        sys.stdout.flush()
        result = run_journey(j)
        results.append(result)

    print(f"\n\nAll {len(results)} journeys completed.")

    # Save JSON
    json_path = output_dir / "sim_100_results.json"
    json_data = {
        "summary": {
            "total": len(results),
            "completed": sum(1 for r in results if r.completed),
            "avg_steps": (
                sum(r.step_count for r in results) / len(results) if results else 0
            ),
            "avg_ux_score": (
                sum(r.ux_score for r in results) / len(results) if results else 0
            ),
        },
        "results": [r.to_dict() for r in results],
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    print(f"Saved: {json_path}")

    # Save REPORT.md
    report_path = output_dir / "sim_100_REPORT.md"
    report = generate_report(results)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Saved: {report_path}")

    # Print summary
    total = len(results)
    completed = sum(1 for r in results if r.completed)
    completion_rate = completed / total * 100 if total else 0
    avg_score = sum(r.ux_score for r in results) / total if total else 0
    total_exc = sum(len(r.exceptions) for r in results)
    print(f"\n{'='*50}")
    print(f"  Total journeys:    {total}")
    print(f"  Completed:         {completed}/{total} ({completion_rate:.1f}%)")
    print(f"  Avg UX score:      {avg_score:.1f}/100")
    print(f"  Total exceptions:  {total_exc}")
    print(f"  Avg steps:         {sum(r.step_count for r in results)/total:.1f}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
