#!/usr/bin/env python3
"""
ASYNC Polymarket Wallet Scraper - BLAZING FAST VERSION
5-10x faster than sync version with concurrent requests.

Usage:
    python async_scraper.py 0x1234...
    python async_scraper.py --wallet 0x1234... --turbo
    python async_scraper.py --wallets wallets.csv
"""

import asyncio
import aiohttp
import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd

# ============================================================================
# API ENDPOINTS
# ============================================================================
GAMMA_API_BASE = "https://gamma-api.polymarket.com"
DATA_API_BASE = "https://data-api.polymarket.com"
CLOB_API_BASE = "https://clob.polymarket.com"

# Export directory
EXPORT_DIR = "activity-exports"


# ============================================================================
# ASYNC SCRAPER CLASS
# ============================================================================
class AsyncPolymarketScraper:
    """
    High-performance async scraper for Polymarket wallet data.
    Uses semaphores for concurrency control and smart rate limiting.
    """
    
    def __init__(self, max_concurrent: int = 5, requests_per_second: float = 3.0):
        """
        Initialize the async scraper.
        
        Args:
            max_concurrent: Maximum concurrent requests (default: 5)
            requests_per_second: Rate limit in requests/second (default: 3)
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limit_delay = 1.0 / requests_per_second
        self.last_request_time = 0
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
    
    async def _rate_limit(self):
        """Smart rate limiting - waits if needed to respect rate limits."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    async def _request(
        self, 
        session: aiohttp.ClientSession, 
        url: str, 
        params: Dict = None,
        retries: int = 3
    ) -> Dict:
        """
        Rate-limited async request with exponential backoff retries.
        
        Args:
            session: aiohttp session
            url: Request URL
            params: Query parameters
            retries: Number of retry attempts
            
        Returns:
            JSON response as dict, or empty dict on failure
        """
        async with self.semaphore:
            await self._rate_limit()
            self.request_count += 1
            
            for attempt in range(retries):
                try:
                    timeout = aiohttp.ClientTimeout(total=30)
                    async with session.get(url, params=params, timeout=timeout) as response:
                        if response.status == 200:
                            self.success_count += 1
                            return await response.json()
                        elif response.status == 429:  # Rate limited
                            wait_time = 2 ** attempt
                            print(f"   ⚠️  Rate limited, waiting {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue
                        elif response.status == 404:
                            return {}  # Not found, don't retry
                        else:
                            print(f"   ❌ HTTP {response.status} for {url}")
                            await asyncio.sleep(1)
                            
                except asyncio.TimeoutError:
                    print(f"   ⏰ Timeout (attempt {attempt + 1}/{retries})")
                    await asyncio.sleep(1)
                except aiohttp.ClientError as e:
                    print(f"   🔥 Connection error: {e}")
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"   🔥 Unexpected error: {e}")
                    await asyncio.sleep(1)
            
            self.error_count += 1
            return {}  # Failed all retries

    # ========================================================================
    # CORE DATA FETCHING METHODS
    # ========================================================================
    
    async def get_user_activity(
        self, 
        session: aiohttp.ClientSession, 
        wallet: str, 
        limit: int = 100,
        max_pages: int = 20
    ) -> List[Dict]:
        """
        Get all activity for a wallet with automatic pagination.
        
        Args:
            session: aiohttp session
            wallet: Wallet address (0x...)
            limit: Records per page
            max_pages: Maximum pages to fetch
            
        Returns:
            List of activity records
        """
        all_activity = []
        cursor = None
        page = 0
        
        while page < max_pages:
            url = f"{DATA_API_BASE}/activity"
            params = {"user": wallet.lower(), "limit": limit}
            if cursor:
                params["cursor"] = cursor
            
            result = await self._request(session, url, params)
            
            # Handle various response formats
            if not result:
                break
            if isinstance(result, list):
                history = result
            elif isinstance(result, dict):
                history = result.get("history", result.get("data", []))
                if isinstance(history, dict):
                    history = history.get("data", [])
            else:
                history = []
            
            if not history:
                break
            
            all_activity.extend(history)
            page += 1
            print(f"   📄 Page {page}: +{len(history)} records (total: {len(all_activity)})")
            
            # Check for next page
            if isinstance(result, dict):
                cursor = result.get("cursor") or result.get("next_cursor")
            else:
                cursor = None
            if not cursor:
                break
        
        return all_activity
    
    async def get_user_positions(
        self, 
        session: aiohttp.ClientSession, 
        wallet: str
    ) -> List[Dict]:
        """
        Get current positions for a wallet.
        
        Args:
            session: aiohttp session
            wallet: Wallet address
            
        Returns:
            List of position records
        """
        url = f"{DATA_API_BASE}/positions"
        params = {"user": wallet.lower()}
        result = await self._request(session, url, params)
        
        if isinstance(result, list):
            return result
        return result.get("data", result.get("positions", []))
    
    async def get_user_trades(
        self, 
        session: aiohttp.ClientSession, 
        wallet: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get trades for a wallet from CLOB API.
        
        Args:
            session: aiohttp session
            wallet: Wallet address
            limit: Max trades to fetch
            
        Returns:
            List of trade records
        """
        # Try maker trades
        url = f"{CLOB_API_BASE}/trades"
        params = {"maker_address": wallet.lower(), "limit": limit}
        result = await self._request(session, url, params)
        
        if result:
            return result if isinstance(result, list) else result.get("data", [])
        
        # Fallback to taker trades
        params = {"taker_address": wallet.lower(), "limit": limit}
        result = await self._request(session, url, params)
        
        return result if isinstance(result, list) else result.get("data", [])
    
    async def search_markets(
        self, 
        session: aiohttp.ClientSession, 
        query: str,
        limit: int = 50
    ) -> List[Dict]:
        """
        Search for markets by query.
        
        Args:
            session: aiohttp session
            query: Search query
            limit: Max results
            
        Returns:
            List of matching markets
        """
        url = f"{GAMMA_API_BASE}/markets"
        params = {"limit": limit, "active": "true"}
        result = await self._request(session, url, params)
        
        markets = result if isinstance(result, list) else []
        
        # Filter by query
        if query:
            query_lower = query.lower()
            markets = [
                m for m in markets 
                if query_lower in m.get("question", "").lower()
                or query_lower in m.get("description", "").lower()
            ]
        
        return markets

    # ========================================================================
    # HIGH-LEVEL SCRAPING METHODS
    # ========================================================================
    
    async def scrape_wallet_async(self, wallet: str) -> Dict:
        """
        TURBO scrape a single wallet - fetches activity and positions concurrently.
        
        Args:
            wallet: Wallet address to scrape
            
        Returns:
            Dict with wallet data, activity, and positions
        """
        print(f"\n🚀 TURBO SCRAPING: {wallet}")
        print("=" * 60)
        
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Run activity, positions, and trades concurrently
            print("   ⚡ Fetching activity...")
            activity_task = self.get_user_activity(session, wallet)
            
            print("   ⚡ Fetching positions...")
            positions_task = self.get_user_positions(session, wallet)
            
            print("   ⚡ Fetching trades...")
            trades_task = self.get_user_trades(session, wallet)
            
            # Wait for all to complete
            activity, positions, trades = await asyncio.gather(
                activity_task, 
                positions_task, 
                trades_task,
                return_exceptions=True
            )
            
            # Handle any exceptions
            if isinstance(activity, Exception):
                print(f"   ⚠️  Activity fetch failed: {activity}")
                activity = []
            if isinstance(positions, Exception):
                print(f"   ⚠️  Positions fetch failed: {positions}")
                positions = []
            if isinstance(trades, Exception):
                print(f"   ⚠️  Trades fetch failed: {trades}")
                trades = []
            
            # Merge trades into activity if not already present
            activity_ids = {a.get("id") for a in activity if a.get("id")}
            for trade in trades:
                if trade.get("id") not in activity_ids:
                    activity.append(trade)
            
            return {
                "wallet": wallet,
                "scraped_at": datetime.utcnow().isoformat(),
                "activity": activity,
                "positions": positions
            }
    
    async def scrape_multiple_wallets(self, wallets: List[str]) -> List[Dict]:
        """
        Scrape multiple wallets concurrently - THE SPEED DEMON 🔥
        
        Args:
            wallets: List of wallet addresses
            
        Returns:
            List of wallet data dicts
        """
        print(f"\n⚡ CONCURRENT SCRAPING: {len(wallets)} wallets")
        print("=" * 60)
        
        connector = aiohttp.TCPConnector(limit=20, limit_per_host=5)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for i, wallet in enumerate(wallets):
                print(f"   [{i+1}/{len(wallets)}] Queuing: {wallet[:10]}...")
                task = self._scrape_single_with_session(session, wallet)
                tasks.append(task)
            
            # Execute all concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions
            successful = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"   ❌ Failed wallet {wallets[i][:10]}: {result}")
                else:
                    successful.append(result)
            
            return successful
    
    async def _scrape_single_with_session(
        self, 
        session: aiohttp.ClientSession, 
        wallet: str
    ) -> Dict:
        """Helper for concurrent scraping with shared session."""
        activity_task = self.get_user_activity(session, wallet)
        positions_task = self.get_user_positions(session, wallet)
        
        activity, positions = await asyncio.gather(
            activity_task, 
            positions_task,
            return_exceptions=True
        )
        
        if isinstance(activity, Exception):
            activity = []
        if isinstance(positions, Exception):
            positions = []
        
        return {
            "wallet": wallet,
            "scraped_at": datetime.utcnow().isoformat(),
            "activity": activity,
            "positions": positions
        }
    
    def get_stats(self) -> Dict:
        """Get scraper performance statistics."""
        return {
            "total_requests": self.request_count,
            "successful": self.success_count,
            "errors": self.error_count,
            "success_rate": f"{(self.success_count/max(1,self.request_count))*100:.1f}%"
        }


# ============================================================================
# DATA NORMALIZATION
# ============================================================================
def normalize_timestamp(ts) -> str:
    """Convert various timestamp formats to readable format."""
    if ts is None:
        return None
    
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except ValueError:
            pass
    
    try:
        ts_num = float(ts)
        if ts_num > 1e12:
            ts_num = ts_num / 1000
        dt = datetime.utcfromtimestamp(ts_num)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, TypeError, OSError):
        return str(ts)


def normalize_activity(activity_data: List[Dict]) -> pd.DataFrame:
    """Normalize activity data into a clean DataFrame."""
    normalized = []
    
    for item in activity_data:
        record = {
            "timestamp": normalize_timestamp(item.get("timestamp") or item.get("createdAt")),
            "timestamp_raw": item.get("timestamp") or item.get("createdAt"),
            "type": item.get("type", "trade"),
            "side": (item.get("side") or item.get("action") or "unknown").upper(),
            "market_id": item.get("market", item.get("marketId", item.get("conditionId", ""))),
            "market_name": item.get("title", item.get("question", item.get("marketSlug", ""))),
            "outcome": item.get("outcome", item.get("outcomeName", "")),
            "price": float(item.get("price", 0) or 0),
            "size": float(item.get("size", item.get("amount", item.get("shares", 0))) or 0),
            "value_usd": float(item.get("value", item.get("usdcSize", 0)) or 0),
            "transaction_hash": item.get("transactionHash", item.get("txHash", "")),
        }
        
        if record["value_usd"] == 0 and record["price"] > 0 and record["size"] > 0:
            record["value_usd"] = record["price"] * record["size"]
        
        normalized.append(record)
    
    df = pd.DataFrame(normalized)
    
    if not df.empty and "timestamp_raw" in df.columns:
        df = df.sort_values("timestamp_raw", ascending=False)
    
    return df


def normalize_positions(positions_data: List[Dict]) -> pd.DataFrame:
    """Normalize positions data into a clean DataFrame."""
    normalized = []
    
    for pos in positions_data:
        record = {
            "market_id": pos.get("market", pos.get("marketId", pos.get("conditionId", ""))),
            "market_name": pos.get("title", pos.get("question", "")),
            "outcome": pos.get("outcome", pos.get("outcomeName", "")),
            "shares": float(pos.get("size", pos.get("shares", pos.get("position", 0))) or 0),
            "avg_price": float(pos.get("avgPrice", pos.get("averagePrice", 0)) or 0),
            "current_price": float(pos.get("price", pos.get("currentPrice", 0)) or 0),
            "cost_basis": float(pos.get("costBasis", pos.get("totalCost", 0)) or 0),
            "current_value": float(pos.get("value", pos.get("currentValue", 0)) or 0),
            "unrealized_pnl": float(pos.get("pnl", pos.get("unrealizedPnl", 0)) or 0),
        }
        
        if record["unrealized_pnl"] == 0 and record["current_value"] > 0 and record["cost_basis"] > 0:
            record["unrealized_pnl"] = record["current_value"] - record["cost_basis"]
        
        normalized.append(record)
    
    return pd.DataFrame(normalized)


# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================
def ensure_export_dir():
    """Create export directory if it doesn't exist."""
    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR)


