"""
PolyClaw Knowledge Base

Pre-built knowledge about prediction markets, trading strategies,
and quantitative finance. This is what makes PolyClaw an expert.
"""

# ============================================================
# PREDICTION MARKET FUNDAMENTALS
# ============================================================

PREDICTION_MARKET_BASICS = """
## What is a Prediction Market?

A prediction market is a market where participants trade contracts that pay out based on the outcome of future events. The prices of these contracts can be interpreted as the market's collective probability estimate for each outcome.

## Key Concepts

### Market Mechanics
- **Binary markets**: Two outcomes (Yes/No), prices sum to $1
- **Multiple outcome markets**: Several outcomes, prices sum to $1
- **Order book**: Bids and asks from traders
- **AMM (Automated Market Maker)**: Algorithm that provides liquidity

### Price Interpretation
- A "Yes" contract at $0.65 implies 65% probability
- Arbitrage keeps prices efficient
- Liquidity affects price accuracy

### Major Platforms
1. **Polymarket**: Largest crypto prediction market, USDC-based
2. **Kalshi**: US-regulated, real USD
3. **Metaculus**: Community forecasting (not real money)
4. **PredictIt**: US political markets (CFTC regulated)
5. **Manifold**: Play money with real track records
"""

TRADING_STRATEGIES = """
## Prediction Market Trading Strategies

### 1. Momentum Trading
- Buy contracts showing upward price movement
- Assume trends continue short-term
- Best during breaking news events
- Risk: Trend reversal

### 2. Mean Reversion
- Bet prices return to historical averages
- Buy oversold, sell overbought
- Works in stable, low-news periods
- Risk: Regime changes

### 3. Arbitrage
- Exploit price differences across platforms
- Same event, different prices
- Near risk-free if executed properly
- Requires capital on multiple platforms

### 4. Information Edge
- Trade on superior research/analysis
- Deep domain expertise
- First to interpret breaking news
- Requires significant effort

### 5. Market Making
- Provide liquidity, earn spread
- Buy at bid, sell at ask
- Requires inventory management
- Risk: Adverse selection

### 6. Event-Driven
- Trade based on scheduled events
- Debates, earnings, announcements
- Position before, exit after
- Risk: Unexpected outcomes

### 7. Contrarian
- Bet against crowd sentiment
- Buy when others panic sell
- Requires strong conviction
- Risk: The crowd might be right
"""

RISK_MANAGEMENT = """
## Risk Management for Prediction Markets

### Position Sizing

#### Kelly Criterion
The mathematically optimal bet size:
- f* = (bp - q) / b
- b = odds - 1
- p = win probability
- q = 1 - p

**Half Kelly**: Use half the Kelly suggestion for safety.

#### Fixed Fraction
- Never risk more than X% of bankroll on single bet
- Common: 1-5% per position
- Adjust based on edge confidence

### Portfolio Management

#### Diversification
- Spread across uncorrelated markets
- Mix timeframes (short/medium/long)
- Avoid concentration in single category

#### Correlation Risk
- Political markets often correlated
- Economic markets linked
- Watch for hidden correlations

### Drawdown Management
- Set maximum drawdown limit (e.g., 20%)
- Reduce size after losses
- Track rolling performance

### Liquidity Risk
- Large positions may move price
- Exit strategy before entry
- Watch bid-ask spreads
"""

QUANTITATIVE_METRICS = """
## Key Trading Metrics

### Performance Metrics

#### P&L (Profit and Loss)
- Total returns minus costs
- Include trading fees
- Realized vs unrealized

#### Win Rate
- Percentage of winning trades
- Not sufficient alone
- High win rate ≠ profitable

#### Profit Factor
- Gross profits / Gross losses
- > 1.0 is profitable
- > 2.0 is excellent

### Risk-Adjusted Returns

#### Sharpe Ratio
- (Return - Risk Free Rate) / Volatility
- > 1.0 is good
- > 2.0 is excellent
- Assumes normal distribution

#### Sortino Ratio
- Like Sharpe, but only downside volatility
- Better for asymmetric returns
- Prediction markets are asymmetric

#### Calmar Ratio
- Return / Max Drawdown
- Measures recovery ability
- Higher is better

### Trade Analysis

#### Average Win/Loss
- Mean size of winning vs losing trades
- Win/Loss ratio matters
- Big wins can overcome low win rate

#### Expectancy
- Average profit per trade
- (Win Rate × Avg Win) - (Loss Rate × Avg Loss)
- Must be positive

#### Trade Frequency
- Trades per day/week/month
- Balance opportunity vs overtrading
- Transaction costs matter
"""

POLYMARKET_SPECIFICS = """
## Polymarket Trading Guide

### Platform Mechanics

#### Order Types
- Limit orders: Specify price
- Market orders: Take best price
- Good-til-cancelled (GTC)

#### Fees
- 0% maker fees (provide liquidity)
- ~1% taker fees (take liquidity)
- No withdrawal fees

#### Settlement
- Binary outcomes: $1 or $0
- Resolution by UMA oracle
- Disputes possible but rare

### Market Categories

#### Politics
- Elections, polls, legislation
- High liquidity during cycles
- Partisan bias possible

#### Crypto
- Price predictions
- ETF approvals
- Regulatory events

#### Sports
- Game outcomes
- Championship winners
- Statistical props

#### Current Events
- Breaking news
- Celebrity events
- Business outcomes

### Alpha Opportunities

#### Information Asymmetry
- First to breaking news
- Deep domain expertise
- Specialized data sources

#### Model Edge
- Better probability models
- Historical base rates
- Bayesian updating

#### Behavioral Edge
- Fade overreaction
- Exploit recency bias
- Contrarian positions

#### Execution Edge
- Better tools (like PolyClaw!)
- Faster execution
- Systematic approach
"""

