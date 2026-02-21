"""
PolyClaw Tools (MCP-style)

Tools the AI agent can use to interact with prediction markets.
Similar to OpenClaw's MCP tools but specialized for trading.
"""

import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

# Tool registry
TOOLS = {}


def tool(name: str, description: str):
    """Decorator to register a tool"""
    def decorator(func):
        TOOLS[name] = {
            "name": name,
            "description": description,
            "function": func,
        }
        return func
    return decorator


# ============================================================
# POLYMARKET TOOLS
# ============================================================

POLYMARKET_API = "https://clob.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"


@tool("polymarket_markets", "Search and list Polymarket markets")
def polymarket_markets(query: str = None, limit: int = 20, active_only: bool = True) -> Dict:
    """
    Search Polymarket markets.
    
    Args:
        query: Search term (optional)
        limit: Max results
        active_only: Only show active markets
    
    Returns:
        List of markets with odds and volume
    """
    try:
        url = f"{GAMMA_API}/markets"
        params = {"limit": limit}
        if active_only:
            params["active"] = "true"
        
        response = requests.get(url, params=params, timeout=10)
        markets = response.json()
        
        if query:
            query = query.lower()
            markets = [m for m in markets if query in m.get("question", "").lower()]
        
        results = []
        for m in markets[:limit]:
            results.append({
                "id": m.get("condition_id"),
                "question": m.get("question"),
                "outcomes": m.get("outcomes", []),
                "volume": m.get("volume", 0),
                "liquidity": m.get("liquidity", 0),
                "end_date": m.get("end_date_iso"),
            })
        
        return {"success": True, "markets": results, "count": len(results)}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool("polymarket_price", "Get current price/odds for a market")
