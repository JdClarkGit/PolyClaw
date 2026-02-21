"""
PolyClaw Channel System

Unified channel integration for Discord, Telegram, and other platforms.
Like OpenClaw's channel system but specialized for prediction markets.
"""

import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable
from abc import ABC, abstractmethod

# Memory system
from memory import get_memory

CONFIG_DIR = Path.home() / ".polyclaw"
CHANNELS_CONFIG = CONFIG_DIR / "channels.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("polyclaw.channels")


class ChannelMessage:
    """Represents a message from any channel"""
    
    def __init__(
        self,
        channel_type: str,
        channel_id: str,
        user_id: str,
        username: str,
        content: str,
        timestamp: datetime = None,
        reply_to: str = None,
        metadata: Dict = None,
    ):
        self.channel_type = channel_type
        self.channel_id = channel_id
        self.user_id = user_id
        self.username = username
        self.content = content
        self.timestamp = timestamp or datetime.now()
        self.reply_to = reply_to
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict:
        return {
            "channel_type": self.channel_type,
            "channel_id": self.channel_id,
            "user_id": self.user_id,
            "username": self.username,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "reply_to": self.reply_to,
            "metadata": self.metadata,
        }


class BaseChannel(ABC):
    """Base class for all channel integrations"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.memory = get_memory()
        self.message_handlers: List[Callable] = []
    
    @abstractmethod
    async def start(self):
        """Start the channel connection"""
        pass
    
    @abstractmethod
    async def stop(self):
        """Stop the channel connection"""
        pass
    
    @abstractmethod
    async def send_message(self, channel_id: str, content: str, **kwargs):
        """Send a message to a channel"""
        pass
    
    def add_handler(self, handler: Callable):
        """Add a message handler"""
        self.message_handlers.append(handler)
    
    async def handle_message(self, message: ChannelMessage):
        """Process an incoming message"""
        # Store in memory
        session_id = f"{message.channel_type}:{message.channel_id}"
        self.memory.remember_conversation(session_id, "user", message.content)
        
        # Call handlers
        for handler in self.message_handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Handler error: {e}")


class DiscordChannel(BaseChannel):
    """Discord channel integration"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.bot = None
        self.client = None
        self.token = config.get("token")
        self.guild_ids = config.get("guild_ids", [])
        self.dm_policy = config.get("dm_policy", "pairing")
        self.allowed_users = config.get("allowed_users", [])
    
    async def start(self):
        """Start Discord bot"""
        if not self.token:
            logger.warning("Discord: No token configured")
            return
        
        try:
            import discord
            from discord.ext import commands
            
            intents = discord.Intents.default()
            intents.message_content = True
            intents.dm_messages = True
            
            self.client = commands.Bot(command_prefix="!", intents=intents)
            
            @self.client.event
            async def on_ready():
                logger.info(f"Discord: Connected as {self.client.user}")
            
            @self.client.event
            async def on_message(msg):
                if msg.author.bot:
                    return
                
                # Check if mentioned or in DM
                mentioned = self.client.user in msg.mentions if self.client.user else False
                is_dm = isinstance(msg.channel, discord.DMChannel)
                
                if mentioned or is_dm:
                    content = msg.content.replace(f"<@{self.client.user.id}>", "").strip()
                    
                    message = ChannelMessage(
                        channel_type="discord",
                        channel_id=str(msg.channel.id),
                        user_id=str(msg.author.id),
                        username=msg.author.name,
                        content=content,
                        metadata={"guild_id": str(msg.guild.id) if msg.guild else None},
                    )
                    
                    await self.handle_message(message)
            
            # Start in background
            asyncio.create_task(self.client.start(self.token))
            logger.info("Discord: Starting...")
            
        except ImportError:
            logger.error("Discord: discord.py not installed")
    
    async def stop(self):
        """Stop Discord bot"""
        if self.client:
            await self.client.close()
    
    async def send_message(self, channel_id: str, content: str, **kwargs):
        """Send message to Discord channel"""
        if not self.client:
            return
        
        channel = self.client.get_channel(int(channel_id))
        if channel:
            await channel.send(content)


