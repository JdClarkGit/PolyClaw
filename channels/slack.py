#!/usr/bin/env python3
"""
Slack Channel Integration

Connect PolyClaw to Slack workspaces.
Inspired by OpenClaw's Slack channel.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger("polyclaw.channels.slack")

# Try to import slack SDK
try:
    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler
    HAS_SLACK = True
except ImportError:
    HAS_SLACK = False
    logger.warning("Slack SDK not installed. Run: pip install slack-bolt")

POLYCLAW_DIR = Path.home() / ".polyclaw"


@dataclass
class SlackConfig:
    """Slack channel configuration."""
    enabled: bool = False
    bot_token: Optional[str] = None  # xoxb-...
    app_token: Optional[str] = None  # xapp-...
    allow_from: List[str] = None  # User IDs
    channels: List[str] = None  # Channel IDs
    dm_policy: str = "pairing"
    require_mention: bool = True
    
    def __post_init__(self):
        if self.allow_from is None:
            self.allow_from = []
        if self.channels is None:
            self.channels = []


class SlackChannel:
    """
    Slack messaging channel.
    
    Uses Slack Bolt for Python with Socket Mode.
    """
    
    def __init__(self, config: SlackConfig = None):
        self.config = config or SlackConfig()
        self.app: Optional[App] = None
        self.handler = None
        self.connected = False
        self.message_handlers: List[Callable] = []
        
        # Load tokens from environment if not in config
        if not self.config.bot_token:
            self.config.bot_token = os.environ.get("SLACK_BOT_TOKEN")
        if not self.config.app_token:
            self.config.app_token = os.environ.get("SLACK_APP_TOKEN")
    
    def _setup_app(self):
        """Set up Slack Bolt app."""
        if not HAS_SLACK:
            raise RuntimeError("Slack SDK not installed")
        
        if not self.config.bot_token:
            raise RuntimeError("SLACK_BOT_TOKEN not set")
        
        self.app = App(token=self.config.bot_token)
        
        # Register event handlers
        @self.app.event("message")
        def handle_message(event, say):
            self._process_message(event, say)
        
        @self.app.event("app_mention")
        def handle_mention(event, say):
            self._process_message(event, say, is_mention=True)
    
    def _process_message(self, event: Dict, say: Callable, is_mention: bool = False):
        """Process incoming Slack message."""
        user = event.get("user", "")
        text = event.get("text", "")
        channel = event.get("channel", "")
        
        # Check permissions
        if not self._is_allowed(user):
            if self.config.dm_policy == "pairing":
                say("🦞 Please ask an admin to approve your access to PolyClaw.")
            return
        
        # Check mention requirement
        if not is_mention and self.config.require_mention:
            return
        
        # Remove bot mention from text
        text = self._clean_text(text)
        
        # Process through handlers
        for handler in self.message_handlers:
            try:
                response = handler({
                    "channel": "slack",
                    "user": user,
                    "text": text,
                    "channel_id": channel,
                    "timestamp": datetime.now().isoformat()
                })
                
                if response:
                    say(response)
            except Exception as e:
                logger.error(f"Handler error: {e}")
                say(f"🦞 Error: {str(e)}")
    
    def _is_allowed(self, user: str) -> bool:
        """Check if user is allowed."""
        if not self.config.allow_from:
            return True
        return user in self.config.allow_from or "*" in self.config.allow_from
    
    def _clean_text(self, text: str) -> str:
        """Remove bot mention from text."""
        import re
        return re.sub(r"<@[A-Z0-9]+>", "", text).strip()
    
    def add_handler(self, handler: Callable):
        """Add message handler."""
        self.message_handlers.append(handler)
    
    def start(self):
        """Start the Slack channel."""
        if not self.config.enabled:
            logger.info("Slack channel disabled")
            return
        
        self._setup_app()
        
        if self.config.app_token:
            self.handler = SocketModeHandler(self.app, self.config.app_token)
            self.handler.start()
            self.connected = True
            logger.info("Slack channel connected (Socket Mode)")
        else:
            logger.warning("SLACK_APP_TOKEN not set - Socket Mode unavailable")
    
    def stop(self):
        """Stop the Slack channel."""
        if self.handler:
            self.handler.close()
        self.connected = False
        logger.info("Slack channel disconnected")
    
    def send_message(self, channel: str, text: str, blocks: List = None) -> bool:
        """Send a message to Slack."""
        if not self.app:
            return False
        
        try:
            self.app.client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=blocks
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False
    
    def get_status(self) -> Dict:
        """Get channel status."""
        return {
            "channel": "slack",
            "connected": self.connected,
            "config": {
                "enabled": self.config.enabled,
                "dm_policy": self.config.dm_policy,
                "require_mention": self.config.require_mention
            }
        }


SLACK_SETUP = """
# Slack Channel Setup

## Create Slack App

1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name it "PolyClaw" and select your workspace

## Configure Permissions

1. Go to "OAuth & Permissions"
2. Add Bot Token Scopes:
   - `app_mentions:read`
   - `chat:write`
   - `channels:history`
   - `im:history`
   - `im:write`
   - `users:read`

## Enable Socket Mode

1. Go to "Socket Mode"
2. Enable Socket Mode
3. Create an App-Level Token with `connections:write` scope
4. Save the token (starts with `xapp-`)

## Install to Workspace

1. Go to "Install App"
2. Click "Install to Workspace"
3. Copy the Bot Token (starts with `xoxb-`)

## Configure PolyClaw

Set environment variables:
```bash
export SLACK_BOT_TOKEN="xoxb-your-token"
export SLACK_APP_TOKEN="xapp-your-token"
```

Or add to ~/.polyclaw/config.json:
```json
{
  "channels": {
    "slack": {
      "enabled": true,
      "bot_token": "xoxb-...",
      "app_token": "xapp-..."
    }
  }
}
```
"""
