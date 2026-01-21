#!/usr/bin/env python3
"""
Quick Trade Puller - Get all available recent trades for any wallet.

Downloads ~3,500 most recent trades to JSON + CSV for analysis.

Usage:
    python pull_trades.py 0xWALLET_ADDRESS
    python pull_trades.py 0xWALLET_ADDRESS --output gabagool
"""

import argparse
import requests
import json
import csv
import time
import sys
from datetime import datetime

DATA_API = "https://data-api.polymarket.com"
BATCH_SIZE = 1000
RATE_LIMIT = 0.25  # seconds between requests


def pull_all_trades(wallet: str) -> dict:
    """Pull all available trades for a wallet."""

    print(f"\n⚡ Pulling trades for {wallet[:10]}...")

    all_trades = []
    offset = 0
    last_timestamps = set()
    username = None

    start_time = time.time()

    while True:
        # Fetch batch
        try:
            response = requests.get(
                f"{DATA_API}/activity",
                params={"user": wallet, "limit": BATCH_SIZE, "offset": offset},
                timeout=30
            )
            response.raise_for_status()
            trades = response.json()
        except Exception as e:
            print(f"\n❌ Error: {e}")
            break

        if not trades or not isinstance(trades, list):
            break

        # Check for duplicate data (API limit reached)
        current_timestamps = {(t.get('timestamp'), t.get('transactionHash')) for t in trades}
        if current_timestamps == last_timestamps:
            print(f"\n✅ Reached API limit at offset {offset}")
            break
        last_timestamps = current_timestamps

        # Get username
        if not username and trades[0].get('name'):
            username = trades[0].get('name')
            print(f"   👤 Found: {username}")

        all_trades.extend(trades)
        offset += BATCH_SIZE

        # Progress
        sys.stdout.write(f"\r   📥 Downloaded: {len(all_trades):,} trades...")
        sys.stdout.flush()

        # Rate limit
        time.sleep(RATE_LIMIT)

        # Safety limit
        if offset > 10000:
            print(f"\n✅ Reached safety limit")
            break

    elapsed = time.time() - start_time

    # Deduplicate by transaction hash + timestamp + asset
    seen = set()
    unique_trades = []
    for t in all_trades:
        key = (t.get('transactionHash'), t.get('timestamp'), t.get('asset'))
        if key not in seen:
            seen.add(key)
            unique_trades.append(t)

    print(f"\n\n📊 Results:")
    print(f"   Total fetched: {len(all_trades):,}")
    print(f"   Unique trades: {len(unique_trades):,}")
    print(f"   Time: {elapsed:.1f}s")

    return {
        "wallet": wallet,
        "username": username,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "trade_count": len(unique_trades),
        "trades": unique_trades
    }


def save_json(data: dict, filepath: str):
    """Save to JSON file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"   💾 JSON: {filepath}")


def save_csv(data: dict, filepath: str):
    """Save to CSV file."""
    trades = data.get('trades', [])
    if not trades:
        return

    fieldnames = [
        'timestamp', 'datetime', 'type', 'side', 'price', 'size', 'usdc_size',
        'market_title', 'outcome', 'transaction_hash'
    ]

    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for t in trades:
            ts = t.get('timestamp', 0)
            dt = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S') if ts else ''

            writer.writerow({
                'timestamp': ts,
                'datetime': dt,
                'type': t.get('type'),
                'side': t.get('side'),
                'price': t.get('price'),
                'size': t.get('size'),
                'usdc_size': t.get('usdcSize'),
                'market_title': t.get('title'),
                'outcome': t.get('outcome'),
                'transaction_hash': t.get('transactionHash')
            })

    print(f"   💾 CSV: {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Pull all recent trades for a Polymarket wallet")
    parser.add_argument("wallet", help="Wallet address (0x...)")
    parser.add_argument("--output", "-o", help="Output filename prefix (default: wallet address)")

    args = parser.parse_args()

    # Pull trades
    data = pull_all_trades(args.wallet)

    # Determine output prefix
    prefix = args.output or args.wallet[:10]

    # Save files
    print(f"\n💾 Saving files...")
    save_json(data, f"activity-exports/{prefix}-trades.json")
    save_csv(data, f"activity-exports/{prefix}-trades.csv")

    # Summary
    if data['trades']:
        trades = data['trades']

        # Calculate stats
        buys = sum(1 for t in trades if t.get('side') == 'BUY')
        sells = sum(1 for t in trades if t.get('side') == 'SELL')
        volume = sum(t.get('usdcSize', 0) or 0 for t in trades)

        # Time range
        timestamps = [t.get('timestamp', 0) for t in trades if t.get('timestamp')]
        if timestamps:
            oldest = datetime.fromtimestamp(min(timestamps)).strftime('%Y-%m-%d %H:%M')
            newest = datetime.fromtimestamp(max(timestamps)).strftime('%Y-%m-%d %H:%M')
        else:
            oldest = newest = 'Unknown'

        print(f"\n📈 Quick Stats:")
        print(f"   Trades: {len(trades):,} ({buys:,} buys, {sells:,} sells)")
        print(f"   Volume: ${volume:,.2f}")
        print(f"   Range: {oldest} → {newest}")
        print(f"   Username: {data.get('username', 'Unknown')}")

    print(f"\n✅ Done! Files ready for analysis.")


if __name__ == "__main__":
    main()
