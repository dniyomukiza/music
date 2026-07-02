#!/usr/bin/env python3
"""Regression checks for JWT signing secret configuration."""

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def main():
    failures = []
    exposed_secret = "".join(("abara", "yon"))

    for relative_path in ("glconnect/__init__.py", "glconnect/pipeline.py"):
        content = _read(relative_path)
        if exposed_secret in content:
            failures.append(f"{relative_path} still contains the exposed JWT secret")

    pipeline_content = _read("glconnect/pipeline.py")
    if 'os.getenv("JWT_SECRET_KEY")' not in pipeline_content:
        failures.append("pipeline.py should load JWT_SECRET_KEY from the environment")

    app_content = _read("glconnect/__init__.py")
    if '"JWT_SECRET_KEY": (os.getenv("JWT_SECRET_KEY")' not in app_content:
        failures.append("__init__.py should load JWT_SECRET_KEY through the existing config path")
    if 'raise RuntimeError("JWT_SECRET_KEY is required in production.")' not in app_content:
        failures.append("__init__.py should fail closed when JWT_SECRET_KEY is missing in production")
    jwt_block = app_content[
        app_content.find("override_jwt_secret"):
        app_content.find("# Secure session cookie configuration")
    ]
    if "is_local_dev" in jwt_block or "/.dockerenv" in jwt_block:
        failures.append("JWT fallback should be limited to FLASK_ENV=development, not Docker detection")
    if "is_local_dev = os.getenv('FLASK_ENV') == 'development' or not os.path.exists('/.dockerenv')" in app_content:
        failures.append("session security mode should not treat every non-Docker host as local dev")

    if failures:
        print("FAILURES:")
        for failure in failures:
            print(" -", failure)
        sys.exit(1)

    print("OK: JWT secret configuration no longer uses the exposed signer")


if __name__ == "__main__":
    main()
