# Frequently Asked Questions

## General

### What is PolyClaw?

PolyClaw is a personal AI trading assistant for Polymarket. It helps you analyze wallets, track whales, detect strategies, and build trading bots. Think of it as OpenClaw, but specifically for prediction market trading.

### Is PolyClaw free?

Yes! PolyClaw is 100% free and open source under the MIT license. You can use, modify, and distribute it freely.

### Do I need API keys?

**No.** Basic features work without any API keys:
- Wallet analysis
- Trade history
- Leaderboard
- Discord/Telegram alerts
- Data export

**Yes, for AI features.** You need an Anthropic or OpenAI API key for:
- AI Chat assistant
- Deep strategy analysis
- Strategy ideation
- Bot configuration generation

### Which AI provider should I use?

We recommend **Anthropic Claude** (Opus or Sonnet) for:
- Better reasoning and analysis
- Longer context windows
- More nuanced strategy recommendations

OpenAI GPT-4 works well too, especially for simpler queries.

### Is my data safe?

Yes. PolyClaw runs entirely on your machine:
- No data is sent to external servers (except Polymarket's public API)
- API keys stay in your local `.env` file
- Webhook URLs stay in local config files
- No analytics or tracking

---

## Setup & Installation

### What are the system requirements?

- **Python 3.9+**
- **2GB RAM** (4GB recommended)
- **1GB disk space**
- **Internet connection** (for Polymarket API)

### Does it work on Windows?

Yes, via WSL2 (Windows Subsystem for Linux). Native Windows support is limited.

1. Install WSL2: `wsl --install`
2. Open Ubuntu/Debian terminal
3. Follow the standard setup instructions

### How do I update PolyClaw?

```bash
cd polyclaw
git pull
pip install -r requirements.txt
# Restart the app
python app.py
```

### Can I run it on a server?

Yes! PolyClaw works great on a VPS or cloud server. Just make sure to:
- Set `DEBUG=false`
- Use a strong `SECRET_KEY`
- Consider using a reverse proxy (nginx) for HTTPS

---

## Features

### How accurate is the P&L calculation?

P&L is calculated from trade history on Polymarket's public API. It's accurate for:
- Realized P&L (closed positions)
- Position sizing

It may not account for:
- Unrealized P&L (open positions)
- Fees in some edge cases

### How does strategy detection work?

PolyClaw analyzes trading patterns:
- **Entry/exit timing** — When do they buy/sell?
- **Position sizing** — How much per trade?
- **Market selection** — What markets do they prefer?
- **Hold duration** — How long do they hold?

Based on these patterns, it classifies traders as:
- Scalper, Swing Trader, Position Trader
- Momentum, Mean Reversion, Arbitrage
- And more...

### Can I copy trade with PolyClaw?

PolyClaw provides alerts and analysis for copy trading research, but doesn't execute trades automatically. You would:

1. Track successful wallets via alerts
2. Receive notifications when they trade
3. Manually execute similar trades

Automated copy trading is on the roadmap.

### How do leaderboard rankings work?

Rankings are based on:
- **P&L** — Total profit/loss
- **Win Rate** — Percentage of winning trades
- **Volume** — Total traded amount
- **Risk-Adjusted Returns** — Sharpe-like ratio

Anyone can submit a wallet to the leaderboard. Stats are refreshed periodically.

---

## Notifications

### Why am I not getting Discord alerts?

1. **Webhook deleted** — Check if it still exists in Discord
2. **Wrong URL** — Verify the webhook URL
3. **Channel permissions** — Ensure webhook can post
4. **Not subscribed** — Check your subscription config

### Why am I not getting Telegram alerts?

1. **Bot not started** — Send `/start` to your bot
2. **Wrong chat ID** — Verify your chat ID
3. **Bot blocked** — Unblock the bot
4. **Token expired** — Regenerate in BotFather

### Can I filter alerts by trade size?

Not currently, but it's on the roadmap. For now, all trades from subscribed wallets trigger alerts.

### How many wallets can I track?

There's no hard limit, but consider:
- API rate limits
- Notification spam
- Your attention capacity

We recommend tracking 5-20 wallets actively.

---

## Troubleshooting

### "Port 8080 is already in use"

```bash
# Find and kill the process
lsof -i :8080
kill -9 <PID>

# Or use a different port
python app.py --port 8081
```

### "Module not found"

```bash
# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### "API key not working"

1. Check `.env` has no extra spaces or quotes
2. Verify the key is valid and has billing
3. Restart PolyClaw after changing `.env`

### "Wallet not found"

- Verify the wallet address is correct
- Make sure the wallet has traded on Polymarket
- Try the full address (not shortened)

---

## Contributing

### How can I contribute?

- ⭐ Star the repo
- 🐛 Report bugs
- 💡 Suggest features
- 📝 Improve docs
- 🔧 Submit PRs

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details.

### What's on the roadmap?

- Strategy backtesting
- Bot marketplace
- Price alerts
- Portfolio tracking
- Slack/Email integration
- Mobile app
- Copy trading automation

---

## Legal

### Is this legal to use?

PolyClaw is a data analysis and notification tool. It accesses only Polymarket's public API. Using it for personal research and analysis is legal.

**Note:** Trading on Polymarket may have legal restrictions in your jurisdiction. Always check local laws.

### Is there any warranty?

No. PolyClaw is provided "as is" under the MIT License. See the [LICENSE](../LICENSE) for full details.

### Can I use this commercially?

Yes, the MIT License allows commercial use. You can:
- Use PolyClaw for commercial trading
- Build products on top of PolyClaw
- Offer PolyClaw as a service

Just include the license and copyright notice.

---

## Still have questions?

- 📖 [Full Documentation](index.md)
- 💬 [GitHub Discussions](https://github.com/polyclaw/polyclaw/discussions)
- 🎮 [Discord Community](https://discord.gg/polyclaw)
