"""
PolyClaw Hooks System

Hooks automate actions when specific events occur.
"""

import json
from pathlib import Path

HOOKS_DIR = Path(__file__).parent
CONFIG_FILE = HOOKS_DIR / "hooks_config.json"

# Built-in hooks
BUILTIN_HOOKS = {
    "command-logger": {
        "name": "command-logger",
        "version": "1.0.0",
        "description": "Log all commands to history file",
        "trigger": "command",
        "enabled": True,
        "builtin": True,
    },
    "session-memory": {
        "name": "session-memory",
        "version": "1.0.0",
        "description": "Save context when creating new session",
        "trigger": "session_start",
        "enabled": True,
        "builtin": True,
    },
    "trade-alert": {
        "name": "trade-alert",
        "version": "1.0.0",
        "description": "Send notification for tracked wallet trades",
        "trigger": "trade_detected",
        "enabled": True,
        "builtin": True,
    },
    "whale-alert": {
        "name": "whale-alert",
        "version": "1.0.0",
        "description": "Alert on positions larger than $10,000",
        "trigger": "trade_detected",
        "enabled": False,
        "builtin": True,
    },
    "leaderboard-update": {
        "name": "leaderboard-update",
        "version": "1.0.0",
        "description": "Refresh leaderboard rankings daily",
        "trigger": "daily",
        "enabled": True,
        "builtin": True,
    },
}


def load_config():
    """Load hooks configuration"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"hooks": {}, "disabled": []}


def save_config(config):
    """Save hooks configuration"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def list_hooks():
    """List all available hooks"""
    config = load_config()
    hooks = []
    
    for name, hook in BUILTIN_HOOKS.items():
        hook_info = hook.copy()
        hook_info["enabled"] = name not in config.get("disabled", [])
        hooks.append(hook_info)
    
    return hooks


def enable_hook(name):
    """Enable a hook"""
    config = load_config()
    if name in config.get("disabled", []):
        config["disabled"].remove(name)
        save_config(config)
        return True
    return False


def disable_hook(name):
    """Disable a hook"""
    config = load_config()
    if "disabled" not in config:
        config["disabled"] = []
    if name not in config["disabled"]:
        config["disabled"].append(name)
        save_config(config)
        return True
    return False


def trigger_hooks(event_type, event_data):
    """Trigger all hooks for an event type"""
    config = load_config()
    results = []
    
    for name, hook in BUILTIN_HOOKS.items():
        if hook["trigger"] != event_type:
            continue
        if name in config.get("disabled", []):
            continue
        
        # Execute built-in hook logic
        try:
            result = execute_builtin_hook(name, event_data)
            results.append({"hook": name, "result": result})
        except Exception as e:
            results.append({"hook": name, "error": str(e)})
    
    return results


def execute_builtin_hook(name, event_data):
    """Execute a built-in hook"""
    if name == "command-logger":
        # Already handled by CLI
        return {"logged": True}
    
    elif name == "trade-alert":
        # Trigger notification
        from notifications import send_trade_alert
        return send_trade_alert(event_data)
    
    elif name == "whale-alert":
        trade = event_data.get("trade", {})
        amount = float(trade.get("amount", 0))
        if amount >= 10000:
            from notifications import send_whale_alert
            return send_whale_alert(event_data)
        return {"skipped": True, "reason": "amount below threshold"}
    
    elif name == "session-memory":
        # Save session context
        return {"saved": True}
    
    elif name == "leaderboard-update":
        # Refresh leaderboard
        return {"updated": True}
    
    return {"executed": True}
