#!/usr/bin/env python3
"""
PolyEdge Analytics Engine
Pattern detection, win/loss tracking, and wallet comparison for Polymarket.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
import statistics
import json
import requests

# Polymarket API for market resolution data
GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"


# =============================================================================
# PRICING TIERS
# =============================================================================

PRICING_TIERS = {
    "free": {
        "name": "Free",
        "price": 0,
        "trades_per_month": 100,
        "features": ["basic_analytics", "single_wallet"],
        "comparison_wallets": 0,
        "api_access": False,
        "export_formats": ["csv"],
    },
    "starter": {
        "name": "Starter",
        "price": 19,
        "trades_per_month": 1000,
        "features": ["basic_analytics", "single_wallet", "win_loss_tracking"],
        "comparison_wallets": 0,
        "api_access": False,
        "export_formats": ["csv", "json"],
    },
    "growth": {
        "name": "Growth",
        "price": 79,
        "trades_per_month": 10000,
        "features": ["basic_analytics", "advanced_analytics", "win_loss_tracking",
                     "comparison_mode", "priority_support"],
        "comparison_wallets": 3,
        "api_access": True,
        "export_formats": ["csv", "json", "markdown"],
    },
    "scale": {
        "name": "Scale",
        "price": 299,
        "trades_per_month": 100000,
        "features": ["basic_analytics", "advanced_analytics", "win_loss_tracking",
                     "comparison_mode", "white_label", "dedicated_support", "webhooks"],
        "comparison_wallets": 10,
        "api_access": True,
        "export_formats": ["csv", "json", "markdown", "api"],
    }
}

OVERAGE_RATE = 0.01  # $0.01 per trade beyond limit


def get_tier_info(tier: str) -> Dict:
    """Get pricing tier information."""
    return PRICING_TIERS.get(tier, PRICING_TIERS["free"])


def check_feature_access(tier: str, feature: str) -> bool:
    """Check if a tier has access to a feature."""
    tier_info = get_tier_info(tier)
    return feature in tier_info.get("features", [])


def calculate_overage(tier: str, trades_used: int) -> Dict:
    """Calculate overage charges."""
    tier_info = get_tier_info(tier)
    limit = tier_info["trades_per_month"]

    if trades_used <= limit:
        return {"overage_trades": 0, "overage_cost": 0}

    overage = trades_used - limit
    return {
        "overage_trades": overage,
        "overage_cost": round(overage * OVERAGE_RATE, 2)
    }


# =============================================================================
# WIN/LOSS TRACKING
# =============================================================================

def fetch_market_resolution(condition_id: str) -> Optional[Dict]:
    """Fetch market resolution status from Polymarket API."""
    try:
        response = requests.get(
            f"{GAMMA_API}/markets",
            params={"condition_id": condition_id},
            timeout=10
        )
        if response.status_code == 200:
            markets = response.json()
            if markets:
                return markets[0]
    except Exception:
        pass
    return None


def fetch_market_by_slug(slug: str) -> Optional[Dict]:
    """Fetch market data by slug."""
    try:
        response = requests.get(
            f"{GAMMA_API}/markets",
            params={"slug": slug},
            timeout=10
        )
        if response.status_code == 200:
            markets = response.json()
            if markets:
                return markets[0]
    except Exception:
        pass
    return None


def calculate_position_pnl(trades: List[Dict]) -> Dict:
    """
    Calculate P&L for positions based on trades.
    Groups trades by market and calculates realized/unrealized P&L.
    """
    positions = defaultdict(lambda: {
        "market": "",
        "slug": "",
        "outcome": "",
        "total_cost": 0,
        "total_shares": 0,
        "avg_entry_price": 0,
        "trades": [],
        "realized_pnl": 0,
        "status": "open"
    })

    for trade in trades:
        market_key = (trade.get('title', ''), trade.get('outcome', ''))
        pos = positions[market_key]

        pos["market"] = trade.get('title', 'Unknown')
        pos["slug"] = trade.get('slug', '')
        pos["outcome"] = trade.get('outcome', '')

        side = trade.get('side', '')
        price = trade.get('price', 0) or 0
        size = trade.get('size', 0) or 0
        usdc = trade.get('usdcSize', 0) or 0

        if side == 'BUY':
            pos["total_cost"] += usdc
            pos["total_shares"] += size
        elif side == 'SELL':
            # Calculate realized P&L on sells
            if pos["total_shares"] > 0:
                avg_cost = pos["total_cost"] / pos["total_shares"]
                realized = (price - avg_cost) * min(size, pos["total_shares"])
                pos["realized_pnl"] += realized
            pos["total_shares"] -= size
            pos["total_cost"] = max(0, pos["total_cost"] - usdc)

        pos["trades"].append(trade)

    # Calculate averages and status
    for key, pos in positions.items():
        if pos["total_shares"] > 0:
            pos["avg_entry_price"] = pos["total_cost"] / pos["total_shares"]
        else:
            pos["status"] = "closed"

    return dict(positions)


def analyze_win_loss(trades: List[Dict], resolved_markets: Dict = None) -> Dict:
    """
    Analyze win/loss statistics for trades.
    Uses market resolution data to determine outcomes.
    """
    if resolved_markets is None:
        resolved_markets = {}

    positions = calculate_position_pnl(trades)

    wins = 0
    losses = 0
    pending = 0
    total_profit = 0
    total_loss = 0

    position_results = []

    for key, pos in positions.items():
        market_slug = pos.get("slug", "")
        outcome = pos.get("outcome", "")

        # Check if market is resolved
        resolution = resolved_markets.get(market_slug)

        result = {
            "market": pos["market"][:60],
            "outcome_bet": outcome,
            "shares": round(pos["total_shares"], 2),
            "cost_basis": round(pos["total_cost"], 2),
            "avg_entry": round(pos["avg_entry_price"], 4),
            "realized_pnl": round(pos["realized_pnl"], 2),
            "status": "pending"
        }

        if resolution:
            winning_outcome = resolution.get("outcome", "")
            result["resolved_outcome"] = winning_outcome

            if pos["total_shares"] > 0:  # Still holding
                if outcome == winning_outcome:
                    # Won - shares worth $1 each
                    pnl = pos["total_shares"] - pos["total_cost"]
                    result["status"] = "won"
                    result["pnl"] = round(pnl, 2)
                    wins += 1
                    total_profit += max(0, pnl)
                else:
                    # Lost - shares worth $0
                    pnl = -pos["total_cost"]
                    result["status"] = "lost"
                    result["pnl"] = round(pnl, 2)
                    losses += 1
                    total_loss += abs(pnl)
            else:
                result["status"] = "closed"
                result["pnl"] = round(pos["realized_pnl"], 2)
                if pos["realized_pnl"] > 0:
                    wins += 1
                    total_profit += pos["realized_pnl"]
                elif pos["realized_pnl"] < 0:
                    losses += 1
                    total_loss += abs(pos["realized_pnl"])
        else:
            pending += 1
            result["pnl"] = round(pos["realized_pnl"], 2)

        position_results.append(result)

    # Sort by absolute PnL
    position_results.sort(key=lambda x: abs(x.get("pnl", 0)), reverse=True)

    total_resolved = wins + losses
    win_rate = (wins / total_resolved * 100) if total_resolved > 0 else 0

    return {
        "summary": {
            "total_positions": len(positions),
            "wins": wins,
            "losses": losses,
            "pending": pending,
            "win_rate": round(win_rate, 1),
            "total_profit": round(total_profit, 2),
            "total_loss": round(total_loss, 2),
            "net_pnl": round(total_profit - total_loss, 2),
            "profit_factor": round(total_profit / total_loss, 2) if total_loss > 0 else float('inf'),
        },
        "positions": position_results[:50],  # Top 50 by PnL
        "best_trade": position_results[0] if position_results else None,
        "worst_trade": min(position_results, key=lambda x: x.get("pnl", 0)) if position_results else None,
    }


# =============================================================================
# COMPARISON MODE
# =============================================================================

def compare_wallets(wallet_analyses: List[Dict]) -> Dict:
    """
    Compare multiple wallet analyses side-by-side.
    Returns comparative metrics and rankings.
    """
    if not wallet_analyses:
        return {"error": "No wallets to compare"}

    if len(wallet_analyses) == 1:
        return {"error": "Need at least 2 wallets to compare", "single": wallet_analyses[0]}

    comparison = {
        "wallet_count": len(wallet_analyses),
        "wallets": [],
        "rankings": {},
        "insights": [],
        "timeline_overlap": {},
        "common_markets": []
    }

    # Collect all markets traded by each wallet
    wallet_markets = {}

    # Extract key metrics for each wallet
    for wa in wallet_analyses:
        summary = wa.get("analysis", {}).get("summary", {})
        pnl = wa.get("pnl", {}).get("summary", {})
        behavior = wa.get("analysis", {}).get("behavioral_patterns", {})
        risk = wa.get("analysis", {}).get("risk_metrics", {})
        
        # Calculate Sharpe-like ratio (return / volatility proxy)
        net_pnl = pnl.get("net_pnl", 0)
        total_volume = summary.get("total_volume_usd", 1)
        win_rate = pnl.get("win_rate", 50)
        
        # Simple Sharpe approximation: (return rate * consistency factor)
        return_rate = net_pnl / total_volume if total_volume > 0 else 0
        consistency = (win_rate - 50) / 50  # Normalized to -1 to 1
        sharpe_like = round(return_rate * (1 + consistency) * 100, 2)
        
        # Max drawdown estimate (from risk metrics or calculate)
        max_drawdown = risk.get("estimated_max_drawdown", 0)
        if not max_drawdown and pnl.get("total_loss", 0) > 0:
            max_drawdown = round(abs(pnl.get("total_loss", 0)) / total_volume * 100, 1)

        wallet_data = {
            "wallet": wa.get("wallet", "")[:10] + "...",
            "full_wallet": wa.get("wallet", ""),
            "username": wa.get("username", "Unknown"),
            "total_trades": summary.get("total_trades", 0),
            "total_volume": summary.get("total_volume_usd", 0),
            "avg_trade_size": summary.get("avg_trade_size", 0),
            "trades_per_day": summary.get("trades_per_day", 0),
            "win_rate": pnl.get("win_rate", 0),
            "net_pnl": pnl.get("net_pnl", 0),
            "profit_factor": pnl.get("profit_factor", 0),
            "trader_type": behavior.get("trader_classification", {}).get("primary_type", "unknown"),
            "sharpe_like": sharpe_like,
            "max_drawdown": max_drawdown,
            "risk_score": risk.get("risk_score", 50),
            "unique_markets": summary.get("unique_markets", 0),
            "oldest_trade": summary.get("oldest_trade"),
            "newest_trade": summary.get("newest_trade"),
        }
        comparison["wallets"].append(wallet_data)
        
        # Collect markets for overlap analysis
        markets = wa.get("analysis", {}).get("top_markets", {}).get("by_trades", [])
        wallet_markets[wallet_data["username"]] = set(m.get("market", "") for m in markets if m.get("market"))

    # Generate rankings for each metric
    metrics_to_rank = [
        ("total_trades", "Most Active", True),
        ("total_volume", "Highest Volume", True),
        ("win_rate", "Best Win Rate", True),
        ("net_pnl", "Most Profitable", True),
        ("profit_factor", "Best Risk/Reward", True),
        ("sharpe_like", "Best Risk-Adj Return", True),
        ("max_drawdown", "Lowest Drawdown", False),
        ("avg_trade_size", "Largest Avg Trade", True),
        ("risk_score", "Lowest Risk", False),
    ]

    for metric, label, higher_better in metrics_to_rank:
        sorted_wallets = sorted(
            comparison["wallets"],
            key=lambda x: x.get(metric, 0) or 0,
            reverse=higher_better
        )
        comparison["rankings"][metric] = {
            "label": label,
            "ranking": [w["username"] for w in sorted_wallets],
            "values": [w.get(metric, 0) for w in sorted_wallets]
        }

    # Calculate timeline overlap
    for i, w1 in enumerate(comparison["wallets"]):
        for w2 in comparison["wallets"][i+1:]:
            if w1.get("oldest_trade") and w2.get("oldest_trade"):
                # Simple overlap check based on date ranges
                overlap_key = f"{w1['username']} vs {w2['username']}"
                comparison["timeline_overlap"][overlap_key] = {
                    "wallet1_range": f"{w1.get('oldest_trade', 'N/A')} to {w1.get('newest_trade', 'N/A')}",
                    "wallet2_range": f"{w2.get('oldest_trade', 'N/A')} to {w2.get('newest_trade', 'N/A')}",
                }

    # Find common markets
    if len(wallet_markets) >= 2:
        all_markets = list(wallet_markets.values())
        common = all_markets[0]
        for markets in all_markets[1:]:
            common = common.intersection(markets)
        comparison["common_markets"] = list(common)[:10]  # Top 10

    # Generate comparison insights
    best_volume = max(comparison["wallets"], key=lambda x: x["total_volume"])
    best_winrate = max(comparison["wallets"], key=lambda x: x["win_rate"])
    best_pnl = max(comparison["wallets"], key=lambda x: x["net_pnl"])
    best_sharpe = max(comparison["wallets"], key=lambda x: x["sharpe_like"])
    lowest_risk = min(comparison["wallets"], key=lambda x: x.get("risk_score", 100))

    comparison["insights"] = [
        {
            "title": "Volume Leader",
            "description": f"{best_volume['username']} has the highest trading volume at ${best_volume['total_volume']:,.0f}",
            "winner": best_volume["username"],
            "icon": "📊"
        },
        {
            "title": "Best Win Rate",
            "description": f"{best_winrate['username']} has the highest win rate at {best_winrate['win_rate']:.1f}%",
            "winner": best_winrate["username"],
            "icon": "🎯"
        },
        {
            "title": "Most Profitable",
            "description": f"{best_pnl['username']} has the highest net P&L at ${best_pnl['net_pnl']:,.2f}",
            "winner": best_pnl["username"],
            "icon": "💰"
        },
        {
            "title": "Best Risk-Adjusted",
            "description": f"{best_sharpe['username']} has the best risk-adjusted returns (Sharpe-like: {best_sharpe['sharpe_like']:.2f})",
            "winner": best_sharpe["username"],
            "icon": "⚡"
        },
        {
            "title": "Lowest Risk",
            "description": f"{lowest_risk['username']} has the lowest risk score at {lowest_risk.get('risk_score', 0):.0f}/100",
            "winner": lowest_risk["username"],
            "icon": "🛡️"
        }
    ]

    # Strategy diversity comparison
    trader_types = [w["trader_type"] for w in comparison["wallets"]]
    if len(set(trader_types)) > 1:
        comparison["insights"].append({
            "title": "Strategy Diversity",
            "description": f"Wallets use different strategies: {', '.join(set(trader_types))}",
            "winner": None,
            "icon": "🔀"
        })

    # Common markets insight
    if comparison["common_markets"]:
        comparison["insights"].append({
            "title": "Market Overlap",
            "description": f"All wallets trade in {len(comparison['common_markets'])} common markets",
            "winner": None,
            "icon": "🔗"
        })

    return comparison


# =============================================================================
# PAIR TRADE DETECTION
# =============================================================================

def detect_pair_trades(trades: List[Dict], time_window_seconds: int = 900) -> Dict:
    """
    Detect pair trades - when a trader buys both sides of the same market
    (Yes/No, Up/Down) within a time window.

    This indicates hedging, arbitrage, or market-making behavior.
    """
    # Sort trades by timestamp
    sorted_trades = sorted(trades, key=lambda x: x.get('timestamp', 0))

    # Group trades by market (title/slug)
    market_trades = defaultdict(list)
    for t in sorted_trades:
        market_key = t.get('title', '') or t.get('slug', '')
        if market_key:
            market_trades[market_key].append(t)

    pair_trades = []
    hedged_markets = set()
    total_hedge_volume = 0

    for market, market_trade_list in market_trades.items():
        # Look for trades on opposite outcomes within time window
        for i, trade1 in enumerate(market_trade_list):
            outcome1 = trade1.get('outcome', '')
            ts1 = trade1.get('timestamp', 0)

            for trade2 in market_trade_list[i+1:]:
                outcome2 = trade2.get('outcome', '')
                ts2 = trade2.get('timestamp', 0)

                # Check if opposite outcomes
                is_opposite = (
                    (outcome1 in ['Yes', 'Up'] and outcome2 in ['No', 'Down']) or
                    (outcome1 in ['No', 'Down'] and outcome2 in ['Yes', 'Up'])
                )

                # Check if within time window
                time_diff = abs(ts2 - ts1)

                if is_opposite and time_diff <= time_window_seconds:
                    pair_trade = {
                        "market": market[:60],
                        "trade1": {
                            "outcome": outcome1,
                            "price": trade1.get('price', 0),
                            "shares": trade1.get('size', 0),
                            "usdc": trade1.get('usdcSize', 0),
                            "timestamp": ts1,
                            "time": datetime.fromtimestamp(ts1).strftime('%Y-%m-%d %H:%M:%S') if ts1 else '',
                        },
                        "trade2": {
                            "outcome": outcome2,
                            "price": trade2.get('price', 0),
                            "shares": trade2.get('size', 0),
                            "usdc": trade2.get('usdcSize', 0),
                            "timestamp": ts2,
                            "time": datetime.fromtimestamp(ts2).strftime('%Y-%m-%d %H:%M:%S') if ts2 else '',
                        },
                        "time_between_seconds": int(time_diff),
                        "combined_cost": round((trade1.get('usdcSize', 0) or 0) + (trade2.get('usdcSize', 0) or 0), 2),
                        "combined_shares": round((trade1.get('size', 0) or 0) + (trade2.get('size', 0) or 0), 2),
                        "spread": round(abs((trade1.get('price', 0) or 0) + (trade2.get('price', 0) or 0) - 1), 4),
                    }

                    # Calculate potential profit if prices sum to < 1
                    price_sum = (trade1.get('price', 0) or 0) + (trade2.get('price', 0) or 0)
                    if price_sum < 1:
                        # Arbitrage opportunity - guaranteed profit
                        min_shares = min(trade1.get('size', 0) or 0, trade2.get('size', 0) or 0)
                        pair_trade["arb_profit"] = round((1 - price_sum) * min_shares, 2)
                        pair_trade["is_arbitrage"] = True
                    else:
                        pair_trade["arb_profit"] = 0
                        pair_trade["is_arbitrage"] = False

                    pair_trades.append(pair_trade)
                    hedged_markets.add(market)
                    total_hedge_volume += pair_trade["combined_cost"]

    # Sort by combined cost (largest hedges first)
    pair_trades.sort(key=lambda x: x["combined_cost"], reverse=True)

    # Calculate statistics
    arb_trades = [p for p in pair_trades if p.get("is_arbitrage")]
    quick_pairs = [p for p in pair_trades if p["time_between_seconds"] < 60]

    return {
        "summary": {
            "total_pair_trades": len(pair_trades),
            "hedged_markets": len(hedged_markets),
            "total_hedge_volume": round(total_hedge_volume, 2),
            "arbitrage_trades": len(arb_trades),
            "total_arb_profit": round(sum(p.get("arb_profit", 0) for p in arb_trades), 2),
            "quick_pairs_under_60s": len(quick_pairs),
            "avg_time_between": round(sum(p["time_between_seconds"] for p in pair_trades) / len(pair_trades), 1) if pair_trades else 0,
        },
        "pair_trades": pair_trades[:100],  # Top 100 pair trades
        "hedged_markets": list(hedged_markets)[:20],
    }


# =============================================================================
# TRADING FREQUENCY ANALYSIS
# =============================================================================

def analyze_trading_frequency(trades: List[Dict]) -> Dict:
    """
    Analyze trading frequency - trades per second, minute, hour.
    Detect burst trading patterns.
    """
    if not trades:
        return {}

    sorted_trades = sorted(trades, key=lambda x: x.get('timestamp', 0))
    timestamps = [t.get('timestamp', 0) for t in sorted_trades if t.get('timestamp')]

    if len(timestamps) < 2:
        return {"error": "Not enough trades for frequency analysis"}

    # Calculate time gaps between consecutive trades
    gaps = []
    for i in range(1, len(timestamps)):
        gap = timestamps[i] - timestamps[i-1]
        if gap >= 0:  # Sanity check
            gaps.append(gap)

    # Frequency buckets
    trades_per_second = defaultdict(int)
    trades_per_minute = defaultdict(int)
    trades_per_hour = defaultdict(int)

    for ts in timestamps:
        second_key = int(ts)
        minute_key = int(ts // 60)
        hour_key = int(ts // 3600)

        trades_per_second[second_key] += 1
        trades_per_minute[minute_key] += 1
        trades_per_hour[hour_key] += 1

    # Find peak activity
    max_per_second = max(trades_per_second.values()) if trades_per_second else 0
    max_per_minute = max(trades_per_minute.values()) if trades_per_minute else 0
    max_per_hour = max(trades_per_hour.values()) if trades_per_hour else 0

    # Calculate averages
    total_seconds = (max(timestamps) - min(timestamps)) if timestamps else 1
    total_minutes = total_seconds / 60
    total_hours = total_seconds / 3600

    avg_per_second = len(trades) / max(total_seconds, 1)
    avg_per_minute = len(trades) / max(total_minutes, 1)
    avg_per_hour = len(trades) / max(total_hours, 1)

    # Detect burst patterns (multiple trades within 5 seconds)
    bursts = []
    current_burst = []
    burst_threshold = 5  # seconds

    for i, ts in enumerate(timestamps):
        if not current_burst:
            current_burst = [sorted_trades[i]]
        else:
            last_ts = current_burst[-1].get('timestamp', 0)
            if ts - last_ts <= burst_threshold:
                current_burst.append(sorted_trades[i])
            else:
                if len(current_burst) >= 3:  # At least 3 trades = burst
                    burst_start = current_burst[0].get('timestamp', 0)
                    burst_end = current_burst[-1].get('timestamp', 0)
                    bursts.append({
                        "trade_count": len(current_burst),
                        "duration_seconds": round(burst_end - burst_start, 1),
                        "start_time": datetime.fromtimestamp(burst_start).strftime('%Y-%m-%d %H:%M:%S') if burst_start else '',
                        "trades_per_second": round(len(current_burst) / max(burst_end - burst_start, 0.1), 2),
                        "total_volume": round(sum(t.get('usdcSize', 0) or 0 for t in current_burst), 2),
                        "markets": list(set(t.get('title', '')[:40] for t in current_burst)),
                    })
                current_burst = [sorted_trades[i]]

    # Check final burst
    if len(current_burst) >= 3:
        burst_start = current_burst[0].get('timestamp', 0)
        burst_end = current_burst[-1].get('timestamp', 0)
        bursts.append({
            "trade_count": len(current_burst),
            "duration_seconds": round(burst_end - burst_start, 1),
            "start_time": datetime.fromtimestamp(burst_start).strftime('%Y-%m-%d %H:%M:%S') if burst_start else '',
            "trades_per_second": round(len(current_burst) / max(burst_end - burst_start, 0.1), 2),
            "total_volume": round(sum(t.get('usdcSize', 0) or 0 for t in current_burst), 2),
            "markets": list(set(t.get('title', '')[:40] for t in current_burst)),
        })

    # Sort bursts by trade count
    bursts.sort(key=lambda x: x["trade_count"], reverse=True)

    # Gap analysis
    if gaps:
        avg_gap = sum(gaps) / len(gaps)
        min_gap = min(gaps)
        max_gap = max(gaps)

        # Count rapid trades (< 1 second apart)
        sub_second_trades = sum(1 for g in gaps if g < 1)
        sub_minute_trades = sum(1 for g in gaps if g < 60)
    else:
        avg_gap = min_gap = max_gap = 0
        sub_second_trades = sub_minute_trades = 0

    return {
        "summary": {
            "total_trades": len(trades),
            "time_span_hours": round(total_hours, 1),
            "avg_trades_per_second": round(avg_per_second, 3),
            "avg_trades_per_minute": round(avg_per_minute, 2),
            "avg_trades_per_hour": round(avg_per_hour, 1),
            "max_trades_per_second": max_per_second,
            "max_trades_per_minute": max_per_minute,
            "max_trades_per_hour": max_per_hour,
        },
        "gaps": {
            "avg_seconds_between_trades": round(avg_gap, 2),
            "min_gap_seconds": round(min_gap, 3),
            "max_gap_seconds": round(max_gap, 1),
            "sub_second_trades": sub_second_trades,
            "sub_second_percentage": round(sub_second_trades / max(len(gaps), 1) * 100, 1),
            "sub_minute_trades": sub_minute_trades,
            "sub_minute_percentage": round(sub_minute_trades / max(len(gaps), 1) * 100, 1),
        },
        "bursts": {
            "total_bursts": len(bursts),
            "largest_burst": bursts[0] if bursts else None,
            "top_bursts": bursts[:10],
        },
        "is_high_frequency": max_per_second >= 3 or avg_per_minute > 10,
        "is_bot_like": sub_second_trades > len(gaps) * 0.1 if gaps else False,
    }


def analyze_trades(trades: List[Dict], include_pnl: bool = True) -> Dict[str, Any]:
    """
    Comprehensive trade analysis with pattern detection.
    Returns structured insights for UI display and export.
    """
    if not trades:
        return {"error": "No trades to analyze"}

    analysis = {
        "summary": get_summary_stats(trades),
        "position_sizing": analyze_position_sizing(trades),
        "market_analysis": analyze_markets(trades),
        "timing_patterns": analyze_timing(trades),
        "outcome_analysis": analyze_outcomes(trades),
        "behavioral_patterns": detect_behavioral_patterns(trades),
        "risk_metrics": calculate_risk_metrics(trades),
        "pair_trades": detect_pair_trades(trades),
        "frequency": analyze_trading_frequency(trades),
        "insights": [],  # Natural language insights
    }

    # Add P&L analysis if requested
    if include_pnl:
        analysis["pnl"] = analyze_win_loss(trades)

    # Generate natural language insights
    analysis["insights"] = generate_insights(analysis, trades)

    return analysis


def get_summary_stats(trades: List[Dict]) -> Dict:
    """High-level summary statistics."""
    buys = [t for t in trades if t.get('side') == 'BUY']
    sells = [t for t in trades if t.get('side') == 'SELL']

    volumes = [t.get('usdcSize', 0) or 0 for t in trades]
    timestamps = [t.get('timestamp', 0) for t in trades if t.get('timestamp')]

    total_volume = sum(volumes)
    avg_trade_size = statistics.mean(volumes) if volumes else 0
    median_trade_size = statistics.median(volumes) if volumes else 0

    # Date range
    if timestamps:
        oldest = datetime.fromtimestamp(min(timestamps))
        newest = datetime.fromtimestamp(max(timestamps))
        days_active = (newest - oldest).days + 1
        trades_per_day = len(trades) / max(days_active, 1)
    else:
        oldest = newest = None
        days_active = 0
        trades_per_day = 0

    return {
        "total_trades": len(trades),
        "total_buys": len(buys),
        "total_sells": len(sells),
        "buy_sell_ratio": len(buys) / max(len(sells), 1),
        "total_volume_usd": round(total_volume, 2),
        "avg_trade_size": round(avg_trade_size, 2),
        "median_trade_size": round(median_trade_size, 2),
        "largest_trade": round(max(volumes), 2) if volumes else 0,
        "smallest_trade": round(min(volumes), 2) if volumes else 0,
        "days_active": days_active,
        "trades_per_day": round(trades_per_day, 1),
        "date_range": {
            "start": oldest.strftime('%Y-%m-%d %H:%M') if oldest else None,
            "end": newest.strftime('%Y-%m-%d %H:%M') if newest else None,
        }
    }


def analyze_position_sizing(trades: List[Dict]) -> Dict:
    """Analyze position sizing patterns."""
    volumes = [t.get('usdcSize', 0) or 0 for t in trades]
    if not volumes:
        return {}

    # Size buckets
    buckets = {
        "micro": 0,      # < $10
        "small": 0,      # $10-50
        "medium": 0,     # $50-200
        "large": 0,      # $200-1000
        "whale": 0       # > $1000
    }

    for v in volumes:
        if v < 10:
            buckets["micro"] += 1
        elif v < 50:
            buckets["small"] += 1
        elif v < 200:
            buckets["medium"] += 1
        elif v < 1000:
            buckets["large"] += 1
        else:
            buckets["whale"] += 1

    # Convert to percentages
    total = len(volumes)
    distribution = {k: round(v / total * 100, 1) for k, v in buckets.items()}

    # Standard deviation and variance
    std_dev = statistics.stdev(volumes) if len(volumes) > 1 else 0

    # Detect if sizing is consistent or variable
    cv = std_dev / statistics.mean(volumes) if statistics.mean(volumes) > 0 else 0
    sizing_style = "consistent" if cv < 0.5 else "variable" if cv < 1.5 else "highly_variable"

    return {
        "distribution": distribution,
        "distribution_counts": buckets,
        "std_deviation": round(std_dev, 2),
        "coefficient_of_variation": round(cv, 2),
        "sizing_style": sizing_style,
        "percentiles": {
            "p25": round(sorted(volumes)[len(volumes)//4], 2) if volumes else 0,
            "p50": round(statistics.median(volumes), 2),
            "p75": round(sorted(volumes)[3*len(volumes)//4], 2) if volumes else 0,
            "p95": round(sorted(volumes)[int(len(volumes)*0.95)], 2) if volumes else 0,
        }
    }


def analyze_markets(trades: List[Dict]) -> Dict:
    """Analyze market preferences and diversification."""
    market_stats = defaultdict(lambda: {
        "count": 0,
        "volume": 0,
        "buys": 0,
        "sells": 0,
        "outcomes": defaultdict(int)
    })

    for t in trades:
        title = t.get('title', 'Unknown')
        market_stats[title]["count"] += 1
        market_stats[title]["volume"] += t.get('usdcSize', 0) or 0
        if t.get('side') == 'BUY':
            market_stats[title]["buys"] += 1
        else:
            market_stats[title]["sells"] += 1
        outcome = t.get('outcome', 'Unknown')
        market_stats[title]["outcomes"][outcome] += 1

    # Sort by volume
    sorted_markets = sorted(
        market_stats.items(),
        key=lambda x: x[1]["volume"],
        reverse=True
    )

    # Top markets
    top_markets = []
    for name, stats in sorted_markets[:20]:
        top_markets.append({
            "name": name[:80],  # Truncate long names
            "trade_count": stats["count"],
            "volume": round(stats["volume"], 2),
            "buys": stats["buys"],
            "sells": stats["sells"],
            "primary_outcome": max(stats["outcomes"].items(), key=lambda x: x[1])[0] if stats["outcomes"] else None
        })

    # Concentration metrics
    total_volume = sum(m["volume"] for m in top_markets)
    top_5_volume = sum(m["volume"] for m in top_markets[:5])
    concentration = top_5_volume / total_volume if total_volume > 0 else 0

    return {
        "unique_markets": len(market_stats),
        "top_markets": top_markets,
        "concentration_top5": round(concentration * 100, 1),
        "diversification_score": round((1 - concentration) * 100, 1),
    }


def analyze_timing(trades: List[Dict]) -> Dict:
    """Analyze trading time patterns."""
    hour_counts = defaultdict(int)
    day_counts = defaultdict(int)
    hourly_volume = defaultdict(float)

    for t in trades:
        ts = t.get('timestamp', 0)
        if ts:
            dt = datetime.fromtimestamp(ts)
            hour_counts[dt.hour] += 1
            day_counts[dt.strftime('%A')] += 1
            hourly_volume[dt.hour] += t.get('usdcSize', 0) or 0

    # Find peak hours
    sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
    peak_hours = [h for h, _ in sorted_hours[:3]]

    # Find peak days
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    sorted_days = sorted(day_counts.items(), key=lambda x: x[1], reverse=True)

    # Trading session classification
    morning = sum(hour_counts[h] for h in range(6, 12))
    afternoon = sum(hour_counts[h] for h in range(12, 18))
    evening = sum(hour_counts[h] for h in range(18, 24))
    night = sum(hour_counts[h] for h in range(0, 6))

    total = morning + afternoon + evening + night
    sessions = {
        "morning_6_12": round(morning / max(total, 1) * 100, 1),
        "afternoon_12_18": round(afternoon / max(total, 1) * 100, 1),
        "evening_18_24": round(evening / max(total, 1) * 100, 1),
        "night_0_6": round(night / max(total, 1) * 100, 1),
    }

    return {
        "hourly_distribution": dict(hour_counts),
        "daily_distribution": dict(day_counts),
        "peak_hours": peak_hours,
        "peak_day": sorted_days[0][0] if sorted_days else None,
        "sessions": sessions,
        "primary_session": max(sessions.items(), key=lambda x: x[1])[0] if sessions else None,
    }


def analyze_outcomes(trades: List[Dict]) -> Dict:
    """Analyze outcome preferences (Yes/No, Up/Down)."""
    outcome_counts = defaultdict(int)
    outcome_volumes = defaultdict(float)

    for t in trades:
        outcome = t.get('outcome', 'Unknown')
        outcome_counts[outcome] += 1
        outcome_volumes[outcome] += t.get('usdcSize', 0) or 0

    total_trades = sum(outcome_counts.values())
    total_volume = sum(outcome_volumes.values())

    # Calculate preferences
    yes_count = outcome_counts.get('Yes', 0) + outcome_counts.get('Up', 0)
    no_count = outcome_counts.get('No', 0) + outcome_counts.get('Down', 0)

    return {
        "outcome_distribution": dict(outcome_counts),
        "outcome_volumes": {k: round(v, 2) for k, v in outcome_volumes.items()},
        "yes_percentage": round(yes_count / max(total_trades, 1) * 100, 1),
        "no_percentage": round(no_count / max(total_trades, 1) * 100, 1),
        "preference": "bullish" if yes_count > no_count * 1.2 else "bearish" if no_count > yes_count * 1.2 else "neutral",
    }


def detect_behavioral_patterns(trades: List[Dict]) -> Dict:
    """Detect behavioral trading patterns."""
    patterns = []

    # Sort trades by timestamp
    sorted_trades = sorted(trades, key=lambda x: x.get('timestamp', 0))

    # Detect rapid trading (multiple trades within minutes)
    rapid_sequences = 0
    for i in range(1, len(sorted_trades)):
        t1 = sorted_trades[i-1].get('timestamp', 0)
        t2 = sorted_trades[i].get('timestamp', 0)
        if t2 - t1 < 60:  # Within 1 minute
            rapid_sequences += 1

    rapid_trading_pct = rapid_sequences / max(len(trades), 1) * 100

    # Detect averaging patterns (same market, same outcome, multiple buys)
    market_outcome_sequences = defaultdict(list)
    for t in sorted_trades:
        key = (t.get('title'), t.get('outcome'))
        market_outcome_sequences[key].append(t)

    averaging_detected = sum(1 for seq in market_outcome_sequences.values() if len(seq) >= 3)

    # Detect price sensitivity (buying at specific price points)
    prices = [t.get('price', 0) for t in trades if t.get('price')]
    if prices:
        common_prices = defaultdict(int)
        for p in prices:
            rounded = round(p, 2)
            common_prices[rounded] += 1

        # Find prices with high frequency
        price_preference = sorted(common_prices.items(), key=lambda x: x[1], reverse=True)[:5]
    else:
        price_preference = []

    # Classify trader type
    trader_type = classify_trader(trades, rapid_trading_pct, averaging_detected)

    return {
        "rapid_trading_percentage": round(rapid_trading_pct, 1),
        "averaging_behavior_count": averaging_detected,
        "common_entry_prices": price_preference,
        "trader_classification": trader_type,
        "patterns_detected": patterns,
    }


def classify_trader(trades: List[Dict], rapid_pct: float, avg_count: int) -> Dict:
    """Classify the trader type based on behavior."""
    classifications = []
    confidence_scores = {}

    # High frequency trader
    if rapid_pct > 30:
        classifications.append("high_frequency")
        confidence_scores["high_frequency"] = min(rapid_pct / 50 * 100, 100)

    # Position builder (averaging)
    if avg_count > 10:
        classifications.append("position_builder")
        confidence_scores["position_builder"] = min(avg_count / 20 * 100, 100)

    # Scalper (many small quick trades)
    volumes = [t.get('usdcSize', 0) or 0 for t in trades]
    if volumes:
        avg_size = statistics.mean(volumes)
        if avg_size < 20 and rapid_pct > 20:
            classifications.append("scalper")
            confidence_scores["scalper"] = 80

    # Whale (large positions)
    if volumes and statistics.mean(volumes) > 200:
        classifications.append("whale")
        confidence_scores["whale"] = min(statistics.mean(volumes) / 500 * 100, 100)

    # Market maker (balanced buys/sells)
    buys = sum(1 for t in trades if t.get('side') == 'BUY')
    sells = sum(1 for t in trades if t.get('side') == 'SELL')
    if sells > 0 and 0.8 < buys/sells < 1.2:
        classifications.append("market_maker")
        confidence_scores["market_maker"] = 70

    if not classifications:
        classifications.append("standard")
        confidence_scores["standard"] = 50

    return {
        "types": classifications,
        "primary_type": classifications[0] if classifications else "unknown",
        "confidence_scores": confidence_scores,
    }


def calculate_risk_metrics(trades: List[Dict]) -> Dict:
    """Calculate risk-related metrics."""
    volumes = [t.get('usdcSize', 0) or 0 for t in trades]
    if not volumes:
        return {}

    total_volume = sum(volumes)
    max_single = max(volumes)

    # Single trade risk (largest trade as % of total)
    max_trade_risk = max_single / total_volume * 100 if total_volume > 0 else 0

    # Market concentration
    market_volumes = defaultdict(float)
    for t in trades:
        market_volumes[t.get('title', 'Unknown')] += t.get('usdcSize', 0) or 0

    if market_volumes:
        max_market_volume = max(market_volumes.values())
        market_concentration = max_market_volume / total_volume * 100 if total_volume > 0 else 0
    else:
        market_concentration = 0

    # Volatility of position sizes
    if len(volumes) > 1:
        size_volatility = statistics.stdev(volumes) / statistics.mean(volumes)
    else:
        size_volatility = 0

    return {
        "max_single_trade_risk": round(max_trade_risk, 2),
        "market_concentration_risk": round(market_concentration, 2),
        "position_size_volatility": round(size_volatility, 2),
        "risk_score": round(
            (max_trade_risk * 0.3 + market_concentration * 0.4 + size_volatility * 30) / 3, 1
        ),
    }


def generate_insights(analysis: Dict, trades: List[Dict]) -> List[Dict]:
    """Generate natural language insights from analysis."""
    insights = []

    summary = analysis.get("summary", {})
    sizing = analysis.get("position_sizing", {})
    markets = analysis.get("market_analysis", {})
    timing = analysis.get("timing_patterns", {})
    outcomes = analysis.get("outcome_analysis", {})
    behavior = analysis.get("behavioral_patterns", {})
    risk = analysis.get("risk_metrics", {})

    # Trading frequency insight
    tpd = summary.get("trades_per_day", 0)
    if tpd > 100:
        insights.append({
            "category": "frequency",
            "title": "Extremely High Frequency Trader",
            "description": f"Averaging {tpd:.0f} trades per day. This indicates algorithmic or bot-assisted trading.",
            "importance": "high"
        })
    elif tpd > 20:
        insights.append({
            "category": "frequency",
            "title": "Active Day Trader",
            "description": f"Averaging {tpd:.0f} trades per day. Very active market participant.",
            "importance": "medium"
        })

    # Position sizing insight
    if sizing.get("sizing_style") == "consistent":
        insights.append({
            "category": "sizing",
            "title": "Consistent Position Sizing",
            "description": f"Trade sizes are relatively uniform (CV: {sizing.get('coefficient_of_variation', 0):.2f}). Suggests disciplined risk management.",
            "importance": "medium"
        })
    elif sizing.get("sizing_style") == "highly_variable":
        insights.append({
            "category": "sizing",
            "title": "Variable Position Sizing",
            "description": "Trade sizes vary significantly. May indicate conviction-based sizing or opportunistic trading.",
            "importance": "medium"
        })

    # Market concentration
    conc = markets.get("concentration_top5", 0)
    if conc > 80:
        insights.append({
            "category": "concentration",
            "title": "Highly Concentrated Strategy",
            "description": f"{conc:.0f}% of volume in top 5 markets. Focused specialist approach.",
            "importance": "high"
        })
    elif conc < 30:
        insights.append({
            "category": "concentration",
            "title": "Diversified Approach",
            "description": f"Volume spread across many markets ({markets.get('unique_markets', 0)} unique). Broad market coverage.",
            "importance": "medium"
        })

    # Outcome preference
    pref = outcomes.get("preference")
    if pref == "bullish":
        insights.append({
            "category": "bias",
            "title": "Bullish Bias Detected",
            "description": f"{outcomes.get('yes_percentage', 0):.0f}% of trades are Yes/Up positions. Strong optimistic tendency.",
            "importance": "high"
        })
    elif pref == "bearish":
        insights.append({
            "category": "bias",
            "title": "Bearish Bias Detected",
            "description": f"{outcomes.get('no_percentage', 0):.0f}% of trades are No/Down positions. Contrarian or hedging strategy.",
            "importance": "high"
        })

    # Timing insight
    primary_session = timing.get("primary_session", "")
    if "night" in primary_session:
        insights.append({
            "category": "timing",
            "title": "Night Owl Trader",
            "description": "Most active during night hours (12am-6am). May be in different timezone or trading off-hours for edge.",
            "importance": "low"
        })

    # Trader type insight
    trader_type = behavior.get("trader_classification", {}).get("primary_type", "")
    if trader_type == "high_frequency":
        insights.append({
            "category": "style",
            "title": "High Frequency Trading Pattern",
            "description": f"{behavior.get('rapid_trading_percentage', 0):.0f}% of trades within 1 minute of each other. Likely automated.",
            "importance": "high"
        })
    elif trader_type == "whale":
        insights.append({
            "category": "style",
            "title": "Whale Activity",
            "description": f"Average trade size ${summary.get('avg_trade_size', 0):.0f}. Large capital deployment per position.",
            "importance": "high"
        })

    # Risk insight
    risk_score = risk.get("risk_score", 0)
    if risk_score > 50:
        insights.append({
            "category": "risk",
            "title": "Elevated Risk Profile",
            "description": "High concentration in single markets/trades. Consider this when replicating strategy.",
            "importance": "high"
        })

    # Pair trade insights
    pair_trades = analysis.get("pair_trades", {})
    pair_summary = pair_trades.get("summary", {})
    if pair_summary.get("total_pair_trades", 0) > 0:
        total_pairs = pair_summary.get("total_pair_trades", 0)
        hedge_volume = pair_summary.get("total_hedge_volume", 0)
        arb_count = pair_summary.get("arbitrage_trades", 0)
        arb_profit = pair_summary.get("total_arb_profit", 0)
        quick_pairs = pair_summary.get("quick_pairs_under_60s", 0)

        if arb_count > 0:
            insights.append({
                "category": "pair_trades",
                "title": "Arbitrage Activity Detected",
                "description": f"{arb_count} arbitrage opportunities captured totaling ${arb_profit:,.2f} profit. Buying both sides when prices sum to < $1.",
                "importance": "high"
            })

        if total_pairs > 10:
            insights.append({
                "category": "pair_trades",
                "title": "Frequent Hedging Behavior",
                "description": f"{total_pairs} pair trades detected across {pair_summary.get('hedged_markets', 0)} markets. Total hedged volume: ${hedge_volume:,.2f}.",
                "importance": "high"
            })
        elif total_pairs > 0:
            insights.append({
                "category": "pair_trades",
                "title": "Hedging Activity",
                "description": f"{total_pairs} pair trade(s) detected - buying both sides of same market to hedge risk.",
                "importance": "medium"
            })

        if quick_pairs > 5:
            insights.append({
                "category": "pair_trades",
                "title": "Rapid Pair Execution",
                "description": f"{quick_pairs} pair trades executed within 60 seconds. Indicates systematic hedging strategy.",
                "importance": "medium"
            })

    # Frequency insights
    frequency = analysis.get("frequency", {})
    freq_summary = frequency.get("summary", {})
    bursts = frequency.get("bursts", {})
    gaps = frequency.get("gaps", {})

    if frequency.get("is_bot_like"):
        insights.append({
            "category": "frequency",
            "title": "Bot-Like Trading Pattern",
            "description": f"{gaps.get('sub_second_percentage', 0):.1f}% of trades executed within 1 second of each other. Likely automated trading.",
            "importance": "high"
        })
    elif frequency.get("is_high_frequency"):
        insights.append({
            "category": "frequency",
            "title": "High-Frequency Trading",
            "description": f"Peak of {freq_summary.get('max_trades_per_second', 0)} trades/second, {freq_summary.get('max_trades_per_minute', 0)} trades/minute detected.",
            "importance": "high"
        })

    if bursts.get("total_bursts", 0) > 10:
        largest_burst = bursts.get("largest_burst", {})
        insights.append({
            "category": "frequency",
            "title": "Burst Trading Pattern",
            "description": f"{bursts.get('total_bursts', 0)} trading bursts detected. Largest burst: {largest_burst.get('trade_count', 0)} trades in {largest_burst.get('duration_seconds', 0):.1f}s.",
            "importance": "medium"
        })

    if gaps.get("avg_seconds_between_trades", 0) < 30:
        insights.append({
            "category": "frequency",
            "title": "Rapid-Fire Trading",
            "description": f"Average gap between trades: {gaps.get('avg_seconds_between_trades', 0):.1f} seconds. Very active trader.",
            "importance": "medium"
        })

    # P&L insights
    pnl = analysis.get("pnl", {}).get("summary", {})
    if pnl:
        win_rate = pnl.get("win_rate", 0)
        net_pnl = pnl.get("net_pnl", 0)
        profit_factor = pnl.get("profit_factor", 0)

        if win_rate > 60:
            insights.append({
                "category": "performance",
                "title": "Strong Win Rate",
                "description": f"{win_rate:.1f}% win rate indicates consistent profitable trading.",
                "importance": "high"
            })
        elif win_rate < 40 and win_rate > 0:
            insights.append({
                "category": "performance",
                "title": "Low Win Rate",
                "description": f"{win_rate:.1f}% win rate. May rely on larger wins to offset frequent losses.",
                "importance": "medium"
            })

        if net_pnl > 10000:
            insights.append({
                "category": "performance",
                "title": "Highly Profitable",
                "description": f"Net P&L of ${net_pnl:,.2f}. This wallet has generated significant returns.",
                "importance": "high"
            })
        elif net_pnl < -5000:
            insights.append({
                "category": "performance",
                "title": "Significant Losses",
                "description": f"Net P&L of ${net_pnl:,.2f}. Strategy may need review.",
                "importance": "high"
            })

        if profit_factor > 2:
            insights.append({
                "category": "performance",
                "title": "Excellent Risk/Reward",
                "description": f"Profit factor of {profit_factor:.2f}. Wins significantly outpace losses.",
                "importance": "high"
            })

    return insights


def generate_report(analysis: Dict, wallet: str, username: str = None) -> str:
    """Generate a markdown report from analysis."""
    report = []
    report.append(f"# PolyEdge Analysis Report")
    report.append(f"**Wallet:** `{wallet}`")
    if username:
        report.append(f"**Username:** {username}")
    report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")

    # Summary
    summary = analysis.get("summary", {})
    report.append("## Summary Statistics")
    report.append(f"- **Total Trades:** {summary.get('total_trades', 0):,}")
    report.append(f"- **Total Volume:** ${summary.get('total_volume_usd', 0):,.2f}")
    report.append(f"- **Buys/Sells:** {summary.get('total_buys', 0):,} / {summary.get('total_sells', 0):,}")
    report.append(f"- **Avg Trade Size:** ${summary.get('avg_trade_size', 0):,.2f}")
    report.append(f"- **Trades Per Day:** {summary.get('trades_per_day', 0):.1f}")
    report.append(f"- **Active Period:** {summary.get('days_active', 0)} days")
    report.append("")

    # Key Insights
    insights = analysis.get("insights", [])
    if insights:
        report.append("## Key Insights")
        for insight in insights:
            importance = insight.get("importance", "low")
            icon = "🔴" if importance == "high" else "🟡" if importance == "medium" else "🟢"
            report.append(f"### {icon} {insight.get('title')}")
            report.append(f"{insight.get('description')}")
            report.append("")

    # Position Sizing
    sizing = analysis.get("position_sizing", {})
    report.append("## Position Sizing Analysis")
    report.append(f"- **Style:** {sizing.get('sizing_style', 'N/A').replace('_', ' ').title()}")
    report.append(f"- **Median Size:** ${sizing.get('percentiles', {}).get('p50', 0):,.2f}")
    report.append(f"- **95th Percentile:** ${sizing.get('percentiles', {}).get('p95', 0):,.2f}")
    dist = sizing.get("distribution", {})
    report.append(f"- **Distribution:** Micro {dist.get('micro', 0)}% | Small {dist.get('small', 0)}% | Medium {dist.get('medium', 0)}% | Large {dist.get('large', 0)}% | Whale {dist.get('whale', 0)}%")
    report.append("")

    # Market Analysis
    markets = analysis.get("market_analysis", {})
    report.append("## Market Analysis")
    report.append(f"- **Unique Markets:** {markets.get('unique_markets', 0)}")
    report.append(f"- **Top 5 Concentration:** {markets.get('concentration_top5', 0)}%")
    report.append(f"- **Diversification Score:** {markets.get('diversification_score', 0)}/100")
    report.append("")
    report.append("### Top Markets by Volume")
    for m in markets.get("top_markets", [])[:10]:
        report.append(f"- {m.get('name', 'Unknown')[:50]}: ${m.get('volume', 0):,.0f} ({m.get('trade_count', 0)} trades)")
    report.append("")

    # Behavioral Patterns
    behavior = analysis.get("behavioral_patterns", {})
    classification = behavior.get("trader_classification", {})
    report.append("## Behavioral Analysis")
    report.append(f"- **Trader Type:** {classification.get('primary_type', 'Unknown').replace('_', ' ').title()}")
    report.append(f"- **Rapid Trading:** {behavior.get('rapid_trading_percentage', 0):.1f}% of trades within 1 minute")
    report.append(f"- **Averaging Behavior:** {behavior.get('averaging_behavior_count', 0)} instances detected")
    report.append("")

    # Risk Metrics
    risk = analysis.get("risk_metrics", {})
    report.append("## Risk Metrics")
    report.append(f"- **Max Single Trade Risk:** {risk.get('max_single_trade_risk', 0):.1f}%")
    report.append(f"- **Market Concentration Risk:** {risk.get('market_concentration_risk', 0):.1f}%")
    report.append(f"- **Overall Risk Score:** {risk.get('risk_score', 0):.0f}/100")
    report.append("")

    # P&L Analysis
    pnl = analysis.get("pnl", {})
    if pnl:
        pnl_summary = pnl.get("summary", {})
        report.append("## Win/Loss Analysis")
        report.append(f"- **Total Positions:** {pnl_summary.get('total_positions', 0)}")
        report.append(f"- **Wins:** {pnl_summary.get('wins', 0)} | **Losses:** {pnl_summary.get('losses', 0)} | **Pending:** {pnl_summary.get('pending', 0)}")
        report.append(f"- **Win Rate:** {pnl_summary.get('win_rate', 0):.1f}%")
        report.append(f"- **Total Profit:** ${pnl_summary.get('total_profit', 0):,.2f}")
        report.append(f"- **Total Loss:** ${pnl_summary.get('total_loss', 0):,.2f}")
        report.append(f"- **Net P&L:** ${pnl_summary.get('net_pnl', 0):,.2f}")
        report.append(f"- **Profit Factor:** {pnl_summary.get('profit_factor', 0):.2f}")
        report.append("")

        best = pnl.get("best_trade")
        worst = pnl.get("worst_trade")
        if best:
            report.append(f"### Best Trade")
            report.append(f"- **Market:** {best.get('market', 'Unknown')}")
            report.append(f"- **P&L:** ${best.get('pnl', 0):,.2f}")
            report.append("")
        if worst and worst.get("pnl", 0) < 0:
            report.append(f"### Worst Trade")
            report.append(f"- **Market:** {worst.get('market', 'Unknown')}")
            report.append(f"- **P&L:** ${worst.get('pnl', 0):,.2f}")
            report.append("")

    report.append("---")
    report.append("*Generated by PolyEdge.io*")

    return "\n".join(report)
