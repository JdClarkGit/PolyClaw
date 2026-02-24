#!/usr/bin/env python3
"""
WhatsApp Channel Integration

Connect PolyClaw to WhatsApp using whatsapp-web.js bridge.
Inspired by OpenClaw's WhatsApp channel.
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass

logger = logging.getLogger("polyclaw.channels.whatsapp")

POLYCLAW_DIR = Path.home() / ".polyclaw"
WHATSAPP_DIR = POLYCLAW_DIR / "channels" / "whatsapp"
CREDENTIALS_FILE = WHATSAPP_DIR / "credentials.json"


@dataclass
class WhatsAppConfig:
    """WhatsApp channel configuration."""
    enabled: bool = False
    allow_from: List[str] = None  # Phone numbers allowed to chat
    groups: List[str] = None  # Allowed group IDs
    dm_policy: str = "pairing"  # "pairing", "open", or "closed"
    require_mention: bool = True  # Require @mention in groups
    chunking_enabled: bool = True
    max_message_length: int = 4096
    
    def __post_init__(self):
        if self.allow_from is None:
            self.allow_from = []
        if self.groups is None:
            self.groups = []


class WhatsAppChannel:
    """
    WhatsApp messaging channel.
    
    Note: Full implementation requires a Node.js bridge using whatsapp-web.js
    This is a Python interface that communicates with that bridge.
    """
    
    def __init__(self, config: WhatsAppConfig = None):
        self.config = config or WhatsAppConfig()
        self.connected = False
        self.qr_code: Optional[str] = None
        self.phone_number: Optional[str] = None
        self.message_handlers: List[Callable] = []
        
        WHATSAPP_DIR.mkdir(parents=True, exist_ok=True)
    
    def is_allowed(self, sender: str) -> bool:
        """Check if sender is allowed to message."""
        if not self.config.allow_from:
            return True  # Allow all if no whitelist
        return sender in self.config.allow_from or "*" in self.config.allow_from
    
    def add_handler(self, handler: Callable):
        """Add a message handler."""
        self.message_handlers.append(handler)
    
    async def connect(self):
        """
        Connect to WhatsApp.
        
        In production, this would communicate with a Node.js bridge
        running whatsapp-web.js.
        """
        logger.info("WhatsApp connection requires Node.js bridge")
        logger.info("Run: npx polyclaw-whatsapp-bridge")
        
        # Check if bridge is running
        # This would be implemented via HTTP/WebSocket to the bridge
        
        return False
    
    async def disconnect(self):
        """Disconnect from WhatsApp."""
        self.connected = False
        logger.info("WhatsApp disconnected")
    
    async def send_message(self, to: str, message: str) -> bool:
        """
        Send a message via WhatsApp.
        
        Args:
            to: Phone number or group ID
            message: Message text
        """
        if not self.connected:
            logger.error("WhatsApp not connected")
            return False
        
        # Chunk long messages
        if self.config.chunking_enabled and len(message) > self.config.max_message_length:
            chunks = self._chunk_message(message)
            for chunk in chunks:
                # Send via bridge
                pass
        else:
            # Send via bridge
            pass
        
        logger.info(f"Sent WhatsApp message to {to[:8]}...")
        return True
    
    def _chunk_message(self, message: str) -> List[str]:
        """Split message into chunks."""
        chunks = []
        max_len = self.config.max_message_length
        
        while message:
            if len(message) <= max_len:
                chunks.append(message)
                break
            
            # Find a good break point
            break_point = message.rfind('\n', 0, max_len)
            if break_point == -1:
                break_point = message.rfind(' ', 0, max_len)
            if break_point == -1:
                break_point = max_len
            
            chunks.append(message[:break_point])
            message = message[break_point:].lstrip()
        
        return chunks
    
    async def handle_incoming(self, message: Dict):
        """Handle incoming WhatsApp message."""
        sender = message.get("from", "")
        text = message.get("body", "")
        is_group = message.get("isGroup", False)
        
        # Check permissions
        if not self.is_allowed(sender):
            if self.config.dm_policy == "pairing":
                # Send pairing code
                await self._send_pairing_code(sender)
            return
        
        # Check mention requirement in groups
        if is_group and self.config.require_mention:
            if "@polyclaw" not in text.lower():
                return
        
        # Process message through handlers
        for handler in self.message_handlers:
            try:
                await handler({
                    "channel": "whatsapp",
                    "sender": sender,
                    "text": text,
                    "is_group": is_group,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Handler error: {e}")
    
    async def _send_pairing_code(self, sender: str):
        """Send pairing code to unknown sender."""
        import secrets
        code = secrets.token_hex(3).upper()
        
        # Store pairing code
        pairing_file = WHATSAPP_DIR / "pairing_codes.json"
        codes = {}
        if pairing_file.exists():
            codes = json.loads(pairing_file.read_text())
        
        codes[sender] = {
            "code": code,
            "created_at": datetime.now().isoformat()
        }
        pairing_file.write_text(json.dumps(codes, indent=2))
        
        # Send code message
        await self.send_message(
            sender,
            f"🦞 PolyClaw Pairing\n\n"
            f"Your pairing code: {code}\n\n"
            f"Run: polyclaw pairing approve {code}\n\n"
            f"to allow messages from this number."
        )
    
    def get_status(self) -> Dict:
        """Get channel status."""
        return {
            "channel": "whatsapp",
            "connected": self.connected,
            "phone": self.phone_number,
            "config": {
                "enabled": self.config.enabled,
                "dm_policy": self.config.dm_policy,
                "allow_from_count": len(self.config.allow_from),
                "groups_count": len(self.config.groups)
            }
        }


# Setup instructions
WHATSAPP_SETUP = """
# WhatsApp Channel Setup

PolyClaw can connect to WhatsApp using the whatsapp-web.js library.

## Requirements
- Node.js 18+
- A phone with WhatsApp installed

## Setup Steps

1. Install the WhatsApp bridge:
   ```
   npm install -g polyclaw-whatsapp-bridge
   ```

2. Run the bridge:
   ```
   polyclaw-whatsapp-bridge
   ```

3. Scan the QR code with your phone

4. Configure allowed contacts in ~/.polyclaw/config.json:
   ```json
   {
     "channels": {
       "whatsapp": {
         "enabled": true,
         "allow_from": ["+1234567890"],
         "dm_policy": "pairing"
       }
     }
   }
   ```

## Security Notes

- Use "pairing" dm_policy to require approval for new senders
- Never set dm_policy to "open" unless you want anyone to message your bot
- Keep your session credentials secure
"""
