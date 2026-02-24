#!/usr/bin/env python3
"""
Simple trade fetcher - Input wallet address, get 100 recent trades as JSON.

Usage:
    python fetch_trades.py 0xWALLET_ADDRESS
    python fetch_trades.py 0xWALLET_ADDRESS --output myfile.json
    python fetch_trades.py 0xWALLET_ADDRESS --limit 50
"""

import argparse
import json
import sys
import requests
from datetime import datetime

DATA_API = "https://data-api.polymarket.com"

def fetch_recent_trades(wallet_address: str, limit: int = 100) -> dict:
    """Fetch the most recent trades for a wallet."""

    url = f"{DATA_API}/activity"
    params = {
        "user": wallet_address,
        "limit": limit
    }

    print(f"Fetching {limit} recent trades for {wallet_address[:10]}...")

    try:
        # Bypass any system proxy to connect directly to Polymarket API
        response = requests.get(url, params=params, timeout=30, proxies={"http": None, "https": None})
        response.raise_for_status()
        data = response.json()

        # Handle different response formats
        if isinstance(data, list):
            trades = data
        elif isinstance(data, dict) and 'history' in data:
            trades = data['history']
        elif isinstance(data, dict) and 'data' in data:
            trades = data['data']
        else:
            trades = data if isinstance(data, list) else []

        # Get username from first trade if available
        username = None
        if trades and isinstance(trades[0], dict):
            username = trades[0].get('name') or trades[0].get('pseudonym')

        return {
            "wallet": wallet_address,
            "username": username,
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "trade_count": len(trades),
            "trades": trades[:limit]
        }

    except requests.exceptions.RequestException as e:
        print(f"Error fetching trades: {e}")
        return {"wallet": wallet_address, "error": str(e), "trades": []}

def main():
    parser = argparse.ArgumentParser(description="Fetch recent trades for a Polymarket wallet")
    parser.add_argument("wallet", help="Wallet address (0x...)")
    parser.add_argument("--limit", "-n", type=int, default=100, help="Number of trades (default: 100)")
    parser.add_argument("--output", "-o", help="Output filename (default: {wallet}-trades.json)")

    args = parser.parse_args()

    # Fetch trades
    result = fetch_recent_trades(args.wallet, args.limit)

    # Determine output filename
    if args.output:
        output_file = args.output
    else:
        short_wallet = args.wallet[:10]
        output_file = f"activity-exports/{short_wallet}-trades.json"

    # Save to file
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\n✅ Saved {result['trade_count']} trades to: {output_file}")
    if result.get('username'):
        print(f"   Username: {result['username']}")
    print(f"   Wallet: {result['wallet']}")

    # Show sample
    if result['trades']:
        print(f"\n📊 Most recent trade:")
        t = result['trades'][0]
        print(f"   {t.get('side', '?')} {t.get('size', '?')} @ ${t.get('price', '?')} - {t.get('title', 'Unknown market')[:50]}")

if __name__ == "__main__":
    main()
