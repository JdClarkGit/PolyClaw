#!/usr/bin/env python3
"""
Full Historical Sync - Get ALL trades for any Polymarket wallet.

Uses timestamp-based backward pagination to fetch complete trade history.

Usage:
    python full_sync.py 0xWALLET_ADDRESS
    python full_sync.py 0xWALLET_ADDRESS --output gabagool22
"""

import argparse
import requests
import json
import csv
import time
import sys
import os
from datetime import datetime
from typing import List, Dict, Set, Optional

DATA_API = "https://data-api.polymarket.com"
BATCH_SIZE = 1000
RATE_LIMIT = 0.3  # seconds between requests
OUTPUT_DIR = "activity-exports"


def fetch_batch(wallet: str, end_ts: Optional[int] = None) -> List[Dict]:
    """Fetch a batch of trades, optionally before a timestamp."""
    params = {"user": wallet, "limit": BATCH_SIZE}
    if end_ts:
        params["end"] = end_ts

    try:
        response = requests.get(f"{DATA_API}/activity", params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"\n⚠️  Error: {e}")
        return []


def save_checkpoint(wallet: str, username: str, all_trades: List[Dict], batch_num: int):
    """Save incremental checkpoint."""
    prefix = username or wallet[:10]
    checkpoint_file = f"{OUTPUT_DIR}/{prefix}-checkpoint.json"

    # Calculate quick stats
    timestamps = [t.get('timestamp', 0) for t in all_trades if t.get('timestamp')]
    oldest = datetime.fromtimestamp(min(timestamps)).strftime('%Y-%m-%d %H:%M') if timestamps else 'Unknown'
    newest = datetime.fromtimestamp(max(timestamps)).strftime('%Y-%m-%d %H:%M') if timestamps else 'Unknown'

    checkpoint = {
        "wallet": wallet,
        "username": username,
        "checkpoint_at": datetime.now().isoformat(),
        "trade_count": len(all_trades),
        "batches": batch_num,
        "oldest_trade": oldest,
        "newest_trade": newest,
        "status": "in_progress",
        "trades": sorted(all_trades, key=lambda t: t.get('timestamp', 0), reverse=True)
    }

    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint, f, indent=2)

    return checkpoint_file


