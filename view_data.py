#!/usr/bin/env python3
"""Utility to view SQLite and MongoDB data for the Santa backend.

Run from the backend folder:
  python view_data.py

It prints table names and sample rows from the SQLite DB (santa_gambling.db)
and lists collections + sample docs from the MongoDB configured via
MONGO_URI / MONGO_DB env vars (defaults to mongodb://localhost:27017 and 'santa').
"""
import os
import sqlite3
import json
from pprint import pprint

try:
    from pymongo import MongoClient
except Exception:
    MongoClient = None


ROOT = os.path.dirname(__file__)
DB_PATH = os.path.join(ROOT, "santa_gambling.db")


def print_sqlite_overview(db_path=DB_PATH):
    print("\n--- SQLite overview ---\n")
    if not os.path.exists(db_path):
        print(f"SQLite DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [r[0] for r in cur.fetchall()]
    print("Tables:")
    for t in tables:
        print(" -", t)

    sample_tables = [t for t in ('user','users','deposit','deposits','transaction','transactions','withdrawal','withdrawals') if t in tables]
    for t in sample_tables:
        print(f"\nSample rows from table '{t}':")
        try:
            cur.execute(f"SELECT * FROM {t} LIMIT 5;")
            rows = cur.fetchall()
            for r in rows:
                print(r)
        except Exception as e:
            print("  (error reading rows)", e)

    conn.close()


def print_mongo_overview():
    print("\n--- MongoDB overview ---\n")
    if MongoClient is None:
        print("pymongo not installed. Install with: pip install pymongo")
        return

    MONGO_URI = os.getenv('MONGO_URI') or os.getenv('MONGO_URL') or 'mongodb://localhost:27017'
    MONGO_DB = os.getenv('MONGO_DB') or os.getenv('DB_NAME') or 'santa'

    print(f"Connecting to Mongo URI: {MONGO_URI}  DB: {MONGO_DB}")
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        # quick server check
        client.admin.command('ping')
    except Exception as e:
        print("Failed to connect to MongoDB:", e)
        return

    db = client[MONGO_DB]
    try:
        cols = db.list_collection_names()
    except Exception as e:
        print("Failed to list collections:", e)
        return

    print("Collections:")
    for c in cols:
        print(" -", c)

    # Show samples from likely collections
    candidates = ['balances', 'transactions', 'webhook_events', 'users']
    for c in candidates:
        if c in cols:
            print(f"\nSample docs from collection '{c}':")
            try:
                docs = list(db[c].find().limit(5))
                for d in docs:
                    # make BSON safe for printing
                    try:
                        print(json.dumps(d, default=str))
                    except Exception:
                        pprint(d)
            except Exception as e:
                print(" (error reading collection)", e)


if __name__ == '__main__':
    print_sqlite_overview()
    print_mongo_overview()
