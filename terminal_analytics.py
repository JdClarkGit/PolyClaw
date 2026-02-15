#!/usr/bin/env python3
"""
Terminal Analytics Engine
Advanced metrics for the Polymarket Wallet Analyzer Terminal.
Kelly Criterion, Sharpe/Sortino, Strategy Fingerprinting, High-Confidence Detection, etc.
"""

import math
import statistics
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Any, Optional


# =============================================================================
# KELLY CRITERION
# =============================================================================

def calculate_kelly(trades: List[Dict], pnl_summary: Dict) -> Dict:
    """
    Kelly Criterion for optimal position sizing.
    Kelly % = W - [(1 - W) / R]
    For binary markets: Kelly = (b*p - q) / b
    """
    win_rate = (pnl_summary.get('win_rate', 0) or 0) / 100.0
    total_profit = pnl_summary.get('total_profit', 0) or 0
    total_loss = pnl_summary.get('total_loss', 0) or 0
    wins = pnl_summary.get('wins', 0) or 0
    losses = pnl_summary.get('losses', 0) or 0

    avg_win = total_profit / wins if wins > 0 else 0
    avg_loss = total_loss / losses if losses > 0 else 0
    wl_ratio = avg_win / avg_loss if avg_loss > 0 else 0

    # Standard Kelly
    if wl_ratio > 0:
        kelly_pct = win_rate - ((1 - win_rate) / wl_ratio)
    else:
        kelly_pct = 0

    kelly_pct = max(kelly_pct, 0)

    # Binary market Kelly using average buy price
    buy_prices = [t.get('price', 0) or 0 for t in trades if t.get('side') == 'BUY' and (t.get('price', 0) or 0) > 0]
    avg_buy_price = statistics.mean(buy_prices) if buy_prices else 0.5

    if avg_buy_price > 0 and avg_buy_price < 1:
        b = (1.0 / avg_buy_price) - 1  # odds
        p = win_rate
        q = 1 - p
        binary_kelly = ((b * p) - q) / b if b > 0 else 0
        binary_kelly = max(binary_kelly, 0)
    else:
        binary_kelly = 0

    return {
        'kelly_pct': round(kelly_pct * 100, 2),
        'half_kelly': round(kelly_pct * 50, 2),
        'quarter_kelly': round(kelly_pct * 25, 2),
        'binary_kelly_pct': round(binary_kelly * 100, 2),
        'win_rate': round(win_rate * 100, 1),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'wl_ratio': round(wl_ratio, 2),
        'avg_buy_price': round(avg_buy_price, 4),
    }


# =============================================================================
# RISK-ADJUSTED RETURNS (Sharpe, Sortino, Calmar, Max Drawdown)
# =============================================================================

