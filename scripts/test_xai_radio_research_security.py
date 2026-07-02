#!/usr/bin/env python3
"""Security regressions for the XAI radio research dev endpoint."""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    secret = "test-radio-research-secret"
    content = (ROOT / "glconnect" / "xai_radio_research.py").read_text(encoding="utf-8")
    failures = []

    if "xai_research_secret" in content:
        failures.append("server secret should not be passed into the rendered dev page")
    if 'os.getenv("XAI_RADIO_RESEARCH_SECRET") or ""' in content:
        failures.append("dev page should not render XAI_RADIO_RESEARCH_SECRET")
    if "var secret = {{" in content:
        failures.append("client JavaScript should not initialize the header from a server template value")
    if secret in content:
        failures.append("test fixture secret should not appear in source")
    if 'id="researchSecret"' not in content:
        failures.append("dev page should keep an operator-entered research secret field")

    if failures:
        print("FAILURES:")
        for failure in failures:
            print(" -", failure)
        sys.exit(1)

    print("OK: XAI radio research page does not expose the server secret")


if __name__ == "__main__":
    main()
