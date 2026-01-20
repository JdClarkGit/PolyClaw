#!/usr/bin/env python3
"""
Polymarket Wallet Scraper
Scrapes trade history and positions from a specific wallet address.

Usage:
    python scrape_trades.py
    python scrape_trades.py --query "Bitcoin" --select all --user 0x... --limit 200
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from functools import wraps
from typing import Optional

import requests
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
# RATE LIMITING
# ============================================================================
def rate_limited(max_per_sec: float = 1.0):
    """Decorator to rate limit function calls."""
    min_interval = 1.0 / max_per_sec
    
    def decorator(fn):
        last_call = [0.0]
        
        @wraps(fn)
        def wrapped(*args, **kwargs):
            elapsed = time.time() - last_call[0]
            wait = min_interval - elapsed
            if wait > 0:
                time.sleep(wait)
            result = fn(*args, **kwargs)
            last_call[0] = time.time()
            return result
        return wrapped
    return decorator


# ============================================================================
# API FUNCTIONS
# ============================================================================
@rate_limited(2)
def search_markets(query: str, limit: int = 20) -> list:
    """Search for markets using the Gamma API."""
    url = f"{GAMMA_API_BASE}/markets"
    params = {
        "limit": limit,
        "active": "true",
        "closed": "false"
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        markets = response.json()
        
        # Filter by query if provided
        if query:
            query_lower = query.lower()
            markets = [m for m in markets if query_lower in m.get("question", "").lower() 
                      or query_lower in m.get("description", "").lower()]
        
        return markets
    except requests.RequestException as e:
        print(f"Error searching markets: {e}")
        return []


@rate_limited(2)
def get_market_by_id(market_id: str) -> Optional[dict]:
    """Get detailed market info by ID."""
    url = f"{GAMMA_API_BASE}/markets/{market_id}"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching market {market_id}: {e}")
        return None


@rate_limited(2)
def get_events(query: str = "", limit: int = 50) -> list:
    """Get events from Gamma API."""
    url = f"{GAMMA_API_BASE}/events"
    params = {"limit": limit, "active": "true"}
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        events = response.json()
        
        if query:
            query_lower = query.lower()
            events = [e for e in events if query_lower in e.get("title", "").lower()
                     or query_lower in e.get("description", "").lower()]
        
        return events
    except requests.RequestException as e:
        print(f"Error fetching events: {e}")
        return []


@rate_limited(1.5)
def get_user_activity(user_address: str, limit: int = 100, cursor: str = None) -> dict:
    """
    Get user trading activity from the Data API.
    Returns trades/activity for a specific wallet address.
    """
    url = f"{DATA_API_BASE}/activity"
    params = {
        "user": user_address.lower(),
        "limit": limit
    }
    if cursor:
        params["cursor"] = cursor
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching user activity: {e}")
        return {"history": [], "cursor": None}


@rate_limited(1.5)
def get_user_positions(user_address: str) -> list:
    """Get current positions for a user."""
    url = f"{DATA_API_BASE}/positions"
    params = {"user": user_address.lower()}
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching positions: {e}")
        return []


@rate_limited(1.5)
def get_user_trades(user_address: str, market_id: str = None, limit: int = 100) -> list:
    """Get trades for a user, optionally filtered by market."""
    url = f"{CLOB_API_BASE}/trades"
    params = {
        "maker_address": user_address.lower(),
        "limit": limit
    }
    if market_id:
        params["market"] = market_id
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        # Try alternate endpoint
        pass
    
    # Fallback to data API
    url = f"{DATA_API_BASE}/trades"
    params = {"user": user_address.lower(), "limit": limit}
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching trades: {e}")
        return []


# ============================================================================
# DATA NORMALIZATION
# ============================================================================
def normalize_timestamp(ts) -> str:
    """Convert various timestamp formats to ISO format."""
    if ts is None:
        return None
    
    # If already a string in ISO format
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except ValueError:
            pass
    
    # If Unix timestamp (seconds or milliseconds)
    try:
        ts_num = float(ts)
        # Check if milliseconds
        if ts_num > 1e12:
            ts_num = ts_num / 1000
        dt = datetime.utcfromtimestamp(ts_num)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, TypeError, OSError):
        return str(ts)


def normalize_activity(activity_data: list) -> pd.DataFrame:
    """Normalize activity data into a clean DataFrame."""
    normalized = []
    
    for item in activity_data:
        record = {
            "timestamp": normalize_timestamp(item.get("timestamp") or item.get("createdAt")),
            "timestamp_raw": item.get("timestamp") or item.get("createdAt"),
            "type": item.get("type", "trade"),
            "side": item.get("side", item.get("action", "unknown")).upper(),
            "market_id": item.get("market", item.get("marketId", item.get("conditionId", ""))),
            "market_name": item.get("title", item.get("question", item.get("marketSlug", ""))),
            "outcome": item.get("outcome", item.get("outcomeName", "")),
            "price": float(item.get("price", 0) or 0),
            "size": float(item.get("size", item.get("amount", item.get("shares", 0))) or 0),
            "value_usd": float(item.get("value", item.get("usdcSize", 0)) or 0),
            "transaction_hash": item.get("transactionHash", item.get("txHash", "")),
        }
        
        # Calculate value if not provided
        if record["value_usd"] == 0 and record["price"] > 0 and record["size"] > 0:
            record["value_usd"] = record["price"] * record["size"]
        
        normalized.append(record)
    
    df = pd.DataFrame(normalized)
    
    # Sort by timestamp
    if not df.empty and "timestamp_raw" in df.columns:
        df = df.sort_values("timestamp_raw", ascending=False)
    
    return df


def normalize_positions(positions_data: list) -> pd.DataFrame:
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
        
        # Calculate unrealized PnL if not provided
        if record["unrealized_pnl"] == 0 and record["current_value"] > 0 and record["cost_basis"] > 0:
            record["unrealized_pnl"] = record["current_value"] - record["cost_basis"]
        
        normalized.append(record)
    
    return pd.DataFrame(normalized)


# ============================================================================
# SCRAPING FUNCTIONS
# ============================================================================
def scrape_all_activity(user_address: str, limit_per_page: int = 100, max_pages: int = 50) -> list:
    """Scrape all activity for a user with pagination."""
    all_activity = []
    cursor = None
    page = 0
    
    print(f"\n📊 Fetching activity for wallet: {user_address}")
    
    while page < max_pages:
        page += 1
        print(f"   Page {page}...", end=" ", flush=True)
        
        result = get_user_activity(user_address, limit=limit_per_page, cursor=cursor)
        
        history = result.get("history", result) if isinstance(result, dict) else result
        if isinstance(history, dict):
            history = history.get("data", [])
        
        if not history:
            print("no more data")
            break
        
        all_activity.extend(history)
        print(f"got {len(history)} records")
        
        # Check for next page
        cursor = result.get("cursor") if isinstance(result, dict) else None
        if not cursor:
            break
    
    print(f"   ✅ Total activity records: {len(all_activity)}")
    return all_activity


def scrape_wallet(user_address: str, limit: int = 200) -> dict:
    """
    Main function to scrape all data for a wallet.
    Returns dict with activity, positions, and metadata.
    """
    print(f"\n🔍 Starting scrape for wallet: {user_address}")
    print("=" * 60)
    
    # Get activity/trades
    activity = scrape_all_activity(user_address, limit_per_page=min(limit, 100))
    
    # Get current positions
    print("\n📈 Fetching current positions...")
    positions = get_user_positions(user_address)
    print(f"   ✅ Found {len(positions) if positions else 0} positions")
    
    return {
        "wallet": user_address,
        "scraped_at": datetime.utcnow().isoformat(),
        "activity": activity,
        "positions": positions
    }


# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================
def ensure_export_dir():
    """Create export directory if it doesn't exist."""
    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR)
        print(f"📁 Created export directory: {EXPORT_DIR}/")