def calculate_risk_adjusted_returns(trades: List[Dict]) -> Dict:
    """
    Calculate Sharpe ratio, Sortino ratio, Max Drawdown, Calmar ratio.
    Uses cumulative cash-flow P&L and position-level sell returns.
    """
    sorted_trades = sorted(trades, key=lambda x: x.get('timestamp', 0))

    # Build cumulative P&L series (cash-flow based)
    cumulative = 0
    total_invested = 0  # total capital deployed (buys)
    peak = 0
    max_drawdown = 0

    # Collect sell-side returns for Sharpe/Sortino
    # (buy is deploying capital, sell is realizing — return = sell_price - avg_buy_price)
    returns = []

    for t in sorted_trades:
        side = t.get('side', '')
        price = t.get('price', 0) or 0
        usdc = t.get('usdcSize', 0) or 0

        if side == 'BUY':
            cumulative -= usdc
            total_invested += usdc
        elif side == 'SELL':
            cumulative += usdc
            # Sell return: how much we got vs the "fair" cost at avg price
            if price > 0:
                returns.append(price - 0.5)  # excess return vs 50¢ baseline

        # Track drawdown relative to total capital invested
        if cumulative > peak:
            peak = cumulative
        if total_invested > 0:
            dd = (peak - cumulative) / total_invested
            if dd > max_drawdown:
                max_drawdown = dd

    max_drawdown = min(max_drawdown, 1.0)  # cap at 100%

    if len(returns) < 2:
        total_volume = sum(t.get('usdcSize', 0) or 0 for t in trades)
        total_return = cumulative / total_volume if total_volume > 0 else 0
        return {
            'sharpe': 0, 'sortino': 0, 'calmar': 0,
            'max_drawdown_pct': round(max_drawdown * 100, 2),
            'total_return_pct': round(total_return * 100, 2),
            'annual_return_pct': 0, 'volatility': 0,
            'avg_return_per_trade': 0,
            'cumulative_pnl': round(cumulative, 2),
        }

    avg_return = statistics.mean(returns)
    std_return = statistics.stdev(returns)

    risk_free = 0

    # Sharpe Ratio (scale by sqrt of trades per year, capped)
    trades_per_year = min(len(trades), 12500)
    sharpe = (avg_return - risk_free) / std_return * math.sqrt(trades_per_year) if std_return > 0 else 0

    # Sortino (only downside deviation)
    negative_returns = [r for r in returns if r < 0]
    downside_std = statistics.stdev(negative_returns) if len(negative_returns) > 1 else std_return
    sortino = (avg_return - risk_free) / downside_std * math.sqrt(trades_per_year) if downside_std > 0 else 0

    # Total return
    total_volume = sum(t.get('usdcSize', 0) or 0 for t in trades)
    total_return = cumulative / total_volume if total_volume > 0 else 0

    # Annualized return (cap factor to avoid extreme extrapolation on short windows)
    timestamps = [t.get('timestamp', 0) for t in sorted_trades if t.get('timestamp')]
    if len(timestamps) >= 2:
        days = max((timestamps[-1] - timestamps[0]) / 86400, 1)
        annual_factor = min(365 / days, 12)  # cap at 12x extrapolation
        annual_return = ((1 + abs(total_return)) ** annual_factor - 1)
        if total_return < 0:
            annual_return = -annual_return
    else:
        annual_return = 0

    # Calmar ratio (capped)
    calmar = annual_return / max_drawdown if max_drawdown > 0 else 0
    calmar = max(min(calmar, 100), -100)

    return {
        'sharpe': round(sharpe, 2),
        'sortino': round(sortino, 2),
        'calmar': round(calmar, 2),
        'max_drawdown_pct': round(max_drawdown * 100, 2),
        'total_return_pct': round(total_return * 100, 2),
        'annual_return_pct': round(min(max(annual_return * 100, -999), 9999), 2),
        'volatility': round(std_return * 100, 2),
        'avg_return_per_trade': round(avg_return * 100, 4),
        'cumulative_pnl': round(cumulative, 2),
    }


# =============================================================================
# HIGH-CONFIDENCE TRADE DETECTION
# =============================================================================

def detect_high_confidence_trades(trades: List[Dict]) -> Dict:
    """
    Detect trades at high prices (>85¢, >90¢, >95¢).
    Check if high-confidence trades are one-sided (all on eventual winner).
    """
    thresholds = [0.85, 0.90, 0.95]
    results = {}

    for thresh in thresholds:
        key = f'above_{int(thresh*100)}c'
        high_conf = [t for t in trades if (t.get('price', 0) or 0) > thresh]

        # Check one-sidedness per market
        market_sides = defaultdict(lambda: defaultdict(int))
        for t in high_conf:
            mkt = t.get('title', 'Unknown')
            outcome = t.get('outcome', 'Unknown')
            market_sides[mkt][outcome] += 1

        one_sided_markets = 0
        total_markets = len(market_sides)
        for mkt, outcomes in market_sides.items():
            if len(outcomes) == 1:
                one_sided_markets += 1

        one_sided_pct = (one_sided_markets / total_markets * 100) if total_markets > 0 else 0

        # Volume at high confidence
        hc_volume = sum(t.get('usdcSize', 0) or 0 for t in high_conf)
        hc_buys = sum(1 for t in high_conf if t.get('side') == 'BUY')
        hc_sells = len(high_conf) - hc_buys

        results[key] = {
            'count': len(high_conf),
            'pct_of_total': round(len(high_conf) / max(len(trades), 1) * 100, 2),
            'volume': round(hc_volume, 2),
            'buys': hc_buys,
            'sells': hc_sells,
            'one_sided_pct': round(one_sided_pct, 1),
            'markets_count': total_markets,
        }

    return results


