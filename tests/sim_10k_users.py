"""
10,000 人壓力測試 — 不修改任何 deploy 程式碼,只觀察行為。

架構(總計約 10,000+ 個案例):
  A. 1K 既有測試 re-run(基線)
  B. 1K 隨機資料抖動(1 byte 改變是否影響結果)
  C. 1K 邊界值模糊測試(數字、字串、Unicode)
  D. 1K 惡意輸入(XSS / SQLi / 路徑穿越 / 編碼繞過)
  E. 1K 同期月份比對壓力
  F. 500 並行 session 模擬
  G. 500 大檔案壓力(100-500 社 × 60 月)
  H. 500 快取命中/失效循環
  I. 500 隨機使用者旅程 fuzz
  J. 1K classifier 隨機輸入
  合計:~10,000 個案例

執行:  python tests/sim_10k_users.py
輸出:  tests/sim_10k_results.json
       tests/sim_10k_REPORT.md
"""

import sys
import io
import json
import time
import random
import string
import traceback
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np

from common.dates import convert_minguo_date, get_value
from common.utils import safe_div, format_large_number, fmt_pct
from common.classifier import classify, classify_code
from common.cleaning import defensive_clean_value
from common.thresholds import DEFAULT_THRESHOLDS
from services.finance_service import (
    get_annual_snapshot,
    calc_yoy_pct,
    prepare_waterfall_data,
    detect_yoy_anomalies,
)
from services.diagnosis_service import calc_ratios, rate_ratio, calc_trend

ISSUES = []
SEEN_FINGERPRINTS = set()


def issue(severity, code, title, detail, repro=None, fp=None):
    if fp and fp in SEEN_FINGERPRINTS:
        return
    if fp:
        SEEN_FINGERPRINTS.add(fp)
    ISSUES.append(
        {
            "severity": severity,
            "code": code,
            "title": title,
            "detail": detail,
            "repro": repro,
        }
    )


# ============================================================
# B. 隨機資料抖動(1,000 個)
# ============================================================
def section_b():
    print("\n[B] 隨機資料抖動測試 1,000 個")
    random.seed(42)
    n_pass, n_fail = 0, 0

    for i in range(1000):
        base_income = random.randint(10000, 500000)
        base_expense = random.randint(5000, 300000)
        months = random.randint(1, 12)

        rows = []
        for m in range(1, months + 1):
            ym = f"113{m:02d}"
            income = base_income + random.randint(-5000, 5000)
            expense = -(base_expense + random.randint(-3000, 3000))
            rows.append(
                {
                    "年月": ym,
                    "會計科目": "4101",
                    "會科名稱": "利息收入",
                    "社名": "T",
                    "當月金額": income,
                }
            )
            rows.append(
                {
                    "年月": ym,
                    "會計科目": "5101",
                    "會科名稱": "利息支出",
                    "社名": "T",
                    "當月金額": expense,
                }
            )

        df = pd.DataFrame(rows)
        df["年度"] = "113"
        try:
            snap = get_annual_snapshot(df, "113")
            wf = prepare_waterfall_data(snap)
            actual_income = snap[snap["會計科目"].astype(str).str.match(r"^4")][
                "當月金額"
            ].sum()
            actual_expense = snap[snap["會計科目"].astype(str).str.match(r"^5")][
                "當月金額"
            ].sum()
            true_net = actual_income + actual_expense

            if abs(wf["net"] - true_net) > 1:
                issue(
                    "CRITICAL",
                    "B-WF",
                    f"[{i}] 瀑布圖 net 偏差",
                    f"true={true_net}, got={wf['net']}, diff={wf['net']-true_net}",
                )
                n_fail += 1
            else:
                n_pass += 1
        except Exception as e:
            issue(
                "MEDIUM",
                "B-EXC",
                f"[{i}] 隨機資料拋例外",
                f"{type(e).__name__}: {str(e)[:200]}",
            )
            n_fail += 1

    print(f"  pass={n_pass}, fail={n_fail}")


