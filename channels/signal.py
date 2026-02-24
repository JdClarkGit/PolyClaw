#!/usr/bin/env python3
"""
Signal Channel Integration

Connect PolyClaw to Signal messenger using signal-cli.
Inspired by OpenClaw's Signal channel.
"""

import os
import json
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger("polyclaw.channels.signal")

POLYCLAW_DIR = Path.home() / ".polyclaw"
SIGNAL_DIR = POLYCLAW_DIR / "channels" / "signal"


@dataclass
class SignalConfig:
    """Signal channel configuration."""
    enabled: bool = False
    phone_number: Optional[str] = None  # Your Signal number
    allow_from: List[str] = None  # Allowed phone numbers
    groups: List[str] = None  # Allowed group IDs
    dm_policy: str = "pairing"
    signal_cli_path: str = "signal-cli"
    
    def __post_init__(self):
        if self.allow_from is None:
            self.allow_from = []
        if self.groups is None:
            self.groups = []


class SignalChannel:
    """
    Signal messaging channel using signal-cli.
    
    Requires signal-cli to be installed and configured.
    """
    
    def __init__(self, config: SignalConfig = None):
        self.config = config or SignalConfig()
        self.connected = False
        self.message_handlers: List[Callable] = []
        
        SIGNAL_DIR.mkdir(parents=True, exist_ok=True)
    
    def _run_signal_cli(self, *args) -> str:
        """Run a signal-cli command."""
        cmd = [self.config.signal_cli_path, "-u", self.config.phone_number] + list(args)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                logger.error(f"signal-cli error: {result.stderr}")
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.error("signal-cli timed out")
            return ""
        except FileNotFoundError:
            logger.error("signal-cli not found")
            return ""
    
    def check_installation(self) -> bool:
        """Check if signal-cli is installed and configured."""
        try:
            result = subprocess.run(
                [self.config.signal_cli_path, "--version"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def register(self, phone_number: str, captcha: str = None):
        """Register a new Signal number."""
        args = ["register", phone_number]
        if captcha:
            args.extend(["--captcha", captcha])
        
        return self._run_signal_cli(*args)
    
    def verify(self, verification_code: str):
        """Verify Signal registration."""
        return self._run_signal_cli("verify", verification_code)
    
    def send_message(self, to: str, message: str) -> bool:
        """Send a Signal message."""
        if not self.config.phone_number:
            logger.error("Signal phone number not configured")
            return False
        
        output = self._run_signal_cli(
            "send",
            "-m", message,
            to
        )
        
        return "successfully" in output.lower() or output == ""
    
    def receive_messages(self) -> List[Dict]:
        """Receive pending messages."""
        output = self._run_signal_cli("receive", "--json")
        
        messages = []
        for line in output.strip().split("\n"):
            if line:
                try:
                    msg = json.loads(line)
                    if msg.get("envelope", {}).get("dataMessage"):
                        messages.append({
                            "from": msg["envelope"]["source"],
                            "text": msg["envelope"]["dataMessage"].get("message", ""),
                            "timestamp": msg["envelope"]["timestamp"],
                            "group": msg["envelope"]["dataMessage"].get("groupInfo", {}).get("groupId")
                        })
                except json.JSONDecodeError:
                    continue
        
        return messages
    
    def _is_allowed(self, sender: str) -> bool:
        """Check if sender is allowed."""
        if not self.config.allow_from:
            return True
        return sender in self.config.allow_from or "*" in self.config.allow_from
    
    def add_handler(self, handler: Callable):
        """Add message handler."""
        self.message_handlers.append(handler)
    
    def process_messages(self):
        """Process incoming messages."""
        messages = self.receive_messages()
        
        for msg in messages:
            sender = msg["from"]
            
            if not self._is_allowed(sender):
                if self.config.dm_policy == "pairing":
                    self.send_message(
                        sender,
                        "🦞 PolyClaw: Please ask an admin to approve your access."
                    )
                continue
            
            for handler in self.message_handlers:
                try:
                    response = handler({
                        "channel": "signal",
                        "sender": sender,
                        "text": msg["text"],
                        "group": msg.get("group"),
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    if response:
                        self.send_message(sender, response)
                except Exception as e:
                    logger.error(f"Handler error: {e}")
    
    def get_status(self) -> Dict:
        """Get channel status."""
        return {
            "channel": "signal",
            "connected": self.connected,
            "installed": self.check_installation(),
            "phone": self.config.phone_number,
            "config": {
                "enabled": self.config.enabled,
                "dm_policy": self.config.dm_policy
            }
        }


SIGNAL_SETUP = """
# Signal Channel Setup

## Install signal-cli

### macOS
```bash
brew install signal-cli
```

### Linux
```bash
# Download from https://github.com/AsamK/signal-cli/releases
wget https://github.com/AsamK/signal-cli/releases/download/v0.12.0/signal-cli-0.12.0.tar.gz
tar xf signal-cli-0.12.0.tar.gz
sudo mv signal-cli-0.12.0/bin/signal-cli /usr/local/bin/
```

## Register Your Number

```bash
# Request verification code
signal-cli -u +1234567890 register

# If captcha required, get it from:
# https://signalcaptchas.org/registration/generate.html
signal-cli -u +1234567890 register --captcha "captcha-token"

# Verify with SMS code
signal-cli -u +1234567890 verify 123456
```

## Configure PolyClaw

Add to ~/.polyclaw/config.json:
```json
{
  "channels": {
    "signal": {
      "enabled": true,
      "phone_number": "+1234567890",
      "allow_from": ["+0987654321"],
      "dm_policy": "pairing"
    }
  }
}
```

## Security Notes

- Signal provides end-to-end encryption
- Keep your signal-cli data directory secure
- Use "pairing" dm_policy to prevent spam
"""
