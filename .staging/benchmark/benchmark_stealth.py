"""SannySoft anti-bot benchmark for PlayStealth.

Loads https://bot.sannysoft.com inside a Playwright chromium context and
counts how many of the well-known detection probes pass. Writes a JSON
artifact to `stealth-score.json` that CI uploads, and exits non-zero if
the score drops below `--min-pass`.

Why SannySoft: it's the de-facto smoke test for stealth claims since
2019, costs nothing, runs in under a minute, and gives a single integer
score that compares cleanly across runs. CreepJS is the deeper test we
add later as a separate workflow.

Usage (locally):
    python scripts/benchmark_stealth.py --headless --min-pass 18

In CI it runs without --min-pass on PRs (informational), and with the
threshold on main and on the nightly schedule.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

URL = "https://bot.sannysoft.com/"


async def collect_results(headless: bool) -> dict:
    """Open the SannySoft page and read the result table.

    The page paints rows with class 'passed' (green) or 'failed' (red)
    inside two tables (sequential and 'old' tests). We count both.
    """
    # Import lazily so the script remains importable in environments
    # without playwright (e.g. for `--help`).
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(URL, wait_until="networkidle", timeout=60_000)
        # Give the slow async probes a moment to finish.
        await page.wait_for_timeout(2_500)

        result = await page.evaluate(
            """
            () => {
              const rows = Array.from(document.querySelectorAll('table tr'));
              const items = [];
              for (const row of rows) {
                const tds = row.querySelectorAll('td');
                if (tds.length < 2) continue;
                const name = (tds[0].innerText || '').trim();
                const valueCell = tds[tds.length - 1];
                const cls = valueCell.className || '';
                const text = (valueCell.innerText || '').trim();
                let status = 'unknown';
                if (cls.includes('passed') || cls.includes('result-passed')) status = 'pass';
                else if (cls.includes('failed') || cls.includes('result-failed')) status = 'fail';
                else if (text.toLowerCase().includes('passed')) status = 'pass';
                else if (text.toLowerCase().includes('failed')) status = 'fail';
                items.push({ name, value: text, status });
              }
              return items;
            }
            """
        )
        await browser.close()
        return {
            "url": URL,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "items": result,
        }


def summarize(report: dict) -> dict:
    items = report["items"]
    passed = sum(1 for x in items if x["status"] == "pass")
    failed = sum(1 for x in items if x["status"] == "fail")
    other = sum(1 for x in items if x["status"] not in ("pass", "fail"))
    total = len(items)
    return {
        **report,
        "passed": passed,
        "failed": failed,
        "other": other,
        "total": total,
        "score_percent": round(100.0 * passed / total, 1) if total else 0.0,
    }


def print_human(report: dict) -> None:
    print("=" * 60)
    print("PlayStealth — SannySoft benchmark")
    print(f"  URL:       {report['url']}")
    print(f"  Timestamp: {report['timestamp']}")
    print(f"  Passed:    {report['passed']}/{report['total']}  "
          f"({report['score_percent']}%)")
    print(f"  Failed:    {report['failed']}")
    print(f"  Other:     {report['other']}")
    print("-" * 60)
    for item in report["items"]:
        status = item["status"][:4].ljust(4)
        name = item["name"][:38].ljust(38)
        value = item["value"][:18]
        print(f"  [{status}] {name} {value}")
    print("=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(description="SannySoft anti-bot benchmark")
    parser.add_argument("--headless", action="store_true", default=True,
                        help="Run headless (default in CI)")
    parser.add_argument("--no-headless", dest="headless", action="store_false",
                        help="Run with a visible browser (debugging)")
    parser.add_argument("--out", type=Path, default=Path("stealth-score.json"),
                        help="Write JSON report to this path")
    parser.add_argument("--min-pass", type=int, default=0,
                        help="Exit non-zero if passed_count < min-pass (0 = never fail)")
    args = parser.parse_args()

    raw = asyncio.run(collect_results(headless=args.headless))
    report = summarize(raw)

    args.out.write_text(json.dumps(report, indent=2))
    print_human(report)
    print(f"\nReport written to {args.out}")

    if args.min_pass and report["passed"] < args.min_pass:
        print(f"\nFAIL: passed={report['passed']} < min-pass={args.min_pass}",
              file=sys.stderr)
        return 1

    if report["total"] == 0:
        print("\nFAIL: scraper read zero rows from the page", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
