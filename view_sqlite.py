#!/usr/bin/env python3
"""Quick SQLite inspector for local development.

Usage:
  python view_sqlite.py [--user-id ID] [--email EMAIL]

This prints table list, counts, and sample rows for key tables.
"""
import sqlite3
import argparse
from pathlib import Path


DB_PATH = Path(__file__).parent / "santa_gambling.db"


def list_tables(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    return [r[0] for r in cur.fetchall()]


def sample_rows(cur, table, limit=5, where=None):
    try:
        q = f"SELECT * FROM {table}"
        if where:
            q += f" WHERE {where}"
        q += f" LIMIT {limit};"
        cur.execute(q)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return cols, rows
    except Exception as e:
        return [], []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=int, help="Filter by user_id")
    parser.add_argument("--email", help="Filter by user email")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print("SQLite DB not found at:", DB_PATH)
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("Database:", DB_PATH)
    tables = list_tables(cur)
    print("Tables:", tables)

    # Show counts for key tables
    for t in ["users", "deposits", "transactions", "withdrawals"]:
        if t in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                cnt = cur.fetchone()[0]
            except Exception:
                cnt = "?"
            print(f"{t}: {cnt}")

    print("\n-- Sample data --")

    # User filter
    user_where = None
    if args.user_id:
        user_where = f"user_id = {args.user_id}"
    elif args.email:
        user_where = f"email = '{args.email}'"

    # Users
    if "users" in tables:
        cols, rows = sample_rows(cur, "users", limit=5, where=user_where)
        print("\nusers:")
        print(cols)
        for r in rows:
            print(dict(zip(cols, r)))

    # Deposits — show any recent or matching user deposits
    if "deposits" in tables:
        where = None
        if args.user_id:
            where = f"user_id = {args.user_id}"
        cols, rows = sample_rows(cur, "deposits", limit=10, where=where)
        print("\ndeposits:")
        print(cols)
        for r in rows:
            print(dict(zip(cols, r)))

    # Transactions
    if "transactions" in tables:
        where = None
        if args.user_id:
            where = f"user_id = {args.user_id}"
        cols, rows = sample_rows(cur, "transactions", limit=10, where=where)
        print("\ntransactions:")
        print(cols)
        for r in rows:
            print(dict(zip(cols, r)))

    conn.close()


if __name__ == "__main__":
    main()