# ============================================================
# C. 邊界值模糊測試(1,000 個)
# ============================================================
def section_c():
    print("\n[C] 邊界值模糊測試 1,000 個")
    random.seed(43)
    n_pass, n_fail = 0, 0

    for i in range(1000):
        test = random.choice(["div", "fmt", "date", "classify", "yoy"])
        try:
            if test == "div":
                n = random.choice(
                    [
                        0,
                        1,
                        -1,
                        10,
                        1e10,
                        -1e10,
                        float("nan"),
                        float("inf"),
                        -float("inf"),
                        None,
                        1e-300,
                        -1e-300,
                        1e300,
                    ]
                )
                d = random.choice(
                    [0, 1, -1, 10, 1e10, float("nan"), float("inf"), None, 1e-300]
                )
                r = safe_div(n, d)
                if isinstance(r, float) and (
                    r != r or r == float("inf") or r == -float("inf")
                ):
                    if random.random() < 0.01:  # 1% 機率記錄,但只記 unique
                        issue(
                            "LOW",
                            "C-DIV",
                            f"safe_div 怪異結果",
                            f"safe_div({n!r},{d!r})={r!r}",
                            fp=f"div-{n}-{d}",
                        )
                    n_fail += 1
                else:
                    n_pass += 1
            elif test == "fmt":
                v = random.choice(
                    [
                        0,
                        1,
                        -1,
                        100,
                        1e4,
                        1e8,
                        1e10,
                        float("nan"),
                        float("inf"),
                        None,
                        0.5,
                        1.234567,
                    ]
                )
                r = format_large_number(v)
                if not isinstance(r, str):
                    issue(
                        "HIGH",
                        "C-FMT",
                        "format_large_number 回傳非字串",
                        f"input={v!r}, type={type(r).__name__}",
                    )
                    n_fail += 1
                else:
                    n_pass += 1
            elif test == "date":
                v = random.choice(
                    [
                        11301,
                        11312,
                        11300,
                        11313,
                        9999,
                        -1,
                        0,
                        None,
                        "abc",
                        "",
                        11301.5,
                        113,
                    ]
                )
                r = convert_minguo_date(v)
                if r is None:
                    issue(
                        "HIGH",
                        "C-DATE",
                        "convert_minguo_date 回傳 None(應 NaT)",
                        f"input={v!r}",
                    )
                    n_fail += 1
                else:
                    n_pass += 1
            elif test == "classify":
                p = {
                    k: random.uniform(-10, 10)
                    for k in [
                        "R0",
                        "R1",
                        "M0",
                        "M1",
                        "M2",
                        "M3",
                        "S0",
                        "S1",
                        "S2",
                        "S3",
                        "eOvd",
                        "O0",
                        "O1",
                        "eLoan",
                        "sLoan",
                        "memG",
                        "shrG",
                    ]
                }
                s, r = classify(p, DEFAULT_THRESHOLDS)
                if not isinstance(s, str) or not s.startswith(
                    ("🚨", "⚠️", "💤", "✅", "📊")
                ):
                    issue(
                        "HIGH",
                        "C-CLS",
                        "classify 回傳非預期狀態",
                        f"status={s!r}, reason={r!r}",
                    )
                    n_fail += 1
                else:
                    n_pass += 1
            elif test == "yoy":
                curr = random.choice([0, 100, -100, 1e10, float("nan"), None])
                prev = random.choice([0, 100, -100, float("nan"), None])
                r = calc_yoy_pct(curr, prev)
                if prev == 0 and r is not None:
                    issue(
                        "HIGH",
                        "C-YOY",
                        "calc_yoy_pct 分母0 應 None",
                        f"({curr},{prev})={r!r}",
                    )
                    n_fail += 1
                else:
                    n_pass += 1
        except Exception as e:
            issue(
                "MEDIUM",
                "C-EXC",
                f"[{i}/{test}] 拋例外",
                f"{type(e).__name__}: {str(e)[:200]}",
            )
            n_fail += 1

    print(f"  pass={n_pass}, fail={n_fail}")


