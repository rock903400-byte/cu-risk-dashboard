"""
Cloud Environment Probes
Simulates 100 different requests to the deployed Streamlit Cloud app
to detect crashes, XSS, and performance issues.

Usage: python tests/probe_cloud.py
"""

import requests
import time
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

# Target URL from AGENTS.md
BASE_URL = "https://cu-analysis-v1-vizgphhwjwmfkvrrktdjte.streamlit.app"
OUTPUT_FILE = Path(__file__).resolve().parent / "sim_cloud_results.json"


def generate_probes() -> List[Dict[str, Any]]:
    probes = []

    # 1. Valid Share Links (simulated IDs)
    for i in range(20):
        probes.append(
            {
                "id": f"C-VALID-{i}",
                "url": f"{BASE_URL}/?file=test_file_{i}",
                "expected": "Dashboard",
                "category": "Valid",
            }
        )

    # 2. XSS / Injection Payloads
    xss_payloads = [
        "<script>alert(1)</script>",
        "javascript:alert(1)",
        "\"'><img src=x onerror=alert(1)>",
        "%;-alert(1)",
        "../../etc/passwd",
        "{{ 7*7 }}",
        "SELECT * FROM users",
    ]
    for i, p in enumerate(xss_payloads):
        probes.append(
            {
                "id": f"C-XSS-{i}",
                "url": f"{BASE_URL}/?file={p}",
                "expected": "Filtered",
                "category": "Security",
            }
        )

    # 3. Edge Case Strings
    edge_cases = [
        "A" * 300,  # Long string (just over _MAX_PARAM_LEN=256 to test app guard)
        "😊🚀🔥",  # Emoji
        " ",  # Space
        "",  # Empty
        "0",  # Number
        "null",  # Null string
        "undefined",
        "\x00",  # Null byte
    ]
    for i, p in enumerate(edge_cases):
        probes.append(
            {
                "id": f"C-EDGE-{i}",
                "url": f"{BASE_URL}/?file={p}",
                "expected": "Handled",
                "category": "EdgeCase",
            }
        )

    # 4. Mixed Param Probes
    for i in range(10):
        probes.append(
            {
                "id": f"C-MIXED-{i}",
                "url": f"{BASE_URL}/?file=f{i}&csv=c{i}",
                "expected": "Dashboard",
                "category": "Mixed",
            }
        )

    # 5. Health Checks (Load simulation)
    for i in range(40):
        probes.append(
            {
                "id": f"C-HEALTH-{i}",
                "url": f"{BASE_URL}/?_=time{i}",  # Cache buster
                "expected": "Dashboard",
                "category": "Health",
            }
        )

    return probes


def run_probe(probe: Dict[str, Any]) -> Dict[str, Any]:
    t0 = time.time()
    try:
        # Use a realistic User-Agent
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        r = requests.get(
            probe["url"], headers=headers, timeout=15, allow_redirects=True
        )
        ms = (time.time() - t0) * 1000

        issues = []
        if r.status_code != 200:
            issues.append({"severity": "CRITICAL", "title": f"HTTP {r.status_code}"})

        text = r.text
        if (
            "Exception" in text
            or "Traceback" in text
            or "Internal Server Error" in text
        ):
            issues.append(
                {"severity": "CRITICAL", "title": "Cloud Crash / Stack Trace"}
            )

        if "streamlit" not in text.lower() and r.status_code == 200:
            issues.append({"severity": "HIGH", "title": "Non-Streamlit Response"})

        # Security: check if payload is reflected without encoding
        if probe["category"] in ("Security", "EdgeCase"):
            payload = (
                probe["url"].split("?file=", 1)[-1] if "?file=" in probe["url"] else ""
            )
            if payload and payload in text:
                issues.append({"severity": "HIGH", "title": "XSS Reflection"})

        return {
            "id": probe["id"],
            "url": probe["url"],
            "ms": ms,
            "status": r.status_code,
            "completed": len(issues) == 0,
            "issues": issues,
            "category": probe["category"],
        }
    except requests.Timeout:
        return {
            "id": probe["id"],
            "url": probe["url"],
            "ms": 15000,
            "status": 408,
            "completed": False,
            "issues": [{"severity": "HIGH", "title": "Timeout"}],
        }
    except Exception as e:
        return {
            "id": probe["id"],
            "url": probe["url"],
            "ms": 0,
            "status": 500,
            "completed": False,
            "issues": [{"severity": "CRITICAL", "title": str(e)}],
        }


def main():
    probes = generate_probes()
    print(f"Starting Cloud Probes: {len(probes)} requests...")

    results = []
    # max_workers=5 to avoid rate limiting
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_probe = {executor.submit(run_probe, p): p for p in probes}
        for i, future in enumerate(as_completed(future_to_probe), 1):
            res = future.result()
            results.append(res)
            sys.stdout.write(
                f"\r  Probe {i}/{len(probes)} done: {res['id']} ({res['status']})"
            )
            sys.stdout.flush()

    print("\n\nCloud Probe Summary:")
    total = len(results)
    completed = sum(1 for r in results if r["completed"])
    avg_ms = sum(r["ms"] for r in results) / total

    print(f"  Total: {total}")
    print(f"  Success: {completed}/{total} ({completed/total*100:.1f}%)")
    print(f"  Avg Response: {avg_ms:.1f}ms")

    # Save results
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "summary": {"total": total, "completed": completed, "avg_ms": avg_ms},
                "results": results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"Saved results to: {OUTPUT_FILE}")


if __name__ == "__main__":
    import sys

    main()