def polymarket_price(market_id: str) -> Dict:
    """
    Get current price for a Polymarket market.
    
    Args:
        market_id: The market condition ID
    
    Returns:
        Current prices for all outcomes
    """
    try:
        url = f"{GAMMA_API}/markets/{market_id}"
        response = requests.get(url, timeout=10)
        market = response.json()
        
        return {
            "success": True,
            "question": market.get("question"),
            "prices": market.get("outcomePrices", []),
            "outcomes": market.get("outcomes", []),
            "volume_24h": market.get("volume24hr", 0),
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool("polymarket_orderbook", "Get orderbook depth for a market")
def polymarket_orderbook(token_id: str, side: str = "both") -> Dict:
    """
    Get orderbook for a Polymarket token.
    
    Args:
        token_id: The token ID
        side: "buy", "sell", or "both"
    
    Returns:
        Orderbook with bids and asks
    """
    try:
        url = f"{CLOB_API}/book"
        params = {"token_id": token_id}
        response = requests.get(url, params=params, timeout=10)
        book = response.json()
        
        return {
            "success": True,
            "bids": book.get("bids", [])[:10],
            "asks": book.get("asks", [])[:10],
            "spread": calculate_spread(book),
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def calculate_spread(book: Dict) -> float:
    """Calculate bid-ask spread"""
    bids = book.get("bids", [])
    asks = book.get("asks", [])
    if bids and asks:
        best_bid = float(bids[0].get("price", 0))
        best_ask = float(asks[0].get("price", 1))
        return best_ask - best_bid
    return 0


@tool("wallet_trades", "Get recent trades for a wallet")
def wallet_trades(wallet: str, limit: int = 100) -> Dict:
    """
    Fetch trades for a Polymarket wallet.
    
    Args:
        wallet: Wallet address
        limit: Max trades to fetch
    
    Returns:
        List of trades with details
    """
    try:
        # Use local gateway
        response = requests.get(
            f"http://localhost:8080/api/trades/{wallet}",
            params={"limit": limit},
            timeout=30
        )
        return response.json()
    
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool("wallet_analysis", "Analyze a wallet's trading performance")
def wallet_analysis(wallet: str) -> Dict:
    """
    Full analysis of a wallet's performance.
    
    Args:
        wallet: Wallet address
    
    Returns:
        P&L, win rate, strategy classification, etc.
    """
    try:
        response = requests.get(
            f"http://localhost:8080/api/analyze/{wallet}",
            timeout=30
        )
        return response.json()
    
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool("compare_wallets", "Compare performance of multiple wallets")
def compare_wallets(wallets: List[str]) -> Dict:
    """
    Compare multiple wallets side by side.
    
    Args:
        wallets: List of wallet addresses
    
    Returns:
        Comparison metrics
    """
    try:
        wallet_str = ",".join(wallets)
        response = requests.get(
            f"http://localhost:8080/api/compare",
            params={"wallets": wallet_str},
            timeout=30
        )
        return response.json()
    
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool("leaderboard", "Get top performing wallets")
def leaderboard(limit: int = 20) -> Dict:
    """
    Get leaderboard of top performers.
    
    Args:
        limit: Number of wallets to return
    
    Returns:
        Ranked list of wallets by P&L
    """
    try:
        response = requests.get(
            "http://localhost:8080/api/leaderboard",
            params={"limit": limit},
            timeout=30
        )
        return response.json()
    
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# ANALYSIS TOOLS
# ============================================================

@tool("kelly_criterion", "Calculate optimal bet size using Kelly criterion")
def kelly_criterion(win_prob: float, odds: float, bankroll: float = 1000) -> Dict:
    """
    Calculate optimal bet size using Kelly criterion.
    
    Args:
        win_prob: Probability of winning (0-1)
        odds: Decimal odds (e.g., 2.0 for even money)
        bankroll: Total bankroll
    
    Returns:
        Optimal bet size and Kelly fraction
    """
    # Kelly formula: f* = (bp - q) / b
    # where b = odds - 1, p = win prob, q = 1 - p
    b = odds - 1
    p = win_prob
    q = 1 - p
    
    kelly_fraction = (b * p - q) / b if b > 0 else 0
    kelly_fraction = max(0, min(1, kelly_fraction))  # Clamp 0-1
    
    # Half Kelly for safety
    half_kelly = kelly_fraction / 2
    
    return {
        "success": True,
        "kelly_fraction": kelly_fraction,
        "kelly_bet": bankroll * kelly_fraction,
        "half_kelly_fraction": half_kelly,
        "half_kelly_bet": bankroll * half_kelly,
        "edge": (p * odds) - 1,
        "expected_value": (p * (odds - 1)) - q,
    }


@tool("expected_value", "Calculate expected value of a bet")
def expected_value(win_prob: float, win_amount: float, lose_amount: float) -> Dict:
    """
    Calculate expected value of a bet.
    
    Args:
        win_prob: Probability of winning (0-1)
        win_amount: Amount won if bet wins
        lose_amount: Amount lost if bet loses
    
    Returns:
        Expected value and other metrics
    """
    ev = (win_prob * win_amount) - ((1 - win_prob) * lose_amount)
    roi = ev / lose_amount if lose_amount > 0 else 0
    
    return {
        "success": True,
        "expected_value": ev,
        "roi_percent": roi * 100,
        "is_positive_ev": ev > 0,
        "breakeven_prob": lose_amount / (win_amount + lose_amount),
    }


@tool("sharpe_ratio", "Calculate Sharpe ratio for a series of returns")
def sharpe_ratio(returns: List[float], risk_free_rate: float = 0.05) -> Dict:
    """
    Calculate Sharpe ratio.
    
    Args:
        returns: List of returns (as decimals, e.g., 0.05 for 5%)
        risk_free_rate: Annual risk-free rate
    
    Returns:
        Sharpe ratio and related metrics
    """
    import statistics
    
    if len(returns) < 2:
        return {"success": False, "error": "Need at least 2 returns"}
    
    mean_return = statistics.mean(returns)
    std_dev = statistics.stdev(returns)
    
    # Annualize (assuming daily returns)
    annual_return = mean_return * 252
    annual_std = std_dev * (252 ** 0.5)
    
    sharpe = (annual_return - risk_free_rate) / annual_std if annual_std > 0 else 0
    
    return {
        "success": True,
        "sharpe_ratio": sharpe,
        "mean_return": mean_return,
        "std_dev": std_dev,
        "annual_return": annual_return,
        "annual_volatility": annual_std,
    }


@tool("drawdown", "Calculate maximum drawdown from a series of values")
def drawdown(values: List[float]) -> Dict:
    """
    Calculate maximum drawdown.
    
    Args:
        values: List of portfolio values over time
    
    Returns:
        Max drawdown and related metrics
    """
    if len(values) < 2:
        return {"success": False, "error": "Need at least 2 values"}
    
    peak = values[0]
    max_dd = 0
    max_dd_start = 0
    max_dd_end = 0
    current_dd_start = 0
    
    for i, value in enumerate(values):
        if value > peak:
            peak = value
            current_dd_start = i
        
        dd = (peak - value) / peak if peak > 0 else 0
        
        if dd > max_dd:
            max_dd = dd
            max_dd_start = current_dd_start
            max_dd_end = i
    
    return {
        "success": True,
        "max_drawdown": max_dd,
        "max_drawdown_percent": max_dd * 100,
        "drawdown_start_index": max_dd_start,
        "drawdown_end_index": max_dd_end,
        "current_drawdown": (peak - values[-1]) / peak if peak > 0 else 0,
    }


# ============================================================
# STRATEGY TOOLS
# ============================================================

@tool("detect_strategy", "Detect trading strategy from trade history")
def detect_strategy(trades: List[Dict]) -> Dict:
    """
    Analyze trades to detect the trading strategy being used.
    
    Args:
        trades: List of trade dictionaries
    
    Returns:
        Strategy classification and confidence
    """
    if not trades:
        return {"success": False, "error": "No trades provided"}
    
    # Analyze patterns
    buy_count = sum(1 for t in trades if t.get("side", "").upper() == "BUY")
    sell_count = len(trades) - buy_count
    
    # Calculate hold times
    hold_times = []
    amounts = [float(t.get("amount", 0)) for t in trades]
    avg_amount = sum(amounts) / len(amounts) if amounts else 0
    
    # Determine strategy
    strategies = []
    
    # Momentum: More buys than sells, larger positions
    if buy_count > sell_count * 1.5:
        strategies.append(("momentum", 0.7))
    
    # Mean reversion: Balanced buys/sells
    if 0.8 < buy_count / max(sell_count, 1) < 1.2:
        strategies.append(("mean_reversion", 0.6))
    
    # Scalping: Many small trades
    if len(trades) > 50 and avg_amount < 100:
        strategies.append(("scalping", 0.8))
    
    # Large position: Few big trades
    if len(trades) < 20 and avg_amount > 1000:
        strategies.append(("concentrated", 0.7))
    
    # Sort by confidence
    strategies.sort(key=lambda x: x[1], reverse=True)
    
    primary = strategies[0] if strategies else ("unknown", 0.5)
    
    return {
        "success": True,
        "primary_strategy": primary[0],
        "confidence": primary[1],
        "all_strategies": strategies,
        "trade_count": len(trades),
        "buy_ratio": buy_count / len(trades) if trades else 0,
    }


@tool("backtest_strategy", "Backtest a simple strategy on historical data")
def backtest_strategy(
    strategy: str,
    market_id: str = None,
    start_date: str = None,
    initial_capital: float = 1000,
) -> Dict:
    """
    Backtest a trading strategy.
    
    Args:
        strategy: Strategy name (momentum, mean_reversion, etc.)
        market_id: Market to backtest on (optional)
        start_date: Start date for backtest
        initial_capital: Starting capital
    
    Returns:
        Backtest results with P&L and metrics
    """
    # This is a simplified backtest framework
    # In production, would use actual historical data
    
    return {
        "success": True,
        "strategy": strategy,
        "note": "Full backtesting requires historical data integration",
        "recommendation": "Use wallet_analysis to study real trader performance",
    }


# ============================================================
# TOOL EXECUTION
# ============================================================

def list_tools() -> List[Dict]:
    """List all available tools"""
    return [
        {"name": name, "description": info["description"]}
        for name, info in TOOLS.items()
    ]


def execute_tool(name: str, **kwargs) -> Dict:
    """Execute a tool by name"""
    if name not in TOOLS:
        return {"success": False, "error": f"Unknown tool: {name}"}
    
    try:
        result = TOOLS[name]["function"](**kwargs)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_tool_schema(name: str) -> Dict:
    """Get schema for a tool"""
    if name not in TOOLS:
        return None
    
    tool = TOOLS[name]
    func = tool["function"]
    
    # Get function signature
    import inspect
    sig = inspect.signature(func)
    
    params = {}
    for param_name, param in sig.parameters.items():
        param_info = {"type": "string"}
        if param.default != inspect.Parameter.empty:
            param_info["default"] = param.default
        if param.annotation != inspect.Parameter.empty:
            param_info["type"] = param.annotation.__name__
        params[param_name] = param_info
    
    return {
        "name": name,
        "description": tool["description"],
        "parameters": params,
    }