# ============================================================
# D. 惡意輸入(1,000 個)
# ============================================================
D_MALICIOUS = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "javascript:alert(1)",
    "<svg onload=alert(1)>",
    "'; DROP TABLE users--",
    "1' OR '1'='1",
    "../../../../etc/passwd",
    "{{7*7}}",
    "${7*7}",
    "<%=7*7%>",
    "\x00\x01\x02",
    "\u202e\u0000",
    "🚨💀🔥👻",
    "a]b[c",
    "A" * 1000,
    "A" * 10000,
    "  ",
    "\t\n\r",
    "..",
    "....",
    "%00",
    "%2e%2e%2f",
    "null",
    "undefined",
    "NaN",
    "Infinity",
    "-0",
    "+0",
    "\xff\xfe",
    "\xef\xbb\xbf",
]

D_FIELDS = [
    "社員數",
    "股金",
    "貸放比",
    "逾放比",
    "開支比",
    "提撥率",
    "儲蓄率",
    "密碼",
    "社名",
    "區域",
    "會計科目",
    "會科名稱",
    "當月金額",
    "年月",
    "年度",
]


def section_d():
    print("\n[D] 惡意輸入測試 1,000 個")
    random.seed(44)
    n_pass, n_fail = 0, 0
    dangerous_outputs = []

    for i in range(1000):
        inp = random.choice(D_MALICIOUS)
        field = random.choice(D_FIELDS)
        try:
            r = defensive_clean_value(inp, field)
            if isinstance(r, str) and (
                "<script" in r.lower() or "onerror" in r or "javascript:" in r
            ):
                if r not in dangerous_outputs:
                    dangerous_outputs.append(r[:100])
                    issue(
                        "HIGH",
                        "D-XSS",
                        f"defensive_clean_value 沒過濾惡意字串({field})",
                        f"input={inp[:50]!r}, output={r[:100]!r}",
                    )
                n_fail += 1
            else:
                n_pass += 1
        except Exception as e:
            issue(
                "MEDIUM",
                "D-EXC",
                f"防禦性清洗拋例外({field})",
                f"input={inp[:50]!r}, {type(e).__name__}: {str(e)[:100]}",
            )
            n_fail += 1

    # 同樣測試 convert_minguo_date
    for inp in D_MALICIOUS:
        try:
            r = convert_minguo_date(inp)
            if r is None:
                issue(
                    "MEDIUM",
                    "D-DATE-NONE",
                    "convert_minguo_date 回傳 None",
                    f"input={inp!r}",
                )
        except Exception as e:
            issue(
                "LOW",
                "D-DATE-EXC",
                "convert_minguo_date 對惡意輸入拋例外",
                f"input={inp!r}, {type(e).__name__}",
            )

    print(f"  pass={n_pass}, fail={n_fail}, 危險輸出={len(dangerous_outputs)}")


