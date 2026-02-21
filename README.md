<p align="center">
  <img src="https://em-content.zobj.net/source/twitter/376/lobster_1f99e.png" width="100" alt="PolyClaw Logo"/>
</p>

<h1 align="center">PolyClaw</h1>

<p align="center">
  <strong>PolyClaw is a personal AI trading assistant for Polymarket you run on your own devices.</strong>
</p>

<p align="center">
  It alerts you on the channels you already use (<strong>Discord</strong>, <strong>Telegram</strong>, <strong>WebChat</strong>), analyzes wallets, tracks whales, detects strategies, and helps you build trading bots. The Gateway is just the control plane — the product is the assistant.
</p>

<p align="center">
  If you want a personal, single-user trading intelligence system that feels local, fast, and always-on, this is it.
</p>

<p align="center">
  <a href="docs/getting-started.md">Getting Started</a> ·
  <a href="docs/index.md">Docs</a> ·
  <a href="docs/vision.md">Vision</a> ·
  <a href="docs/configuration.md">Configuration</a> ·
  <a href="docs/channels.md">Channels</a> ·
  <a href="docs/skills.md">Skills</a> ·
  <a href="docs/security.md">Security</a> ·
  <a href="docs/faq.md">FAQ</a> ·
  <a href="https://discord.gg/polyclaw">Discord</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License"/>
  <img src="https://img.shields.io/badge/Python-3.9+-blue?style=flat-square" alt="Python"/>
  <img src="https://img.shields.io/badge/Node-22+-green?style=flat-square" alt="Node"/>
  <img src="https://img.shields.io/badge/PRs-Welcome-brightgreen?style=flat-square" alt="PRs Welcome"/>
</p>

---

**Preferred setup:** run the setup script (`./setup.sh`) in your terminal. The script guides you through setting up the gateway, environment, and dependencies. Works on macOS, Linux, and Windows (via WSL2; strongly recommended).

**New install? Start here:** [Getting started](docs/getting-started.md)

---

## AI Providers (selection + auth)

| Provider | Subscription | Recommended For |
|----------|--------------|-----------------|
| **Anthropic** | Claude Pro/Max | Deep analysis, strategy ideation (recommended) |
| **OpenAI** | ChatGPT Plus/API | General analysis, chat |

**Model note:** while any model is supported, I strongly recommend **Anthropic Claude Opus** for long-context strength, better reasoning, and prompt-injection resistance. See [AI Configuration](docs/ai-config.md).

---

## Install (recommended)

**Runtime:** Python ≥3.9, Node ≥22 (for skills).

```bash
# Clone the repository
git clone https://github.com/polyclaw/polyclaw.git
cd polyclaw

# Run the setup wizard
./setup.sh

# Start PolyClaw
python app.py
```

The setup script creates a virtual environment, installs dependencies, and generates your `.env` file.

---

## Quick start (TL;DR)

**Runtime:** Python ≥3.9.

**Full beginner guide (auth, channels, alerts):** [Getting started](docs/getting-started.md)

```bash
# Setup
./setup.sh

# Start the gateway (web interface)
python app.py

# Open http://localhost:8080 in browser
```

**CLI commands** (add alias to your shell profile):

```bash
polyclaw analyze 0x1234...           # Analyze a wallet
polyclaw track 0x1234...             # Subscribe to alerts
polyclaw leaderboard                 # Show top performers
polyclaw chat "What strategies?"     # Talk to AI
polyclaw daemon start                # Start background monitoring
```

**Interactive bots** (configure in `.env`):

```bash
python telegram_bot.py               # Start Telegram bot
python discord_bot.py                # Start Discord bot
```

**Upgrading?** Pull latest and reinstall deps: `git pull && pip install -r requirements.txt`

---

## Docker (alternative)

```bash
# Clone and run with Docker
git clone https://github.com/polyclaw/polyclaw.git
cd polyclaw

# Configure environment
cp .env.example .env
# Edit .env with your API keys (optional)

# Start
docker-compose up -d
```

Open http://localhost:8080 in your browser.

---

## Security defaults (important)

PolyClaw runs locally on your machine. Treat it as a personal assistant.

