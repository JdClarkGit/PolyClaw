"""
PolyClaw Notifications - Discord & Telegram Integration
Send trade alerts and notifications to external platforms.
"""

import os
import json
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Notifications config file
NOTIFICATIONS_FILE = os.path.join(os.path.dirname(__file__), 'notifications_config.json')


def load_notifications_config() -> Dict:
    """Load notifications configuration from file."""
    if os.path.exists(NOTIFICATIONS_FILE):
        try:
            with open(NOTIFICATIONS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "discord_webhooks": {},
        "telegram_configs": {},
        "wallet_subscriptions": {}
    }


def save_notifications_config(config: Dict):
    """Save notifications configuration to file."""
    with open(NOTIFICATIONS_FILE, 'w') as f:
        json.dump(config, f, indent=2)


# ============ DISCORD ============

def send_discord_notification(webhook_url: str, embed: Dict) -> bool:
    """Send a Discord webhook notification."""
    try:
        payload = {
            "username": "PolyClaw 🦞",
            "avatar_url": "https://em-content.zobj.net/source/twitter/376/lobster_1f99e.png",
            "embeds": [embed]
        }
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        return response.status_code in [200, 204]
    except Exception as e:
        print(f"Discord notification error: {e}")
        return False


def format_trade_discord_embed(trade: Dict, wallet_info: Dict) -> Dict:
    """Format a trade as a Discord embed."""
    side = trade.get('side', 'UNKNOWN').upper()
    is_buy = side == 'BUY'
    
    color = 0x22c55e if is_buy else 0xdc2626  # Green for buy, red for sell
    
    return {
        "title": f"{'🟢' if is_buy else '🔴'} New {side} Trade",
        "description": trade.get('market', 'Unknown Market'),
        "color": color,
        "fields": [
            {
                "name": "💰 Size",
                "value": f"${trade.get('value', 0):,.2f}",
                "inline": True
            },
            {
                "name": "📊 Shares",
                "value": f"{trade.get('shares', 0):,.0f}",
                "inline": True
            },
            {
                "name": "💵 Price",
                "value": f"${trade.get('price', 0):.4f}",
                "inline": True
            },
            {
                "name": "🎯 Outcome",
                "value": trade.get('outcome', 'N/A'),
                "inline": True
            },
            {
                "name": "👤 Trader",
                "value": wallet_info.get('username', trade.get('wallet', 'Unknown')[:10]),
                "inline": True
            }
        ],
        "footer": {
            "text": "PolyClaw Trade Alert"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def format_alert_discord_embed(title: str, message: str, alert_type: str = "info") -> Dict:
    """Format a general alert as a Discord embed."""
    colors = {
        "info": 0x3b82f6,
        "success": 0x22c55e,
        "warning": 0xf59e0b,
        "error": 0xdc2626
    }
    
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    
    return {
        "title": f"{icons.get(alert_type, 'ℹ️')} {title}",
        "description": message,
        "color": colors.get(alert_type, 0x3b82f6),
        "footer": {
            "text": "PolyClaw Alert"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def add_discord_webhook(name: str, webhook_url: str) -> Dict:
    """Add a Discord webhook configuration."""
    config = load_notifications_config()
    
    # Validate webhook URL
    if not webhook_url.startswith('https://discord.com/api/webhooks/'):
        return {"error": "Invalid Discord webhook URL"}
    
    # Test the webhook
    test_embed = format_alert_discord_embed(
        "Webhook Connected!",
        "PolyClaw is now connected to this channel. You'll receive trade alerts here.",
        "success"
    )
    
    if not send_discord_notification(webhook_url, test_embed):
        return {"error": "Failed to send test message. Check your webhook URL."}
    
    config["discord_webhooks"][name] = {
        "url": webhook_url,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "enabled": True
    }
    
    save_notifications_config(config)
    return {"success": True, "name": name}


def remove_discord_webhook(name: str) -> Dict:
    """Remove a Discord webhook configuration."""
    config = load_notifications_config()
    
    if name in config["discord_webhooks"]:
        del config["discord_webhooks"][name]
        save_notifications_config(config)
        return {"success": True}
    
    return {"error": "Webhook not found"}


# ============ TELEGRAM ============

def send_telegram_notification(bot_token: str, chat_id: str, message: str, parse_mode: str = "HTML") -> bool:
    """Send a Telegram notification."""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram notification error: {e}")
        return False


def format_trade_telegram_message(trade: Dict, wallet_info: Dict) -> str:
    """Format a trade as a Telegram message."""
    side = trade.get('side', 'UNKNOWN').upper()
    is_buy = side == 'BUY'
    emoji = '🟢' if is_buy else '🔴'
    
    return f"""
{emoji} <b>New {side} Trade</b>

<b>Market:</b> {trade.get('market', 'Unknown')[:50]}
<b>Outcome:</b> {trade.get('outcome', 'N/A')}

💰 <b>Size:</b> ${trade.get('value', 0):,.2f}
📊 <b>Shares:</b> {trade.get('shares', 0):,.0f}
💵 <b>Price:</b> ${trade.get('price', 0):.4f}

👤 <b>Trader:</b> {wallet_info.get('username', trade.get('wallet', 'Unknown')[:10])}

🦞 <i>PolyClaw Trade Alert</i>
""".strip()


def format_alert_telegram_message(title: str, message: str, alert_type: str = "info") -> str:
    """Format a general alert as a Telegram message."""
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    
    return f"""
{icons.get(alert_type, 'ℹ️')} <b>{title}</b>

{message}

🦞 <i>PolyClaw Alert</i>
""".strip()


def add_telegram_config(name: str, bot_token: str, chat_id: str) -> Dict:
    """Add a Telegram bot configuration."""
    config = load_notifications_config()
    
    # Test the connection
    test_message = format_alert_telegram_message(
        "Bot Connected!",
        "PolyClaw is now connected to this chat. You'll receive trade alerts here.",
        "success"
    )
    
    if not send_telegram_notification(bot_token, chat_id, test_message):
        return {"error": "Failed to send test message. Check your bot token and chat ID."}
    
    config["telegram_configs"][name] = {
        "bot_token": bot_token,
        "chat_id": chat_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "enabled": True
    }
    
    save_notifications_config(config)
    return {"success": True, "name": name}


def remove_telegram_config(name: str) -> Dict:
    """Remove a Telegram configuration."""
    config = load_notifications_config()
    
    if name in config["telegram_configs"]:
        del config["telegram_configs"][name]
        save_notifications_config(config)
        return {"success": True}
    
    return {"error": "Configuration not found"}


# ============ SUBSCRIPTIONS ============

def subscribe_to_wallet(wallet: str, channels: List[str]) -> Dict:
    """Subscribe channels to a wallet's trade alerts."""
    config = load_notifications_config()
    
    if wallet not in config["wallet_subscriptions"]:
        config["wallet_subscriptions"][wallet] = {
            "discord": [],
            "telegram": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    
    for channel in channels:
        if channel.startswith("discord:"):
            name = channel.replace("discord:", "")
            if name in config["discord_webhooks"]:
                if name not in config["wallet_subscriptions"][wallet]["discord"]:
                    config["wallet_subscriptions"][wallet]["discord"].append(name)
        elif channel.startswith("telegram:"):
            name = channel.replace("telegram:", "")
            if name in config["telegram_configs"]:
                if name not in config["wallet_subscriptions"][wallet]["telegram"]:
                    config["wallet_subscriptions"][wallet]["telegram"].append(name)
    
    save_notifications_config(config)
    return {"success": True, "subscriptions": config["wallet_subscriptions"][wallet]}


def unsubscribe_from_wallet(wallet: str, channels: List[str] = None) -> Dict:
    """Unsubscribe channels from a wallet's trade alerts."""
    config = load_notifications_config()
    
    if wallet not in config["wallet_subscriptions"]:
        return {"error": "No subscriptions for this wallet"}
    
    if channels is None:
        # Remove all subscriptions
        del config["wallet_subscriptions"][wallet]
    else:
        for channel in channels:
            if channel.startswith("discord:"):
                name = channel.replace("discord:", "")
                if name in config["wallet_subscriptions"][wallet]["discord"]:
                    config["wallet_subscriptions"][wallet]["discord"].remove(name)
            elif channel.startswith("telegram:"):
                name = channel.replace("telegram:", "")
                if name in config["wallet_subscriptions"][wallet]["telegram"]:
                    config["wallet_subscriptions"][wallet]["telegram"].remove(name)
    
    save_notifications_config(config)
    return {"success": True}


def notify_trade(wallet: str, trade: Dict, wallet_info: Dict) -> Dict:
    """Send trade notifications to all subscribed channels."""
    config = load_notifications_config()
    
    if wallet not in config["wallet_subscriptions"]:
        return {"sent": 0}
    
    subs = config["wallet_subscriptions"][wallet]
    sent_count = 0
    errors = []
    
    # Discord notifications
    for webhook_name in subs.get("discord", []):
        webhook_config = config["discord_webhooks"].get(webhook_name, {})
        if webhook_config.get("enabled"):
            embed = format_trade_discord_embed(trade, wallet_info)
            if send_discord_notification(webhook_config["url"], embed):
                sent_count += 1
            else:
                errors.append(f"discord:{webhook_name}")
    
    # Telegram notifications
    for tg_name in subs.get("telegram", []):
        tg_config = config["telegram_configs"].get(tg_name, {})
        if tg_config.get("enabled"):
            message = format_trade_telegram_message(trade, wallet_info)
            if send_telegram_notification(tg_config["bot_token"], tg_config["chat_id"], message):
                sent_count += 1
            else:
                errors.append(f"telegram:{tg_name}")
    
    return {"sent": sent_count, "errors": errors if errors else None}


def get_notification_channels() -> Dict:
    """Get all configured notification channels."""
    config = load_notifications_config()
    
    return {
        "discord": [
            {"name": name, "enabled": info.get("enabled", True)}
            for name, info in config.get("discord_webhooks", {}).items()
        ],
        "telegram": [
            {"name": name, "chat_id": info.get("chat_id"), "enabled": info.get("enabled", True)}
            for name, info in config.get("telegram_configs", {}).items()
        ],
        "subscriptions": config.get("wallet_subscriptions", {})
    }
