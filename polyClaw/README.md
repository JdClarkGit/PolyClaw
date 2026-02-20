# PolyClaw - Polymarket Intelligence Agent

PolyClaw is the AI-powered brain of PolyEdge, built on the [OpenClaw](https://github.com/openclaw/openclaw) autonomous agent framework.

## What is PolyClaw?

PolyClaw serves as your personal Polymarket intelligence agent that can:

- **Analyze Trading Patterns** - Understand wallet behavior, identify trader types, and detect bot activity
- **Craft Strategies** - Develop and backtest trading strategies using historical data
- **Find Opportunities** - Detect arbitrage opportunities and mispriced markets
- **Risk Management** - Calculate optimal position sizes using Kelly criterion
- **Market Research** - Monitor market sentiment and track smart money flows

## Setup

### Prerequisites

- Node.js v22+
- OpenClaw installed globally: `npm install -g openclaw@latest`
- API keys for your preferred LLM (Claude, GPT-4, etc.)

### Configuration

1. The `SOUL.md` file defines PolyClaw's personality and capabilities
2. Custom skills in `skills/` directory integrate with the PolyEdge API

### Running PolyClaw

```bash
# Navigate to polyClaw directory
cd polyClaw

# Start the agent
openclaw start

# Or run with a specific channel (e.g., Telegram)
openclaw start --channel telegram
```

## Skills

PolyClaw comes with custom skills for Polymarket:

| Skill | Description |
|-------|-------------|
| `fetch_trades` | Fetch trading history for any wallet |
| `analyze_wallet` | Get pattern analysis and performance metrics |
| `compare_wallets` | Compare multiple wallets side-by-side |
| `ai_deep_analysis` | Run AI-powered strategy/risk analysis |
| `calculate_kelly` | Calculate optimal position size |
| `find_arbitrage` | Detect arbitrage opportunities |

## Example Prompts

Ask PolyClaw things like:

- "Analyze the top 5 traders on the Presidential election market"
- "What's the optimal position size for a $1000 bankroll on a 65% confidence trade?"
- "Compare my wallet to this whale: 0x..."
- "Find any arbitrage opportunities in crypto markets"
- "Backtest a momentum strategy on political markets"

## Architecture

```
polyClaw/
├── SOUL.md              # Agent personality & configuration
├── skills/
│   └── polyedge-api.js  # Custom PolyEdge API integrations
└── README.md            # This file
```

## Security

PolyClaw runs locally on your machine. Your API keys and trading data never leave your system unless you explicitly configure external integrations.

## License

MIT - Same as PolyEdge.io
