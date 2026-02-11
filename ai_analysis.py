#!/usr/bin/env python3
"""
PolyEdge AI Analysis Module
LLM-powered trade analysis using OpenAI and Anthropic.
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

# LLM imports
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# Prompt templates for different analysis types
PROMPT_TEMPLATES = {
    "strategy": """You are an expert trading analyst specializing in prediction markets. Analyze this Polymarket trading data and provide insights on the trader's strategy.

## Trader Summary
{summary}

## Analysis Request
Please analyze this trader's strategy and provide:
1. **Trading Style Classification** - What type of trader is this? (scalper, swing trader, market maker, etc.)
2. **Key Patterns** - What recurring patterns do you see in their trading behavior?
3. **Market Focus** - What types of markets do they prefer?
4. **Entry/Exit Strategy** - How do they typically enter and exit positions?
5. **Strengths & Weaknesses** - What are they doing well? What could be improved?

Provide actionable insights in a clear, structured format.""",

    "risk": """You are a risk management expert for prediction market trading. Analyze this Polymarket trading data and assess the trader's risk profile.

## Trader Summary
{summary}

## Risk Assessment Request
Please provide a comprehensive risk assessment:
1. **Risk Score** (1-10) - Overall risk level with justification
2. **Position Sizing Analysis** - Are they sizing positions appropriately?
3. **Concentration Risk** - How diversified are they across markets?
4. **Behavioral Risks** - Any concerning patterns (overtrading, revenge trading, etc.)?
5. **Recommendations** - Specific suggestions to improve risk management

Be direct and specific with your recommendations.""",

    "performance": """You are a quantitative trading analyst. Analyze this Polymarket trading performance data and provide detailed insights.

## Trader Summary
{summary}

## Performance Analysis Request
Please analyze the trader's performance:
1. **P&L Summary** - Overall profitability assessment
2. **Win Rate Analysis** - Is their win rate sustainable?
3. **Best/Worst Trades** - What can we learn from their extremes?
4. **Consistency** - How consistent are their returns?
5. **Edge Identification** - Where does their edge come from?
6. **Improvement Areas** - Specific areas where they could improve returns

Include specific numbers and percentages where relevant.""",

    "custom": """You are an expert Polymarket trading analyst. Analyze this trading data based on the user's specific question.

## Trader Summary
{summary}

## User Question
{custom_prompt}

Please provide a thorough, data-driven response to the user's question."""
}