def export_to_csv(df: pd.DataFrame, filename: str):
    """Export DataFrame to CSV."""
    ensure_export_dir()
    filepath = os.path.join(EXPORT_DIR, filename)
    df.to_csv(filepath, index=False)
    print(f"   💾 Saved: {filepath}")
    return filepath


def export_to_json(data: dict, filename: str):
    """Export data to JSON."""
    ensure_export_dir()
    filepath = os.path.join(EXPORT_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"   💾 Saved: {filepath}")
    return filepath


# ============================================================================
# INTERACTIVE MENU
# ============================================================================
def interactive_market_search():
    """Interactive market search and selection."""
    query = input("\n🔎 Enter market search query (e.g., 'Bitcoin Up or Down'): ").strip()
    
    if not query:
        print("No query provided, skipping market search.")
        return None
    
    print(f"\nSearching for markets matching: '{query}'...")
    markets = search_markets(query, limit=50)
    
    if not markets:
        print("❌ No markets found matching your query.")
        # Try events instead
        print("Searching events...")
        events = get_events(query, limit=20)
        if events:
            print(f"\nFound {len(events)} events:")
            for i, event in enumerate(events[:10]):
                print(f"  [{i+1}] {event.get('title', 'Untitled')}")
        return None
    
    print(f"\n✅ Found {len(markets)} markets:\n")
    for i, market in enumerate(markets[:15]):
        question = market.get("question", market.get("title", "Untitled"))[:70]
        print(f"  [{i+1}] {question}")
    
    selection = input("\nSelect market number (or 'all' for all, or 'skip'): ").strip().lower()
    
    if selection == 'skip':
        return None
    elif selection == 'all':
        return markets
    else:
        try:
            idx = int(selection) - 1
            if 0 <= idx < len(markets):
                return [markets[idx]]
        except ValueError:
            pass
    
    print("Invalid selection.")
    return None


