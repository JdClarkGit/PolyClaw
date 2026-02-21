# Notification Channels

PolyClaw supports multiple notification channels for trade alerts. This guide covers setup for each channel.

## Overview

| Channel | Status | Use Case |
|---------|--------|----------|
| **Discord** | ✅ Full | Team alerts, community tracking |
| **Telegram** | ✅ Full | Personal alerts, mobile notifications |
| **WebChat** | ✅ Full | Built-in browser interface |
| **Slack** | 🔜 Planned | Workspace alerts |
| **Email** | 🔜 Planned | Digest notifications |

## Quick Setup

### Via Web Interface (Recommended)

1. Open PolyClaw at http://localhost:8080
2. Click the ⚙️ Settings icon (top right)
3. Add your Discord webhook or Telegram bot
4. Subscribe to wallets you want to track

### Via API

```bash
# Add Discord webhook
curl -X POST http://localhost:8080/api/notifications/discord \
  -H "Content-Type: application/json" \
  -d '{"name": "alerts", "webhook_url": "https://discord.com/api/webhooks/..."}'

# Add Telegram bot
curl -X POST http://localhost:8080/api/notifications/telegram \
  -H "Content-Type: application/json" \
  -d '{"name": "alerts", "bot_token": "123:ABC", "chat_id": "987654321"}'

# Subscribe to a wallet
curl -X POST http://localhost:8080/api/notifications/subscribe \
  -H "Content-Type: application/json" \
  -d '{"wallet": "0x1234...", "channels": ["discord:alerts"]}'
```

## Alert Format

### Trade Alert Content

When a tracked wallet makes a trade, you'll receive:

- **Trade type** (BUY/SELL)
- **Market name**
- **Outcome** (Yes/No)
- **Trade size** (USD)
- **Share count**
- **Price per share**
- **Wallet identifier**

### Discord Embed

```
🟢 New BUY Trade

Market: Will Trump win 2024?
Outcome: Yes

💰 Size: $1,234.56
📊 Shares: 500
💵 Price: $0.6500

👤 Wallet: 0x1234...abcd

🦞 PolyClaw Trade Alert
```

### Telegram Message

```
🟢 New BUY Trade

Market: Will Trump win 2024?
Outcome: Yes

💰 Size: $1,234.56
📊 Shares: 500
💵 Price: $0.6500

👤 Wallet: 0x1234...abcd

🦞 PolyClaw Trade Alert
```

## Channel Configuration

### Configuration File

All channel configs are stored in `notifications_config.json`:

```json
{
  "discord": {
    "channel-name": {
      "name": "channel-name",
      "webhook_url": "https://discord.com/api/webhooks/..."
    }
  },
  "telegram": {
    "channel-name": {
      "name": "channel-name",
      "bot_token": "123456:ABC...",
      "chat_id": "987654321"
    }
  },
  "subscriptions": {
    "0x1234...": ["discord:channel-name", "telegram:channel-name"]
  }
}
```

### Subscription Format

Subscriptions use the format `{channel_type}:{channel_name}`:

- `discord:whale-alerts`
- `telegram:my-bot`

A wallet can have multiple subscriptions to different channels.

## Detailed Channel Guides

- **[Discord Setup](channels/discord.md)** — Webhooks, embeds, permissions
- **[Telegram Setup](channels/telegram.md)** — Bots, chat IDs, groups
- **[WebChat](channels/webchat.md)** — Built-in interface

## Troubleshooting

### "Webhook failed"

1. Check the webhook URL is correct
2. Verify the webhook hasn't been deleted in Discord
3. Test the webhook with a curl command

### "Telegram not receiving messages"

1. Make sure you've started a chat with your bot
2. Verify your chat ID is correct
3. Check the bot token is valid

### "Subscriptions not working"

1. Check `notifications_config.json` exists
2. Verify the wallet address format
3. Ensure channels are configured before subscribing
