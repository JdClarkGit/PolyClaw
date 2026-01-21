#!/usr/bin/env python3
"""
SQLite Incremental Wallet Sync for Polymarket

Efficiently pulls ALL trades for a wallet into SQLite with:
- Incremental sync (only fetches new trades)
- Resume capability (saves progress, can restart)
- Rate limiting (respects API limits)
- Progress tracking (shows ETA)

Usage:
    python sync_wallet.py 0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d
    python sync_wallet.py 0x6031b6eed1c97e853c6e0f03ad3ce3529351f96d --full   # Force full resync
"""

import argparse
import sqlite3
import requests
import time
import json
import os
import sys
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

# Configuration
DB_PATH = "activity-exports/polymarket.db"
DATA_API = "https://data-api.polymarket.com"
BATCH_SIZE = 100  # Max per API request
REQUESTS_PER_SECOND = 3.0
SAVE_PROGRESS_EVERY = 1000  # Save checkpoint every N trades


class WalletSync:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn = None
        self.request_count = 0
        self.last_request_time = 0
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with schema."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        # Create tables
        self.conn.executescript("""
            -- Main trades table
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

            -- Index for fast queries
            CREATE INDEX IF NOT EXISTS idx_trades_wallet ON trades(wallet);
            CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
            CREATE INDEX IF NOT EXISTS idx_trades_wallet_ts ON trades(wallet, timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_trades_market ON trades(market_id);

            -- Sync progress tracking
            CREATE TABLE IF NOT EXISTS sync_progress (
                wallet TEXT PRIMARY KEY,
                last_sync_at TEXT,
                newest_timestamp INTEGER,
                oldest_timestamp INTEGER,
                total_trades INTEGER DEFAULT 0,
                sync_status TEXT DEFAULT 'pending',
                last_offset INTEGER DEFAULT 0,
                error_message TEXT
            );

            -- Wallet metadata
            CREATE TABLE IF NOT EXISTS wallets (
                address TEXT PRIMARY KEY,
                username TEXT,
                first_seen TEXT,
                last_updated TEXT
            );
        """)
        self.conn.commit()

    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request_time
        min_interval = 1.0 / REQUESTS_PER_SECOND
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self.last_request_time = time.time()

    def _fetch_trades(self, wallet: str, limit: int = BATCH_SIZE, offset: int = 0) -> List[Dict]:
        """Fetch trades from API with rate limiting."""
        self._rate_limit()
        self.request_count += 1

        try:
            response = requests.get(
                f"{DATA_API}/activity",
                params={"user": wallet, "limit": limit, "offset": offset},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []
        except requests.exceptions.RequestException as e:
            print(f"\n⚠️  API error at offset {offset}: {e}")
            return []

    def _insert_trades(self, wallet: str, trades: List[Dict]) -> int:
        """Insert trades into database, returns count of new trades."""
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
            except sqlite3.Error as e:
                print(f"\n⚠️  DB error: {e}")
                continue

        self.conn.commit()
        return new_count

    def _get_progress(self, wallet: str) -> Optional[Dict]:
        """Get sync progress for wallet."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sync_progress WHERE wallet = ?", (wallet,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def _update_progress(self, wallet: str, **kwargs):
        """Update sync progress."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO sync_progress (wallet, last_sync_at)
            VALUES (?, ?)
            ON CONFLICT(wallet) DO UPDATE SET last_sync_at = excluded.last_sync_at
        """, (wallet, datetime.now(timezone.utc).isoformat()))

        if kwargs:
            updates = ", ".join(f"{k} = ?" for k in kwargs.keys())
            cursor.execute(
                f"UPDATE sync_progress SET {updates} WHERE wallet = ?",
                (*kwargs.values(), wallet)
            )
        self.conn.commit()

    def _update_wallet_meta(self, wallet: str, username: str = None):
        """Update wallet metadata."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO wallets (address, username, first_seen, last_updated)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(address) DO UPDATE SET
                username = COALESCE(excluded.username, wallets.username),
                last_updated = excluded.last_updated
        """, (wallet, username, datetime.now(timezone.utc).isoformat(),
              datetime.now(timezone.utc).isoformat()))
        self.conn.commit()

    def get_trade_count(self, wallet: str) -> int:
        """Get current trade count for wallet."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM trades WHERE wallet = ?", (wallet,))
        return cursor.fetchone()[0]

    def sync_wallet(self, wallet: str, full_sync: bool = False) -> Dict[str, Any]:
        """
        Sync all trades for a wallet.

        Args:
            wallet: Wallet address
            full_sync: If True, ignore progress and resync everything

        Returns:
            Dict with sync results
        """
        print(f"\n{'='*60}")
        print(f"🔄 SYNCING WALLET: {wallet[:10]}...")
        print(f"{'='*60}")

        # Check existing progress
        progress = self._get_progress(wallet)
        start_offset = 0

        if progress and not full_sync:
            start_offset = progress.get('last_offset', 0)
            existing_count = self.get_trade_count(wallet)
            print(f"📊 Existing trades in DB: {existing_count:,}")
            if start_offset > 0:
                print(f"📍 Resuming from offset: {start_offset:,}")

        # Start sync
        self._update_progress(wallet, sync_status='syncing')

        offset = start_offset
        total_new = 0
        total_fetched = 0
        username = None
        start_time = time.time()
        newest_ts = 0
        oldest_ts = float('inf')
        consecutive_empty = 0

        print(f"\n⏳ Fetching trades (this may take a while for large wallets)...\n")

        try:
            while True:
                trades = self._fetch_trades(wallet, BATCH_SIZE, offset)

                if not trades:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        print(f"\n✅ Reached end of data at offset {offset:,}")
                        break
                    offset += BATCH_SIZE
                    continue

                consecutive_empty = 0
                total_fetched += len(trades)

                # Extract username from first trade
                if not username and trades[0].get('name'):
                    username = trades[0].get('name')
                    self._update_wallet_meta(wallet, username)
                    print(f"👤 Username: {username}")

                # Track timestamp range
                for t in trades:
                    ts = t.get('timestamp', 0)
                    if ts > newest_ts:
                        newest_ts = ts
                    if ts < oldest_ts:
                        oldest_ts = ts

                # Insert trades
                new_count = self._insert_trades(wallet, trades)
                total_new += new_count

                # Progress display
                elapsed = time.time() - start_time
                rate = total_fetched / elapsed if elapsed > 0 else 0

                # Progress bar
                sys.stdout.write(f"\r   📥 Fetched: {total_fetched:,} | New: {total_new:,} | "
                               f"Rate: {rate:.0f}/sec | Offset: {offset:,}   ")
                sys.stdout.flush()

                # Save progress periodically
                if total_fetched % SAVE_PROGRESS_EVERY == 0:
                    self._update_progress(
                        wallet,
                        last_offset=offset,
                        total_trades=self.get_trade_count(wallet),
                        newest_timestamp=newest_ts,
                        oldest_timestamp=oldest_ts if oldest_ts != float('inf') else 0
                    )

                offset += BATCH_SIZE

                # Check if we got fewer than requested (end of data)
                if len(trades) < BATCH_SIZE:
                    print(f"\n✅ Reached end of data (got {len(trades)} < {BATCH_SIZE})")
                    break

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Interrupted! Saving progress...")
            self._update_progress(
                wallet,
                sync_status='interrupted',
                last_offset=offset,
                total_trades=self.get_trade_count(wallet)
            )
            return {
                "status": "interrupted",
                "trades_fetched": total_fetched,
                "new_trades": total_new,
                "resume_offset": offset
            }

        # Final update
        total_in_db = self.get_trade_count(wallet)
        elapsed = time.time() - start_time

        self._update_progress(
            wallet,
            sync_status='complete',
            last_offset=0,  # Reset for next incremental sync
            total_trades=total_in_db,
            newest_timestamp=newest_ts,
            oldest_timestamp=oldest_ts if oldest_ts != float('inf') else 0
        )

        # Summary
        print(f"\n\n{'='*60}")
        print(f"✅ SYNC COMPLETE")
        print(f"{'='*60}")
        print(f"   👤 Username: {username or 'Unknown'}")
        print(f"   📊 Total trades in DB: {total_in_db:,}")
        print(f"   🆕 New trades added: {total_new:,}")
        print(f"   ⏱️  Time elapsed: {elapsed/60:.1f} minutes")
        print(f"   🚀 Average rate: {total_fetched/elapsed:.0f} trades/sec")

        if newest_ts and oldest_ts != float('inf'):
            newest = datetime.fromtimestamp(newest_ts).strftime('%Y-%m-%d %H:%M')
            oldest = datetime.fromtimestamp(oldest_ts).strftime('%Y-%m-%d %H:%M')
            print(f"   📅 Date range: {oldest} → {newest}")

        print(f"\n   💾 Database: {self.db_path}")

        return {
            "status": "complete",
            "username": username,
            "total_in_db": total_in_db,
            "new_trades": total_new,
            "elapsed_seconds": elapsed,
            "date_range": {
                "oldest": oldest_ts if oldest_ts != float('inf') else None,
                "newest": newest_ts
            }
        }

    def get_stats(self, wallet: str) -> Dict:
        """Get statistics for a wallet."""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN side = 'BUY' THEN 1 ELSE 0 END) as buys,
                SUM(CASE WHEN side = 'SELL' THEN 1 ELSE 0 END) as sells,
                SUM(usdc_size) as total_volume,
                AVG(usdc_size) as avg_trade_size,
                COUNT(DISTINCT market_id) as unique_markets,
                MIN(timestamp) as first_trade,
                MAX(timestamp) as last_trade
            FROM trades WHERE wallet = ?
        """, (wallet,))

        row = cursor.fetchone()
        return dict(row) if row else {}

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def main():
    parser = argparse.ArgumentParser(description="Sync Polymarket wallet trades to SQLite")
    parser.add_argument("wallet", help="Wallet address (0x...)")
    parser.add_argument("--full", action="store_true", help="Force full resync (ignore progress)")
    parser.add_argument("--stats", action="store_true", help="Show stats only, don't sync")
    parser.add_argument("--db", default=DB_PATH, help=f"Database path (default: {DB_PATH})")

    args = parser.parse_args()

    syncer = WalletSync(args.db)

    try:
        if args.stats:
            stats = syncer.get_stats(args.wallet)
            if stats['total_trades']:
                print(f"\n📊 Stats for {args.wallet[:10]}...")
                print(f"   Total trades: {stats['total_trades']:,}")
                print(f"   Buys: {stats['buys']:,} | Sells: {stats['sells']:,}")
                print(f"   Total volume: ${stats['total_volume']:,.2f}")
                print(f"   Avg trade size: ${stats['avg_trade_size']:.2f}")
                print(f"   Unique markets: {stats['unique_markets']:,}")
            else:
                print(f"No data found for {args.wallet[:10]}...")
        else:
            syncer.sync_wallet(args.wallet, full_sync=args.full)
    finally:
        syncer.close()


if __name__ == "__main__":
    main()
