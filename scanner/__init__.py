"""
PolyClaw Market Scanner

Scans prediction markets for trading opportunities.
Identifies momentum, arbitrage, and value plays.
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger("polyclaw.scanner")

GAMMA_API = "https://gamma-api.polymarket.com"


class MarketScanner:
    """
    Scans Polymarket for trading opportunities.
    """
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 60  # seconds
    
    def _fetch_markets(self, limit: int = 100) -> List[Dict]:
        """Fetch active markets"""
        cache_key = f"markets_{limit}"
        
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now() - cached["time"]).seconds < self.cache_ttl:
                return cached["data"]
        
        try:
            response = requests.get(
                f"{GAMMA_API}/markets",
                params={"limit": limit, "active": "true"},
                timeout=10
            )
            markets = response.json()
            
            self.cache[cache_key] = {
                "data": markets,
                "time": datetime.now(),
            }
            return markets
        except Exception as e:
            logger.error(f"Failed to fetch markets: {e}")
            return []
    
    def scan_momentum(self, threshold: float = 0.05) -> List[Dict]:
        """
        Find markets with significant price movement.
        
        Args:
            threshold: Minimum price change (e.g., 0.05 = 5%)
        
        Returns:
            List of markets showing momentum
        """
        markets = self._fetch_markets()
        opportunities = []
        
        for market in markets:
            # Get price change (if available)
            volume_24h = market.get("volume24hr", 0)
            
            # High volume markets more likely to have momentum
            if volume_24h > 10000:  # $10k+ volume
                opportunities.append({
                    "type": "momentum",
                    "market_id": market.get("condition_id"),
                    "question": market.get("question"),
                    "volume_24h": volume_24h,
                    "liquidity": market.get("liquidity", 0),
                    "outcomes": market.get("outcomes", []),
                    "prices": market.get("outcomePrices", []),
                    "signal": "high_volume",
                })
        
        # Sort by volume
        opportunities.sort(key=lambda x: x["volume_24h"], reverse=True)
        return opportunities[:10]
    
    def scan_value(self, min_edge: float = 0.10) -> List[Dict]:
        """
        Find potentially mispriced markets.
        
        Uses heuristics like:
        - Extreme prices (near 0 or 1)
        - Low liquidity (may be inefficient)
        - Recent large moves (possible overreaction)
        
        Args:
            min_edge: Minimum potential edge
        
        Returns:
            List of potentially mispriced markets
        """
        markets = self._fetch_markets()
        opportunities = []
        
        for market in markets:
            prices = market.get("outcomePrices", [])
            liquidity = market.get("liquidity", 0)
            
            for i, price in enumerate(prices):
                try:
                    p = float(price)
                except:
                    continue
                
                # Extreme prices often have edge
                if p < 0.10 or p > 0.90:
                    opportunities.append({
                        "type": "value",
                        "market_id": market.get("condition_id"),
                        "question": market.get("question"),
                        "outcome_index": i,
                        "outcome": market.get("outcomes", [])[i] if i < len(market.get("outcomes", [])) else "?",
                        "price": p,
                        "liquidity": liquidity,
                        "signal": "extreme_price",
                        "potential_edge": "high" if p < 0.05 or p > 0.95 else "medium",
                    })
        
        return opportunities[:20]
    
    def scan_liquidity(self, min_liquidity: float = 50000) -> List[Dict]:
        """
        Find highly liquid markets for safer trading.
        
        Args:
            min_liquidity: Minimum liquidity threshold
        
        Returns:
            List of liquid markets
        """
        markets = self._fetch_markets()
        opportunities = []
        
        for market in markets:
            liquidity = market.get("liquidity", 0)
            
            if liquidity >= min_liquidity:
                opportunities.append({
                    "type": "liquid",
                    "market_id": market.get("condition_id"),
                    "question": market.get("question"),
                    "liquidity": liquidity,
                    "volume_24h": market.get("volume24hr", 0),
                    "outcomes": market.get("outcomes", []),
                    "prices": market.get("outcomePrices", []),
                })
        
        opportunities.sort(key=lambda x: x["liquidity"], reverse=True)
        return opportunities[:20]
    
    def scan_closing_soon(self, hours: int = 72) -> List[Dict]:
        """
        Find markets closing soon (resolution imminent).
        
        Args:
            hours: Hours until market closes
        
        Returns:
            List of markets closing soon
        """
        markets = self._fetch_markets()
        opportunities = []
        cutoff = datetime.now() + timedelta(hours=hours)
        
        for market in markets:
            end_date = market.get("end_date_iso")
            if not end_date:
                continue
            
            try:
                end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                if end.replace(tzinfo=None) < cutoff:
                    hours_remaining = (end.replace(tzinfo=None) - datetime.now()).total_seconds() / 3600
                    
                    if hours_remaining > 0:
                        opportunities.append({
                            "type": "closing_soon",
                            "market_id": market.get("condition_id"),
                            "question": market.get("question"),
                            "end_date": end_date,
                            "hours_remaining": hours_remaining,
                            "outcomes": market.get("outcomes", []),
                            "prices": market.get("outcomePrices", []),
                        })
            except:
                continue
        
        opportunities.sort(key=lambda x: x["hours_remaining"])
        return opportunities[:20]
    
    def scan_new_markets(self, hours: int = 24) -> List[Dict]:
        """
        Find recently created markets.
        
        Args:
            hours: How recent
        
        Returns:
            List of new markets
        """
        markets = self._fetch_markets(limit=200)
        opportunities = []
        cutoff = datetime.now() - timedelta(hours=hours)
        
        for market in markets:
            created = market.get("created_at")
            if not created:
                continue
            
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                if created_dt.replace(tzinfo=None) > cutoff:
                    opportunities.append({
                        "type": "new_market",
                        "market_id": market.get("condition_id"),
                        "question": market.get("question"),
                        "created_at": created,
                        "liquidity": market.get("liquidity", 0),
                        "outcomes": market.get("outcomes", []),
                        "prices": market.get("outcomePrices", []),
                    })
            except:
                continue
        
        return opportunities[:20]
    
    def scan_all(self) -> Dict:
        """
        Run all scans and return combined results.
        
        Returns:
            Dict with all opportunity types
        """
        return {
            "momentum": self.scan_momentum(),
            "value": self.scan_value(),
            "liquid": self.scan_liquidity(),
            "closing_soon": self.scan_closing_soon(),
            "new_markets": self.scan_new_markets(),
            "scanned_at": datetime.now().isoformat(),
        }


class AlertGenerator:
    """
    Generates alerts for trading opportunities.
    """
    
    def __init__(self, scanner: MarketScanner = None):
        self.scanner = scanner or MarketScanner()
        self.last_scan = None
        self.seen_opportunities = set()
    
    def check_for_alerts(self) -> List[Dict]:
        """
        Check for new opportunities since last scan.
        
        Returns:
            List of new alerts
        """
        results = self.scanner.scan_all()
        alerts = []
        
        # Check each opportunity type
        for opp_type, opportunities in results.items():
            if opp_type == "scanned_at":
                continue
            
            for opp in opportunities:
                opp_id = f"{opp_type}:{opp.get('market_id', '')}:{opp.get('outcome_index', 0)}"
                
                if opp_id not in self.seen_opportunities:
                    self.seen_opportunities.add(opp_id)
                    alerts.append({
                        "type": "opportunity",
                        "opportunity_type": opp_type,
                        "data": opp,
                        "timestamp": datetime.now().isoformat(),
                    })
        
        # Limit memory of seen opportunities
        if len(self.seen_opportunities) > 1000:
            self.seen_opportunities = set(list(self.seen_opportunities)[-500:])
        
        self.last_scan = datetime.now()
        return alerts


# Singleton instances
_scanner = None
_alert_generator = None


def get_scanner() -> MarketScanner:
    global _scanner
    if _scanner is None:
        _scanner = MarketScanner()
    return _scanner


def get_alert_generator() -> AlertGenerator:
    global _alert_generator
    if _alert_generator is None:
        _alert_generator = AlertGenerator(get_scanner())
    return _alert_generator
