#!/usr/bin/env python3
"""
Apply investment campaign milestone columns (fixes UndefinedColumn on Ink Studio dashboard).

Requires: DATABASE_URL in the environment (same as the Flask app).

This runs: add_campaign_fund_release.sql
"""

import os
import sys

from sql_migration_runner import run_sql_file

if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__))
    sql_path = os.path.join(root, "add_campaign_fund_release.sql")
    print("Ink Studio / InvestmentCampaign milestone migration")
    print("(author_first_draft_released_at, amounts, publication flags, payout_requests table)\n")
    ok = run_sql_file(sql_path)
    sys.exit(0 if ok else 1)