# =============================================================================
# ORDER FLOW ANALYSIS
# =============================================================================

def analyze_order_flow(trades: List[Dict]) -> Dict:
    """
    Pair trade ratio, buy/sell ratio, trade frequency classification.
    """
    buys = [t for t in trades if t.get('side') == 'BUY']
    sells = [t for t in trades if t.get('side') == 'SELL']

    buy_vol = sum(t.get('usdcSize', 0) or 0 for t in buys)
    sell_vol = sum(t.get('usdcSize', 0) or 0 for t in sells)
    buy_shares = sum(t.get('size', 0) or 0 for t in buys)
    sell_shares = sum(t.get('size', 0) or 0 for t in sells)

    # Buy/Sell ratio
    bs_ratio = buy_vol / sell_vol if sell_vol > 0 else float('inf')

    # Classify
    if bs_ratio > 2.0:
        flow_type = 'Accumulator'
    elif bs_ratio < 0.5:
        flow_type = 'Distributor'
    else:
        flow_type = 'Active Trader'

    # Pair ratio per market (min(up,down)/max(up,down))
    market_outcomes = defaultdict(lambda: defaultdict(float))
    for t in trades:
        mkt = t.get('title', 'Unknown')
        outcome = t.get('outcome', 'Unknown')
        market_outcomes[mkt][outcome] += t.get('size', 0) or 0

    pair_ratios = []
    for mkt, outcomes in market_outcomes.items():
        shares = list(outcomes.values())
        if len(shares) >= 2:
            sorted_s = sorted(shares, reverse=True)
            ratio = sorted_s[1] / sorted_s[0] if sorted_s[0] > 0 else 0
            pair_ratios.append(ratio)

    avg_pair_ratio = statistics.mean(pair_ratios) if pair_ratios else 0

    if avg_pair_ratio > 0.7:
        pair_style = 'Pair Trader (Hedged)'
    elif avg_pair_ratio > 0.3:
        pair_style = 'Mixed Approach'
    else:
        pair_style = 'Directional Trader'

    # Trade frequency
    timestamps = sorted([t.get('timestamp', 0) for t in trades if t.get('timestamp')])
    if len(timestamps) >= 2:
        hours_active = max((timestamps[-1] - timestamps[0]) / 3600, 1)
        trades_per_hour = len(trades) / hours_active
    else:
        hours_active = 0
        trades_per_hour = 0

    if trades_per_hour > 100:
        freq_class = 'High Frequency Bot'
    elif trades_per_hour > 10:
        freq_class = 'Active Trader/Bot'
    else:
        freq_class = 'Manual/Casual'

    # Net flow
    net_flow = buy_vol - sell_vol

    return {
        'buy_volume': round(buy_vol, 2),
        'sell_volume': round(sell_vol, 2),
        'buy_shares': round(buy_shares, 2),
        'sell_shares': round(sell_shares, 2),
        'buy_sell_ratio': round(bs_ratio, 2),
        'flow_type': flow_type,
        'net_flow': round(net_flow, 2),
        'avg_pair_ratio': round(avg_pair_ratio, 2),
        'pair_style': pair_style,
        'trades_per_hour': round(trades_per_hour, 1),
        'freq_class': freq_class,
        'hours_active': round(hours_active, 1),
    }


# =============================================================================
# TIMING / PHASE ANALYSIS
# =============================================================================