def full_sync(wallet: str) -> Dict:
    """Pull complete trade history using backward pagination."""

    print(f"\n{'='*60}")
    print(f"📥 FULL SYNC: {wallet[:10]}...")
    print(f"{'='*60}")

    all_trades = []
    seen_keys: Set[tuple] = set()
    end_ts = None
    username = None
    batch_num = 0
    checkpoint_interval = 50  # Save every 50 batches (~35-40k trades)

    start_time = time.time()

    while True:
        batch_num += 1
        trades = fetch_batch(wallet, end_ts)

        if not trades:
            print(f"\n✅ No more data after batch {batch_num}")
            break

        # Get username from first batch
        if not username and trades[0].get('name'):
            username = trades[0].get('name')
            print(f"👤 Username: {username}\n")

        # Deduplicate and add new trades
        new_in_batch = 0
        oldest_ts = float('inf')

        for t in trades:
            # Unique key: tx hash + timestamp + asset
            key = (t.get('transactionHash'), t.get('timestamp'), t.get('asset'))
            if key not in seen_keys:
                seen_keys.add(key)
                all_trades.append(t)
                new_in_batch += 1

            ts = t.get('timestamp', 0)
            if ts and ts < oldest_ts:
                oldest_ts = ts

        # Progress
        elapsed = time.time() - start_time
        rate = len(all_trades) / elapsed if elapsed > 0 else 0

        # Format oldest timestamp as date
        if oldest_ts != float('inf'):
            oldest_date = datetime.fromtimestamp(oldest_ts).strftime('%Y-%m-%d %H:%M')
        else:
            oldest_date = "?"

        sys.stdout.write(
            f"\r   Batch {batch_num}: +{new_in_batch} new | "
            f"Total: {len(all_trades):,} | "
            f"Rate: {rate:.0f}/sec | "
            f"Oldest: {oldest_date}   "
        )
        sys.stdout.flush()

        # Check if we got fewer trades than requested (end of data)
        if len(trades) < BATCH_SIZE:
            print(f"\n✅ Reached end of history (batch had {len(trades)} < {BATCH_SIZE})")
            break

        # Check if no new trades (stuck)
        if new_in_batch == 0:
            print(f"\n✅ No new trades in batch, stopping")
            break

        # Set end_ts for next batch (go further back in time)
        if oldest_ts != float('inf'):
            end_ts = oldest_ts
        else:
            break

        # Rate limit
        time.sleep(RATE_LIMIT)

        # Save checkpoint periodically
        if batch_num % checkpoint_interval == 0:
            cp_file = save_checkpoint(wallet, username, all_trades, batch_num)
            print(f"\n   💾 Checkpoint saved: {len(all_trades):,} trades → {cp_file}")

    elapsed = time.time() - start_time

    # Sort by timestamp descending (most recent first)
    all_trades.sort(key=lambda t: t.get('timestamp', 0), reverse=True)

    # Calculate stats
    if all_trades:
        timestamps = [t.get('timestamp', 0) for t in all_trades if t.get('timestamp')]
        oldest = datetime.fromtimestamp(min(timestamps)).strftime('%Y-%m-%d %H:%M') if timestamps else 'Unknown'
        newest = datetime.fromtimestamp(max(timestamps)).strftime('%Y-%m-%d %H:%M') if timestamps else 'Unknown'
        buys = sum(1 for t in all_trades if t.get('side') == 'BUY')
        sells = sum(1 for t in all_trades if t.get('side') == 'SELL')
        volume = sum(t.get('usdcSize', 0) or 0 for t in all_trades)
    else:
        oldest = newest = 'Unknown'
        buys = sells = 0
        volume = 0

    print(f"\n\n{'='*60}")
    print(f"✅ SYNC COMPLETE")
    print(f"{'='*60}")
    print(f"   👤 Username: {username or 'Unknown'}")
    print(f"   📊 Total trades: {len(all_trades):,}")
    print(f"   📈 Buys: {buys:,} | Sells: {sells:,}")
    print(f"   💰 Volume: ${volume:,.2f}")
    print(f"   📅 Range: {oldest} → {newest}")
    print(f"   ⏱️  Time: {elapsed:.1f}s ({len(all_trades)/elapsed:.0f} trades/sec)")
    print(f"   📡 API batches: {batch_num}")

    return {
        "wallet": wallet,
        "username": username,
        "fetched_at": datetime.now().isoformat() + "Z",
        "trade_count": len(all_trades),
        "stats": {
            "buys": buys,
            "sells": sells,
            "volume_usd": volume,
            "oldest_trade": oldest,
            "newest_trade": newest,
            "sync_time_seconds": elapsed
        },
        "trades": all_trades
    }


def save_json(data: Dict, filepath: str):
    """Save to JSON."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"   💾 JSON: {filepath} ({size_mb:.1f} MB)")


def save_csv(data: Dict, filepath: str):
    """Save to CSV."""
    trades = data.get('trades', [])
    if not trades:
        return

    fieldnames = [
        'timestamp', 'datetime', 'type', 'side', 'price', 'size', 'usdc_size',
        'market_title', 'market_slug', 'outcome', 'outcome_index', 'transaction_hash', 'asset'
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
                'market_slug': t.get('slug'),
                'outcome': t.get('outcome'),
                'outcome_index': t.get('outcomeIndex'),
                'transaction_hash': t.get('transactionHash'),
                'asset': t.get('asset')
            })

    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"   💾 CSV: {filepath} ({size_mb:.1f} MB)")


def main():
    parser = argparse.ArgumentParser(description="Full historical sync for Polymarket wallet")
    parser.add_argument("wallet", help="Wallet address (0x...)")
    parser.add_argument("--output", "-o", help="Output filename prefix")

    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Full sync
    data = full_sync(args.wallet)

    # Output prefix
    prefix = args.output or data.get('username') or args.wallet[:10]

    # Save files
    print(f"\n💾 Saving files...")
    save_json(data, f"{OUTPUT_DIR}/{prefix}-full.json")
    save_csv(data, f"{OUTPUT_DIR}/{prefix}-full.csv")

    print(f"\n✅ Done! Files ready for analysis.")
    print(f"\n   Load in UI: http://localhost:8080")
    print(f"   Or analyze: {OUTPUT_DIR}/{prefix}-full.csv")


if __name__ == "__main__":
    main()