def prepare_trade_summary(trades: List[Dict], analysis: Dict = None) -> str:
    """
    Prepare a compressed summary of trade data for LLM context.
    This keeps token usage efficient while providing useful data.
    """
    if not trades:
        return "No trade data available."
    
    # Basic stats
    total_trades = len(trades)
    buys = sum(1 for t in trades if t.get('side') == 'BUY')
    sells = sum(1 for t in trades if t.get('side') == 'SELL')
    
    # Volume calculations
    volumes = [t.get('usdcSize', 0) or 0 for t in trades]
    total_volume = sum(volumes)
    avg_trade_size = total_volume / total_trades if total_trades > 0 else 0
    max_trade = max(volumes) if volumes else 0
    min_trade = min(volumes) if volumes else 0
    
    # Time range
    timestamps = [t.get('timestamp', 0) for t in trades if t.get('timestamp')]
    if timestamps:
        oldest = datetime.fromtimestamp(min(timestamps)).strftime('%Y-%m-%d')
        newest = datetime.fromtimestamp(max(timestamps)).strftime('%Y-%m-%d')
        days_active = (datetime.fromtimestamp(max(timestamps)) - datetime.fromtimestamp(min(timestamps))).days + 1
    else:
        oldest = newest = "Unknown"
        days_active = 0
    
    # Market diversity
    markets = {}
    for t in trades:
        title = t.get('title', 'Unknown')
        if title not in markets:
            markets[title] = {'count': 0, 'volume': 0, 'outcomes': set()}
        markets[title]['count'] += 1
        markets[title]['volume'] += t.get('usdcSize', 0) or 0
        markets[title]['outcomes'].add(t.get('outcome', 'Unknown'))
    
    # Top markets by volume
    top_markets = sorted(markets.items(), key=lambda x: x[1]['volume'], reverse=True)[:10]
    
    # Outcome preference
    outcomes = {}
    for t in trades:
        outcome = t.get('outcome', 'Unknown')
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
    
    # Price distribution
    prices = [t.get('price', 0) for t in trades if t.get('price')]
    avg_price = sum(prices) / len(prices) if prices else 0
    
    # Build summary string
    summary_parts = [
        "## Basic Statistics",
        f"- Total Trades: {total_trades:,}",
        f"- Buys: {buys:,} ({buys/total_trades*100:.1f}%)",
        f"- Sells: {sells:,} ({sells/total_trades*100:.1f}%)",
        f"- Buy/Sell Ratio: {buys/sells:.2f}" if sells > 0 else "- Buy/Sell Ratio: N/A (no sells)",
        "",
        "## Volume Analysis",
        f"- Total Volume: ${total_volume:,.2f}",
        f"- Average Trade Size: ${avg_trade_size:,.2f}",
        f"- Largest Trade: ${max_trade:,.2f}",
        f"- Smallest Trade: ${min_trade:,.2f}",
        "",
        "## Time Analysis",
        f"- Date Range: {oldest} to {newest}",
        f"- Days Active: {days_active}",
        f"- Trades per Day: {total_trades/days_active:.1f}" if days_active > 0 else "- Trades per Day: N/A",
        "",
        "## Market Diversity",
        f"- Unique Markets: {len(markets)}",
        f"- Average Price: ${avg_price:.2f}",
        "",
        "## Top 10 Markets by Volume:"
    ]
    
    for i, (market_name, stats) in enumerate(top_markets, 1):
        summary_parts.append(f"{i}. {market_name[:60]}...")
        summary_parts.append(f"   - Trades: {stats['count']}, Volume: ${stats['volume']:,.2f}")
    
    summary_parts.extend([
        "",
        "## Outcome Distribution:"
    ])
    for outcome, count in sorted(outcomes.items(), key=lambda x: x[1], reverse=True):
        summary_parts.append(f"- {outcome}: {count} trades ({count/total_trades*100:.1f}%)")
    
    # Add existing analysis if available
    if analysis:
        summary_parts.extend([
            "",
            "## Pattern Analysis (Pre-computed):"
        ])
        
        # Behavioral patterns
        if 'behavioral_patterns' in analysis:
            bp = analysis['behavioral_patterns']
            trader_type = bp.get('trader_classification', {}).get('primary_type', 'Unknown')
            summary_parts.append(f"- Trader Type: {trader_type}")
            summary_parts.append(f"- Rapid Trading %: {bp.get('rapid_trading_percentage', 0):.1f}%")
        
        # Risk metrics
        if 'risk_metrics' in analysis:
            rm = analysis['risk_metrics']
            summary_parts.append(f"- Risk Score: {rm.get('risk_score', 0):.0f}/100")
            summary_parts.append(f"- Market Concentration: {rm.get('market_concentration_risk', 0):.1f}%")
        
        # P&L if available
        if 'pnl' in analysis and analysis['pnl'].get('summary'):
            pnl = analysis['pnl']['summary']
            summary_parts.extend([
                "",
                "## P&L Summary:",
                f"- Win Rate: {pnl.get('win_rate', 0):.1f}%",
                f"- Net P&L: ${pnl.get('net_pnl', 0):,.2f}",
                f"- Wins: {pnl.get('wins', 0)}, Losses: {pnl.get('losses', 0)}",
                f"- Profit Factor: {pnl.get('profit_factor', 0):.2f}" if pnl.get('profit_factor') != float('inf') else "- Profit Factor: ∞"
            ])
        
        # Pair trades
        if 'pair_trades' in analysis and analysis['pair_trades'].get('summary'):
            pt = analysis['pair_trades']['summary']
            if pt.get('total_pair_trades', 0) > 0:
                summary_parts.extend([
                    "",
                    "## Pair Trading Activity:",
                    f"- Total Pair Trades: {pt.get('total_pair_trades', 0)}",
                    f"- Arbitrage Trades: {pt.get('arbitrage_trades', 0)}",
                    f"- Arb Profit: ${pt.get('total_arb_profit', 0):.2f}"
                ])
        
        # Frequency
        if 'frequency' in analysis:
            freq = analysis['frequency']
            if freq.get('is_bot_like'):
                summary_parts.append("\n⚠️ **Bot-like trading pattern detected**")
            elif freq.get('is_high_frequency'):
                summary_parts.append("\n⚡ **High-frequency trading pattern detected**")
    
    return "\n".join(summary_parts)


