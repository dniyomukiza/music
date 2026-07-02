#!/usr/bin/env python3
"""Security regressions for the XAI radio research dev endpoint."""

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from flask import Flask
    from glconnect.xai_radio_research import register_xai_radio_research

    secret = "test-radio-research-secret"
    os.environ["ENABLE_XAI_RADIO_RESEARCH"] = "1"
    os.environ["XAI_RADIO_RESEARCH_SECRET"] = secret

    app = Flask(__name__)
    register_xai_radio_research(app)

    with app.test_client() as client:
        response = client.get("/api/dev/xai-radio-research/?format=html")

    body = response.get_data(as_text=True)
    failures = []

    if response.status_code != 200:
        failures.append(f"expected HTML page status 200, got {response.status_code}")
    if secret in body:
        failures.append("dev page leaked XAI_RADIO_RESEARCH_SECRET into HTML")
    if 'id="researchSecret"' not in body:
        failures.append("dev page should keep an operator-entered research secret field")

    if failures:
        print("FAILURES:")
        for failure in failures:
            print(" -", failure)
        sys.exit(1)

    print("OK: XAI radio research page does not expose the server secret")


if __name__ == "__main__":
    main()
