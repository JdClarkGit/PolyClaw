# Changelog

All notable changes to PolyClaw will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-10

### Added
- 🎉 Initial public release of PolyClaw
- 🔍 **Wallet Analysis** - Analyze any Polymarket wallet
  - Complete trade history fetching (including full history mode)
  - P&L calculations with detailed breakdown
  - Risk metrics (Sharpe ratio, max drawdown, Kelly criterion)
  - Trading style detection (scalper, swing trader, arbitrageur, etc.)
- 🤖 **AI Chat** - Conversational AI assistant for trading strategies
  - Context-aware chat with current wallet data
  - Strategy ideation and recommendations
  - Supports OpenAI (GPT-4) and Anthropic (Claude)
- 🏆 **Leaderboard** - Public wallet rankings
  - Submit any wallet to the leaderboard
  - Sort by P&L, win rate, volume, or risk-adjusted returns
  - One-click analysis of top traders
- 🔔 **Discord & Telegram Alerts** - Real-time trade notifications
  - Webhook-based Discord integration
  - Telegram bot integration
  - Subscribe to multiple wallets
  - Customizable notification channels
- 📊 **Data Export** - Export trade data
  - CSV format
  - Excel (.xlsx) format with styled headers
- 🖥️ **Terminal Mode** - Alternative terminal-style interface
  - Real-time trade streaming
  - Order book visualization
  - Signal detection
- 🎨 **Modern UI** - Dark theme with red accents
  - Responsive design
  - Pill-shaped modern buttons
  - Floating AI chat panel
  - Settings modal for notifications

### Security
- Local-first architecture - all data stays on your machine
- API keys stored only in local `.env` file
- No external tracking or analytics

---

## [Unreleased]

### Planned
- Strategy backtesting
- Bot marketplace
- Price alerts
- Portfolio tracking
- Mobile app
- Browser extension

---

## How to Update

```bash
cd polyclaw
git pull origin main
pip install -r requirements.txt
```

Then restart the application.