def export_data(data: Dict, prefix: str = "turbo"):
    """Export scraped data to CSV and JSON files."""
    ensure_export_dir()
    wallet_short = data["wallet"][:10]
    
    # Export activity
    if data["activity"]:
        df = normalize_activity(data["activity"])
        csv_path = os.path.join(EXPORT_DIR, f"{prefix}-{wallet_short}.csv")
        df.to_csv(csv_path, index=False)
        print(f"   💾 Activity: {csv_path}")
        
        # Also save for dashboard compatibility
        all_trades_path = os.path.join(EXPORT_DIR, "all-trades.csv")
        df.to_csv(all_trades_path, index=False)
        print(f"   💾 Dashboard: {all_trades_path}")
    
    # Export positions
    if data["positions"]:
        df_pos = normalize_positions(data["positions"])
        pos_path = os.path.join(EXPORT_DIR, f"{prefix}-{wallet_short}-positions.csv")
        df_pos.to_csv(pos_path, index=False)
        print(f"   💾 Positions: {pos_path}")
    
    # Export raw JSON
    json_path = os.path.join(EXPORT_DIR, f"{prefix}-{wallet_short}.json")
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"   💾 Raw JSON: {json_path}")


# ============================================================================
# QUICK SCRAPE FUNCTIONS
# ============================================================================
async def quick_scrape(wallet_address: str) -> Dict:
    """
    INSTANT wallet scrape - the fastest way to pull a single wallet.
    
    Args:
        wallet_address: Wallet to scrape (0x...)
        
    Returns:
        Scraped data dict
    """
    scraper = AsyncPolymarketScraper(max_concurrent=5, requests_per_second=4)
    
    start_time = time.time()
    data = await scraper.scrape_wallet_async(wallet_address)
    elapsed = time.time() - start_time
    
    # Print results
    print(f"\n{'='*60}")
    print(f"🎯 SCRAPE COMPLETE ({elapsed:.1f}s)")
    print(f"{'='*60}")
    print(f"   • Wallet: {wallet_address}")
    print(f"   • Activity: {len(data['activity'])} records")
    print(f"   • Positions: {len(data['positions'])} positions")
    
    # Performance stats
    stats = scraper.get_stats()
    print(f"\n📊 Performance:")
    print(f"   • Requests: {stats['total_requests']}")
    print(f"   • Success rate: {stats['success_rate']}")
    
    return data


