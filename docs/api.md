# API Reference

Complete REST API documentation for PolyClaw.

## Base URL

```
http://localhost:8080
```

## Authentication

No authentication required for local use. All endpoints are open.

---

## Wallet Analysis

### Get Trades

Fetch trade history for a wallet.

```http
GET /api/trades/{wallet}
```

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `wallet` | path | Wallet address (required) |
| `mode` | query | `recent` (default) or `full` |
| `limit` | query | Number of trades (10-10000) |

**Examples:**

```bash
# Recent trades (default ~100)
curl http://localhost:8080/api/trades/0x1234...

# Full history
curl http://localhost:8080/api/trades/0x1234...?mode=full

# Custom limit
curl http://localhost:8080/api/trades/0x1234...?limit=500
```

**Response:**

```json
{
  "success": true,
  "wallet": "0x1234...",
  "trades": [
    {
      "id": "trade_123",
      "timestamp": "2026-02-10T12:00:00Z",
      "market": "Will Trump win 2024?",
      "outcome": "Yes",
      "side": "BUY",
      "price": 0.65,
      "shares": 100,
      "amount": 65.00
    }
  ],
  "count": 100,
  "mode": "recent"
}
```

---

### Pattern Analysis

Get pattern analysis for a wallet.

```http
GET /api/analyze/{wallet}
```

**Response:**

```json
{
  "success": true,
  "wallet": "0x1234...",
  "analysis": {
    "pnl": 15234.56,
    "win_rate": 0.68,
    "total_trades": 342,
    "winning_trades": 233,
    "losing_trades": 109,
    "volume": 125000,
    "avg_trade_size": 365.50,
    "max_drawdown": -2500,
    "sharpe_ratio": 1.85,
    "profit_factor": 2.4,
    "kelly_criterion": 0.28,
    "trading_style": "swing_trader",
    "preferred_markets": ["politics", "sports"],
    "avg_hold_time": "2.5 days"
  }
}
```

---

### Compare Wallets

Compare multiple wallets side-by-side.

```http
GET /api/compare
```

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `wallets` | query | Comma-separated wallet addresses |

**Example:**

```bash
curl "http://localhost:8080/api/compare?wallets=0xabc,0xdef,0x123"
```

**Response:**

```json
{
  "success": true,
  "wallets": [
    {
      "address": "0xabc...",
      "pnl": 15234.56,
      "win_rate": 0.68,
      "volume": 125000
    },
    {
      "address": "0xdef...",
      "pnl": 8500.00,
      "win_rate": 0.72,
      "volume": 85000
    }
  ],
  "comparison": {
    "best_pnl": "0xabc...",
    "best_win_rate": "0xdef...",
    "highest_volume": "0xabc..."
  }
}
```

---

## AI Features

### Chat with PolyClaw

Conversational AI assistant.

```http
POST /api/chat
```

**Request Body:**

```json
{
  "message": "What strategies work best for election markets?",
  "wallet": "0x1234...",  // optional context
  "trades": [...]         // optional context
}
```

**Response:**

```json
{
  "success": true,
  "response": "Based on the data I've seen, successful election market traders often...",
  "provider": "anthropic"
}
```

---

### Deep AI Analysis

AI-powered wallet analysis.

```http
POST /api/ai-analyze
```

**Request Body:**

```json
{
  "wallet": "0x1234...",
  "trades": [...]
}
```

**Response:**

```json
{
  "success": true,
  "analysis": {
    "summary": "This wallet shows characteristics of a momentum trader...",
    "strengths": ["Good timing on entries", "Consistent position sizing"],
    "weaknesses": ["Holds losing positions too long"],
    "recommendations": ["Consider tighter stop losses"],
    "strategy_type": "momentum_trader",
    "confidence": 0.85
  }
}
```

---

### Check AI Providers

Get available AI providers.

```http
GET /api/ai-providers
```

**Response:**

```json
{
  "providers": ["anthropic", "openai"],
  "default": "anthropic"
}
```

---

## Strategy Engine

### Diagnose Strategy

Detect trading strategy from wallet history.

```http
GET /api/strategy/diagnose/{wallet}
```

**Response:**

```json
{
  "success": true,
  "wallet": "0x1234...",
  "strategy": {
    "type": "swing_trader",
    "confidence": 0.82,
    "characteristics": {
      "avg_hold_time": "2.5 days",
      "position_sizing": "consistent",
      "entry_pattern": "momentum_breakout",
      "exit_pattern": "target_based"
    },
    "similar_wallets": ["0xabc...", "0xdef..."]
  }
}
```

---

### Generate Strategy Ideas

Get AI-generated strategy ideas.

```http
POST /api/strategy/ideate
```

**Request Body:**

