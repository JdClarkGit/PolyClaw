#!/usr/bin/env python3
"""
PolyClaw Daemon - Background monitoring service

This daemon runs in the background and:
1. Monitors tracked wallets for new trades
2. Sends alerts to configured channels (Discord, Telegram)
3. Updates leaderboard data periodically
"""

import json
import os
import sys
import time
import signal
import logging
from datetime import datetime
from pathlib import Path
import requests

# Config paths
CONFIG_DIR = Path.home() / ".polyclaw"
TRACKING_FILE = CONFIG_DIR / "tracking.json"
CACHE_FILE = CONFIG_DIR / "trade_cache.json"
LOG_FILE = CONFIG_DIR / "daemon.log"

# Default settings
POLL_INTERVAL = 60  # Check every 60 seconds
GATEWAY_URL = "http://localhost:8080"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("polyclaw-daemon")


class TradeDaemon:
    """Background daemon for monitoring wallets"""
    
    def __init__(self):
        self.running = True
        self.trade_cache = self.load_cache()
        
        # Handle shutdown signals
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)
    
    def shutdown(self, signum, frame):
        """Handle shutdown signal"""
        logger.info("Shutdown signal received, stopping daemon...")
        self.running = False
        self.save_cache()
    
    def load_cache(self):
        """Load trade cache from file"""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE) as f:
                    return json.load(f)
            except:
                pass
        return {"last_trades": {}, "last_check": {}}
    
    def save_cache(self):
        """Save trade cache to file"""
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(self.trade_cache, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def load_tracking(self):
        """Load tracked wallets"""
        if TRACKING_FILE.exists():
            try:
                with open(TRACKING_FILE) as f:
                    return json.load(f).get("wallets", [])
            except:
                pass
        return []
    
    def fetch_trades(self, wallet):
        """Fetch recent trades for a wallet"""
        try:
            response = requests.get(
                f"{GATEWAY_URL}/api/trades/{wallet}?limit=20",
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("trades", [])
        except Exception as e:
            logger.error(f"Failed to fetch trades for {wallet[:8]}...: {e}")
        return []
    
    def get_new_trades(self, wallet, trades):
        """Identify new trades since last check"""
        last_trade_ids = self.trade_cache.get("last_trades", {}).get(wallet, [])
        
        new_trades = []
        current_ids = []
        
        for trade in trades:
            trade_id = trade.get("id") or trade.get("hash") or str(trade.get("timestamp", ""))
            current_ids.append(trade_id)
            
            if trade_id not in last_trade_ids:
                new_trades.append(trade)
        
        # Update cache
        if "last_trades" not in self.trade_cache:
            self.trade_cache["last_trades"] = {}
        self.trade_cache["last_trades"][wallet] = current_ids[:50]  # Keep last 50
        
        return new_trades
    
    def send_alert(self, wallet, trade):
        """Send alert for a new trade"""
        try:
            # Get notification channels for this wallet
            response = requests.get(f"{GATEWAY_URL}/api/notifications/channels", timeout=10)
            if response.status_code != 200:
                return
            
            config = response.json()
            subscriptions = config.get("subscriptions", {})
            
            # Check if wallet is subscribed
            channels = subscriptions.get(wallet, [])
            if not channels:
                return
            
            # Format trade info
            side = trade.get("side", "?").upper()
            market = trade.get("market", trade.get("title", "Unknown"))
            amount = float(trade.get("amount", 0))
            price = float(trade.get("price", 0))
            shares = trade.get("shares", int(amount / price) if price > 0 else 0)
            outcome = trade.get("outcome", "")
            
            wallet_info = {"address": wallet, "short": f"{wallet[:6]}...{wallet[-4:]}"}
            
            trade_data = {
                "side": side,
                "market": market,
                "amount": amount,
                "price": price,
                "shares": shares,
                "outcome": outcome,
            }
            
            # Send to each subscribed channel
            for channel in channels:
                self.send_to_channel(channel, trade_data, wallet_info, config)
            
            logger.info(f"Alert sent for {wallet[:8]}... - {side} {market[:30]}")
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    def send_to_channel(self, channel, trade, wallet_info, config):
        """Send alert to a specific channel"""
        try:
            channel_type, channel_name = channel.split(":", 1)
            
            if channel_type == "discord":
                self.send_discord_alert(channel_name, trade, wallet_info, config)
            elif channel_type == "telegram":
                self.send_telegram_alert(channel_name, trade, wallet_info, config)
                
        except Exception as e:
            logger.error(f"Failed to send to {channel}: {e}")
    
    def send_discord_alert(self, channel_name, trade, wallet_info, config):
        """Send alert to Discord webhook"""
        discord_config = config.get("discord", {}).get(channel_name)
        if not discord_config:
            return
        
        webhook_url = discord_config.get("webhook_url")
        if not webhook_url:
            return
        
        # Create embed
        side = trade["side"]
        color = 0x22c55e if side == "BUY" else 0xef4444  # Green or red
        emoji = "🟢" if side == "BUY" else "🔴"
        
        embed = {
            "title": f"{emoji} New {side} Trade",
            "color": color,
            "fields": [
                {"name": "Market", "value": trade["market"][:100], "inline": False},
                {"name": "💰 Size", "value": f"${trade['amount']:,.2f}", "inline": True},
                {"name": "📊 Shares", "value": str(trade["shares"]), "inline": True},
                {"name": "💵 Price", "value": f"${trade['price']:.4f}", "inline": True},
                {"name": "👤 Wallet", "value": wallet_info["short"], "inline": False},
            ],
            "footer": {"text": "🦞 PolyClaw Trade Alert"},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if trade.get("outcome"):
            embed["fields"].insert(1, {"name": "Outcome", "value": trade["outcome"], "inline": True})
        
        # Send webhook
        requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
    
    def send_telegram_alert(self, channel_name, trade, wallet_info, config):
        """Send alert to Telegram"""
        telegram_config = config.get("telegram", {}).get(channel_name)
        if not telegram_config:
            return
        
        bot_token = telegram_config.get("bot_token")
        chat_id = telegram_config.get("chat_id")
        if not bot_token or not chat_id:
            return
        
        # Format message
        side = trade["side"]
        emoji = "🟢" if side == "BUY" else "🔴"
        
        message = f"""{emoji} <b>New {side} Trade</b>

<b>Market:</b> {trade['market'][:100]}
"""
        if trade.get("outcome"):
            message += f"<b>Outcome:</b> {trade['outcome']}\n"
        
        message += f"""
💰 <b>Size:</b> ${trade['amount']:,.2f}
📊 <b>Shares:</b> {trade['shares']}
💵 <b>Price:</b> ${trade['price']:.4f}

👤 <b>Wallet:</b> <code>{wallet_info['short']}</code>

🦞 PolyClaw Trade Alert"""
        
        # Send message
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
    
    def check_wallets(self):
        """Check all tracked wallets for new trades"""
        wallets = self.load_tracking()
        
        if not wallets:
            return
        
        for wallet in wallets:
            try:
                trades = self.fetch_trades(wallet)
                
                if not trades:
                    continue
                
                # Check for new trades (skip on first run)
                if wallet in self.trade_cache.get("last_trades", {}):
                    new_trades = self.get_new_trades(wallet, trades)
                    
                    for trade in new_trades[:5]:  # Limit alerts per check
                        self.send_alert(wallet, trade)
                else:
                    # First run - just cache without alerting
                    self.get_new_trades(wallet, trades)
                    logger.info(f"Initialized tracking for {wallet[:8]}... ({len(trades)} trades)")
                
                # Update last check time
                if "last_check" not in self.trade_cache:
                    self.trade_cache["last_check"] = {}
                self.trade_cache["last_check"][wallet] = datetime.utcnow().isoformat()
                
            except Exception as e:
                logger.error(f"Error checking {wallet[:8]}...: {e}")
            
            # Small delay between wallets to avoid rate limiting
            time.sleep(2)
        
        # Save cache after checking all wallets
        self.save_cache()
    
    def run(self):
        """Main daemon loop"""
        logger.info("PolyClaw daemon started")
        logger.info(f"Monitoring interval: {POLL_INTERVAL}s")
        
        while self.running:
            try:
                wallets = self.load_tracking()
                logger.info(f"Checking {len(wallets)} tracked wallet(s)...")
                
                self.check_wallets()
                
            except Exception as e:
                logger.error(f"Error in daemon loop: {e}")
            
            # Wait for next check
            for _ in range(POLL_INTERVAL):
                if not self.running:
                    break
                time.sleep(1)
        
        logger.info("PolyClaw daemon stopped")


PID_FILE = CONFIG_DIR / "daemon.pid"


def run_daemon():
    """Entry point for daemon"""
    # Ensure config directory exists
    CONFIG_DIR.mkdir(exist_ok=True)
    
    # Write PID file
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    
    # Redirect stdout/stderr to log file for background operation
    sys.stdout = open(LOG_FILE, 'a')
    sys.stderr = sys.stdout
    
    try:
        daemon = TradeDaemon()
        daemon.run()
    finally:
        # Clean up PID file on exit
        try:
            PID_FILE.unlink()
        except:
            pass


if __name__ == "__main__":
    run_daemon()