def interactive_wallet_input():
    """Get wallet address interactively."""
    address = input("\n👛 Enter wallet address (0x...): ").strip()
    
    # Basic validation
    if not address.startswith("0x") or len(address) != 42:
        print("⚠️  Warning: Address doesn't look like a valid Ethereum address.")
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            return None
    
    return address


# ============================================================================
# MAIN
# ============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Polymarket Wallet Scraper - Fetch trades and positions for any wallet"
    )
    parser.add_argument("--query", "-q", help="Market search query")
    parser.add_argument("--select", "-s", help="Market selection (number or 'all')")
    parser.add_argument("--user", "-u", help="Wallet address to scrape")
    parser.add_argument("--limit", "-l", type=int, default=200, help="Max records per request")
    parser.add_argument("--output", "-o", default="all-trades", help="Output filename prefix")
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("🕵️  POLYMARKET WALLET SCRAPER")
    print("=" * 60)
    
    # Get wallet address
    user_address = args.user
    if not user_address:
        user_address = interactive_wallet_input()
        if not user_address:
            print("No wallet address provided. Exiting.")
            sys.exit(1)
    
    # Optional: Search markets
    selected_markets = None
    if args.query:
        markets = search_markets(args.query, limit=50)
        if args.select == 'all':
            selected_markets = markets
        elif args.select:
            try:
                idx = int(args.select) - 1
                selected_markets = [markets[idx]] if 0 <= idx < len(markets) else None
            except (ValueError, IndexError):
                pass
    elif not args.user:  # Only do interactive if not in script mode
        selected_markets = interactive_market_search()
    
    # Scrape wallet data
    print("\n" + "-" * 60)
    data = scrape_wallet(user_address, limit=args.limit)
    
    # Normalize and export
    print("\n" + "-" * 60)
    print("📤 EXPORTING DATA")
    print("-" * 60)
    
    # Activity/Trades
    if data["activity"]:
        df_activity = normalize_activity(data["activity"])
        export_to_csv(df_activity, f"{args.output}.csv")
        
        # Also save raw JSON
        export_to_json({
            "wallet": user_address,
            "scraped_at": data["scraped_at"],
            "activity": data["activity"]
        }, f"{args.output}.json")
    else:
        print("   ⚠️  No activity data to export")
    
    # Positions
    if data["positions"]:
        df_positions = normalize_positions(data["positions"])
        export_to_csv(df_positions, "positions.csv")
    else:
        print("   ⚠️  No positions data to export")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ SCRAPE COMPLETE!")
    print("=" * 60)
    print(f"\n📊 Summary:")
    print(f"   • Wallet: {user_address}")
    print(f"   • Activity records: {len(data['activity'])}")
    print(f"   • Current positions: {len(data['positions']) if data['positions'] else 0}")
    print(f"\n📁 Files saved to: {EXPORT_DIR}/")
    print(f"\n💡 Next steps:")
    print(f"   1. Start local server: python3 -m http.server")
    print(f"   2. Open: http://localhost:8000/trades-dashboard.html")
    print(f"   3. Load: {EXPORT_DIR}/{args.output}.csv")


if __name__ == "__main__":
    main()