```json
{
  "market_type": "election",
  "risk_tolerance": "medium",
  "capital": 5000
}
```

**Response:**

```json
{
  "success": true,
  "ideas": [
    {
      "name": "Momentum Breakout",
      "description": "Buy when price crosses above 0.6 with volume spike",
      "entry_rules": ["price > 0.6", "volume > 2x average"],
      "exit_rules": ["price > 0.85 OR price < 0.45"],
      "risk_per_trade": "2%",
      "expected_win_rate": 0.55
    }
  ]
}
```

---

### Define Custom Strategy

Save a custom strategy definition.

```http
POST /api/strategy/define
```

**Request Body:**

```json
{
  "name": "My Momentum Strategy",
  "entry_rules": {
    "price_below": 0.4,
    "volume_min": 50000
  },
  "exit_rules": {
    "take_profit": 0.75,
    "stop_loss": 0.25
  },
  "position_sizing": {
    "max_position": 500,
    "risk_per_trade": 0.02
  }
}
```

---

## Leaderboard

### Get Leaderboard

Get wallet rankings.

```http
GET /api/leaderboard
```

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `sort` | query | `pnl`, `win_rate`, `volume`, `trades` |
| `limit` | query | Number of results (default: 50) |

**Response:**

```json
{
  "success": true,
  "wallets": [
    {
      "rank": 1,
      "address": "0x1234...",
      "pnl": 50000.00,
      "win_rate": 0.72,
      "volume": 250000,
      "total_trades": 500
    }
  ],
  "stats": {
    "total_wallets": 150,
    "total_volume": 5000000,
    "avg_win_rate": 0.52
  }
}
```

---

### Submit Wallet

Add a wallet to the leaderboard.

```http
POST /api/leaderboard/submit
```

**Request Body:**

```json
{
  "wallet": "0x1234..."
}
```

**Response:**

```json
{
  "success": true,
  "message": "Wallet added to leaderboard",
  "wallet": {
    "address": "0x1234...",
    "pnl": 15234.56,
    "win_rate": 0.68
  }
}
```

---

### Refresh Wallet

Update a wallet's stats on the leaderboard.

```http
POST /api/leaderboard/refresh/{wallet}
```

---

## Notifications

### List Channels

Get configured notification channels.

```http
GET /api/notifications/channels
```

**Response:**

```json
{
  "discord": {
    "whale-alerts": {
      "name": "whale-alerts",
      "webhook_url": "https://discord.com/..."
    }
  },
  "telegram": {
    "my-alerts": {
      "name": "my-alerts",
      "bot_token": "123...",
      "chat_id": "987..."
    }
  },
  "subscriptions": {
    "0x1234...": ["discord:whale-alerts"]
  }
}
```

---

### Add Discord Webhook

```http
POST /api/notifications/discord
```

**Request Body:**

```json
{
  "name": "whale-alerts",
  "webhook_url": "https://discord.com/api/webhooks/..."
}
```

---

### Add Telegram Bot

```http
POST /api/notifications/telegram
```

**Request Body:**

```json
{
  "name": "my-alerts",
  "bot_token": "123456:ABC...",
  "chat_id": "987654321"
}
```

---

### Subscribe to Wallet

```http
POST /api/notifications/subscribe
```

**Request Body:**

```json
{
  "wallet": "0x1234...",
  "channels": ["discord:whale-alerts", "telegram:my-alerts"]
}
```

---

### Unsubscribe from Wallet

```http
POST /api/notifications/unsubscribe
```

**Request Body:**

```json
{
  "wallet": "0x1234...",
  "channels": ["discord:whale-alerts"]
}
```

---

### Test Notification

```http
POST /api/notifications/test
```

**Request Body:**

```json
{
  "channel": "discord:whale-alerts"
}
```

---

### Delete Discord Webhook

```http
DELETE /api/notifications/discord/{name}
```

---

### Delete Telegram Bot

```http
DELETE /api/notifications/telegram/{name}
```

---

## Data Export

### Download CSV

```http
GET /api/download/{wallet}/csv
```

Returns a CSV file download.

---

### Download Excel

```http
GET /api/download/{wallet}/xlsx
```

Returns an Excel file download with styled headers.

---

## Error Responses

All errors follow this format:

```json
{
  "success": false,
  "error": "Error message here",
  "code": "ERROR_CODE"
}
```

**Common Error Codes:**

| Code | Description |
|------|-------------|
| `INVALID_WALLET` | Invalid wallet address format |
| `WALLET_NOT_FOUND` | No trades found for wallet |
| `RATE_LIMITED` | Too many requests |
| `AI_UNAVAILABLE` | No AI provider configured |
| `CHANNEL_NOT_FOUND` | Notification channel not found |
| `WEBHOOK_FAILED` | Failed to send notification |