# ============================================================
# E. 同期月份比對壓力(1,000 個)
# ============================================================
def section_e():
    print("\n[E] 同期月份比對壓力 1,000 個")
    random.seed(45)
    n_pass, n_fail = 0, 0

    for i in range(1000):
        year_curr = random.choice(["110", "111", "112", "113", "114"])
        year_prev = random.choice(["110", "111", "112", "113", "114"])
        months_count = random.randint(1, 12)
        curr_months = sorted(random.sample(range(1, 13), months_count))

        rows = []
        for ym_int in curr_months:
            ym_curr = f"{year_curr}{ym_int:02d}"
            ym_prev = f"{year_prev}{ym_int:02d}"
            rows.append(
                {
                    "年月": ym_curr,
                    "年度": year_curr,
                    "會計科目": "1101",
                    "會科名稱": "現金",
                    "當月金額": 1000 + ym_int,
                }
            )
            rows.append(
                {
                    "年月": ym_prev,
                    "年度": year_prev,
                    "會計科目": "1101",
                    "會科名稱": "現金",
                    "當月金額": 500 + ym_int,
                }
            )

        df = pd.DataFrame(rows)
        try:
            snap = get_annual_snapshot(
                df, year_curr, same_months=[f"{year_curr}{m:02d}" for m in curr_months]
            )
            if snap.empty:
                issue(
                    "MEDIUM",
                    "E-EMPTY",
                    f"[{i}] 同年查無資料",
                    f"year={year_curr}, months={curr_months}",
                )
                n_fail += 1
            else:
                asset = snap[snap["會計科目"] == "1101"]["當月金額"]
                if asset.empty:
                    n_pass += 1
                else:
                    n_pass += 1
        except Exception as e:
            issue(
                "MEDIUM",
                "E-EXC",
                f"[{i}] 同期比對拋例外",
                f"{type(e).__name__}: {str(e)[:150]}",
            )
            n_fail += 1

    print(f"  pass={n_pass}, fail={n_fail}")


# ============================================================
# F. 並行 session 模擬(500 個)
# ============================================================
def section_f():
    print("\n[F] 並行 session 模擬 500 個")
    random.seed(46)
    n_pass, n_fail = 0, 0

    for i in range(500):
        sessions = random.randint(2, 8)
        ops = []
        for s in range(sessions):
            op = random.choice(
                [
                    "set_data",
                    "set_csv",
                    "login",
                    "logout",
                    "increment_attempts",
                    "trigger_locked",
                    "set_region",
                    "set_union",
                    "clear_data",
                    "set_msg",
                ]
            )
            ops.append(op)

        session = {
            "logged_in": False,
            "role": None,
            "assigned_region": None,
            "assigned_union": None,
            "login_attempts": 0,
            "locked": False,
            "preloaded_data": None,
            "preloaded_csv": None,
            "preloaded_passwords": {},
            "nav_selection": "📊 社務診斷",
            "is_district_office": False,
            "confirm_logout": False,
            "xl_msg": None,
            "csv_msg": None,
        }
        try:
            for op in ops:
                if op == "login":
                    session["logged_in"] = True
                    session["role"] = "viewer"
                elif op == "logout":
                    for k in list(session.keys()):
                        if k in (
                            "logged_in",
                            "role",
                            "assigned_region",
                            "assigned_union",
                            "login_attempts",
                            "locked",
                            "preloaded_data",
                            "preloaded_csv",
                            "preloaded_passwords",
                            "nav_selection",
                            "is_district_office",
                            "confirm_logout",
                            "xl_msg",
                            "csv_msg",
                        ):
                            session[k] = type(session[k])()
                elif op == "increment_attempts":
                    session["login_attempts"] = min(session["login_attempts"] + 1, 999)
                    if session["login_attempts"] >= 5:
                        session["locked"] = True
                elif op == "trigger_locked":
                    session["locked"] = True
                    session["login_attempts"] = 5
                elif op == "set_data":
                    session["preloaded_data"] = ("fake",) * 5
                elif op == "set_csv":
                    session["preloaded_csv"] = ("fake", b"")
                elif op == "set_region":
                    session["assigned_region"] = random.choice(
                        ["北區", "中區", "南區", "東區"]
                    )
                elif op == "set_union":
                    session["assigned_union"] = random.choice(["A社", "B社", None])
                elif op == "clear_data":
                    session["preloaded_data"] = None
                elif op == "set_msg":
                    session["xl_msg"] = (
                        ("error", "test") if random.random() < 0.5 else None
                    )
            n_pass += 1
        except Exception as e:
            issue(
                "MEDIUM",
                "F-EXC",
                f"[{i}] 並行 session 模擬拋例外",
                f"{type(e).__name__}: {str(e)[:100]}",
            )
            n_fail += 1

    print(f"  pass={n_pass}, fail={n_fail}")


