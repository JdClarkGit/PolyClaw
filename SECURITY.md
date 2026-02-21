# Security Policy

## Overview

PolyClaw is designed with security in mind. This document outlines our security practices and how to report vulnerabilities.

## Security Features

### 🔒 Local-First Architecture

PolyClaw runs entirely on your local machine. Your data stays with you:

- **No cloud storage** - All data is stored locally in JSON files
- **No tracking** - We don't collect any usage analytics
- **No external servers** - Only Polymarket's public API is accessed
- **No accounts required** - Use PolyClaw without creating an account

### 🔑 API Key Security

Your API keys are never exposed:

- **Stored locally only** - Keys are read from your `.env` file
- **Never transmitted** - Keys are only used for local API calls
- **Not in git** - `.env` is gitignored by default
- **Optional** - Basic features work without any API keys

### 🔔 Notification Security

Discord webhooks and Telegram bots:

- **Stored locally** - In `notifications_config.json`
- **You control access** - Create your own webhooks/bots
- **Test before use** - Built-in test functionality
- **Easy to revoke** - Delete webhooks/bots from Discord/Telegram anytime

## Best Practices

### Environment Variables

1. **Never commit `.env`** - It's gitignored by default
2. **Use strong keys** - Generate random strings for `SECRET_KEY`
3. **Rotate keys** - Periodically update API keys
4. **Limit permissions** - Use API keys with minimal required permissions

### Webhook Security

1. **Keep URLs private** - Webhook URLs are like passwords
2. **Use unique webhooks** - Create separate webhooks for PolyClaw
3. **Monitor activity** - Check webhook usage in Discord settings
4. **Revoke if compromised** - Delete and recreate if leaked

### Running PolyClaw

1. **Use latest version** - Keep PolyClaw updated
2. **Review code changes** - Check updates before pulling
3. **Use virtual environment** - Isolate Python dependencies
4. **Firewall** - Don't expose port 8080 to the internet unless intended

## Data Storage

PolyClaw stores data in these local files:

| File | Contents | Sensitive? |
|------|----------|------------|
| `.env` | API keys, secrets | **Yes** - Never share |
| `notifications_config.json` | Webhooks, bot tokens | **Yes** - Contains secrets |
| `leaderboard_data.json` | Public wallet data | No - Public addresses |

## Reporting Vulnerabilities

If you discover a security vulnerability:

1. **Do NOT** open a public issue
2. **Email** security concerns to [your-email@example.com]
3. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work with you to address the issue.

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest  | ✅ Yes    |
| < Latest | ❌ No    |

Always use the latest version for security updates.

## Security Checklist

Before deploying PolyClaw:

- [ ] Created `.env` from `.env.example`
- [ ] Generated random `SECRET_KEY`
- [ ] Verified `.env` is gitignored
- [ ] Set `DEBUG=false` for production
- [ ] Created dedicated Discord webhooks
- [ ] Created dedicated Telegram bot
- [ ] Not exposing port 8080 publicly

## Third-Party Services

PolyClaw interacts with these external services:

| Service | Data Sent | Purpose |
|---------|-----------|---------|
| Polymarket API | Wallet addresses | Fetch trade data |
| OpenAI API (optional) | Trade data for analysis | AI analysis |
| Anthropic API (optional) | Trade data for analysis | AI analysis |
| Discord Webhooks (optional) | Trade alerts | Notifications |
| Telegram API (optional) | Trade alerts | Notifications |

## License

This security policy is part of the PolyClaw project under the MIT License.

---

Questions about security? Open a discussion or contact us directly.
