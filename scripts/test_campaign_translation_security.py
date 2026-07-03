#!/usr/bin/env python3
"""Security regression checks for campaign translation rendering."""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    service = (ROOT / "glconnect" / "campaign_translation_service.py").read_text(encoding="utf-8")
    client = (
        ROOT
        / "glconnect"
        / "templates"
        / "book_platform"
        / "includes"
        / "_campaign_translate_script.html"
    ).read_text(encoding="utf-8")

    failures = []

    if "def _sanitize_translation_fields" not in service:
        failures.append("translation service should centralize translated field sanitization")
    if "bleach.clean(str(value or ''), tags=[], strip=True)" not in service:
        failures.append("plain translated fields should strip HTML")
    if "sanitize_project_description(raw, book_id=None)" not in service:
        failures.append("rich translated descriptions should reuse project description sanitization")
    if service.find("sanitized = _sanitize_translation_fields") > service.find("record = CampaignTranslation"):
        failures.append("translations should be sanitized before persistence")
    if "'translations': _translation_payload(record)" not in service:
        failures.append("JSON responses should return sanitized translation payloads")
    if "htmlFields" not in client or "el.textContent = value;" not in client:
        failures.append("client should render plain translated fields with textContent")
    if "el.innerHTML = value;" not in client:
        failures.append("client should preserve sanitized rich description rendering")

    if failures:
        print("FAILURES:")
        for failure in failures:
            print(" -", failure)
        sys.exit(1)

    print("OK: campaign translation output is sanitized before HTML rendering")


if __name__ == "__main__":
    main()
