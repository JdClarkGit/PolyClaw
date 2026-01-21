#!/usr/bin/env python3
"""
Quick Extract - Pull up to N trades and save immediately.
Use this while the full sync is running to get partial data.

Usage:
    python quick_extract.py 0xWALLET --trades 100000
"""

import argparse
import requests
import json
import csv
import time
import sys
import os
from datetime import datetime
from typing import List, Dict, Set

DATA_API = "https://data-api.polymarket.com"
BATCH_SIZE = 1000
OUTPUT_DIR = "activity-exports"


def quick_extract(wallet: str, max_trades: int = 100000) -> Dict:
    """Pull trades up to max_trades limit."""

    print(f"\n📥 Quick Extract: {wallet[:10]}... (up to {max_trades:,} trades)")
    print("=" * 60)

    all_trades = []
    seen_keys: Set[tuple] = set()
    end_ts = None
    username = None
    batch_num = 0
    start_time = time.time()

    while len(all_trades) < max_trades:
        batch_num += 1

        params = {"user": wallet, "limit": BATCH_SIZE}
        if end_ts:
            params["end"] = end_ts

        try:
            response = requests.get(f"{DATA_API}/activity", params=params, timeout=30)
            response.raise_for_status()
            trades = response.json()
            if not isinstance(trades, list):
                break
        except Exception as e:
            print(f"\n⚠️  Error: {e}")
            break

        if not trades:
            break

        # Get username
        if not username and trades[0].get('name'):
            username = trades[0].get('name')
            print(f"👤 Username: {username}\n")

        # Process batch
        new_count = 0
        oldest_ts = float('inf')

        for t in trades:
            if len(all_trades) >= max_trades:
                break
            key = (t.get('transactionHash'), t.get('timestamp'), t.get('asset'))
            if key not in seen_keys:
                seen_keys.add(key)
                all_trades.append(t)
                new_count += 1

            ts = t.get('timestamp', 0)
            if ts and ts < oldest_ts:
                oldest_ts = ts

        # Progress
        elapsed = time.time() - start_time
        rate = len(all_trades) / elapsed if elapsed > 0 else 0

        if oldest_ts != float('inf'):
            oldest_date = datetime.fromtimestamp(oldest_ts).strftime('%Y-%m-%d %H:%M')
        else:
            oldest_date = "?"

        sys.stdout.write(
            f"\r   Batch {batch_num}: Total: {len(all_trades):,} / {max_trades:,} | "
            f"Rate: {rate:.0f}/sec | Oldest: {oldest_date}   "
        )
        sys.stdout.flush()

        if len(trades) < BATCH_SIZE or new_count == 0:
            break

        if oldest_ts != float('inf'):
            end_ts = oldest_ts
        else:
            break

        time.sleep(0.2)

    elapsed = time.time() - start_time
    all_trades.sort(key=lambda t: t.get('timestamp', 0), reverse=True)

    # Stats
    timestamps = [t.get('timestamp', 0) for t in all_trades if t.get('timestamp')]
    oldest = datetime.fromtimestamp(min(timestamps)).strftime('%Y-%m-%d %H:%M') if timestamps else 'Unknown'
    newest = datetime.fromtimestamp(max(timestamps)).strftime('%Y-%m-%d %H:%M') if timestamps else 'Unknown'
    buys = sum(1 for t in all_trades if t.get('side') == 'BUY')
    sells = sum(1 for t in all_trades if t.get('side') == 'SELL')
    volume = sum(t.get('usdcSize', 0) or 0 for t in all_trades)

    print(f"\n\n{'='*60}")
    print(f"✅ EXTRACTION COMPLETE")
    print(f"   📊 Trades: {len(all_trades):,}")
    print(f"   📈 Buys: {buys:,} | Sells: {sells:,}")
    print(f"   💰 Volume: ${volume:,.2f}")
    print(f"   📅 Range: {oldest} → {newest}")
    print(f"   ⏱️  Time: {elapsed:.1f}s")

    return {
        "wallet": wallet,
        "username": username,
        "extracted_at": datetime.now().isoformat(),
        "trade_count": len(all_trades),
        "stats": {
            "buys": buys,
            "sells": sells,
            "volume_usd": volume,
            "oldest_trade": oldest,
            "newest_trade": newest
        },
        "trades": all_trades
    }


def save_files(data: Dict, prefix: str):
    """Save to JSON and CSV."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # JSON
    json_file = f"{OUTPUT_DIR}/{prefix}-extract.json"
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)
    size_mb = os.path.getsize(json_file) / (1024 * 1024)
    print(f"   💾 JSON: {json_file} ({size_mb:.1f} MB)")

    # CSV
    csv_file = f"{OUTPUT_DIR}/{prefix}-extract.csv"
    trades = data.get('trades', [])
    if trades:
        fieldnames = ['timestamp', 'datetime', 'type', 'side', 'price', 'size',
                      'usdc_size', 'market_title', 'outcome', 'transaction_hash']
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for t in trades:
                ts = t.get('timestamp', 0)
                writer.writerow({
                    'timestamp': ts,
                    'datetime': datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S') if ts else '',
                    'type': t.get('type'),
                    'side': t.get('side'),
                    'price': t.get('price'),
                    'size': t.get('size'),
                    'usdc_size': t.get('usdcSize'),
                    'market_title': t.get('title'),
                    'outcome': t.get('outcome'),
                    'transaction_hash': t.get('transactionHash')
                })
        size_mb = os.path.getsize(csv_file) / (1024 * 1024)
        print(f"   💾 CSV: {csv_file} ({size_mb:.1f} MB)")


def main():
    parser = argparse.ArgumentParser(description="Quick extract trades")
    parser.add_argument("wallet", help="Wallet address")
    parser.add_argument("--trades", "-t", type=int, default=100000, help="Max trades to fetch")
    parser.add_argument("--output", "-o", help="Output filename prefix")

    args = parser.parse_args()

    data = quick_extract(args.wallet, args.trades)
    prefix = args.output or data.get('username') or args.wallet[:10]

    print(f"\n💾 Saving files...")
    save_files(data, prefix)
    print(f"\n✅ Done! Files saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
