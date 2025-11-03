#!/usr/bin/env python3
"""Simulate a Flutterwave webhook POST to the local server.

Generates a payload for a completed charge and signs it with the WEBHOOK_SECRET
from the environment, then POSTs it to /api/payments/webhook on localhost:8001 by default.

Usage:
  python webhook_simulator.py --tx-ref <tx_ref> --amount 500 --user-id 2 [--host http://localhost:8001]
If --flutter-id is omitted we generate a fake id.
"""
import argparse
import hmac
import hashlib
import json
import os
import requests
from datetime import datetime


WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")


def make_payload(tx_ref, flutter_id, amount, currency="UGX"):
    data = {
        "id": flutter_id,
        "tx_ref": tx_ref,
        "amount": amount,
        "currency": currency,
        "status": "successful",
        "created_at": datetime.utcnow().isoformat()
    }

    payload = {
        "event": "charge.completed",
        "data": data
    }
    return payload


def sign_body(body_text: str) -> str:
    if not WEBHOOK_SECRET:
        raise RuntimeError("WEBHOOK_SECRET not set in environment (.env)")
    sig = hmac.new(WEBHOOK_SECRET.encode(), body_text.encode(), hashlib.sha256).hexdigest()
    return sig


def post_webhook(url: str, payload: dict, signature: str):
    headers = {
        "Content-Type": "application/json",
        # Flutterwave sometimes uses 'verif-hash' or 'x-flutterwave-signature'
        "verif-hash": signature
    }
    r = requests.post(url, json=payload, headers=headers, timeout=15)
    return r


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tx-ref", required=True)
    parser.add_argument("--amount", type=float, default=0.0)
    parser.add_argument("--flutter-id", help="Optional flutterwave tx id to include")
    parser.add_argument("--host", default="http://localhost:8001", help="Host where backend is running")
    parser.add_argument("--currency", default="UGX")
    args = parser.parse_args()

    flutter_id = args.flutter_id or f"SIM_{int(datetime.utcnow().timestamp())}"
    payload = make_payload(args.tx_ref, flutter_id, args.amount, args.currency)
    body_text = json.dumps(payload)

    try:
        signature = sign_body(body_text)
    except RuntimeError as e:
        print("Error:", e)
        print("Set WEBHOOK_SECRET in your .env (or environment) before running this script.")
        return

    url = args.host.rstrip("/") + "/api/payments/webhook"
    print(f"Posting simulated webhook to: {url}\nPayload: {json.dumps(payload, indent=2)}\nSignature: {signature}")

    try:
        resp = post_webhook(url, payload, signature)
        print(f"Status: {resp.status_code}")
        try:
            print(resp.json())
        except Exception:
            print(resp.text)
    except Exception as e:
        print("Failed to post webhook:", e)


if __name__ == "__main__":
    main()
