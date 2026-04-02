#!/usr/bin/env python3
"""
Execute a .sql file against PostgreSQL using DATABASE_URL from the environment.
Splits on ';' boundaries (migration files here use one statement per ALTER/CREATE line or
multi-line CREATE ... );).

Usage:
  export DATABASE_URL='postgresql://...'
  python sql_migration_runner.py add_campaign_fund_release.sql
  python sql_migration_runner.py add_accountability_columns.sql
"""

from __future__ import annotations

import os
import sys


def _statement_blocks(sql: str) -> list[str]:
    """Return executable SQL statements (trimmed, with trailing ';')."""
    parts: list[str] = []
    for raw in sql.split(";"):
        block = raw.strip()
        if not block:
            continue
        lines = []
        for line in block.splitlines():
            stripped = line.strip()
            if stripped.startswith("--"):
                continue
            if stripped:
                lines.append(line)
        stmt = "\n".join(lines).strip()
        if stmt:
            parts.append(stmt + ";")
    return parts


def run_sql_file(path: str, database_url: str | None = None) -> bool:
    database_url = database_url or os.environ.get("DATABASE_URL")
    if not database_url:
        print("❌ Set DATABASE_URL (e.g. postgresql://user:pass@host:5432/dbname)", file=sys.stderr)
        return False
    try:
        import psycopg2
    except ImportError:
        print("❌ Install psycopg2: pip install psycopg2-binary", file=sys.stderr)
        return False

    if not os.path.isfile(path):
        print(f"❌ File not found: {path}", file=sys.stderr)
        return False

    with open(path, encoding="utf-8") as f:
        sql = f.read()

    statements = _statement_blocks(sql)
    if not statements:
        print("❌ No statements found in file.", file=sys.stderr)
        return False

    print(f"Connecting (host from URL)…")
    print(f"Running {len(statements)} statement(s) from {path!r}…")
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cur = conn.cursor()
        for i, stmt in enumerate(statements, 1):
            short = stmt.replace("\n", " ")[:120]
            if len(stmt) > 120:
                short += "…"
            print(f"  [{i}/{len(statements)}] {short}")
            cur.execute(stmt)
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ {e}", file=sys.stderr)
        return False

    print("✅ Done.")
    return True


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    path = sys.argv[1]
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    return 0 if run_sql_file(path) else 1


if __name__ == "__main__":
    sys.exit(main())
