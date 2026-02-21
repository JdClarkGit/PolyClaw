# Configuration Reference

Complete reference for all PolyClaw configuration options.

## Environment Variables

PolyClaw uses a `.env` file for configuration. Copy `.env.example` to `.env` and customize.

### Server Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | Port to run the gateway on |
| `DEBUG` | `false` | Enable debug mode (verbose logging) |
| `SECRET_KEY` | (required) | Random string for session security |

```env
PORT=8080
DEBUG=false
SECRET_KEY=your-random-secret-key-here
```

**Generating a secret key:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### AI Providers

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (none) | Anthropic API key for Claude |
| `OPENAI_API_KEY` | (none) | OpenAI API key for GPT |

```env
ANTHROPIC_API_KEY=sk-ant-api03-...
OPENAI_API_KEY=sk-...
```

**Notes:**
- At least one AI provider is required for AI features
- If both are configured, Anthropic is preferred
- Basic features work without any AI keys

### Advanced Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_TRADES` | `10000` | Maximum trades to fetch in full history mode |
| `RATE_LIMIT` | `60` | Requests per minute to Polymarket API |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

```env
MAX_TRADES=10000
RATE_LIMIT=60
LOG_LEVEL=INFO
```

## Configuration Files

### notifications_config.json

Stores Discord webhooks, Telegram bots, and wallet subscriptions.

```json
{
  "discord": {
    "whale-alerts": {
      "webhook_url": "https://discord.com/api/webhooks/...",
      "name": "whale-alerts"
    }
  },
  "telegram": {
    "my-alerts": {
      "bot_token": "123456:ABC...",
      "chat_id": "987654321",
      "name": "my-alerts"
    }
  },
  "subscriptions": {
    "0x1234...": ["discord:whale-alerts", "telegram:my-alerts"]
  }
}
```

**Note:** This file is created automatically when you configure channels via the Settings UI. It's gitignored by default.

### leaderboard_data.json

Stores leaderboard entries and cached wallet stats.

```json
{
  "wallets": {
    "0x1234...": {
      "address": "0x1234...",
      "pnl": 15234.56,
      "win_rate": 0.68,
      "total_trades": 342,
      "volume": 125000,
      "last_updated": "2026-02-10T12:00:00Z"
    }
  }
}
```

**Note:** This file is created automatically. It's gitignored by default.

## Command Line Options

### Starting the Gateway

```bash
python app.py [options]
```

| Option | Description |
|--------|-------------|
| `--port PORT` | Override the port (default: 8080) |
| `--debug` | Enable debug mode |
| `--doctor` | Run diagnostic checks |

### Examples

```bash
# Start on a different port
python app.py --port 3000

# Start in debug mode
python app.py --debug

# Run diagnostics
python app.py --doctor
```

## Docker Configuration

### docker-compose.yml

```yaml
version: '3.8'

services:
  polyclaw:
    build: .
    ports:
      - "${PORT:-8080}:8080"
    environment:
      - PORT=8080
      - DEBUG=${DEBUG:-false}
      - SECRET_KEY=${SECRET_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
    volumes:
      - ./notifications_config.json:/app/notifications_config.json
      - ./leaderboard_data.json:/app/leaderboard_data.json
    restart: unless-stopped
```

### Environment with Docker

Create a `.env` file next to `docker-compose.yml`:

```env
PORT=8080
DEBUG=false
SECRET_KEY=your-secret-key
ANTHROPIC_API_KEY=sk-ant-...
```

Then run:
```bash
docker-compose up -d
```

## Best Practices

### Security

1. **Never commit `.env`** — It's gitignored by default
2. **Use strong secret keys** — Generate random strings
3. **Rotate API keys** — Periodically update keys
4. **Monitor webhooks** — Check Discord/Telegram for unexpected activity

### Performance

1. **Adjust rate limits** — Lower `RATE_LIMIT` if you're hitting API limits
2. **Limit full history** — Set `MAX_TRADES` based on your needs
3. **Use debug sparingly** — Debug mode is verbose and slower

### Deployment

1. **Set DEBUG=false** — Never run debug in production
2. **Use Docker** — For consistent deployments
3. **Persist config files** — Mount volumes for notifications and leaderboard data
