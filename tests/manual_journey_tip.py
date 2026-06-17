"""
完整測試 onboarding 模組的行為,包含首次提示、按鈕、CTA 渲染。
不依賴完整 app.py 的 session state,直接呼叫 onboarding 函式。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
from streamlit.testing.v1 import AppTest
from components import onboarding


def make_minimal_preloaded_data():
    """建立最小可用的 preloaded_data tuple,模擬 admin 有資料的狀態。"""
    df_m = pd.DataFrame(
        {
            "年月": [pd.Timestamp("2023-12-01")],
            "社號": ["001"],
            "社名": ["測試社"],
            "社員數": [1000],
            "股金": [50_000_000],
            "貸放比": [0.6],
            "儲蓄率": [0.85],
        }
    )
    df_l = pd.DataFrame(
        {
            "年月": [pd.Timestamp("2023-12-01")],
            "社號": ["001"],
            "社名": ["測試社"],
            "逾期貸款": [100_000],
            "逾放比": [0.005],
            "開支比": [0.95],
            "提撥率": [0.02],
        }
    )
    main = pd.DataFrame(
        [
            {
                "社號": "001",
                "社名": "測試社",
                "區域": "未分類",
                "診斷狀態": "📊 一般狀態",
                "建議留意事項": "各指標平穩",
                "現有社員": 1000,
                "社員成長數(12M)": 50,
                "社員成長率(12M)": 0.05,
                "現有股金": 50_000_000,
                "股金成長率(12M)": 0.05,
                "貸放比": 0.6,
                "儲蓄率": 0.85,
                "逾放比(12M)": 0.005,
                "逾放比": 0.005,
                "開支比": 0.95,
                "開支比(年)": 0.95,
                "提撥率": 0.02,
                "_sM": 950,
                "_sS": 47_000_000,
            }
        ]
    )
    region_map = {"測試社": "未分類"}
    region_pws = {"1234": {"name": "測試社", "region": "未分類"}}
    return (main, df_m, df_l, b"fake_bytes", region_map, region_pws)


def snapshot_quiet(at, label):
    """安靜版的 snapshot,只印關鍵數字。"""
    print(f"\n>>> {label}")
    print(
        f"  [exception] {len(at.exception)} | [error] {len(at.error)} | [warning] {len(at.warning)}"
    )
    print(
        f"  [markdown]  {len(at.markdown)} | [button] {len(at.button)} | [text_input] {len(at.text_input)}"
    )


# =========================================================================
# 場景 1: 未登入 → 登入頁
# =========================================================================
print("\n" + "=" * 70)
print("  場景 1: 未登入,看到什麼?")
print("=" * 70)
at = AppTest.from_file("app.py", default_timeout=30)
at.run()
snapshot_quiet(at, "首訪,無 query params")
# 預期: 0 error, 0 welcome, 只有登入頁

# =========================================================================
# 場景 2: 已登入 admin, 但沒資料 → 看到 welcome page
# =========================================================================
print("\n" + "=" * 70)
print("  場景 2: admin 登入但無資料,看到什麼?")
print("=" * 70)
at = AppTest.from_file("app.py", default_timeout=30)
at.session_state["logged_in"] = True
at.session_state["role"] = "admin"
at.session_state["is_district_office"] = False
at.run()
snapshot_quiet(at, "admin,無資料")

# 數數有幾個 step card / legend card
step_cards = sum(1 for m in at.markdown if "step-card" in m.value)
legend_cards = sum(1 for m in at.markdown if "legend-card" in m.value)
cta_boxes = sum(1 for m in at.markdown if "cta-box" in m.value)
print(f"  step cards: {step_cards} (預期 3)")
print(f"  legend cards: {legend_cards} (預期 5)")
print(f"  cta boxes: {cta_boxes} (預期 1)")

# =========================================================================
# 場景 3: 區會訪客, 雲端失敗
# =========================================================================
print("\n" + "=" * 70)
print("  場景 3: 區會訪客,雲端 404")
print("=" * 70)
at = AppTest.from_file("app.py", default_timeout=30)
at.query_params["file"] = "xl_xxx.xlsx"
at.session_state["logged_in"] = True
at.session_state["role"] = "viewer"
at.session_state["assigned_region"] = "中區"
at.session_state["assigned_union"] = None
at.session_state["is_district_office"] = True
at.session_state["preload_err"] = "找不到檔案"
at.session_state["preloaded_data"] = None
at.session_state["preloaded_csv"] = None
at.run()
snapshot_quiet(at, "區會訪客,雲端失敗")

# 預期: 1 error (雲端失敗) + welcome page 完整內容
ctas = [m.value for m in at.markdown if "cta-box" in m.value]
if ctas:
    is_district = "cta-viewer" in ctas[0] and "區會" in ctas[0]
    print(f"  CTA 內容判斷: {'✅ 區會專用 CTA' if is_district else '❌ 不是區會 CTA'}")

# =========================================================================
# 場景 4: admin + 有完整資料 + 第一次看到 (tip 未關)
# =========================================================================
print("\n" + "=" * 70)
print("  場景 4: admin + 有資料 + 第一次（tip 應出現）")
print("=" * 70)
data_tuple = make_minimal_preloaded_data()
at = AppTest.from_file("app.py", default_timeout=30)
at.session_state["logged_in"] = True
at.session_state["role"] = "admin"
at.session_state["is_district_office"] = False
at.session_state["preloaded_data"] = data_tuple[:5]
at.session_state["preloaded_csv"] = None
at.session_state["seen_color_tip"] = False
at.run()
snapshot_quiet(at, "admin,有資料,首次")
# 找 tip 按鈕
tip_buttons = [b for b in at.button if "知道了" in b.label or "不再顯示" in b.label]
print(f"  tip 按鈕數: {len(tip_buttons)} (預期 1)")
if tip_buttons:
    print(f"  ✅ 首次 tip 正確顯示,按鈕文字: '{tip_buttons[0].label}'")

# =========================================================================
# 場景 5: admin + 有資料 + 第二次（tip 應不出現）
# =========================================================================
print("\n" + "=" * 70)
print("  場景 5: admin + 有資料 + 第二次（tip 應不出現）")
print("=" * 70)
at = AppTest.from_file("app.py", default_timeout=30)
at.session_state["logged_in"] = True
at.session_state["role"] = "admin"
at.session_state["is_district_office"] = False
at.session_state["preloaded_data"] = data_tuple[:5]
at.session_state["preloaded_csv"] = None
at.session_state["seen_color_tip"] = True  # 已關
at.run()
snapshot_quiet(at, "admin,有資料,已關 tip")

tip_buttons = [b for b in at.button if "知道了" in b.label or "不再顯示" in b.label]
print(f"  tip 按鈕數: {len(tip_buttons)} (預期 0)")
if len(tip_buttons) == 0:
    print(f"  ✅ tip 已正確不再出現")

print("\n" + "=" * 70)
print("  測試結束")
print("=" * 70)
