#!/usr/bin/env python3
"""Unit tests for glconnect.password_reset_service helpers."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from glconnect.password_reset_service import mask_email, password_strength_error


def test_mask_email():
    assert mask_email("john@example.com") == "j**n@example.com"
    assert mask_email("a@b.co") == "*@b.co"
    assert "@" in mask_email("alice.smith@ndotonic.com")


def test_password_strength():
    assert password_strength_error("short1!") is not None
    assert password_strength_error("alllower1!") is not None
    assert password_strength_error("NoSpecial1") is not None
    assert password_strength_error("ValidPass1!") is None


def main():
    test_mask_email()
    test_password_strength()
    print("OK: password_reset_service tests passed")


if __name__ == "__main__":
    main()
