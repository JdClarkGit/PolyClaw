# Security Guide

PolyClaw is designed with security in mind. This guide explains the security model and best practices.

## Architecture

### Local-First Design

PolyClaw runs entirely on your machine:

```
┌─────────────────────────────────────────────────┐
│              Your Machine                        │
│                                                 │
│  ┌─────────────┐    ┌─────────────────────┐    │
│  │    .env     │    │ notifications_      │    │
│  │ (API keys)  │    │ config.json         │    │
│  └─────────────┘    │ (webhooks, tokens)  │    │
│                     └─────────────────────┘    │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │         PolyClaw Gateway                 │   │
│  │       http://localhost:8080              │   │
│  └─────────────────────────────────────────┘   │
│                     │                          │
└─────────────────────│──────────────────────────┘
                      │
                      ▼ (outbound only)
        ┌─────────────────────────────────┐
        │   External Services (Public)     │
        │                                  │
        │ • Polymarket API (trade data)   │
        │ • Anthropic/OpenAI (AI - opt)   │
        │ • Discord Webhooks (opt)        │
        │ • Telegram Bot API (opt)        │
        └─────────────────────────────────┘
```

### What Stays Local

| Data | Location | Encrypted? |
|------|----------|------------|
| API keys | `.env` | No (plaintext) |
| Webhook URLs | `notifications_config.json` | No |
| Bot tokens | `notifications_config.json` | No |
| Leaderboard data | `leaderboard_data.json` | No |
| Trade data | In-memory | N/A |

### What Goes External

| Data | Destination | Purpose |
|------|-------------|---------|
| Wallet addresses | Polymarket API | Fetch trades |
| Trade data | AI providers | Analysis (optional) |
| Alert messages | Discord/Telegram | Notifications (optional) |

## Sensitive Data

### API Keys (.env)

Your `.env` file contains sensitive credentials:

```env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
SECRET_KEY=your-random-key
```

**Protection measures:**
- `.env` is in `.gitignore` — never committed
- Only read at startup — not exposed via API
- Not logged — even in debug mode

### Webhook URLs (notifications_config.json)

Discord webhook URLs are effectively passwords:

```json
{
  "discord": {
    "alerts": {
      "webhook_url": "https://discord.com/api/webhooks/123/abc..."
    }
  }
}
```

**Protection measures:**
- File is gitignored
- Only used for sending notifications
- Not exposed via any API (only name is shown)

### Telegram Bot Tokens

Bot tokens give full control over your bot:

```json
{
  "telegram": {
    "alerts": {
      "bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
    }
  }
}
```

**Protection measures:**
- File is gitignored
- Only used for sending messages
- Token not exposed via API

## Best Practices

### Environment Security

1. **Generate strong SECRET_KEY:**
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Never commit .env:**
   ```bash
   # Verify .env is ignored
   git status --ignored | grep .env
   ```

3. **Restrict file permissions:**
   ```bash
   chmod 600 .env
   chmod 600 notifications_config.json
   ```

### API Key Security

1. **Use dedicated keys** — Create keys just for PolyClaw
2. **Set spending limits** — Configure billing limits on AI providers
3. **Monitor usage** — Check provider dashboards regularly
4. **Rotate periodically** — Update keys every few months

### Webhook Security

1. **Use dedicated webhooks** — Create webhooks just for PolyClaw
2. **Monitor activity** — Check Discord webhook logs
3. **Name clearly** — Use names like "polyclaw-alerts"
4. **Delete if unused** — Remove webhooks you no longer need

### Network Security

1. **Don't expose publicly** — Keep on localhost unless needed
2. **Use reverse proxy** — If exposing, use nginx with HTTPS
3. **Set DEBUG=false** — Never run debug in production
4. **Firewall** — Block port 8080 from external access

## Threat Model

### What We Protect Against

| Threat | Mitigation |
|--------|------------|
| API key exposure | Local storage, gitignore |
| Webhook theft | Local storage, gitignore |
| Data exfiltration | No external data storage |
| MITM attacks | HTTPS for external APIs |
| Unauthorized access | Local-only by default |

### What We Don't Protect Against

| Threat | Your Responsibility |
|--------|---------------------|
| Compromised machine | System security |
| Stolen .env file | File permissions, encryption |
| Malicious code injection | Code review, trusted sources |
| Physical access | Device security |

## Diagnostics

### Check Configuration

Run the doctor command to check for security issues:

```bash
python app.py --doctor
```

This checks for:
- Missing SECRET_KEY
- DEBUG mode enabled
- Exposed ports
- Insecure file permissions

### Audit Your Setup

```bash
# Check what's exposed
netstat -an | grep 8080

# Check file permissions
ls -la .env notifications_config.json

# Check git status
git status --ignored

# Check for accidental commits
git log --all --full-history -- .env
```

## Incident Response

### If API Keys Are Exposed

1. **Revoke immediately:**
   - Anthropic: console.anthropic.com → API Keys → Delete
   - OpenAI: platform.openai.com → API Keys → Delete

2. **Generate new keys**

3. **Update .env:**
   ```bash
   # Edit .env with new keys
   nano .env
   
   # Restart PolyClaw
   python app.py
   ```

4. **Check for unauthorized usage:**
   - Review provider billing/usage dashboards
   - Look for unexpected charges

### If Webhooks Are Exposed

1. **Delete in Discord:**
   - Server Settings → Integrations → Webhooks → Delete

2. **Create new webhook**

3. **Update PolyClaw:**
   - Settings → Add new webhook
   - Update subscriptions

4. **Monitor for spam:**
   - Check channel for unexpected messages

### If Bot Token Is Exposed

1. **Revoke in BotFather:**
   - @BotFather → /mybots → Select bot → API Token → Revoke

2. **Get new token**

3. **Update config:**
   - Settings → Delete old bot → Add new bot

## Compliance

### Data Privacy

PolyClaw stores:
- No personal data
- No user accounts
- No analytics
- Only wallet addresses (public blockchain data)

### GDPR/CCPA

Since PolyClaw:
- Runs locally
- Stores no personal data
- Has no user accounts
- Sends no data to our servers

There are minimal privacy compliance concerns. You control all data.

## Reporting Vulnerabilities

If you discover a security issue:

1. **Do NOT** open a public issue
2. **Email:** [security contact]
3. **Include:**
   - Description
   - Steps to reproduce
   - Potential impact
   - Suggested fix

We'll respond within 48 hours.

## Security Checklist

Before using PolyClaw:

- [ ] Generated random SECRET_KEY
- [ ] Set DEBUG=false
- [ ] .env is gitignored
- [ ] File permissions restricted
- [ ] Not exposing port publicly
- [ ] Using dedicated API keys
- [ ] Using dedicated webhooks
- [ ] Monitoring API usage