def analyze_phases(trades: List[Dict]) -> Dict:
    """
    Analyze trade timing within market windows.
    Early (0-60%), Mid (60-90%), Late (90-100%).
    Also detect burst trading (sub-second).
    """
    timestamps = sorted([t.get('timestamp', 0) for t in trades if t.get('timestamp')])
    if len(timestamps) < 2:
        return {'early_pct': 0, 'mid_pct': 0, 'late_pct': 0, 'burst_ratio': 0}

    total_span = timestamps[-1] - timestamps[0]
    if total_span <= 0:
        return {'early_pct': 100, 'mid_pct': 0, 'late_pct': 0, 'burst_ratio': 0}

    early = mid = late = 0
    for ts in timestamps:
        progress = (ts - timestamps[0]) / total_span
        if progress <= 0.6:
            early += 1
        elif progress <= 0.9:
            mid += 1
        else:
            late += 1

    total = len(timestamps)

    # Burst detection (trades within 1 second of each other)
    burst_count = 0
    for i in range(1, len(timestamps)):
        if timestamps[i] - timestamps[i-1] < 1:
            burst_count += 1

    return {
        'early_pct': round(early / total * 100, 1),
        'mid_pct': round(mid / total * 100, 1),
        'late_pct': round(late / total * 100, 1),
        'burst_trades': burst_count,
        'burst_ratio': round(burst_count / max(total - 1, 1) * 100, 1),
    }


# =============================================================================
# STRATEGY FINGERPRINTING
# =============================================================================

def fingerprint_strategy(trades: List[Dict], order_flow: Dict, phases: Dict,
                         high_conf: Dict, frequency_data: Dict, pair_data: Dict) -> Dict:
    """
    Auto-detect trading strategy based on multiple signals.
    Returns strategy type, confidence, and matching fingerprint traits.
    """
    traits = []
    confidence = 0
    strategy = 'Unknown'

    pair_ratio = order_flow.get('avg_pair_ratio', 0)
    tph = order_flow.get('trades_per_hour', 0)
    burst = phases.get('burst_ratio', 0)
    hc_90 = high_conf.get('above_90c', {})
    hc_one_sided = hc_90.get('one_sided_pct', 0)
    hc_count = hc_90.get('count', 0)
    pair_count = pair_data.get('summary', {}).get('total_pair_trades', 0) if isinstance(pair_data, dict) else 0

    # Pair trading
    if pair_ratio > 0.7:
        traits.append({'name': 'Pair Trading', 'value': round(pair_ratio, 2), 'match': True})
        confidence += 15
    else:
        traits.append({'name': 'Pair Trading', 'value': round(pair_ratio, 2), 'match': False})

    # High frequency
    if tph > 50:
        traits.append({'name': 'High Frequency', 'value': f'{tph:.0f}/hr', 'match': True})
        confidence += 10
    else:
        traits.append({'name': 'High Frequency', 'value': f'{tph:.0f}/hr', 'match': False})

    # Burst trading
    if burst > 50:
        traits.append({'name': 'Burst Trading', 'value': f'{burst:.0f}%', 'match': True})
        confidence += 10
    else:
        traits.append({'name': 'Burst Trading', 'value': f'{burst:.0f}%', 'match': False})

    # Active rebalancing
    rebalance_count = pair_count
    if rebalance_count > 5:
        traits.append({'name': 'Active Rebalancing', 'value': rebalance_count, 'match': True})
        confidence += 10
    else:
        traits.append({'name': 'Active Rebalancing', 'value': rebalance_count, 'match': False})

    # High confidence one-sided
    if hc_count > 0 and hc_one_sided > 80:
        traits.append({'name': 'One-Sided High Conf (>90¢)', 'value': f'{hc_one_sided:.0f}%', 'match': True})
        confidence += 20
    else:
        traits.append({'name': 'One-Sided High Conf (>90¢)', 'value': f'{hc_one_sided:.0f}%' if hc_count > 0 else 'N/A', 'match': False})

    # Phase-based execution
    early = phases.get('early_pct', 0)
    late = phases.get('late_pct', 0)
    if early > 40 and late > 10:
        traits.append({'name': 'Phase-Based Execution', 'value': f'E:{early:.0f}% L:{late:.0f}%', 'match': True})
        confidence += 10
    else:
        traits.append({'name': 'Phase-Based Execution', 'value': f'E:{early:.0f}% L:{late:.0f}%', 'match': False})

    # Determine strategy type
    matched = sum(1 for t in traits if t['match'])

    if pair_ratio > 0.7 and tph > 50 and burst > 50:
        strategy = 'Pair Trade Market Maker'
        confidence = min(confidence + 15, 99)
    elif pair_ratio > 0.7 and tph > 10:
        strategy = 'Active Market Maker'
        confidence = min(confidence + 10, 90)
    elif tph > 200:
        strategy = 'Scalper / Arbitrageur'
        confidence = min(confidence + 10, 85)
    elif pair_ratio < 0.3 and tph < 10:
        strategy = 'Swing Trader'
        confidence = min(confidence + 5, 70)
    elif pair_ratio < 0.5:
        strategy = 'Directional Trader'
        confidence = min(confidence + 5, 75)
    elif pair_ratio > 0.5:
        strategy = 'Hedged Trader'
        confidence = min(confidence + 5, 70)

    return {
        'strategy': strategy,
        'confidence': confidence,
        'traits': traits,
        'matched_traits': matched,
        'total_traits': len(traits),
    }


