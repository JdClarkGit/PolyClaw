# PolyClaw Documentation

Welcome to the PolyClaw documentation. This is your guide to setting up, configuring, and using PolyClaw for Polymarket trading intelligence.

## Quick Links

| Getting Started | Reference | Guides |
|-----------------|-----------|--------|
| [Installation](getting-started.md) | [API Reference](api.md) | [Discord Setup](channels/discord.md) |
| [Configuration](configuration.md) | [Skills](skills.md) | [Telegram Setup](channels/telegram.md) |
| [First Analysis](getting-started.md#first-analysis) | [Analytics](analytics.md) | [Bot Factory](bot-factory.md) |

## Documentation Index

### Core Documentation

- **[Getting Started](getting-started.md)** — First-time setup and your first analysis
- **[Configuration](configuration.md)** — All environment variables and options
- **[API Reference](api.md)** — Complete REST API documentation
- **[Security](security.md)** — Security model and best practices

### Features

- **[Channels](channels.md)** — Discord, Telegram, WebChat setup
- **[Skills](skills.md)** — Extensible AI capabilities
- **[Strategies](strategies.md)** — Pattern detection and strategy analysis
- **[Analytics](analytics.md)** — Metrics, calculations, and analysis
- **[Leaderboard](leaderboard.md)** — Public wallet rankings

### Channel Guides

- **[Discord](channels/discord.md)** — Webhook alerts and embeds
- **[Telegram](channels/telegram.md)** — Bot integration and alerts
- **[WebChat](channels/webchat.md)** — Built-in chat interface

### Advanced

- **[Gateway](gateway.md)** — Flask server architecture
- **[AI Config](ai-config.md)** — LLM provider configuration
- **[Bot Factory](bot-factory.md)** — Generating trading bots
- **[Docker](docker.md)** — Container deployment

### Support

- **[FAQ](faq.md)** — Frequently asked questions
- **[Troubleshooting](troubleshooting.md)** — Common issues and solutions

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    PolyClaw Gateway                      │
│                  http://localhost:8080                   │
├─────────────────────────────────────────────────────────┤
│  Web Interfaces:                                        │
│  • Trade Viewer (/)       • Terminal Mode (/terminal)   │
│  • Leaderboard (/leaderboard)                          │
├─────────────────────────────────────────────────────────┤
│  API Layer:                                             │
│  • /api/trades/*          • /api/analyze/*             │
│  • /api/chat              • /api/ai-analyze            │
│  • /api/leaderboard/*     • /api/notifications/*       │
│  • /api/strategy/*        • /api/download/*            │
├─────────────────────────────────────────────────────────┤
│  Core Engines:                                          │
│  • Analytics Engine       • AI Engine (Anthropic/OpenAI)│
│  • Strategy Engine        • Notification Engine        │
├─────────────────────────────────────────────────────────┤
│  External Connections:                                  │
│  • Polymarket API         • Discord Webhooks           │
│  • Telegram Bot API       • LLM Providers              │
└─────────────────────────────────────────────────────────┘
```

## What You Can Do

### Analyze Wallets
Pull complete trade history, calculate P&L, assess risk metrics, and detect trading patterns for any Polymarket wallet.

### Track Whales
Subscribe to wallet alerts and get real-time Discord/Telegram notifications when tracked wallets make trades.

### Build Strategies
Use AI-powered analysis to understand successful trading patterns and generate bot configurations.

### Compare Traders
Side-by-side comparison of multiple wallets to identify the best performers and their strategies.

### Export Data
Download trade history in CSV or Excel format for your own analysis.

## Need Help?

- **Discord:** [Join our community](https://discord.gg/polyclaw)
- **Issues:** [Report a bug](https://github.com/polyclaw/polyclaw/issues)
- **Discussions:** [Ask questions](https://github.com/polyclaw/polyclaw/discussions)