WHALE_PATTERNS = """
## Whale Trading Patterns

### Identifying Whales
- Consistent large positions ($10k+)
- High win rates over time
- Specific market expertise

### Common Whale Strategies

#### Information Traders
- Move quickly on news
- Often right directionally
- Worth tracking closely

#### Market Makers
- Two-sided activity
- Profit from spread
- Neutral on direction

#### Position Builders
- Slow accumulation
- Avoid moving price
- Large final positions

### Following Whales

#### Copy Trading Signals
- Delay: They get there first
- Size: They can afford losses
- Diversify your follows

#### When NOT to Follow
- Late to the trade
- Unknown wallet history
- Unusual size for them

### Top Trader Characteristics
1. Consistent, not flashy
2. Position sizing discipline
3. Focus on specific categories
4. Patience for right opportunities
5. Cut losses quickly
"""

# ============================================================
# STRATEGY TEMPLATES
# ============================================================

STRATEGY_TEMPLATES = {
    "momentum": {
        "name": "Momentum Strategy",
        "description": "Trade in the direction of recent price movement",
        "entry": "Price moved >5% in last 24h in one direction",
        "exit": "Price reverses 2% or target reached",
        "position_size": "1-3% of bankroll",
        "best_for": "Breaking news, trending events",
        "risk": "Reversal, late entry",
    },
    "mean_reversion": {
        "name": "Mean Reversion Strategy", 
        "description": "Bet that extreme prices return to normal",
        "entry": "Price deviates >10% from 7-day average",
        "exit": "Price returns to average",
        "position_size": "2-5% of bankroll",
        "best_for": "Stable markets, overreactions",
        "risk": "Regime change, new information",
    },
    "value": {
        "name": "Value Strategy",
        "description": "Find mispriced markets using research",
        "entry": "Your probability differs >10% from market",
        "exit": "Market agrees or event resolves",
        "position_size": "Based on Kelly criterion",
        "best_for": "Expertise areas, obscure markets",
        "risk": "Being wrong, illiquidity",
    },
    "event_driven": {
        "name": "Event-Driven Strategy",
        "description": "Trade around scheduled events",
        "entry": "Before debate, announcement, etc.",
        "exit": "Shortly after event",
        "position_size": "1-2% per event",
        "best_for": "Predictable catalysts",
        "risk": "Unexpected outcomes, volatility",
    },
    "arbitrage": {
        "name": "Arbitrage Strategy",
        "description": "Exploit price differences across platforms",
        "entry": "Same event priced differently",
        "exit": "Prices converge",
        "position_size": "Max available at spread",
        "best_for": "Cross-platform traders",
        "risk": "Execution, settlement differences",
    },
}

# ============================================================
# KNOWLEDGE RETRIEVAL
# ============================================================

def get_knowledge(topic: str) -> str:
    """Retrieve knowledge on a topic"""
    topic = topic.lower()
    
    knowledge_map = {
        "basics": PREDICTION_MARKET_BASICS,
        "fundamentals": PREDICTION_MARKET_BASICS,
        "strategies": TRADING_STRATEGIES,
        "strategy": TRADING_STRATEGIES,
        "risk": RISK_MANAGEMENT,
        "risk_management": RISK_MANAGEMENT,
        "metrics": QUANTITATIVE_METRICS,
        "quantitative": QUANTITATIVE_METRICS,
        "polymarket": POLYMARKET_SPECIFICS,
        "whale": WHALE_PATTERNS,
        "whales": WHALE_PATTERNS,
    }
    
    for key, content in knowledge_map.items():
        if key in topic:
            return content
    
    # Return all knowledge if no specific match
    return "\n\n".join([
        PREDICTION_MARKET_BASICS,
        TRADING_STRATEGIES,
        RISK_MANAGEMENT,
    ])


def get_strategy_template(strategy_name: str) -> dict:
    """Get a strategy template"""
    return STRATEGY_TEMPLATES.get(strategy_name.lower())


def list_strategies() -> list:
    """List all strategy templates"""
    return list(STRATEGY_TEMPLATES.keys())


def build_context_for_ai() -> str:
    """Build knowledge context for AI prompts"""
    return f"""
You are PolyClaw, an expert AI assistant for prediction market trading.

{PREDICTION_MARKET_BASICS}

{TRADING_STRATEGIES}

{RISK_MANAGEMENT}

{QUANTITATIVE_METRICS}

When helping users:
1. Always consider risk management
2. Use quantitative metrics to evaluate strategies
3. Reference specific platform mechanics when relevant
4. Provide actionable, specific advice
5. Acknowledge uncertainty in predictions

You have access to tools to analyze wallets, fetch market data, and calculate optimal positions.
"""
