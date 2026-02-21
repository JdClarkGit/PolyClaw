# Telegram Integration

Complete guide to setting up Telegram bot alerts in PolyClaw.

## Prerequisites

- A Telegram account
- Basic familiarity with Telegram bots

## Setup

### Step 1: Create a Bot

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Start a chat and send `/newbot`
3. Follow the prompts:
   - Enter a name for your bot (e.g., "PolyClaw Alerts")
   - Enter a username (must end in `bot`, e.g., `polyclaw_alerts_bot`)
4. BotFather will give you a **token** like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
5. **Save this token** — you'll need it

### Step 2: Get Your Chat ID

**Option A: Use @userinfobot**
1. Search for [@userinfobot](https://t.me/userinfobot)
2. Start a chat and send any message
3. It will reply with your user ID

**Option B: Use @getidsbot**
1. Search for [@getidsbot](https://t.me/getidsbot)
2. Forward any message to it
3. It will show the chat ID

**Option C: For Groups**
1. Add your bot to the group
2. Send a message in the group
3. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
4. Find the `chat.id` in the response

### Step 3: Start Your Bot

**Important:** You must start a conversation with your bot before it can send you messages.

1. Search for your bot by its username
2. Click **Start** or send `/start`

### Step 4: Add to PolyClaw

**Via Web Interface:**

1. Open http://localhost:8080
2. Click the ⚙️ Settings icon
3. In the Telegram section, click **Add Telegram Bot**
4. Enter a name (e.g., "my-alerts")
5. Paste your bot token
6. Enter your chat ID
7. Click **Add Bot**

**Via API:**

```bash
curl -X POST http://localhost:8080/api/notifications/telegram \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-alerts",
    "bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
    "chat_id": "987654321"
  }'
```

### Step 5: Subscribe to Wallets

1. In Settings, go to **Wallet Subscriptions**
2. Enter a wallet address
3. Select your Telegram channel
4. Click **Subscribe**

Or via API:

```bash
curl -X POST http://localhost:8080/api/notifications/subscribe \
  -H "Content-Type: application/json" \
  -d '{
    "wallet": "0x1234...",
    "channels": ["telegram:my-alerts"]
  }'
```

### Step 6: Test

Click **Test** next to your bot in Settings, or:

```bash
curl -X POST http://localhost:8080/api/notifications/test \
  -H "Content-Type: application/json" \
  -d '{"channel": "telegram:my-alerts"}'
```

## Alert Format

PolyClaw sends HTML-formatted Telegram messages:

```
🟢 New BUY Trade

<b>Market:</b> Will Trump win 2024?
<b>Outcome:</b> Yes

💰 <b>Size:</b> $1,234.56
📊 <b>Shares:</b> 500
💵 <b>Price:</b> $0.6500

👤 <b>Wallet:</b> <code>0x1234...abcd</code>

🦞 PolyClaw Trade Alert
```

## Group Alerts

You can send alerts to a Telegram group:

1. Create a group or use an existing one
2. Add your bot to the group (as admin recommended)
3. Get the group's chat ID (usually starts with `-`)
4. Use the group chat ID in your config

**Note:** Group chat IDs are negative numbers (e.g., `-1001234567890`).

## Advanced Configuration

### Multiple Bots

You can configure multiple Telegram bots:

```json
{
  "telegram": {
    "whale-alerts": {
      "name": "whale-alerts",
      "bot_token": "111:AAA...",
      "chat_id": "123456789"
    },
    "group-alerts": {
      "name": "group-alerts",
      "bot_token": "222:BBB...",
      "chat_id": "-1001234567890"
    }
  }
}
```

### Silent Notifications

To send silent (no-sound) notifications, this would require modifying the notification code. Currently all alerts use default notification settings.

## Security Best Practices

1. **Keep bot tokens private** — Never share your token
2. **Don't post tokens publicly** — Regenerate if exposed
3. **Use dedicated bots** — Create separate bots for PolyClaw
4. **Limit bot permissions** — Don't give admin rights unless needed

### Regenerating a Token

If your token is compromised:

1. Go to [@BotFather](https://t.me/BotFather)
2. Send `/mybots`
3. Select your bot
4. Choose **API Token** → **Revoke current token**
5. Update your PolyClaw config with the new token

## Troubleshooting

### "Bot token is invalid"

- Check you copied the full token
- Verify there are no extra spaces
- Make sure you're using the token, not the bot username

### "Chat not found"

- Verify your chat ID is correct
- Make sure you've started a conversation with the bot
- For groups, ensure the bot is a member

### "Forbidden: bot was blocked"

- You've blocked the bot — unblock it
- Or the bot was removed from the group

### "Not receiving messages"

1. Verify you started a chat with the bot
2. Check the chat ID is correct
3. Test with a direct API call:

```bash
curl "https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=Test"
```

## Removing a Bot

**Via Web Interface:**
Click the ❌ next to the bot in Settings.

**Via API:**
```bash
curl -X DELETE http://localhost:8080/api/notifications/telegram/my-alerts
```

This removes the config from PolyClaw but doesn't delete the bot. To fully remove, go to @BotFather and use `/deletebot`.