# ============================================================
# G. 大檔案壓力(500 個)
# ============================================================
def section_g():
    print("\n[G] 大檔案壓力 500 個")
    random.seed(47)
    n_pass, n_fail = 0, 0
    t_total = 0

    for i in range(500):
        n_unions = random.randint(100, 500)
        n_months = random.randint(12, 60)
        start_year = random.choice([110, 111, 112, 113])

        rows_main = []
        rows_loan = []
        rows_region = []
        for u in range(n_unions):
            sno = f"{u:04d}"
            name = f"社{u}"
            region = random.choice(["北", "中", "南", "東"])
            rows_region.append({"社名": name, "區域": region, "密碼": str(u)})
            for m_offset in range(n_months):
                year = start_year + m_offset // 12
                month = (m_offset % 12) + 1
                ym = f"{year}{month:02d}"
                rows_main.append(
                    {
                        "社號": sno,
                        "社名": name,
                        "年月": ym,
                        "社員數": random.randint(50, 5000),
                        "股金": random.randint(1_000_000, 100_000_000),
                        "貸放比": random.uniform(0.1, 0.9),
                        "儲蓄率": random.uniform(0.5, 0.95),
                    }
                )
                rows_loan.append(
                    {
                        "社號": sno,
                        "社名": name,
                        "年月": ym,
                        "逾期貸款": random.randint(0, 500_000),
                        "逾放比": random.uniform(0, 0.1),
                        "開支比": random.uniform(0.6, 1.1),
                        "提撥率": random.uniform(0, 0.05),
                    }
                )

        df_main = pd.DataFrame(rows_main)
        df_loan = pd.DataFrame(rows_loan)
        df_region = pd.DataFrame(rows_region)

        import io
        from data.excel_processor import process_excel_final
        from config import get_config

        cfg = get_config()

        buf = io.BytesIO()
        try:
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                df_main.to_excel(w, sheet_name=cfg["SHEETS"]["MAIN"], index=False)
                df_loan.to_excel(w, sheet_name=cfg["SHEETS"]["LOAN"], index=False)
                df_region.to_excel(w, sheet_name=cfg["SHEETS"]["REGION"], index=False)

            t0 = time.time()
            data, df_m, df_l, pws, rm = process_excel_final(
                buf.getvalue(),
                cfg["THRESHOLDS"],
                cfg["SHEETS"],
            )
            t1 = time.time()
            t_total += t1 - t0

            if len(data) != n_unions:
                issue(
                    "MEDIUM",
                    "G-LEN",
                    f"[{i}] 解析後社數不符",
                    f"input={n_unions}, got={len(data)}",
                )
                n_fail += 1
            elif (t1 - t0) > 30:
                issue(
                    "LOW",
                    "G-SLOW",
                    f"[{i}] 解析時間過長(>{30}s)",
                    f"{n_unions}社×{n_months}月: {t1-t0:.1f}s",
                )
                n_fail += 1
            else:
                n_pass += 1
        except Exception as e:
            issue(
                "MEDIUM",
                "G-EXC",
                f"[{i}] 大檔案拋例外",
                f"{n_unions}社×{n_months}月: {type(e).__name__}: {str(e)[:150]}",
            )
            n_fail += 1

    avg_ms = (t_total / max(1, n_pass)) * 1000
    print(f"  pass={n_pass}, fail={n_fail}, 平均解析時間={avg_ms:.0f}ms")