class TelegramChannel(BaseChannel):
    """Telegram channel integration"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.app = None
        self.token = config.get("token")
        self.allowed_users = config.get("allowed_users", [])
    
    async def start(self):
        """Start Telegram bot"""
        if not self.token:
            logger.warning("Telegram: No token configured")
            return
        
        try:
            from telegram import Update
            from telegram.ext import Application, MessageHandler, CommandHandler, filters
            
            self.app = Application.builder().token(self.token).build()
            
            async def handle_msg(update: Update, context):
                if not update.message or not update.message.text:
                    return
                
                user = update.message.from_user
                chat = update.message.chat
                
                message = ChannelMessage(
                    channel_type="telegram",
                    channel_id=str(chat.id),
                    user_id=str(user.id),
                    username=user.username or user.first_name,
                    content=update.message.text,
                    metadata={"chat_type": chat.type},
                )
                
                await self.handle_message(message)
            
            self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
            
            # Start polling
            asyncio.create_task(self._run_polling())
            logger.info("Telegram: Starting...")
            
        except ImportError:
            logger.error("Telegram: python-telegram-bot not installed")
    
    async def _run_polling(self):
        """Run Telegram polling"""
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
    
    async def stop(self):
        """Stop Telegram bot"""
        if self.app:
            await self.app.stop()
    
    async def send_message(self, channel_id: str, content: str, **kwargs):
        """Send message to Telegram chat"""
        if not self.app:
            return
        
        await self.app.bot.send_message(chat_id=int(channel_id), text=content)


class WebChatChannel(BaseChannel):
    """WebChat channel (built-in web UI)"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
    
    async def start(self):
        """WebChat is handled by the main Flask app"""
        logger.info("WebChat: Available at gateway")
    
    async def stop(self):
        pass
    
    async def send_message(self, channel_id: str, content: str, **kwargs):
        """WebChat messages are handled via SSE"""
        pass


class ChannelManager:
    """
    Manages all channel integrations.
    Like OpenClaw's channel manager.
    """
    
    def __init__(self):
        self.channels: Dict[str, BaseChannel] = {}
        self.config = self._load_config()
        self.memory = get_memory()
        self._message_handler = None
    
    def _load_config(self) -> Dict:
        """Load channels configuration"""
        if CHANNELS_CONFIG.exists():
            with open(CHANNELS_CONFIG) as f:
                return json.load(f)
        return {"channels": {}}
    
    def _save_config(self):
        """Save channels configuration"""
        with open(CHANNELS_CONFIG, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def set_message_handler(self, handler: Callable):
        """Set the global message handler"""
        self._message_handler = handler
    
    async def _default_handler(self, message: ChannelMessage):
        """Default message handler - routes to AI"""
        if self._message_handler:
            response = await self._message_handler(message)
            
            if response:
                # Store response in memory
                session_id = f"{message.channel_type}:{message.channel_id}"
                self.memory.remember_conversation(session_id, "assistant", response)
                
                # Send response back
                channel = self.channels.get(message.channel_type)
                if channel:
                    await channel.send_message(message.channel_id, response)
    
    def register_channel(self, name: str, channel: BaseChannel):
        """Register a channel"""
        channel.add_handler(self._default_handler)
        self.channels[name] = channel
        logger.info(f"Registered channel: {name}")
    
    async def start_all(self):
        """Start all enabled channels"""
        for name, channel in self.channels.items():
            if channel.enabled:
                try:
                    await channel.start()
                except Exception as e:
                    logger.error(f"Failed to start {name}: {e}")
    
    async def stop_all(self):
        """Stop all channels"""
        for name, channel in self.channels.items():
            try:
                await channel.stop()
            except Exception as e:
                logger.error(f"Failed to stop {name}: {e}")
    
    def get_status(self) -> Dict:
        """Get status of all channels"""
        status = {}
        for name, channel in self.channels.items():
            status[name] = {
                "enabled": channel.enabled,
                "configured": bool(channel.config.get("token")),
            }
        return status
    
    def configure_channel(self, name: str, config: Dict):
        """Configure a channel"""
        if "channels" not in self.config:
            self.config["channels"] = {}
        self.config["channels"][name] = config
        self._save_config()


def create_channel_manager() -> ChannelManager:
    """Create and configure channel manager"""
    manager = ChannelManager()
    
    # Load configurations
    config = manager.config.get("channels", {})
    
    # Register Discord
    discord_config = config.get("discord", {})
    if discord_config.get("token"):
        manager.register_channel("discord", DiscordChannel(discord_config))
    
    # Register Telegram
    telegram_config = config.get("telegram", {})
    if telegram_config.get("token"):
        manager.register_channel("telegram", TelegramChannel(telegram_config))
    
    # Register WebChat (always available)
    manager.register_channel("webchat", WebChatChannel({}))
    
    return manager
