#!/usr/bin/env python3
"""
PolyClaw Strategy Engine
AI-powered strategy ideation, analysis, diagnosis, and iteration for Polymarket trading.
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict

# Strategy templates for different trading styles
STRATEGY_TEMPLATES = {
    "momentum": {
        "name": "Momentum Trading",
        "description": "Buy assets showing strong price momentum, ride the trend",
        "entry_rules": [
            "Price increased >10% in last 24h",
            "Volume spike >2x average",
            "Price above 0.3 (room to run)"
        ],
        "exit_rules": [
            "Take profit at 50% gain",
            "Stop loss at 20% decline",
            "Exit if momentum reverses (3 red candles)"
        ],
        "position_sizing": "5-10% of bankroll per trade",
        "risk_level": "Medium-High",
        "best_for": "Trending markets with clear catalysts"
    },
    "contrarian": {
        "name": "Contrarian/Mean Reversion",
        "description": "Buy when others are fearful, sell when greedy",
        "entry_rules": [
            "Price dropped >15% in 24h without fundamental change",
            "Sentiment extremely negative",
            "Price below 0.4 (high upside potential)"
        ],
        "exit_rules": [
            "Take profit when sentiment normalizes",
            "Stop loss if new negative catalyst emerges",
            "Scale out in 3 tranches"
        ],
        "position_sizing": "3-5% of bankroll, scale in on dips",
        "risk_level": "High",
        "best_for": "Overreaction to news events"
    },
    "arbitrage": {
        "name": "Arbitrage Trading",
        "description": "Exploit price inefficiencies between related markets",
        "entry_rules": [
            "Related markets have >5% price discrepancy",
            "Both markets have sufficient liquidity",
            "Clear logical relationship exists"
        ],
        "exit_rules": [
            "Exit when spread narrows to <1%",
            "Exit if one market resolves",
            "Time-based exit before resolution"
        ],
        "position_sizing": "Equal size in both legs",
        "risk_level": "Low",
        "best_for": "Correlated prediction markets"
    },
    "event_driven": {
        "name": "Event-Driven Trading",
        "description": "Position before known catalysts (debates, earnings, announcements)",
        "entry_rules": [
            "Major event within 7 days",
            "Market hasn't fully priced in expected outcome",
            "Historical data shows predictable pattern"
        ],
        "exit_rules": [
            "Exit immediately after event",
            "Take profit if price moves 20%+ pre-event",
            "Cut losses if thesis invalidated"
        ],
        "position_sizing": "5% of bankroll, increase if high conviction",
        "risk_level": "Medium",
        "best_for": "Scheduled events with historical precedent"
    },
    "copy_trade": {
        "name": "Copy Trading",
        "description": "Mirror trades of successful wallets with proven track records",
        "entry_rules": [
            "Source wallet has >60% win rate",
            "Source wallet profitable over 90+ days",
            "Trade size >$500 (filters noise)"
        ],
        "exit_rules": [
            "Exit when source wallet exits",
            "Independent stop loss at 25%",
            "Don't follow into illiquid markets"
        ],
        "position_sizing": "50% of source wallet size",
        "risk_level": "Medium",
        "best_for": "Learning from proven traders"
    },
    "scalping": {
        "name": "Scalping",
        "description": "Quick in-and-out trades capturing small price movements",
        "entry_rules": [
            "High liquidity market (>$100k volume)",
            "Tight spread (<2%)",
            "Clear short-term catalyst"
        ],
        "exit_rules": [
            "Take profit at 5-10% gain",
            "Strict stop loss at 3%",
            "Max hold time: 4 hours"
        ],
        "position_sizing": "10-20% of bankroll (quick turnover)",
        "risk_level": "Medium",
        "best_for": "Active traders with time to monitor"
    }
}

# Ideation prompts to help generate strategy ideas
IDEATION_PROMPTS = [
    {
        "category": "Market Selection",
        "prompts": [
            "What markets have predictable patterns around specific events?",
            "Which market categories have the most inefficient pricing?",
            "What markets do top traders focus on?",
            "Are there markets with consistent overreaction to news?"
        ]
    },
    {
        "category": "Entry Timing",
        "prompts": [
            "What signals indicate a good entry point?",
            "How far before an event should I enter?",
            "What volume/price patterns precede big moves?",
            "When do smart money wallets typically enter?"
        ]
    },
    {
        "category": "Position Sizing",
        "prompts": [
            "How much should I risk on high vs low conviction trades?",
            "Should I scale in or enter full size?",
            "What's my maximum exposure to any single market?",
            "How do I size based on my edge strength?"
        ]
    },
    {
        "category": "Exit Strategy",
        "prompts": [
            "What's my take profit target?",
            "Where should I set stop losses?",
            "Should I scale out or exit all at once?",
            "How do I handle winning vs losing positions differently?"
        ]
    },
    {
        "category": "Risk Management",
        "prompts": [
            "What's my maximum daily loss limit?",
            "How many positions can I hold simultaneously?",
            "How do I handle correlated positions?",
            "What's my plan for a losing streak?"
        ]
    }
]


def analyze_wallet_strategy(trades: List[Dict], wallet: str = None) -> Dict:
    """
    Diagnose and analyze the trading strategy of a wallet based on trade history.
    Returns detailed strategy characteristics and recommendations.
    """
    if not trades:
        return {"error": "No trades to analyze"}
    
    # Basic stats
    total_trades = len(trades)
    buys = [t for t in trades if t.get('side') == 'BUY']
    sells = [t for t in trades if t.get('side') == 'SELL']
    
    # Time analysis
    timestamps = [t.get('timestamp', 0) for t in trades if t.get('timestamp')]
    if timestamps:
        time_diffs = []
        sorted_ts = sorted(timestamps)
        for i in range(1, len(sorted_ts)):
            time_diffs.append(sorted_ts[i] - sorted_ts[i-1])
        avg_time_between = sum(time_diffs) / len(time_diffs) if time_diffs else 0
    else:
        avg_time_between = 0
    
    # Position analysis
    positions = defaultdict(list)
    for t in trades:
        market = t.get('title', 'Unknown')
        positions[market].append(t)
    
    # Calculate holding periods by matching buys/sells
    holding_periods = []
    for market, market_trades in positions.items():
        market_buys = [t for t in market_trades if t.get('side') == 'BUY']
        market_sells = [t for t in market_trades if t.get('side') == 'SELL']
        
        for buy in market_buys:
            buy_ts = buy.get('timestamp', 0)
            # Find next sell after this buy
            for sell in market_sells:
                sell_ts = sell.get('timestamp', 0)
                if sell_ts > buy_ts:
                    holding_periods.append((sell_ts - buy_ts) / 3600)  # hours
                    break
    
    avg_holding = sum(holding_periods) / len(holding_periods) if holding_periods else 0
    
    # Trade size analysis
    sizes = [t.get('usdcSize', 0) or 0 for t in trades]
    avg_size = sum(sizes) / len(sizes) if sizes else 0
    max_size = max(sizes) if sizes else 0
    min_size = min(sizes) if sizes else 0
    size_variance = max_size / min_size if min_size > 0 else 0
    
    # Price analysis
    entry_prices = [t.get('price', 0) for t in buys if t.get('price')]
    avg_entry_price = sum(entry_prices) / len(entry_prices) if entry_prices else 0
    
    # Market concentration
    market_volumes = defaultdict(float)
    for t in trades:
        market_volumes[t.get('title', 'Unknown')] += t.get('usdcSize', 0) or 0
    
    total_volume = sum(market_volumes.values())
    top_market_pct = max(market_volumes.values()) / total_volume * 100 if total_volume > 0 else 0
    
    # Classify trading style
    if avg_holding < 1:
        trading_style = "Scalper"
        style_description = "Quick trades, high frequency"
    elif avg_holding < 24:
        trading_style = "Day Trader"
        style_description = "Intraday positions, closes daily"
    elif avg_holding < 168:  # 1 week
        trading_style = "Swing Trader"
        style_description = "Multi-day holds, trend following"
    else:
        trading_style = "Position Trader"
        style_description = "Long-term conviction plays"
    
    # Determine strategy type
    strategy_signals = {
        "momentum": 0,
        "contrarian": 0,
        "arbitrage": 0,
        "event_driven": 0,
        "copy_trade": 0,
        "scalping": 0
    }
    
    # Signal detection
    if avg_holding < 4:
        strategy_signals["scalping"] += 2
    if avg_entry_price < 0.4:
        strategy_signals["contrarian"] += 1
    if avg_entry_price > 0.6:
        strategy_signals["momentum"] += 1
    if len(positions) < 5 and total_trades > 20:
        strategy_signals["event_driven"] += 1
    if size_variance < 2:
        strategy_signals["copy_trade"] += 1
    if top_market_pct > 50:
        strategy_signals["event_driven"] += 1
    
    likely_strategy = max(strategy_signals, key=strategy_signals.get)
    
    # Generate diagnosis
    diagnosis = {
        "wallet": wallet,
        "analyzed_at": datetime.now().isoformat(),
        "trade_count": total_trades,
        "summary": {
            "trading_style": trading_style,
            "style_description": style_description,
            "likely_strategy": likely_strategy,
            "strategy_template": STRATEGY_TEMPLATES.get(likely_strategy, {})
        },
        "metrics": {
            "avg_holding_hours": round(avg_holding, 2),
            "avg_trade_size": round(avg_size, 2),
            "max_trade_size": round(max_size, 2),
            "avg_entry_price": round(avg_entry_price, 4),
            "market_concentration": round(top_market_pct, 1),
            "unique_markets": len(positions),
            "trades_per_day": round(total_trades / max(1, (max(timestamps) - min(timestamps)) / 86400), 2) if timestamps else 0
        },
        "patterns": {
            "prefers_low_prices": avg_entry_price < 0.4,
            "concentrated_bets": top_market_pct > 40,
            "high_frequency": avg_time_between < 3600,
            "consistent_sizing": size_variance < 3
        },
        "strengths": [],
        "weaknesses": [],
        "recommendations": []
    }
    
    # Add strengths/weaknesses/recommendations
    if diagnosis["patterns"]["consistent_sizing"]:
        diagnosis["strengths"].append("Consistent position sizing shows discipline")
    else:
        diagnosis["weaknesses"].append("Inconsistent position sizing may indicate emotional trading")
        diagnosis["recommendations"].append("Standardize position sizes based on conviction level")
    
    if diagnosis["patterns"]["concentrated_bets"]:
        diagnosis["weaknesses"].append("High concentration in single markets increases risk")
        diagnosis["recommendations"].append("Diversify across uncorrelated markets")
    else:
        diagnosis["strengths"].append("Good diversification across markets")
    
    if avg_holding < 2 and avg_size > 1000:
        diagnosis["weaknesses"].append("Large positions with short holds = high transaction costs")
        diagnosis["recommendations"].append("Consider holding longer or reducing size")
    
    if diagnosis["patterns"]["prefers_low_prices"]:
        diagnosis["strengths"].append("Buying undervalued positions shows contrarian thinking")
        diagnosis["recommendations"].append("Ensure you're not catching falling knives - check for catalysts")
    
    return diagnosis


def generate_strategy_ideas(
    wallet_analysis: Dict = None,
    market_category: str = None,
    risk_tolerance: str = "medium",
    capital: float = 10000
) -> Dict:
    """
    Generate personalized strategy ideas based on analysis and preferences.
    """
    ideas = {
        "generated_at": datetime.now().isoformat(),
        "parameters": {
            "risk_tolerance": risk_tolerance,
            "capital": capital,
            "market_category": market_category
        },
        "strategy_ideas": [],
        "ideation_questions": []
    }
    
    # Select appropriate templates based on risk tolerance
    risk_map = {
        "low": ["arbitrage", "copy_trade"],
        "medium": ["momentum", "event_driven", "copy_trade"],
        "high": ["contrarian", "scalping", "momentum"]
    }
    
    suitable_strategies = risk_map.get(risk_tolerance, risk_map["medium"])
    
    for strategy_key in suitable_strategies:
        template = STRATEGY_TEMPLATES[strategy_key]
        
        # Customize for capital
        if capital < 1000:
            size_rec = "1-2 trades at a time, $50-100 each"
        elif capital < 10000:
            size_rec = "3-5 trades at a time, $200-500 each"
        else:
            size_rec = "5-10 trades at a time, $500-2000 each"
        
        idea = {
            "strategy": template["name"],
            "description": template["description"],
            "why_suitable": f"Matches your {risk_tolerance} risk tolerance",
            "entry_rules": template["entry_rules"],
            "exit_rules": template["exit_rules"],
            "recommended_sizing": size_rec,
            "markets_to_watch": [],
            "example_setup": None
        }
        
        # Add market recommendations based on category
        if market_category == "politics":
            idea["markets_to_watch"] = ["Election markets", "Policy decision markets", "Approval rating markets"]
        elif market_category == "crypto":
            idea["markets_to_watch"] = ["BTC price markets", "ETH price markets", "Regulatory decision markets"]
        elif market_category == "sports":
            idea["markets_to_watch"] = ["Championship markets", "Player performance markets", "Season outcome markets"]
        else:
            idea["markets_to_watch"] = ["Trending markets", "High volume markets", "Upcoming event markets"]
        
        ideas["strategy_ideas"].append(idea)
    
    # Add relevant ideation questions
    for prompt_category in IDEATION_PROMPTS:
        ideas["ideation_questions"].append({
            "category": prompt_category["category"],
            "questions": prompt_category["prompts"][:2]  # Top 2 questions per category
        })
    
    # If we have wallet analysis, add personalized recommendations
    if wallet_analysis and "summary" in wallet_analysis:
        ideas["personalized_insights"] = {
            "current_style": wallet_analysis["summary"].get("trading_style"),
            "suggested_improvements": wallet_analysis.get("recommendations", []),
            "leverage_strengths": wallet_analysis.get("strengths", [])
        }
    
    return ideas


def iterate_strategy(
    current_strategy: Dict,
    performance_data: Dict,
    feedback: str = None
) -> Dict:
    """
    Iterate and improve a strategy based on performance data and feedback.
    """
    iteration = {
        "iteration_at": datetime.now().isoformat(),
        "original_strategy": current_strategy.get("name", "Unnamed"),
        "analysis": {},
        "suggested_changes": [],
        "updated_strategy": {}
    }
    
    # Analyze performance
    if performance_data:
        win_rate = performance_data.get("win_rate", 0)
        profit_factor = performance_data.get("profit_factor", 0)
        max_drawdown = performance_data.get("max_drawdown", 0)
        avg_win = performance_data.get("avg_win", 0)
        avg_loss = performance_data.get("avg_loss", 0)
        
        iteration["analysis"] = {
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "risk_reward": abs(avg_win / avg_loss) if avg_loss != 0 else 0,
            "overall_assessment": "profitable" if profit_factor > 1 else "unprofitable"
        }
        
        # Generate improvement suggestions
        if win_rate < 0.4:
            iteration["suggested_changes"].append({
                "area": "Entry Rules",
                "issue": f"Low win rate ({win_rate*100:.0f}%)",
                "suggestion": "Tighten entry criteria - add volume confirmation or wait for pullbacks",
                "priority": "high"
            })
        
        if profit_factor < 1.5 and win_rate > 0.5:
            iteration["suggested_changes"].append({
                "area": "Exit Rules",
                "issue": "Winners not big enough relative to losers",
                "suggestion": "Let winners run longer - consider trailing stops instead of fixed take profit",
                "priority": "high"
            })
        
        if max_drawdown > 0.3:
            iteration["suggested_changes"].append({
                "area": "Risk Management",
                "issue": f"High drawdown ({max_drawdown*100:.0f}%)",
                "suggestion": "Reduce position sizes or add correlation limits",
                "priority": "critical"
            })
        
        if profit_factor > 2:
            iteration["suggested_changes"].append({
                "area": "Position Sizing",
                "issue": "Strong edge detected",
                "suggestion": "Consider increasing position sizes using Kelly criterion",
                "priority": "medium"
            })
    
    # Incorporate feedback
    if feedback:
        iteration["suggested_changes"].append({
            "area": "User Feedback",
            "issue": "Manual observation",
            "suggestion": feedback,
            "priority": "medium"
        })
    
    # Generate updated strategy
    iteration["updated_strategy"] = {
        **current_strategy,
        "version": current_strategy.get("version", 0) + 1,
        "last_iteration": datetime.now().isoformat(),
        "changes_made": [c["suggestion"] for c in iteration["suggested_changes"]]
    }
    
    return iteration


def define_strategy(
    name: str,
    entry_rules: List[str],
    exit_rules: List[str],
    position_sizing: str,
    risk_params: Dict = None
) -> Dict:
    """
    Define a new trading strategy with clear, executable rules.
    """
    strategy = {
        "name": name,
        "version": 1,
        "created_at": datetime.now().isoformat(),
        "status": "draft",
        "rules": {
            "entry": {
                "conditions": entry_rules,
                "logic": "AND",  # All conditions must be met
                "confirmation_required": True
            },
            "exit": {
                "conditions": exit_rules,
                "logic": "OR",  # Any condition triggers exit
                "partial_exits_allowed": True
            },
            "position_sizing": {
                "method": position_sizing,
                "max_position_pct": risk_params.get("max_position_pct", 10) if risk_params else 10,
                "scale_in_allowed": risk_params.get("scale_in", False) if risk_params else False
            }
        },
        "risk_management": {
            "max_daily_loss_pct": risk_params.get("max_daily_loss", 5) if risk_params else 5,
            "max_open_positions": risk_params.get("max_positions", 5) if risk_params else 5,
            "correlation_limit": risk_params.get("correlation_limit", 0.7) if risk_params else 0.7,
            "stop_loss_required": True
        },
        "checklist": {
            "pre_trade": [
                "Check if entry conditions are met",
                "Verify position size is within limits",
                "Confirm no correlated positions exceed limit",
                "Set stop loss and take profit levels"
            ],
            "during_trade": [
                "Monitor for exit conditions",
                "Track unrealized P&L",
                "Watch for thesis invalidation"
            ],
            "post_trade": [
                "Log trade details and outcome",
                "Note what worked and what didn't",
                "Update strategy if patterns emerge"
            ]
        },
        "journal_template": {
            "trade_id": "",
            "date": "",
            "market": "",
            "entry_price": 0,
            "exit_price": 0,
            "position_size": 0,
            "outcome": "",
            "notes": "",
            "lessons_learned": ""
        }
    }
    
    return strategy


# Export functions for use in Flask app
__all__ = [
    'STRATEGY_TEMPLATES',
    'IDEATION_PROMPTS', 
    'analyze_wallet_strategy',
    'generate_strategy_ideas',
    'iterate_strategy',
    'define_strategy'
]