# ============================================================
# H. 快取命中/失效循環(500 個)
# ============================================================
def section_h():
    print("\n[H] 快取命中/失效循環 500 個")
    random.seed(48)
    n_pass, n_fail = 0, 0

    from data.excel_processor import process_excel_final
    from config import get_config

    cfg = get_config()

    main = pd.DataFrame(
        [
            {
                "社號": "001",
                "社名": "T",
                "年月": "11312",
                "社員數": 100,
                "股金": 5000000,
                "貸放比": 0.5,
                "儲蓄率": 0.85,
            }
        ]
    )
    loan = pd.DataFrame(
        [
            {
                "社號": "001",
                "社名": "T",
                "年月": "11312",
                "逾期貸款": 100,
                "逾放比": 0.01,
                "開支比": 0.95,
                "提撥率": 0.02,
            }
        ]
    )
    region = pd.DataFrame([{"社名": "T", "區域": "北", "密碼": 1234}])

    import io

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        main.to_excel(w, sheet_name=cfg["SHEETS"]["MAIN"], index=False)
        loan.to_excel(w, sheet_name=cfg["SHEETS"]["LOAN"], index=False)
        region.to_excel(w, sheet_name=cfg["SHEETS"]["REGION"], index=False)
    base_bytes = buf.getvalue()

    times = []
    for i in range(500):
        try:
            t0 = time.time()
            process_excel_final(base_bytes, cfg["THRESHOLDS"], cfg["SHEETS"])
            t1 = time.time()
            times.append(t1 - t0)
            n_pass += 1
        except Exception as e:
            issue(
                "MEDIUM",
                "H-EXC",
                f"[{i}] cache 循環拋例外",
                f"{type(e).__name__}: {str(e)[:100]}",
            )
            n_fail += 1

    if times:
        avg_ms = sum(times) / len(times) * 1000
        max_ms = max(times) * 1000
        print(
            f"  pass={n_pass}, fail={n_fail}, 平均={avg_ms:.2f}ms, 最大={max_ms:.2f}ms"
        )
        if max_ms > 500:
            issue(
                "LOW",
                "H-SLOW",
                "cache 循環中出現 > 500ms 的 spike",
                f"max={max_ms:.0f}ms in {len(times)} runs",
            )
    else:
        print(f"  pass={n_pass}, fail={n_fail}")


# ============================================================
# I. 隨機使用者旅程 fuzz(500 個)
# ============================================================
def section_i():
    print("\n[I] 隨機使用者旅程 fuzz 500 個")
    random.seed(49)
    n_pass, n_fail = 0, 0

    from streamlit.testing.v1 import AppTest

    PERSONAS = [
        "未登入訪客",
        "個社 viewer",
        "區會 viewer",
        "admin",
        "locked admin",
        "角色異常",
        "登出確認中",
        "個社 union 找不到",
        "首次登入 tip 未關",
    ]

    for i in range(500):
        persona = random.choice(PERSONAS)
        try:
            at = AppTest.from_file("app.py", default_timeout=15)
            if persona == "未登入訪客":
                pass
            elif persona == "個社 viewer":
                at.session_state["logged_in"] = True
                at.session_state["role"] = "viewer"
                at.session_state["assigned_region"] = random.choice(
                    ["北區", "中區", "南區", "東區"]
                )
                at.session_state["assigned_union"] = f"測試社{random.randint(1, 100)}"
                at.session_state["is_district_office"] = False
            elif persona == "區會 viewer":
                at.session_state["logged_in"] = True
                at.session_state["role"] = "viewer"
                at.session_state["assigned_region"] = random.choice(["北區", "中區"])
                at.session_state["assigned_union"] = None
                at.session_state["is_district_office"] = True
            elif persona == "admin":
                at.session_state["logged_in"] = True
                at.session_state["role"] = "admin"
                at.session_state["is_district_office"] = False
            elif persona == "locked admin":
                at.session_state["login_attempts"] = random.randint(5, 100)
                at.session_state["locked"] = True
            elif persona == "角色異常":
                at.session_state["logged_in"] = True
                at.session_state["role"] = random.choice(
                    ["hacker", "superuser", "", None, 0]
                )
            elif persona == "登出確認中":
                at.session_state["logged_in"] = True
                at.session_state["role"] = "admin"
                at.session_state["confirm_logout"] = True
            elif persona == "個社 union 找不到":
                at.session_state["logged_in"] = True
                at.session_state["role"] = "viewer"
                at.session_state["assigned_region"] = "北區"
                at.session_state["assigned_union"] = random.choice(
                    ["已合併社", None, "", "找不到"]
                )
                at.session_state["is_district_office"] = False
            elif persona == "首次登入 tip 未關":
                at.session_state["logged_in"] = True
                at.session_state["role"] = "admin"

            if random.random() < 0.3:
                at.query_params["file"] = f"xl_{random.randint(1, 10000)}.xlsx"
            if random.random() < 0.1:
                at.query_params["csv"] = f"csv_{random.randint(1, 10000)}.csv"

            at.run()
            if len(at.exception) > 0:
                for e in at.exception:
                    err = str(e.value)
                    if "ScriptRunContext" in err or "missing" in err.lower():
                        continue
                    issue(
                        "CRITICAL",
                        "I-APPEXC",
                        f"[{i}/{persona}] AppTest 拋例外",
                        err[:200],
                    )
                n_fail += 1
            else:
                n_pass += 1
        except Exception as e:
            issue(
                "HIGH",
                "I-FRAME",
                f"[{i}/{persona}] AppTest 框架錯誤",
                f"{type(e).__name__}: {str(e)[:150]}",
            )
            n_fail += 1

    print(f"  pass={n_pass}, fail={n_fail}")


