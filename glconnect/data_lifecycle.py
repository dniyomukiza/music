"""Environment-specific data deletion policy.

Testing environments may purge synthetic commerce data. Live environments
must preserve financial and entitlement records and use archive/anonymization.
Set DATA_LIFECYCLE_MODE=live before launch.
"""

import os


def data_lifecycle_mode() -> str:
    value = (os.getenv("DATA_LIFECYCLE_MODE") or "testing").strip().lower()
    return "live" if value in {"live", "production", "prod"} else "testing"


def is_live_data_mode() -> bool:
    return data_lifecycle_mode() == "live"
