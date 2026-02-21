"""
PolyClaw Strategy Library

Pre-built trading strategies for prediction markets.
Users can browse, customize, and deploy these strategies.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

STRATEGIES_DIR = Path.home() / ".polyclaw" / "strategies"
STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)


class Strategy:
    """Base class for trading strategies"""
    
    def __init__(
        self,
        name: str,
        description: str,
        category: str,
        parameters: Dict = None,
    ):
        self.name = name
        self.description = description
        self.category = category
        self.parameters = parameters or {}
        self.created = datetime.now()
        self.trades = []
        self.performance = {}
    
    def should_enter(self, market_data: Dict) -> bool:
        """Determine if strategy should enter a position"""
        raise NotImplementedError
    
    def should_exit(self, position: Dict, market_data: Dict) -> bool:
        """Determine if strategy should exit a position"""
        raise NotImplementedError
    
    def position_size(self, capital: float, market_data: Dict) -> float:
        """Calculate position size"""
        risk_percent = self.parameters.get("risk_percent", 0.02)
        return capital * risk_percent
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "parameters": self.parameters,
            "created": self.created.isoformat(),
            "performance": self.performance,
        }


# ============================================================
# PRE-BUILT STRATEGIES
# ============================================================

class MomentumStrategy(Strategy):
    """
    Momentum Strategy
    
    Trades in the direction of recent price movement.
    Best for breaking news and trending events.
    """
    
    def __init__(self, lookback_hours: int = 24, threshold: float = 0.05):
        super().__init__(
            name="Momentum",
            description="Trade in direction of price momentum",
            category="trend_following",
            parameters={
                "lookback_hours": lookback_hours,
                "threshold": threshold,
                "exit_reversal": 0.02,
            }
        )
    
    def should_enter(self, market_data: Dict) -> bool:
        price_change = market_data.get("price_change_24h", 0)
        threshold = self.parameters["threshold"]
        
        if abs(price_change) > threshold:
            return True
        return False
    
    def should_exit(self, position: Dict, market_data: Dict) -> bool:
        entry_price = position.get("entry_price", 0)
        current_price = market_data.get("current_price", 0)
        direction = position.get("direction", "long")
        
        if direction == "long":
            return current_price < entry_price * (1 - self.parameters["exit_reversal"])
        else:
            return current_price > entry_price * (1 + self.parameters["exit_reversal"])


class MeanReversionStrategy(Strategy):
    """
    Mean Reversion Strategy
    
    Bets that extreme prices return to average.
    Best for stable markets and overreactions.
    """
    
    def __init__(self, lookback_days: int = 7, deviation_threshold: float = 0.10):
        super().__init__(
            name="Mean Reversion",
            description="Bet on prices returning to average",
            category="mean_reversion",
            parameters={
                "lookback_days": lookback_days,
                "deviation_threshold": deviation_threshold,
            }
        )
    
    def should_enter(self, market_data: Dict) -> bool:
        current_price = market_data.get("current_price", 0.5)
        avg_price = market_data.get("avg_price_7d", 0.5)
        
        deviation = abs(current_price - avg_price) / avg_price if avg_price > 0 else 0
        
        return deviation > self.parameters["deviation_threshold"]
    
    def should_exit(self, position: Dict, market_data: Dict) -> bool:
        current_price = market_data.get("current_price", 0.5)
        avg_price = market_data.get("avg_price_7d", 0.5)
        
        # Exit when price returns to average
        deviation = abs(current_price - avg_price) / avg_price if avg_price > 0 else 0
        return deviation < 0.02  # Within 2% of average


class ValueStrategy(Strategy):
    """
    Value Strategy
    
    Identifies mispriced markets using research.
    Requires user to input their probability estimate.
    """
    
    def __init__(self, min_edge: float = 0.10):
        super().__init__(
            name="Value",
            description="Trade when market differs from your estimate",
            category="value",
            parameters={
                "min_edge": min_edge,
                "kelly_fraction": 0.5,  # Half Kelly
            }
        )
    
    def should_enter(self, market_data: Dict) -> bool:
        market_prob = market_data.get("market_probability", 0.5)
        user_prob = market_data.get("user_probability", 0.5)
        
        edge = abs(user_prob - market_prob)
        return edge > self.parameters["min_edge"]
    
    def should_exit(self, position: Dict, market_data: Dict) -> bool:
        # Exit when market agrees with estimate
        market_prob = market_data.get("market_probability", 0.5)
        user_prob = position.get("user_probability", 0.5)
        
        return abs(user_prob - market_prob) < 0.03
    
    def position_size(self, capital: float, market_data: Dict) -> float:
        """Use Kelly criterion for position sizing"""
        market_prob = market_data.get("market_probability", 0.5)
        user_prob = market_data.get("user_probability", 0.5)
        
        # Kelly formula
        odds = 1 / market_prob if market_prob > 0 else 2
        b = odds - 1
        p = user_prob
        q = 1 - p
        
        kelly = (b * p - q) / b if b > 0 else 0
        kelly = max(0, min(0.25, kelly))  # Cap at 25%
        
        # Use half Kelly
        return capital * kelly * self.parameters["kelly_fraction"]


class WhaleFollowStrategy(Strategy):
    """
    Whale Follow Strategy
    
    Follows trades from profitable wallets.
    Tracks specified whale addresses.
    """
    
    def __init__(self, whale_wallets: List[str] = None, delay_minutes: int = 5):
        super().__init__(
            name="Whale Follow",
            description="Copy trades from profitable wallets",
            category="copy_trading",
            parameters={
                "whale_wallets": whale_wallets or [],
                "delay_minutes": delay_minutes,
                "max_position_pct": 0.05,
            }
        )
    
    def should_enter(self, market_data: Dict) -> bool:
        # Check if any tracked whale has entered
        whale_trades = market_data.get("recent_whale_trades", [])
        
        for trade in whale_trades:
            if trade.get("wallet") in self.parameters["whale_wallets"]:
                return True
        return False
    
    def should_exit(self, position: Dict, market_data: Dict) -> bool:
        # Exit if whale exits
        whale_trades = market_data.get("recent_whale_trades", [])
        
        for trade in whale_trades:
            if (trade.get("wallet") in self.parameters["whale_wallets"] and
                trade.get("side", "").upper() == "SELL"):
                return True
        return False


class ArbitrageStrategy(Strategy):
    """
    Arbitrage Strategy
    
    Exploits price differences across platforms.
    Requires capital on multiple platforms.
    """
    
    def __init__(self, min_spread: float = 0.02):
        super().__init__(
            name="Arbitrage",
            description="Exploit cross-platform price differences",
            category="arbitrage",
            parameters={
                "min_spread": min_spread,
                "platforms": ["polymarket", "kalshi"],
            }
        )
    
    def should_enter(self, market_data: Dict) -> bool:
        prices = market_data.get("cross_platform_prices", {})
        
        if len(prices) < 2:
            return False
        
        price_list = list(prices.values())
        spread = max(price_list) - min(price_list)
        
        return spread > self.parameters["min_spread"]
    
    def should_exit(self, position: Dict, market_data: Dict) -> bool:
        # Exit when spread closes
        prices = market_data.get("cross_platform_prices", {})
        
        if len(prices) < 2:
            return True
        
        price_list = list(prices.values())
        spread = max(price_list) - min(price_list)
        
        return spread < 0.005  # Less than 0.5%


class EventDrivenStrategy(Strategy):
    """
    Event-Driven Strategy
    
    Trades around scheduled events.
    Position before, exit after.
    """
    
    def __init__(self, entry_hours_before: int = 24, exit_hours_after: int = 2):
        super().__init__(
            name="Event-Driven",
            description="Trade around scheduled events",
            category="event_driven",
            parameters={
                "entry_hours_before": entry_hours_before,
                "exit_hours_after": exit_hours_after,
            }
        )
    
    def should_enter(self, market_data: Dict) -> bool:
        event_time = market_data.get("event_time")
        if not event_time:
            return False
        
        hours_until = (event_time - datetime.now()).total_seconds() / 3600
        return 0 < hours_until < self.parameters["entry_hours_before"]
    
    def should_exit(self, position: Dict, market_data: Dict) -> bool:
        event_time = market_data.get("event_time")
        if not event_time:
            return True
        
        hours_since = (datetime.now() - event_time).total_seconds() / 3600
        return hours_since > self.parameters["exit_hours_after"]


# ============================================================
# STRATEGY MANAGER
# ============================================================

BUILT_IN_STRATEGIES = {
    "momentum": MomentumStrategy,
    "mean_reversion": MeanReversionStrategy,
    "value": ValueStrategy,
    "whale_follow": WhaleFollowStrategy,
    "arbitrage": ArbitrageStrategy,
    "event_driven": EventDrivenStrategy,
}


class StrategyManager:
    """Manage user strategies"""
    
    def __init__(self):
        self.strategies_file = STRATEGIES_DIR / "user_strategies.json"
        self._strategies = self._load()
    
    def _load(self) -> Dict:
        if self.strategies_file.exists():
            with open(self.strategies_file) as f:
                return json.load(f)
        return {"strategies": {}}
    
    def _save(self):
        with open(self.strategies_file, 'w') as f:
            json.dump(self._strategies, f, indent=2, default=str)
    
    def list_builtin(self) -> List[Dict]:
        """List built-in strategies"""
        return [
            {
                "name": name,
                "class": cls.__name__,
                "description": cls.__doc__.split("\n")[1].strip() if cls.__doc__ else "",
            }
            for name, cls in BUILT_IN_STRATEGIES.items()
        ]
    
    def list_user(self) -> List[Dict]:
        """List user-defined strategies"""
        return [
            {"name": name, **data}
            for name, data in self._strategies.get("strategies", {}).items()
        ]
    
    def create_strategy(self, name: str, base: str, parameters: Dict = None) -> Dict:
        """Create a new strategy based on a built-in"""
        if base not in BUILT_IN_STRATEGIES:
            return {"success": False, "error": f"Unknown base strategy: {base}"}
        
        strategy_class = BUILT_IN_STRATEGIES[base]
        strategy = strategy_class(**(parameters or {}))
        
        self._strategies["strategies"][name] = {
            "base": base,
            "parameters": strategy.parameters,
            "created": datetime.now().isoformat(),
        }
        self._save()
        
        return {"success": True, "strategy": strategy.to_dict()}
    
    def get_strategy(self, name: str) -> Optional[Strategy]:
        """Get a strategy instance"""
        if name in BUILT_IN_STRATEGIES:
            return BUILT_IN_STRATEGIES[name]()
        
        user_strategy = self._strategies.get("strategies", {}).get(name)
        if user_strategy:
            base = user_strategy.get("base")
            params = user_strategy.get("parameters", {})
            if base in BUILT_IN_STRATEGIES:
                return BUILT_IN_STRATEGIES[base](**params)
        
        return None
    
    def delete_strategy(self, name: str) -> bool:
        """Delete a user strategy"""
        if name in self._strategies.get("strategies", {}):
            del self._strategies["strategies"][name]
            self._save()
            return True
        return False


# Singleton instance
_manager = None

def get_strategy_manager() -> StrategyManager:
    global _manager
    if _manager is None:
        _manager = StrategyManager()
    return _manager
