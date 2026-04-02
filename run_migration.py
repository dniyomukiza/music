#!/usr/bin/env python3
"""
Run the accountability columns migration (add_accountability_columns.sql).

Requires: DATABASE_URL in the environment — never commit real credentials to this file.
"""

import os
import sys

from sql_migration_runner import run_sql_file

if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__))
    migration_file = os.path.join(root, "add_accountability_columns.sql")
    print("Accountability columns migration\n")
    success = run_sql_file(migration_file)
    if success:
        print("\nColumns / tables (see add_accountability_columns.sql) applied.")
        print("Restart the Flask app after running.")
    sys.exit(0 if success else 1)