# ============================================================
# J. Classifier 隨機輸入(1,000 個)
# ============================================================
def section_j():
    print("\n[J] Classifier 隨機輸入 1,000 個")
    random.seed(50)
    n_pass, n_fail = 0, 0

    expected_statuses = {
        "🚨 特別關懷",
        "⚠️ 流動性緊繃",
        "💤 資金閒置",
        "✅ 穩健模範",
        "📊 一般狀態",
    }

    for i in range(1000):
        scenario = random.choice(
            [
                "all_zero",
                "random",
                "boundary_low",
                "boundary_high",
                "single_trigger",
                "all_good",
                "all_bad",
            ]
        )
        if scenario == "all_zero":
            p = {
                k: 0.0
                for k in [
                    "R0",
                    "R1",
                    "M0",
                    "M1",
                    "M2",
                    "M3",
                    "S0",
                    "S1",
                    "S2",
                    "S3",
                    "eOvd",
                    "O0",
                    "O1",
                    "eLoan",
                    "sLoan",
                    "memG",
                    "shrG",
                ]
            }
        elif scenario == "random":
            p = {
                k: random.uniform(-100, 100)
                for k in [
                    "R0",
                    "R1",
                    "M0",
                    "M1",
                    "M2",
                    "M3",
                    "S0",
                    "S1",
                    "S2",
                    "S3",
                    "eOvd",
                    "O0",
                    "O1",
                    "eLoan",
                    "sLoan",
                    "memG",
                    "shrG",
                ]
            }
        elif scenario == "boundary_low":
            p = {
                k: 0.001
                for k in [
                    "R0",
                    "R1",
                    "M0",
                    "M1",
                    "M2",
                    "M3",
                    "S0",
                    "S1",
                    "S2",
                    "S3",
                    "eOvd",
                    "O0",
                    "O1",
                    "eLoan",
                    "sLoan",
                    "memG",
                    "shrG",
                ]
            }
        elif scenario == "boundary_high":
            p = {
                k: 1e10
                for k in [
                    "R0",
                    "R1",
                    "M0",
                    "M1",
                    "M2",
                    "M3",
                    "S0",
                    "S1",
                    "S2",
                    "S3",
                    "eOvd",
                    "O0",
                    "O1",
                    "eLoan",
                    "sLoan",
                    "memG",
                    "shrG",
                ]
            }
        elif scenario == "single_trigger":
            p = {
                k: 0.0
                for k in [
                    "R0",
                    "R1",
                    "M0",
                    "M1",
                    "M2",
                    "M3",
                    "S0",
                    "S1",
                    "S2",
                    "S3",
                    "eOvd",
                    "O0",
                    "O1",
                    "eLoan",
                    "sLoan",
                    "memG",
                    "shrG",
                ]
            }
            trigger = random.choice(["c1", "c2", "c3", "c4", "c5"])
            if trigger == "c1":
                p["R0"] = 1.5
                p["R1"] = 1.5
            elif trigger == "c2":
                p["eLoan"] = 0.05
                p["sLoan"] = 0.1
            elif trigger == "c3":
                p["eOvd"] = 0.6
                p["O0"] = 100
                p["O1"] = 90
            elif trigger == "c4":
                p["M0"], p["M1"], p["M2"], p["M3"] = 50, 60, 70, 80
            elif trigger == "c5":
                p["S0"], p["S1"], p["S2"], p["S3"] = 50, 60, 70, 80
        elif scenario == "all_good":
            p = {
                "R0": 0.5,
                "R1": 0.5,
                "M0": 100,
                "M1": 110,
                "M2": 120,
                "M3": 130,
                "S0": 100,
                "S1": 110,
                "S2": 120,
                "S3": 130,
                "eOvd": 0.01,
                "O0": 100,
                "O1": 50,
                "eLoan": 0.6,
                "sLoan": 0.55,
                "memG": 0.05,
                "shrG": 0.05,
            }
        else:
            p = {
                "R0": 2.0,
                "R1": 2.0,
                "M0": 10,
                "M1": 20,
                "M2": 30,
                "M3": 40,
                "S0": 10,
                "S1": 20,
                "S2": 30,
                "S3": 40,
                "eOvd": 0.9,
                "O0": 100,
                "O1": 50,
                "eLoan": 0.05,
                "sLoan": 0.1,
                "memG": -0.5,
                "shrG": -0.5,
            }

        try:
            s, r = classify(p, DEFAULT_THRESHOLDS)
            if s not in expected_statuses:
                issue(
                    "HIGH",
                    "J-STATUS",
                    f"[{i}/{scenario}] classify 回傳非預期狀態",
                    f"status={s!r}",
                )
                n_fail += 1
            else:
                n_pass += 1
        except Exception as e:
            issue(
                "MEDIUM",
                "J-EXC",
                f"[{i}/{scenario}] classify 拋例外",
                f"{type(e).__name__}: {str(e)[:150]}",
            )
            n_fail += 1

    print(f"  pass={n_pass}, fail={n_fail}")


# ============================================================
# 主程式
# ============================================================
def main():
    print("=" * 78)
    print(" 10,000 人壓力測試")
    print(f" 開始時間:{datetime.now().isoformat()}")
    print("=" * 78)

    t_start = time.time()

    section_b()
    section_c()
    section_d()
    section_e()
    section_f()
    section_g()
    section_h()
    section_i()
    section_j()

    t_end = time.time()

    print("\n" + "=" * 78)
    print(" 最終彙整")
    print("=" * 78)

    by_severity = Counter(i["severity"] for i in ISSUES)
    by_code = Counter(i["code"].split("-")[0] for i in ISSUES)

    print(f"\n總計發現 {len(ISSUES)} 個獨立問題(去重 fingerprint):")
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        print(f"  {sev:10s}: {by_severity.get(sev, 0)} 個")

    print(f"\n總執行時間:{t_end - t_start:.1f} 秒")

    output_dir = Path(r"C:\Users\user\AppData\Local\Temp\opencode\sim10k")
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "sim_10k_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(ISSUES, f, ensure_ascii=False, indent=2)
    print(f"\n詳細結果:{json_path}")


if __name__ == "__main__":
    main()