# =============================================================================
# TIME-WINDOWED P&L
# =============================================================================

def calculate_time_windowed_pnl(trades: List[Dict]) -> Dict:
    """
    Calculate P&L for different time windows: 1min, 15min, 1hr, 24hr, 7d, 30d, 90d, 1yr.
    """
    if not trades:
        return {}

    now = max(t.get('timestamp', 0) for t in trades if t.get('timestamp'))
    if not now:
        return {}

    windows = {
        '1m': 60,
        '15m': 900,
        '1h': 3600,
        '24h': 86400,
        '7d': 604800,
        '30d': 2592000,
        '90d': 7776000,
        '1y': 31536000,
    }

    results = {}
    for label, seconds in windows.items():
        cutoff = now - seconds
        window_trades = [t for t in trades if (t.get('timestamp', 0) or 0) >= cutoff]

        pnl = 0
        volume = 0
        count = len(window_trades)
        for t in window_trades:
            usdc = t.get('usdcSize', 0) or 0
            volume += usdc
            if t.get('side') == 'SELL':
                pnl += usdc
            else:
                pnl -= usdc

        results[label] = {
            'pnl': round(pnl, 2),
            'volume': round(volume, 2),
            'trades': count,
        }

    return results


# =============================================================================
# EXECUTION METRICS
# =============================================================================

def calculate_execution_metrics(trades: List[Dict]) -> Dict:
    """
    Detailed execution metrics: avg price, avg size, trades/hour, etc.
    """
    if not trades:
        return {}

    prices = [t.get('price', 0) or 0 for t in trades if (t.get('price', 0) or 0) > 0]
    sizes = [t.get('size', 0) or 0 for t in trades if (t.get('size', 0) or 0) > 0]
    volumes = [t.get('usdcSize', 0) or 0 for t in trades]

    avg_price = statistics.mean(prices) if prices else 0
    avg_size = statistics.mean(sizes) if sizes else 0
    total_shares = sum(sizes)
    total_volume = sum(volumes)

    timestamps = sorted([t.get('timestamp', 0) for t in trades if t.get('timestamp')])
    if len(timestamps) >= 2:
        hours = max((timestamps[-1] - timestamps[0]) / 3600, 0.01)
        trades_per_hour = len(trades) / hours
    else:
        trades_per_hour = 0

    # Buy vs sell breakdown
    buy_trades = [t for t in trades if t.get('side') == 'BUY']
    sell_trades = [t for t in trades if t.get('side') == 'SELL']

    buy_avg_price = statistics.mean([t.get('price', 0) or 0 for t in buy_trades if (t.get('price', 0) or 0) > 0]) if buy_trades else 0
    sell_avg_price = statistics.mean([t.get('price', 0) or 0 for t in sell_trades if (t.get('price', 0) or 0) > 0]) if sell_trades else 0

    return {
        'total_trades': len(trades),
        'total_shares': round(total_shares, 2),
        'total_volume': round(total_volume, 2),
        'avg_price': round(avg_price, 4),
        'avg_size': round(avg_size, 2),
        'avg_trade_value': round(total_volume / max(len(trades), 1), 2),
        'trades_per_hour': round(trades_per_hour, 1),
        'buy_count': len(buy_trades),
        'sell_count': len(sell_trades),
        'buy_avg_price': round(buy_avg_price, 4),
        'sell_avg_price': round(sell_avg_price, 4),
    }