**Full security guide:** [Security](docs/security.md)

**Default behavior:**

- **Local-first:** All data stays on your machine
- **No tracking:** Zero analytics or telemetry
- **API keys local:** Stored only in `.env`, never transmitted
- **Webhooks local:** Stored in `notifications_config.json`
- **Public API only:** Only Polymarket's public API is accessed

**Run `python app.py --doctor` to surface risky configurations.**

---

## Highlights

- **🔍 Wallet Intelligence** — analyze any Polymarket wallet instantly
- **🤖 AI Chat** — conversational assistant for strategy development
- **📊 Whale Tracking** — real-time alerts when tracked wallets trade
- **🏆 Leaderboard** — public rankings of top performers
- **🔔 Multi-channel alerts** — Discord, Telegram, WebChat
- **📈 Strategy Detection** — automatically identify trading patterns
- **🧠 Bot Factory** — generate trading bot configurations
- **📥 Data Export** — CSV, Excel, JSON formats
- **🖥️ Terminal Mode** — power-user interface with live streaming
- **💬 Interactive Bots** — 2-way chat on Telegram & Discord
- **⌨️ CLI Tool** — `polyclaw` command for terminal power users
- **👁️ Background Daemon** — always-on monitoring with `polyclaw daemon`

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=polyclaw/polyclaw&type=Date)](https://star-history.com/#polyclaw/polyclaw&Date)

---

## Everything we built so far

### Core platform

| Component | Description |
|-----------|-------------|
| **Gateway** | Flask control plane with sessions, API routes, WebChat, and Canvas host |
| **CLI surface** | `python app.py`, environment config, doctor mode |
| **AI runtime** | Multi-provider (Anthropic/OpenAI) with context-aware prompts |
| **Session model** | Wallet context, trade history, analysis state |
| **Media pipeline** | Trade data, exports (CSV/XLSX), chart generation |

### Channels

| Channel | Status | Description |
|---------|--------|-------------|
| **Discord** | ✅ Full | Webhook alerts, embeds, trade notifications |
| **Telegram** | ✅ Full | Bot alerts, formatted messages, subscriptions |
| **WebChat** | ✅ Full | Built-in chat UI with AI assistant |
| **Slack** | 🔜 Planned | Webhook integration |
| **Email** | 🔜 Planned | SMTP alerts |

### Apps + surfaces

| Surface | Description |
|---------|-------------|
| **Trade Viewer** | Main web interface — wallet analysis, comparison, AI chat |
| **Terminal Mode** | Power-user interface — live streaming, order book, signals |
| **Leaderboard** | Public wallet rankings with one-click analysis |
| **Settings Modal** | Configure Discord/Telegram channels and subscriptions |

### Tools + automation

| Tool | Description |
|------|-------------|
| **Wallet Analysis** | P&L, win rate, risk metrics, Kelly criterion |
| **Strategy Detection** | Scalper, swing trader, arbitrageur classification |
| **Comparison Engine** | Side-by-side wallet analysis |
| **Bot Factory** | Generate JSON/Python bot configurations |
| **Data Aggregator** | Multi-source data collection |
| **Alert System** | Real-time trade notifications |

### Runtime + safety

| Feature | Description |
|---------|-------------|
| **Rate limiting** | Polymarket API respect |
| **Error handling** | Graceful failures, retries |
| **Logging** | Configurable log levels |
| **Health checks** | `--doctor` mode for diagnostics |

---

## How it works (short)

```
Polymarket API ──► Trade Data ──► Analysis Engine
                                       │
                                       ▼
┌───────────────────────────────────────────────────────────┐
│                      PolyClaw Gateway                      │
│                    http://localhost:8080                   │
│                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   WebChat   │  │  Terminal   │  │ Leaderboard │       │
│  │     UI      │  │    Mode     │  │    Page     │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
│                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │  AI Chat    │  │  Strategy   │  │    Alert    │       │
│  │   Engine    │  │   Engine    │  │   System    │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
└───────────────────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    ┌─────────┐    ┌──────────┐    ┌─────────┐
    │ Discord │    │ Telegram │    │ WebChat │
    │ Alerts  │    │  Alerts  │    │   UI    │
    └─────────┘    └──────────┘    └─────────┘
```

---

## Key subsystems

| Subsystem | Description | Docs |
|-----------|-------------|------|
| **Gateway** | Flask server, API routes, static files | [Gateway](docs/gateway.md) |
| **AI Engine** | Multi-provider LLM integration | [AI Config](docs/ai-config.md) |
| **Alert System** | Discord/Telegram notifications | [Channels](docs/channels.md) |
| **Strategy Engine** | Pattern detection, bot generation | [Strategies](docs/strategies.md) |
| **Analytics** | P&L, risk metrics, comparisons | [Analytics](docs/analytics.md) |
| **Skills** | Extensible capability system | [Skills](docs/skills.md) |

---

## CLI (Command Line Interface)

PolyClaw includes a powerful CLI for terminal power users:

```bash
# Add to your shell profile (~/.bashrc or ~/.zshrc)
alias polyclaw='/path/to/polyclaw/cli.py'

# Then use anywhere
polyclaw analyze 0x1234...           # Analyze a wallet
polyclaw track 0x1234...             # Subscribe to alerts
polyclaw untrack 0x1234...           # Unsubscribe
polyclaw list                        # List tracked wallets
polyclaw leaderboard                 # Show top 10
polyclaw compare 0xabc 0xdef         # Compare two wallets
polyclaw chat "strategy question"    # AI chat
polyclaw export 0x1234...            # Export to CSV
polyclaw doctor                      # Run diagnostics
```

**Background daemon** for always-on monitoring:

```bash
polyclaw daemon start                # Start monitoring
polyclaw daemon status               # Check status
polyclaw daemon stop                 # Stop monitoring
```

The daemon monitors tracked wallets and sends alerts to configured channels when new trades are detected.

---

## Interactive Telegram Bot

Beyond simple webhook alerts, PolyClaw includes a full interactive Telegram bot:

```bash
# Add to .env
TELEGRAM_BOT_TOKEN=your_token_from_botfather

# Start the bot
python telegram_bot.py
```

**Bot commands:**
| Command | Description |
|---------|-------------|
| `/analyze <wallet>` | Full wallet analysis |
| `/track <wallet>` | Subscribe to alerts |
| `/untrack <wallet>` | Unsubscribe |
| `/mywallets` | Your tracked wallets |
| `/leaderboard` | Top performers |
| `/compare <w1> <w2>` | Compare wallets |
| `/chat <message>` | Talk to AI |
| `/help` | Show commands |

You can also just send messages to the bot and it will respond with AI-powered answers.

---

## Interactive Discord Bot

Full interactive Discord bot with slash commands:

```bash
# Add to .env
DISCORD_BOT_TOKEN=your_token_from_discord_developers

# Start the bot
python discord_bot.py
```

**Slash commands:**
| Command | Description |
|---------|-------------|
| `/analyze <wallet>` | Full wallet analysis |
| `/track <wallet>` | Subscribe to alerts |
| `/untrack <wallet>` | Unsubscribe |
| `/mywallets` | Your tracked wallets |
| `/leaderboard` | Top performers |
| `/compare <w1> <w2>` | Compare wallets |
| `/chat <message>` | Talk to AI |
| `/help` | Show commands |

You can also @mention the bot in any channel and it will respond.

---

## Discord Webhook Alerts

For simple one-way alerts (without the interactive bot), PolyClaw can send trade alerts to Discord via webhooks.

1. **Create a webhook:** Server Settings → Integrations → Webhooks → New Webhook
2. **Copy the URL:** Click "Copy Webhook URL"
3. **Add to PolyClaw:** Settings (⚙️) → Add Discord Webhook → Paste URL
4. **Subscribe to wallets:** Enter wallet address → Select Discord channel → Subscribe

```json
// Example notification_config.json
{
  "discord": {
    "whale-alerts": {
      "webhook_url": "https://discord.com/api/webhooks/...",
      "name": "whale-alerts"
    }
  },
  "subscriptions": {
    "0x1234...": ["discord:whale-alerts"]
  }
}
```

**Docs:** [Discord Integration](docs/channels/discord.md)

---

## Telegram Webhook Alerts

For simple one-way alerts (without the interactive bot), PolyClaw can send trade alerts to Telegram.

1. **Create a bot:** Message [@BotFather](https://t.me/BotFather) → `/newbot`
2. **Get your token:** BotFather will send you a token like `123456:ABC-DEF...`
3. **Get your chat ID:** Message [@userinfobot](https://t.me/userinfobot) or start a chat with your bot
4. **Add to PolyClaw:** Settings (⚙️) → Add Telegram Bot → Enter token + chat ID
5. **Subscribe to wallets:** Enter wallet address → Select Telegram channel → Subscribe

```json
// Example notification_config.json
{
  "telegram": {
    "my-alerts": {
      "bot_token": "123456:ABC-DEF...",
      "chat_id": "987654321",
      "name": "my-alerts"
    }
  },
  "subscriptions": {
    "0x1234...": ["telegram:my-alerts"]
  }
}
```

**Docs:** [Telegram Integration](docs/channels/telegram.md)

---

## Chat commands

Send these in the WebChat interface or via API:

| Command | Description |
|---------|-------------|
| `analyze 0x...` | Analyze a wallet |
| `compare 0x1 vs 0x2` | Compare two wallets |
| `track 0x...` | Subscribe to wallet alerts |
| `leaderboard` | Show top performers |
| `strategy help` | Get strategy recommendations |
| `bot create momentum` | Generate a bot config |

**Examples:**
```
"What's the win rate for wallet 0x1234?"
"Compare these two traders: 0xabc and 0xdef"
"What patterns do you see in my trading?"
"Generate a copy-trade bot for this whale"
```

---

## API Reference

### Wallet Analysis

```bash
# Fetch trades (recent)
GET /api/trades/{wallet}

# Fetch trades (full history)
GET /api/trades/{wallet}?mode=full

# Fetch trades (custom limit)
GET /api/trades/{wallet}?limit=500

# Pattern analysis
GET /api/analyze/{wallet}

# Compare wallets
GET /api/compare?wallets=0x1,0x2,0x3

# Strategy diagnosis
GET /api/strategy/diagnose/{wallet}
```

### AI Features

```bash
# Chat with PolyClaw
POST /api/chat
{
  "message": "What strategies work for election markets?",
  "wallet": "0x1234...",  # optional context
  "trades": [...]         # optional context
}

# Deep AI analysis
POST /api/ai-analyze
{
  "wallet": "0x1234...",
  "trades": [...]
}

# Check available AI providers
GET /api/ai-providers
```

### Strategy Engine

```bash
# Generate strategy ideas
POST /api/strategy/ideate
{
  "market_type": "election",
  "risk_tolerance": "medium"
}

# Define custom strategy
POST /api/strategy/define
{
  "name": "Momentum Scalper",
  "rules": {...}
}
```

### Leaderboard

```bash
# Get rankings
GET /api/leaderboard

# Submit wallet
POST /api/leaderboard/submit
{
  "wallet": "0x1234..."
}

# Refresh stats
POST /api/leaderboard/refresh/{wallet}
```

### Notifications

```bash
# List channels
GET /api/notifications/channels

# Add Discord webhook
POST /api/notifications/discord
{
  "name": "whale-alerts",
  "webhook_url": "https://discord.com/api/webhooks/..."
}

# Add Telegram bot
POST /api/notifications/telegram
{
  "name": "my-alerts",
  "bot_token": "123456:ABC...",
  "chat_id": "987654321"
}

# Subscribe to wallet
POST /api/notifications/subscribe
{
  "wallet": "0x1234...",
  "channels": ["discord:whale-alerts", "telegram:my-alerts"]
}

# Test notification
POST /api/notifications/test
{
  "channel": "discord:whale-alerts"
}
```

### Data Export

```bash
# CSV export
GET /api/download/{wallet}/csv

# Excel export
GET /api/download/{wallet}/xlsx
```

**Full API reference:** [API Docs](docs/api.md)

---

## Configuration

### Minimal `.env`

```env
# No API keys required for basic features!
PORT=8080
```

### Full `.env` (all options)

```env
# Server
PORT=8080
DEBUG=false
SECRET_KEY=your-random-secret-key

# AI Providers (optional - enables AI features)
ANTHROPIC_API_KEY=sk-ant-...  # Recommended
OPENAI_API_KEY=sk-...

# Advanced
# MAX_TRADES=10000
# RATE_LIMIT=60
# LOG_LEVEL=INFO
```

**Full configuration reference:** [Configuration](docs/configuration.md)

---

## Security model (important)

**Default:** PolyClaw runs locally. All data stays on your machine.

| Data | Storage | Sensitive? |
|------|---------|------------|
| `.env` | Local file | **Yes** - API keys |
| `notifications_config.json` | Local file | **Yes** - Webhook URLs, bot tokens |
| `leaderboard_data.json` | Local file | No - Public wallet addresses |
| Trade data | In-memory | No - From public API |

**Best practices:**
- Never commit `.env` to git
- Generate random `SECRET_KEY`
- Use dedicated webhooks/bots for PolyClaw
- Monitor webhook activity in Discord/Telegram settings
- Revoke and recreate if credentials are compromised

**Details:** [Security guide](docs/security.md)

---

## Skills platform

PolyClaw uses a skills system inspired by OpenClaw. Skills are modular capabilities the AI can invoke.

### Built-in skills

| Skill | Description | File |
|-------|-------------|------|
| `polyedge-api` | Wallet analysis, trade fetching | `skills/polyedge-api.js` |
| `bot-factory` | Bot config generation | `skills/bot-factory.js` |
| `data-aggregator` | Multi-source data collection | `skills/data-aggregator.js` |

### Skill structure

```
polyClaw/
├── SOUL.md           # Agent personality + capabilities
└── skills/
    ├── polyedge-api.js
    ├── bot-factory.js
    └── data-aggregator.js
```

### SOUL.md

The `SOUL.md` file defines PolyClaw's personality:

```markdown
# PolyClaw

You are PolyClaw, an AI-powered trading intelligence system for Polymarket.

## Core Mission
Collect → Analyze → Build → Deploy

## Capabilities
- Wallet analysis and comparison
- Strategy detection and ideation
- Bot configuration generation
- Real-time alert management
```

**Details:** [Skills](docs/skills.md)

---

## Project structure

```
polyclaw/
├── app.py                    # Main Flask gateway
├── trade-viewer.html         # Main web interface
├── terminal-mode.html        # Terminal interface
├── leaderboard.html          # Leaderboard page
│
├── analytics.py              # Trade analysis
├── ai_analysis.py            # AI integration
├── strategy_engine.py        # Strategy detection
├── notifications.py          # Discord/Telegram
├── terminal_analytics.py     # Terminal mode logic
│
├── polyClaw/                 # AI agent config
│   ├── SOUL.md              # Agent personality
│   └── skills/              # Modular capabilities
│
├── docs/                     # Documentation
│   ├── index.md
│   ├── getting-started.md
│   ├── configuration.md
│   ├── api.md
│   ├── channels.md
│   ├── skills.md
│   ├── security.md
│   └── faq.md
│
├── .github/                  # GitHub templates
│   ├── ISSUE_TEMPLATE/
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── FUNDING.yml
│
├── requirements.txt          # Python dependencies
├── setup.sh                  # Setup wizard
├── Dockerfile               # Docker image
├── docker-compose.yml       # Docker compose
├── .env.example             # Environment template
├── .gitignore
├── LICENSE
├── CONTRIBUTING.md
├── SECURITY.md
├── CODE_OF_CONDUCT.md
├── CHANGELOG.md
└── README.md
```

---

## Docs

Use these when you're past setup and want the deeper reference.

| Doc | Description |
|-----|-------------|
| [Getting Started](docs/getting-started.md) | First-time setup guide |
| [Configuration](docs/configuration.md) | All config options |
| [API Reference](docs/api.md) | Full API documentation |
| [Channels](docs/channels.md) | Discord, Telegram, WebChat |
| [Skills](docs/skills.md) | Extensible capabilities |
| [Strategies](docs/strategies.md) | Pattern detection, bot building |
| [Analytics](docs/analytics.md) | Metrics and calculations |
| [Security](docs/security.md) | Best practices |
| [Troubleshooting](docs/troubleshooting.md) | Common issues |
| [FAQ](docs/faq.md) | Frequently asked questions |

### Channel guides

| Channel | Docs |
|---------|------|
| [Discord](docs/channels/discord.md) | Webhook setup, embeds, alerts |
| [Telegram](docs/channels/telegram.md) | Bot setup, messages, alerts |
| [WebChat](docs/channels/webchat.md) | Built-in chat interface |

### Advanced docs

| Topic | Docs |
|-------|------|
| [Gateway](docs/gateway.md) | Flask server internals |
| [AI Config](docs/ai-config.md) | LLM provider setup |
| [Bot Factory](docs/bot-factory.md) | Generating trading bots |
| [Leaderboard](docs/leaderboard.md) | Ranking system |
| [Docker](docs/docker.md) | Container deployment |

---

## Roadmap

- [ ] **Strategy Backtesting** — test strategies on historical data
- [ ] **Bot Marketplace** — share and download bot configurations
- [ ] **Price Alerts** — notifications on market price movements
- [ ] **Portfolio Tracking** — track multiple wallets as a portfolio
- [ ] **Slack Integration** — Slack webhook alerts
- [ ] **Email Alerts** — SMTP notifications
- [ ] **Mobile App** — iOS/Android companion
- [ ] **Browser Extension** — Chrome extension for quick analysis
- [ ] **Copy Trading** — automated trade mirroring
- [ ] **Paper Trading** — risk-free strategy testing

---

## FAQ

**Q: Is this free to use?**
A: Yes! PolyClaw is 100% free and open source. AI features require your own API keys.

**Q: Do I need API keys?**
A: No. Basic features (wallet analysis, leaderboard, alerts) work without any API keys. Add Anthropic or OpenAI keys for AI chat and deep analysis.

**Q: Is my data safe?**
A: Yes. PolyClaw runs locally. No data is sent to external servers except Polymarket's public API and your configured notification channels.

**Q: Can I use this for automated trading?**
A: PolyClaw is for analysis, alerts, and strategy development. For automated trading, use the strategies and bot configs you generate with your own trading infrastructure.

**Q: How do I find good wallets to track?**
A: Use the leaderboard to find top performers, then analyze their strategies and subscribe to alerts.

**Q: How is this different from OpenClaw?**
A: OpenClaw is a general-purpose AI assistant for messaging. PolyClaw is specifically built for Polymarket trading intelligence — wallet analysis, strategy detection, trade alerts, and bot building.

**Q: Can I self-host this?**
A: Yes! That's the primary use case. Clone the repo, run setup, and you have your own trading intelligence system.

**Full FAQ:** [FAQ](docs/faq.md)

---

## Support

- 📖 [Documentation](docs/index.md)
- 🐛 [Report a Bug](https://github.com/polyclaw/polyclaw/issues/new?template=bug_report.md)
- 💡 [Request a Feature](https://github.com/polyclaw/polyclaw/issues/new?template=feature_request.md)
- 💬 [Discussions](https://github.com/polyclaw/polyclaw/discussions)
- 🎮 [Discord](https://discord.gg/polyclaw)

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Quick ways to contribute:**
- ⭐ **Star the repo** if you find it useful
- 🐛 **Report bugs** via Issues
- 💡 **Suggest features**
- 📝 **Improve documentation**
- 🔧 **Submit PRs**

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Disclaimer

PolyClaw is for educational and research purposes only. Trading prediction markets involves risk. Past performance does not guarantee future results. Always do your own research and never trade more than you can afford to lose.

---

## Molty

PolyClaw was inspired by [OpenClaw](https://github.com/openclaw/openclaw), built for Molty, a space lobster AI assistant. 🦞

We're building the same vision — but for Polymarket traders.

---

<p align="center">
  <strong>Built with 🦞 by the PolyClaw community</strong>
</p>

<p align="center">
  <a href="https://github.com/polyclaw/polyclaw">⭐ Star us on GitHub</a> ·
  <a href="https://discord.gg/polyclaw">Join our Discord</a>
</p>
