"""
Middleton Finance Suite
Script 04: Run SQL Analysis Queries

Executes 03_queries.sql against all three databases and prints
formatted results to console. Each query is labeled and separated
so output can be copied directly into finance commentary or reports.

Usage:
    python 04_run_queries.py

Prerequisites:
    Run 01_generate_and_load_data.py first to build the databases.
"""

import sqlite3
import re
import os
import pandas as pd

DB_DIR   = "databases"
SQL_FILE = "03_queries.sql"

# ── Display settings ───────────────────────────────────────────
pd.set_option("display.max_columns",  20)
pd.set_option("display.max_rows",     50)
pd.set_option("display.width",        120)
pd.set_option("display.float_format", "{:,.2f}".format)

# ── Map each SQL section to its database ──────────────────────
DB_MAP = {
    "SECTION 1": f"{DB_DIR}/pricing_rebates.db",
    "SECTION 2": f"{DB_DIR}/deal_pipeline.db",
    "SECTION 3": f"{DB_DIR}/channel_sales.db",
    "SECTION 4": None,   # cross-database — handled per block below
}

# Section 4 sub-queries map to specific databases
SECTION_4_DB = {
    "4A": f"{DB_DIR}/pricing_rebates.db",
    "4B": f"{DB_DIR}/deal_pipeline.db",
    "4C": f"{DB_DIR}/channel_sales.db",
}


def divider(char="─", width=72):
    return char * width


def run_query(db_path, sql, label):
    """Execute a single SQL statement and print a formatted result."""
    if not os.path.exists(db_path):
        print(f"  ✗ Database not found: {db_path}")
        print(f"    Run 01_generate_and_load_data.py first.\n")
        return

    try:
        conn = sqlite3.connect(db_path)
        df   = pd.read_sql(sql.strip(), conn)
        conn.close()
        print(f"\n{label}")
        print(divider())
        if df.empty:
            print("  (no rows returned)")
        else:
            print(df.to_string(index=False))
    except Exception as e:
        print(f"  ✗ Query failed: {e}")


def parse_sql_file(path):
    """
    Parse 03_queries.sql into a list of dicts:
        { "label": "1A. ...", "section": "SECTION 1", "sql": "SELECT ..." }
    """
    with open(path) as f:
        raw = f.read()

    # Split on query label comments like "-- 1A." or "-- 4C."
    pattern = re.compile(
        r"--\s+(\d[A-Z])\.\s+(.+?)\n(.*?)(?=--\s+\d[A-Z]\.|-- ─|$)",
        re.DOTALL
    )

    queries = []
    for match in pattern.finditer(raw):
        code    = match.group(1)          # e.g. "1A"
        title   = match.group(2).strip()  # e.g. "Discount rate actual vs. plan..."
        sql_raw = match.group(3).strip()

        # Strip inline comments from SQL body
        sql_clean = re.sub(r"--[^\n]*", "", sql_raw).strip()
        if not sql_clean:
            continue

        section = f"SECTION {code[0]}"
        queries.append({
            "code":    code,
            "label":   f"Query {code}: {title}",
            "section": section,
            "sql":     sql_clean,
        })

    return queries


def get_db_for_query(code, section):
    """Return the correct DB path for a given query code and section."""
    if section == "SECTION 4":
        return SECTION_4_DB.get(code)
    return DB_MAP.get(section)


def main():
    print("\n" + "=" * 72)
    print("  Middleton Finance Suite — SQL Analysis Runner")
    print("=" * 72)

    if not os.path.exists(SQL_FILE):
        print(f"\n✗ {SQL_FILE} not found. Make sure it's in the same directory.")
        return

    queries = parse_sql_file(SQL_FILE)
    if not queries:
        print("\n✗ No queries parsed from SQL file.")
        return

    print(f"\n  Found {len(queries)} queries across 4 sections.\n")

    current_section = None
    for q in queries:
        # Print section header when we enter a new section
        if q["section"] != current_section:
            current_section = q["section"]
            print(f"\n{'=' * 72}")
            section_labels = {
                "SECTION 1": "SECTION 1 — Pricing & Rebate Analysis      [pricing_rebates.db]",
                "SECTION 2": "SECTION 2 — Deal Pipeline & Approvals      [deal_pipeline.db]",
                "SECTION 3": "SECTION 3 — Channel Sales Performance      [channel_sales.db]",
                "SECTION 4": "SECTION 4 — Cross-Database Snapshots       [all three DBs]",
            }
            print(f"  {section_labels.get(current_section, current_section)}")
            print("=" * 72)

        db_path = get_db_for_query(q["code"], q["section"])
        if db_path is None:
            print(f"\n  Skipping {q['code']} — no database mapped.")
            continue

        run_query(db_path, q["sql"], q["label"])

    print(f"\n\n{'=' * 72}")
    print("  All queries complete.")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    main()
