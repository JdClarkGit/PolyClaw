# Discord Integration

Complete guide to setting up Discord webhook alerts in PolyClaw.

## Prerequisites

- A Discord server where you have admin/manage webhooks permission
- A channel where you want to receive alerts

## Setup

### Step 1: Create a Webhook

1. Open Discord and go to your server
2. Click the gear icon (⚙️) next to the channel name to open Channel Settings
3. Go to **Integrations** → **Webhooks**
4. Click **New Webhook**
5. Give it a name (e.g., "PolyClaw Alerts")
6. Optionally upload an avatar (🦞)
7. Click **Copy Webhook URL**

### Step 2: Add to PolyClaw

**Via Web Interface:**

1. Open http://localhost:8080
2. Click the ⚙️ Settings icon
3. In the Discord section, click **Add Discord Webhook**
4. Enter a name (e.g., "whale-alerts")
5. Paste your webhook URL
6. Click **Add Webhook**

**Via API:**

```bash
curl -X POST http://localhost:8080/api/notifications/discord \
  -H "Content-Type: application/json" \
  -d '{
    "name": "whale-alerts",
    "webhook_url": "https://discord.com/api/webhooks/123456789/abcdefgh..."
  }'
```

### Step 3: Subscribe to Wallets

1. In Settings, go to **Wallet Subscriptions**
2. Enter a wallet address
3. Select your Discord channel
4. Click **Subscribe**

Or via API:

```bash
curl -X POST http://localhost:8080/api/notifications/subscribe \
  -H "Content-Type: application/json" \
  -d '{
    "wallet": "0x1234...",
    "channels": ["discord:whale-alerts"]
  }'
```

### Step 4: Test

Click **Test** next to your webhook in Settings, or:

```bash
curl -X POST http://localhost:8080/api/notifications/test \
  -H "Content-Type: application/json" \
  -d '{"channel": "discord:whale-alerts"}'
```

## Alert Format

PolyClaw sends rich Discord embeds:

```
┌─────────────────────────────────────┐
│ 🟢 New BUY Trade                    │
├─────────────────────────────────────┤
│ Market: Will Trump win 2024?        │
│ Outcome: Yes                        │
│                                     │
│ 💰 Size: $1,234.56                  │
│ 📊 Shares: 500                      │
│ 💵 Price: $0.6500                   │
│                                     │
│ 👤 Wallet: 0x1234...abcd            │
├─────────────────────────────────────┤
│ 🦞 PolyClaw Trade Alert             │
└─────────────────────────────────────┘
```

**Colors:**
- 🟢 Green border for BUY trades
- 🔴 Red border for SELL trades

## Advanced Configuration

### Multiple Webhooks

You can create multiple webhooks for different purposes:

```json
{
  "discord": {
    "whale-alerts": {
      "name": "whale-alerts",
      "webhook_url": "https://discord.com/api/webhooks/111..."
    },
    "small-trades": {
      "name": "small-trades",
      "webhook_url": "https://discord.com/api/webhooks/222..."
    }
  }
}
```

### Channel Organization Tips

- **#whale-alerts** — Track large traders
- **#my-trades** — Your own wallet activity
- **#leaderboard** — Top performer alerts
- **#research** — Wallets you're studying

## Security Best Practices

1. **Keep webhook URLs private** — Treat them like passwords
2. **Use dedicated webhooks** — Create separate webhooks for PolyClaw
3. **Monitor webhook activity** — Check Discord's webhook logs periodically
4. **Revoke if compromised** — Delete and recreate if URL is exposed

## Troubleshooting

### "Webhook URL is invalid"

- Make sure you copied the full URL
- Check there are no extra spaces
- Verify the webhook still exists in Discord

### "Rate limited"

Discord has rate limits on webhooks. PolyClaw respects these, but if you're tracking many active wallets, you may hit limits.

**Solutions:**
- Use fewer webhooks
- Track fewer wallets
- Use channel-specific filtering

### "Embed not showing"

- Check Discord embed permissions in the channel
- Verify webhook has "Send Messages" permission
- Try sending a test message

## Removing a Webhook

**Via Web Interface:**
Click the ❌ next to the webhook in Settings.

**Via API:**
```bash
curl -X DELETE http://localhost:8080/api/notifications/discord/whale-alerts
```

This removes the webhook config but doesn't delete it from Discord. To fully remove, also delete it in Discord's Channel Settings.
