"""
以真人視角跑過 5 個情境,記錄使用者實際看到的內容。
執行: python tests/manual_human_journey.py
"""
import sys
import io
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force UTF-8 stdout (Windows cp950 can't print emoji)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from streamlit.testing.v1 import AppTest


def section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def snapshot(label, at):
    print(f"\n>>> {label}")
    print(f"   [exception] 數: {len(at.exception)}")
    for e in at.exception:
        print(f"     !! {e.value}")
    print(f"   [info]      數: {len(at.info)}")
    for m in at.info:
        print(f"     - {m.value[:100]}")
    print(f"   [warning]   數: {len(at.warning)}")
    for m in at.warning:
        print(f"     - {m.value[:100]}")
    print(f"   [error]     數: {len(at.error)}")
    for m in at.error:
        print(f"     - {m.value[:100]}")
    print(f"   [success]   數: {len(at.success)}")
    for m in at.success:
        print(f"     - {m.value[:100]}")
    print(f"   [markdown]  數: {len(at.markdown)}")
    for i, m in enumerate(at.markdown[:5]):
        body = m.value.replace('\n', ' ')[:150]
        print(f"     [{i}] {body}")
    if len(at.markdown) > 5:
        print(f"     ... +{len(at.markdown) - 5} more")
    print(f"   [button]    數: {len(at.button)}")
    for b in at.button:
        print(f"     - {b.label}")
    print(f"   [text_input] 數: {len(at.text_input)}")
    for t in at.text_input:
        print(f"     - label='{t.label}'")


# ============================================================
# 情境 1: 未登入 + 無資料（首次訪客,直接訪問首頁）
# ============================================================
section("情境 1: 未登入 + 無資料（首次訪客）")
at = AppTest.from_file("app.py", default_timeout=30)
at.run()
snapshot("首頁,無 query params", at)


# ============================================================
# 情境 2: 已登入管理員 + 無資料
# ============================================================
section("情境 2: 已登入管理員 + 無資料")
at = AppTest.from_file("app.py", default_timeout=30)
at.session_state["logged_in"] = True
at.session_state["role"] = "admin"
at.session_state["assigned_region"] = None
at.session_state["assigned_union"] = None
at.session_state["is_district_office"] = False
at.run()
snapshot("管理員登入後,還沒上傳", at)


# ============================================================
# 情境 3: 已登入個社 + 雲端連結失敗
# ============================================================
section("情境 3: 已登入個社 + 雲端連結失敗")
at = AppTest.from_file("app.py", default_timeout=30)
at.query_params["file"] = "xl_nonexistent.xlsx"
at.session_state["logged_in"] = True
at.session_state["role"] = "viewer"
at.session_state["assigned_region"] = "北區"
at.session_state["assigned_union"] = "某社"
at.session_state["is_district_office"] = False
at.session_state["preload_err"] = (
    "Supabase 找不到 xl_nonexistent.xlsx,可能連結過期或檔案被刪除"
)
at.session_state["preloaded_data"] = None
at.session_state["preloaded_csv"] = None
at.run()
snapshot("個社訪客,雲端連結 404", at)


# ============================================================
# 情境 4: 個社訪客,看到登入頁（已登出但有分享連結）
# ============================================================
section("情境 4: 未登入 + 帶雲端分享連結（正常運作）")
at = AppTest.from_file("app.py", default_timeout=30)
at.query_params["file"] = "xl_test123.xlsx"
at.run()
snapshot("首訪客帶正確 query params", at)


print("\n" + "=" * 70)
print("  測試結束")
print("=" * 70)