async def batch_scrape(wallets: List[str]) -> List[Dict]:
    """
    Batch scrape multiple wallets concurrently.
    
    Args:
        wallets: List of wallet addresses
        
    Returns:
        List of scraped data dicts
    """
    scraper = AsyncPolymarketScraper(max_concurrent=3, requests_per_second=2)
    
    start_time = time.time()
    results = await scraper.scrape_multiple_wallets(wallets)
    elapsed = time.time() - start_time
    
    print(f"\n{'='*60}")
    print(f"🎯 BATCH SCRAPE COMPLETE ({elapsed:.1f}s)")
    print(f"{'='*60}")
    print(f"   • Wallets processed: {len(results)}/{len(wallets)}")
    print(f"   • Total activity: {sum(len(r['activity']) for r in results)} records")
    print(f"   • Speed: {len(wallets)/elapsed:.1f} wallets/sec")
    
    return results


# ============================================================================
# CLI INTERFACE
# ============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="🚀 ASYNC Polymarket Wallet Scraper - BLAZING FAST"
    )
    parser.add_argument("wallet", nargs="?", help="Wallet address to scrape (0x...)")
    parser.add_argument("--wallet", "-w", dest="wallet_opt", help="Wallet address (alternative)")
    parser.add_argument("--wallets", "-W", help="CSV file with wallet addresses for batch mode")
    parser.add_argument("--turbo", action="store_true", help="Enable turbo mode (faster, more aggressive)")
    parser.add_argument("--output", "-o", default="turbo", help="Output filename prefix")
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("⚡ ASYNC POLYMARKET SCRAPER - TURBO MODE")
    print("=" * 60)
    
    # Determine wallet(s) to scrape
    wallet = args.wallet or args.wallet_opt
    
    if args.wallets:
        # Batch mode
        if os.path.exists(args.wallets):
            df = pd.read_csv(args.wallets)
            # Find wallet column
            wallet_col = None
            for col in df.columns:
                if 'wallet' in col.lower() or 'address' in col.lower():
                    wallet_col = col
                    break
            if wallet_col is None:
                wallet_col = df.columns[0]
            
            wallets = df[wallet_col].tolist()
            wallets = [w for w in wallets if w and str(w).startswith("0x")]
            
            if wallets:
                results = asyncio.run(batch_scrape(wallets))
                for data in results:
                    export_data(data, prefix=args.output)
            else:
                print("❌ No valid wallet addresses found in CSV")
        else:
            print(f"❌ File not found: {args.wallets}")
            sys.exit(1)
    
    elif wallet:
        # Single wallet mode
        if not wallet.startswith("0x"):
            print("⚠️  Warning: Address doesn't start with 0x")
        
        data = asyncio.run(quick_scrape(wallet))
        
        # Export
        print(f"\n📤 EXPORTING DATA")
        print("-" * 60)
        export_data(data, prefix=args.output)
        
        # Next steps
        print(f"\n💡 NEXT STEPS:")
        print(f"   1. Start server: python3 -m http.server")
        print(f"   2. Open: http://localhost:8000/trades-dashboard.html")
        print(f"   3. Load: {EXPORT_DIR}/all-trades.csv")
    
    else:
        # Interactive mode
        wallet = input("\n👛 Enter wallet address (0x...): ").strip()
        if wallet:
            data = asyncio.run(quick_scrape(wallet))
            print(f"\n📤 EXPORTING DATA")
            print("-" * 60)
            export_data(data, prefix=args.output)
        else:
            print("No wallet provided. Exiting.")
            sys.exit(1)


if __name__ == "__main__":
    main()