# =============================================================================
# ACTIVE POSITIONS (from trade data)
# =============================================================================

def calculate_active_positions(trades: List[Dict]) -> List[Dict]:
    """
    Calculate current positions per market/outcome from trade history.
    """
    positions = defaultdict(lambda: {'shares': 0, 'cost': 0, 'buys': 0, 'sells': 0})

    for t in trades:
        key = (t.get('title', 'Unknown'), t.get('outcome', ''))
        side = t.get('side', '')
        size = t.get('size', 0) or 0
        usdc = t.get('usdcSize', 0) or 0

        if side == 'BUY':
            positions[key]['shares'] += size
            positions[key]['cost'] += usdc
            positions[key]['buys'] += 1
        elif side == 'SELL':
            positions[key]['shares'] -= size
            positions[key]['cost'] -= usdc
            positions[key]['sells'] += 1

    result = []
    for (market, outcome), pos in positions.items():
        if abs(pos['shares']) > 0.01:  # Still has a position
            avg_entry = pos['cost'] / pos['shares'] if pos['shares'] > 0 else 0
            result.append({
                'market': market[:80],
                'outcome': outcome,
                'shares': round(pos['shares'], 2),
                'cost_basis': round(pos['cost'], 2),
                'avg_entry': round(avg_entry, 4),
                'trades': pos['buys'] + pos['sells'],
            })

    # Sort by absolute cost basis
    result.sort(key=lambda x: abs(x['cost_basis']), reverse=True)
    return result[:20]  # Top 20 positions


# =============================================================================
# MASTER TERMINAL ANALYSIS
# =============================================================================

def run_terminal_analysis(trades: List[Dict], existing_analysis: Dict = None) -> Dict:
    """
    Run all terminal-specific analytics on trade data.
    Combines with existing analysis from analytics.py if provided.
    """
    if not trades:
        return {'error': 'No trades'}

    # Use existing analysis or empty dict
    base = existing_analysis or {}

    # P&L summary from existing analysis
    pnl_summary = base.get('pnl', {}).get('summary', {})

    # New terminal metrics
    kelly = calculate_kelly(trades, pnl_summary)
    risk_adj = calculate_risk_adjusted_returns(trades)
    high_conf = detect_high_confidence_trades(trades)
    order_flow = analyze_order_flow(trades)
    phases = analyze_phases(trades)
    execution = calculate_execution_metrics(trades)
    time_pnl = calculate_time_windowed_pnl(trades)
    positions = calculate_active_positions(trades)

    # Strategy fingerprint (needs multiple inputs)
    pair_data = base.get('pair_trades', {})
    frequency_data = base.get('frequency', {})
    fingerprint = fingerprint_strategy(trades, order_flow, phases, high_conf, frequency_data, pair_data)

    return {
        'kelly': kelly,
        'risk_adjusted': risk_adj,
        'high_confidence': high_conf,
        'order_flow': order_flow,
        'phases': phases,
        'execution': execution,
        'time_pnl': time_pnl,
        'positions': positions,
        'fingerprint': fingerprint,
    }