async def analyze_with_openai(
    trades_summary: str,
    prompt_type: str = "strategy",
    custom_prompt: str = None,
    model: str = "gpt-4o"
) -> Dict[str, Any]:
    """
    Analyze trades using OpenAI's API.
    """
    if not OPENAI_AVAILABLE:
        return {"error": "OpenAI package not installed. Run: pip install openai"}
    
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return {"error": "OPENAI_API_KEY environment variable not set"}
    
    # Get the appropriate prompt template
    template = PROMPT_TEMPLATES.get(prompt_type, PROMPT_TEMPLATES['strategy'])
    
    # Format the prompt
    if prompt_type == 'custom' and custom_prompt:
        prompt = template.format(summary=trades_summary, custom_prompt=custom_prompt)
    else:
        prompt = template.format(summary=trades_summary)
    
    try:
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert trading analyst specializing in Polymarket prediction markets. Provide clear, actionable insights based on trading data. Use markdown formatting for readability."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        return {
            "success": True,
            "provider": "openai",
            "model": model,
            "analysis": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
        
    except openai.APIError as e:
        return {"error": f"OpenAI API error: {str(e)}"}
    except Exception as e:
        return {"error": f"Error calling OpenAI: {str(e)}"}


async def analyze_with_anthropic(
    trades_summary: str,
    prompt_type: str = "strategy",
    custom_prompt: str = None,
    model: str = "claude-sonnet-4-20250514"
) -> Dict[str, Any]:
    """
    Analyze trades using Anthropic's Claude API.
    """
    if not ANTHROPIC_AVAILABLE:
        return {"error": "Anthropic package not installed. Run: pip install anthropic"}
    
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY environment variable not set"}
    
    # Get the appropriate prompt template
    template = PROMPT_TEMPLATES.get(prompt_type, PROMPT_TEMPLATES['strategy'])
    
    # Format the prompt
    if prompt_type == 'custom' and custom_prompt:
        prompt = template.format(summary=trades_summary, custom_prompt=custom_prompt)
    else:
        prompt = template.format(summary=trades_summary)
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            system="You are an expert trading analyst specializing in Polymarket prediction markets. Provide clear, actionable insights based on trading data. Use markdown formatting for readability.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        # Extract text from response
        analysis_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                analysis_text += block.text
        
        return {
            "success": True,
            "provider": "anthropic",
            "model": model,
            "analysis": analysis_text,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }
        }
        
    except anthropic.APIError as e:
        return {"error": f"Anthropic API error: {str(e)}"}
    except Exception as e:
        return {"error": f"Error calling Anthropic: {str(e)}"}


async def analyze_trades_with_ai(
    trades: List[Dict],
    analysis: Dict = None,
    provider: str = "openai",
    prompt_type: str = "strategy",
    custom_prompt: str = None
) -> Dict[str, Any]:
    """
    Main entry point for AI analysis.
    Prepares trade summary and calls the appropriate LLM provider.
    """
    # Prepare the trade summary
    summary = prepare_trade_summary(trades, analysis)
    
    # Call the appropriate provider
    if provider == "openai":
        result = await analyze_with_openai(summary, prompt_type, custom_prompt)
    elif provider == "anthropic":
        result = await analyze_with_anthropic(summary, prompt_type, custom_prompt)
    else:
        return {"error": f"Unknown provider: {provider}. Use 'openai' or 'anthropic'."}
    
    # Add metadata
    result["prompt_type"] = prompt_type
    result["trade_count"] = len(trades)
    result["timestamp"] = datetime.now().isoformat()
    
    return result


def get_available_providers() -> Dict[str, bool]:
    """
    Check which AI providers are available (installed and configured).
    """
    return {
        "openai": {
            "installed": OPENAI_AVAILABLE,
            "configured": bool(os.environ.get('OPENAI_API_KEY'))
        },
        "anthropic": {
            "installed": ANTHROPIC_AVAILABLE,
            "configured": bool(os.environ.get('ANTHROPIC_API_KEY'))
        }
    }


# Synchronous wrapper for Flask routes
def run_ai_analysis(
    trades: List[Dict],
    analysis: Dict = None,
    provider: str = "openai",
    prompt_type: str = "strategy",
    custom_prompt: str = None
) -> Dict[str, Any]:
    """
    Synchronous wrapper for the async AI analysis function.
    Use this in Flask routes.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            analyze_trades_with_ai(trades, analysis, provider, prompt_type, custom_prompt)
        )
        return result
    finally:
        loop.close()
