#!/usr/bin/env python3
"""Verify a Flutterwave transaction using the project's payment_service helper.

Usage:
  python verify_tx.py --identifier <tx_ref_or_id>

This calls flutterwave_service.verify_transaction_safe and prints the result.
"""
import argparse
import asyncio

from payment_service import flutterwave_service


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--identifier", required=True, help="Transaction id or tx_ref to verify")
    args = parser.parse_args()

    try:
        res = await flutterwave_service.verify_transaction_safe(args.identifier)
        print("Verify result:")
        print(res)
    except Exception as e:
        print("Error verifying transaction:", e)


if __name__ == "__main__":
    asyncio.run(main())
