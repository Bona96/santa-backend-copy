#!/usr/bin/env python3
"""Quick Mongo inspector for local development.

Usage:
  python view_mongo.py [--user-id ID]

This prints collection list, counts, and sample documents for key collections.
"""
import argparse
from db.mongo_client import get_mongo_db


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=int, help="Filter by user_id")
    args = parser.parse_args()

    db = get_mongo_db()
    print("Mongo DB:", db.name)

    # List collections
    cols = db.list_collection_names()
    print("Collections:", cols)

    # Show counts for relevant collections
    for c in ["balances", "transactions", "webhook_events"]:
        if c in cols:
            try:
                cnt = db[c].count_documents({})
            except Exception:
                cnt = "?"
            print(f"{c}: {cnt}")

    # If user_id provided, show their balance and transactions
    if args.user_id:
        uid = args.user_id
        print(f"\nBalances for user_id={uid}:")
        for doc in db.balances.find({"user_id": uid}).limit(10):
            print(doc)

        print(f"\nTransactions for user_id={uid} (latest 10):")
        for doc in db.transactions.find({"user_id": uid}).sort("created_at", -1).limit(10):
            print(doc)
    else:
        # Show some sample docs
        if "balances" in cols:
            print("\nSample balances:")
            for doc in db.balances.find().limit(5):
                print(doc)

        if "transactions" in cols:
            print("\nSample transactions:")
            for doc in db.transactions.find().sort("created_at", -1).limit(5):
                print(doc)


if __name__ == "__main__":
    main()
