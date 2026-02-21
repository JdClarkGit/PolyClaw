# PolyClaw Hooks

Hooks let you automate actions when specific events occur in PolyClaw.

## Built-in Hooks

| Hook | Trigger | Description |
|------|---------|-------------|
| `command-logger` | Any command | Log all commands to history |
| `session-memory` | `/new` command | Save context when starting new session |
| `trade-alert` | New trade detected | Send notification for tracked wallet trades |
| `whale-alert` | Large position | Alert on positions > $10,000 |
| `leaderboard-update` | Daily | Refresh leaderboard rankings |

## Managing Hooks

```bash
polyclaw hooks list                 # List all hooks
polyclaw hooks enable <name>        # Enable a hook
polyclaw hooks disable <name>       # Disable a hook
```

## Creating Custom Hooks

Hooks are Python modules in the `hooks/` directory:

```python
# hooks/my_hook.py

HOOK_META = {
    "name": "my-hook",
    "version": "1.0.0",
    "description": "My custom hook",
    "trigger": "trade_detected",  # or "command", "daily", etc.
}

def execute(event):
    """
    Called when the trigger fires.
    
    Args:
        event: dict with event details
    
    Returns:
        dict with result or None
    """
    wallet = event.get("wallet")
    trade = event.get("trade")
    
    # Do something with the event
    print(f"New trade from {wallet}")
    
    return {"processed": True}
```

## Hook Events

| Event | Data |
|-------|------|
| `command` | `{"command": str, "args": list}` |
| `trade_detected` | `{"wallet": str, "trade": dict}` |
| `analysis_complete` | `{"wallet": str, "analysis": dict}` |
| `session_start` | `{"session_id": str}` |
| `session_end` | `{"session_id": str, "messages": int}` |
| `daily` | `{"date": str}` |

## Example: Discord Alert Hook

```python
# hooks/discord_alert.py
import requests

HOOK_META = {
    "name": "discord-alert",
    "trigger": "trade_detected",
}

WEBHOOK_URL = "your-webhook-url"

def execute(event):
    trade = event.get("trade", {})
    wallet = event.get("wallet", "Unknown")
    
    message = {
        "content": f"🦞 **New Trade Alert**\n"
                   f"Wallet: `{wallet[:8]}...`\n"
                   f"Side: {trade.get('side')}\n"
                   f"Amount: ${trade.get('amount', 0):,.2f}"
    }
    
    requests.post(WEBHOOK_URL, json=message)
    return {"sent": True}
```
