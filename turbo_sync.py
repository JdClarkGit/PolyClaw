#!/usr/bin/env python3
"""
TURBO SQLite Sync - Optimized for millions of trades

Optimizations:
- 1000 trades per request (10x faster than 100)
- Async concurrent requests (5-10 parallel)
- Connection pooling
- Smart batching

Expected performance: ~10M trades in 30-60 minutes

Usage:
    python turbo_sync.py 0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d
"""

import asyncio
import aiohttp
import sqlite3
import json
import time
import sys
import os
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Configuration
DB_PATH = "activity-exports/polymarket.db"
DATA_API = "https://data-api.polymarket.com"
BATCH_SIZE = 1000  # Max allowed by API
MAX_CONCURRENT = 5  # Parallel requests
REQUESTS_PER_SECOND = 4.0  # Rate limit


class TurboSync:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn = None
        self.stats = {
            "requests": 0,
            "trades_fetched": 0,
            "trades_inserted": 0,
            "errors": 0
        }
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database."""
        os.makedirs(os.path.dirname(self.db_path) or '.', exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")  # Faster writes
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=10000")

        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                transaction_hash TEXT,
                type TEXT,
                side TEXT,
                price REAL,
                size REAL,
                usdc_size REAL,
                market_id TEXT,
                market_title TEXT,
                market_slug TEXT,
                outcome TEXT,
                outcome_index INTEGER,
                asset TEXT,
                raw_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(wallet, transaction_hash, timestamp, asset)
            );

            CREATE INDEX IF NOT EXISTS idx_trades_wallet ON trades(wallet);
            CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
            CREATE INDEX IF NOT EXISTS idx_trades_wallet_ts ON trades(wallet, timestamp DESC);

            CREATE TABLE IF NOT EXISTS sync_progress (
                wallet TEXT PRIMARY KEY,
                last_sync_at TEXT,
                newest_timestamp INTEGER,
                oldest_timestamp INTEGER,
                total_trades INTEGER DEFAULT 0,
                sync_status TEXT DEFAULT 'pending',
                last_offset INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS wallets (
                address TEXT PRIMARY KEY,
                username TEXT,
                first_seen TEXT,
                last_updated TEXT
            );
        """)
        self.conn.commit()

    async def _fetch_batch(
        self,
        session: aiohttp.ClientSession,
        wallet: str,
        offset: int,
        semaphore: asyncio.Semaphore,
        rate_limiter: asyncio.Lock
    ) -> tuple[int, List[Dict]]:
        """Fetch a single batch with rate limiting."""
        async with semaphore:
            async with rate_limiter:
                await asyncio.sleep(1.0 / REQUESTS_PER_SECOND)

            try:
                url = f"{DATA_API}/activity"
                params = {"user": wallet, "limit": BATCH_SIZE, "offset": offset}

                async with session.get(url, params=params, timeout=30) as response:
                    self.stats["requests"] += 1
                    if response.status == 200:
                        data = await response.json()
                        trades = data if isinstance(data, list) else []
                        return offset, trades
                    else:
                        self.stats["errors"] += 1
                        return offset, []
            except Exception as e:
                self.stats["errors"] += 1
                return offset, []

    def _insert_batch(self, wallet: str, trades: List[Dict]) -> int:
        """Insert trades into database."""
        if not trades:
            return 0

        cursor = self.conn.cursor()
        new_count = 0

        for trade in trades:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO trades (
                        wallet, timestamp, transaction_hash, type, side,
                        price, size, usdc_size, market_id, market_title,
                        market_slug, outcome, outcome_index, asset, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    wallet,
                    trade.get('timestamp'),
                    trade.get('transactionHash'),
                    trade.get('type'),
                    trade.get('side'),
                    trade.get('price'),
                    trade.get('size'),
                    trade.get('usdcSize'),
                    trade.get('conditionId'),
                    trade.get('title'),
                    trade.get('slug'),
                    trade.get('outcome'),
                    trade.get('outcomeIndex'),
                    trade.get('asset'),
                    json.dumps(trade)
                ))
                if cursor.rowcount > 0:
                    new_count += 1
            except sqlite3.Error:
                continue

        self.conn.commit()
        return new_count

    def _get_resume_offset(self, wallet: str) -> int:
        """Get offset to resume from."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT last_offset FROM sync_progress WHERE wallet = ?", (wallet,))
        row = cursor.fetchone()
        return row[0] if row else 0

    def _save_progress(self, wallet: str, offset: int, total: int, status: str = "syncing"):
        """Save sync progress."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO sync_progress (wallet, last_offset, total_trades, sync_status, last_sync_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(wallet) DO UPDATE SET
                last_offset = excluded.last_offset,
                total_trades = excluded.total_trades,
                sync_status = excluded.sync_status,
                last_sync_at = excluded.last_sync_at
        """, (wallet, offset, total, status, datetime.now(timezone.utc).isoformat()))
        self.conn.commit()

    def get_trade_count(self, wallet: str) -> int:
        """Get trade count for wallet."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM trades WHERE wallet = ?", (wallet,))
        return cursor.fetchone()[0]

    async def sync_wallet(self, wallet: str, full_sync: bool = False) -> Dict[str, Any]:
        """Sync all trades using async concurrent requests."""
        print(f"\n{'='*60}")
        print(f"⚡ TURBO SYNC: {wallet[:10]}...")
        print(f"{'='*60}")

        # Check for resume
        start_offset = 0 if full_sync else self._get_resume_offset(wallet)
        existing = self.get_trade_count(wallet)

        if existing > 0:
            print(f"📊 Existing trades: {existing:,}")
        if start_offset > 0:
            print(f"📍 Resuming from offset: {start_offset:,}")

        print(f"\n⏳ Starting turbo sync...")
        print(f"   Batch size: {BATCH_SIZE} | Concurrent: {MAX_CONCURRENT} | Rate: {REQUESTS_PER_SECOND}/sec\n")

        # Setup async
        semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        rate_limiter = asyncio.Lock()

        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=60)

        start_time = time.time()
        offset = start_offset
        total_new = 0
        username = None
        consecutive_empty = 0
        last_save_offset = offset

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            try:
                while True:
                    # Create batch of concurrent requests
                    tasks = []
                    for i in range(MAX_CONCURRENT):
                        batch_offset = offset + (i * BATCH_SIZE)
                        tasks.append(
                            self._fetch_batch(session, wallet, batch_offset, semaphore, rate_limiter)
                        )

                    # Execute concurrently
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Process results
                    got_data = False
                    for result in results:
                        if isinstance(result, Exception):
                            continue
                        batch_offset, trades = result
                        if trades:
                            got_data = True
                            consecutive_empty = 0
                            self.stats["trades_fetched"] += len(trades)

                            # Get username
                            if not username and trades[0].get('name'):
                                username = trades[0].get('name')
                                print(f"   👤 Username: {username}")

                            # Insert
                            new = self._insert_batch(wallet, trades)
                            total_new += new
                            self.stats["trades_inserted"] += new

                    if not got_data:
                        consecutive_empty += 1
                        if consecutive_empty >= 2:
                            print(f"\n   ✅ Reached end of data")
                            break

                    offset += MAX_CONCURRENT * BATCH_SIZE

                    # Progress
                    elapsed = time.time() - start_time
                    rate = self.stats["trades_fetched"] / elapsed if elapsed > 0 else 0
                    total_in_db = existing + total_new

                    sys.stdout.write(
                        f"\r   📥 Fetched: {self.stats['trades_fetched']:,} | "
                        f"New: {total_new:,} | "
                        f"Total: {total_in_db:,} | "
                        f"Rate: {rate:.0f}/sec | "
                        f"Reqs: {self.stats['requests']}   "
                    )
                    sys.stdout.flush()

                    # Save progress every 50k trades
                    if offset - last_save_offset >= 50000:
                        self._save_progress(wallet, offset, total_in_db)
                        last_save_offset = offset

            except KeyboardInterrupt:
                print(f"\n\n⚠️  Interrupted! Saving progress at offset {offset}...")
                total_in_db = self.get_trade_count(wallet)
                self._save_progress(wallet, offset, total_in_db, "interrupted")
                return {"status": "interrupted", "offset": offset, "total": total_in_db}

        # Final stats
        elapsed = time.time() - start_time
        total_in_db = self.get_trade_count(wallet)
        self._save_progress(wallet, 0, total_in_db, "complete")

        print(f"\n\n{'='*60}")
        print(f"✅ TURBO SYNC COMPLETE")
        print(f"{'='*60}")
        print(f"   👤 Username: {username or 'Unknown'}")
        print(f"   📊 Total trades in DB: {total_in_db:,}")
        print(f"   🆕 New trades added: {total_new:,}")
        print(f"   ⏱️  Time: {elapsed/60:.1f} minutes ({elapsed:.0f} seconds)")
        print(f"   🚀 Rate: {self.stats['trades_fetched']/elapsed:.0f} trades/sec")
        print(f"   📡 API requests: {self.stats['requests']}")
        print(f"   💾 Database: {self.db_path}")

        return {
            "status": "complete",
            "total": total_in_db,
            "new": total_new,
            "elapsed": elapsed
        }

    def close(self):
        if self.conn:
            self.conn.close()


async def main():
    parser = argparse.ArgumentParser(description="Turbo sync Polymarket wallet")
    parser.add_argument("wallet", help="Wallet address")
    parser.add_argument("--full", action="store_true", help="Force full resync")
    parser.add_argument("--db", default=DB_PATH, help="Database path")

    args = parser.parse_args()

    syncer = TurboSync(args.db)
    try:
        await syncer.sync_wallet(args.wallet, full_sync=args.full)
    finally:
        syncer.close()


if __name__ == "__main__":
    asyncio.run(main())
