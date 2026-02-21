#!/usr/bin/env python3
"""
PolyClaw Discord Bot - Interactive Discord interface

This bot allows users to interact with PolyClaw via Discord:
- /analyze <wallet> - Analyze a wallet
- /track <wallet> - Subscribe to alerts
- /untrack <wallet> - Unsubscribe
- /leaderboard - Show top performers
- /compare <w1> <w2> - Compare wallets
- /chat <message> - Talk to AI
- /help - Show commands
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
import requests
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8080")
ALLOWED_GUILD_IDS = os.getenv("DISCORD_GUILD_IDS", "").split(",")

# Paths
CONFIG_DIR = Path.home() / ".polyclaw"
DISCORD_TRACKING_FILE = CONFIG_DIR / "discord_tracking.json"

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Discord intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True


def load_tracking():
    """Load tracking data"""
    CONFIG_DIR.mkdir(exist_ok=True)
    if DISCORD_TRACKING_FILE.exists():
        with open(DISCORD_TRACKING_FILE) as f:
            return json.load(f)
    return {}


def save_tracking(data):
    """Save tracking data"""
    with open(DISCORD_TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def api_request(endpoint, method="GET", data=None):
    """Make API request to gateway"""
    url = f"{GATEWAY_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=30)
        else:
            response = requests.post(url, json=data, timeout=60)
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to PolyClaw gateway. Is it running?"}
    except Exception as e:
        return {"error": str(e)}


def format_currency(amount):
    """Format currency"""
    if amount >= 0:
        return f"+${amount:,.2f}"
    return f"-${abs(amount):,.2f}"


def shorten_address(addr):
    """Shorten wallet address"""
    if len(addr) > 12:
        return f"{addr[:6]}...{addr[-4:]}"
    return addr


class PolyClaw(commands.Bot):
    """PolyClaw Discord Bot"""
    
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.synced = False
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"Logged in as {self.user}")
        
        if not self.synced:
            # Sync slash commands
            if ALLOWED_GUILD_IDS and ALLOWED_GUILD_IDS != [""]:
                for guild_id in ALLOWED_GUILD_IDS:
                    try:
                        guild = discord.Object(id=int(guild_id))
                        await self.tree.sync(guild=guild)
                        logger.info(f"Synced commands to guild {guild_id}")
                    except Exception as e:
                        logger.error(f"Failed to sync to guild {guild_id}: {e}")
            else:
                # Global sync
                await self.tree.sync()
                logger.info("Synced commands globally")
            
            self.synced = True
        
        # Set status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Polymarket trades | /help"
            )
        )


bot = PolyClaw()


# ============================================================
# SLASH COMMANDS
# ============================================================

@bot.tree.command(name="help", description="Show PolyClaw commands")
async def cmd_help(interaction: discord.Interaction):
    """Show help message"""
    embed = discord.Embed(
        title="🦞 PolyClaw Commands",
        color=0xef4444
    )
    
    embed.add_field(
        name="📊 Analysis",
        value="`/analyze <wallet>` - Analyze a wallet\n"
              "`/compare <w1> <w2>` - Compare wallets\n"
              "`/leaderboard` - Top performers",
        inline=False
    )
    
    embed.add_field(
        name="🔔 Alerts",
        value="`/track <wallet>` - Subscribe to alerts\n"
              "`/untrack <wallet>` - Unsubscribe\n"
              "`/mywallets` - Your tracked wallets",
        inline=False
    )
    
    embed.add_field(
        name="🤖 AI Assistant",
        value="`/chat <message>` - Ask PolyClaw anything",
        inline=False
    )
    
    embed.set_footer(text="🦞 PolyClaw - Polymarket Trading Intelligence")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="analyze", description="Analyze a Polymarket wallet")
@app_commands.describe(wallet="The wallet address to analyze")
async def cmd_analyze(interaction: discord.Interaction, wallet: str):
    """Analyze a wallet"""
    await interaction.response.defer(thinking=True)
    
    # Fetch data
    result = api_request(f"/api/trades/{wallet}")
    
    if result.get("error"):
        await interaction.followup.send(f"❌ Error: {result['error']}")
        return
    
    trades = result.get("trades", [])
    
    if not trades:
        await interaction.followup.send("No trades found for this wallet.")
        return
    
    # Get analysis
    analysis = api_request(f"/api/analyze/{wallet}")
    
    # Build embed
    embed = discord.Embed(
        title="📊 Wallet Analysis",
        color=0xef4444
    )
    
    embed.add_field(
        name="Address",
        value=f"`{shorten_address(wallet)}`",
        inline=False
    )
    
    total_trades = len(trades)
    total_volume = sum(float(t.get("amount", 0)) for t in trades)
    
    if analysis.get("analysis"):
        a = analysis["analysis"]
        pnl = a.get("pnl", 0)
        pnl_color = "🟢" if pnl >= 0 else "🔴"
        
        embed.add_field(
            name="P&L",
            value=f"{pnl_color} {format_currency(pnl)}",
            inline=True
        )
        
        win_rate = a.get("win_rate", 0) * 100
        wr_color = "🟢" if win_rate >= 50 else "🔴"
        embed.add_field(
            name="Win Rate",
            value=f"{wr_color} {win_rate:.1f}%",
            inline=True
        )
        
        if a.get("sharpe_ratio"):
            embed.add_field(
                name="Sharpe Ratio",
                value=f"{a['sharpe_ratio']:.2f}",
                inline=True
            )
        
        if a.get("trading_style"):
            style = a["trading_style"].replace("_", " ").title()
            embed.add_field(name="Style", value=style, inline=True)
    
    embed.add_field(name="Total Trades", value=str(total_trades), inline=True)
    embed.add_field(name="Volume", value=f"${total_volume:,.2f}", inline=True)
    
    # Recent trades
    recent = ""
    for trade in trades[:3]:
        side = trade.get("side", "?").upper()
        emoji = "🟢" if side == "BUY" else "🔴"
        market = trade.get("market", trade.get("title", "?"))[:30]
        amount = float(trade.get("amount", 0))
        recent += f"{emoji} {side} ${amount:.2f} - {market}...\n"
    
    if recent:
        embed.add_field(name="Recent Trades", value=recent, inline=False)
    
    embed.set_footer(text="🦞 PolyClaw | Use /track to get alerts")
    
    # Add buttons
    view = AnalysisView(wallet)
    
    await interaction.followup.send(embed=embed, view=view)


@bot.tree.command(name="track", description="Subscribe to trade alerts for a wallet")
@app_commands.describe(wallet="The wallet address to track")
async def cmd_track(interaction: discord.Interaction, wallet: str):
    """Track a wallet"""
    user_id = str(interaction.user.id)
    channel_id = str(interaction.channel_id)
    
    tracking = load_tracking()
    
    if user_id not in tracking:
        tracking[user_id] = {"wallets": [], "channel_id": channel_id}
    
    tracking[user_id]["channel_id"] = channel_id
    
    if wallet in tracking[user_id]["wallets"]:
        await interaction.response.send_message(
            f"You're already tracking `{shorten_address(wallet)}`",
            ephemeral=True
        )
        return
    
    tracking[user_id]["wallets"].append(wallet)
    save_tracking(tracking)
    
    # Also register with gateway
    api_request("/api/notifications/subscribe", method="POST", data={
        "wallet": wallet,
        "channels": [f"discord:{user_id}"]
    })
    
    embed = discord.Embed(
        title="✅ Wallet Tracked",
        description=f"Now tracking `{shorten_address(wallet)}`\n\n"
                    f"You'll receive alerts in this channel when this wallet trades.",
        color=0x22c55e
    )
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="untrack", description="Unsubscribe from wallet alerts")
@app_commands.describe(wallet="The wallet address to stop tracking")
async def cmd_untrack(interaction: discord.Interaction, wallet: str):
    """Untrack a wallet"""
    user_id = str(interaction.user.id)
    tracking = load_tracking()
    
    if user_id not in tracking or wallet not in tracking[user_id].get("wallets", []):
        await interaction.response.send_message(
            f"You're not tracking `{shorten_address(wallet)}`",
            ephemeral=True
        )
        return
    
    tracking[user_id]["wallets"].remove(wallet)
    save_tracking(tracking)
    
    embed = discord.Embed(
        title="✅ Wallet Untracked",
        description=f"Stopped tracking `{shorten_address(wallet)}`",
        color=0x22c55e
    )
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="mywallets", description="List your tracked wallets")
async def cmd_mywallets(interaction: discord.Interaction):
    """List tracked wallets"""
    user_id = str(interaction.user.id)
    tracking = load_tracking()
    
    wallets = tracking.get(user_id, {}).get("wallets", [])
    
    if not wallets:
        await interaction.response.send_message(
            "You're not tracking any wallets.\n\n"
            "Use `/track <wallet>` to start receiving alerts.",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title=f"🔔 Your Tracked Wallets ({len(wallets)})",
        color=0xef4444
    )
    
    wallet_list = "\n".join([f"• `{w}`" for w in wallets])
    embed.description = wallet_list + "\n\nUse `/untrack <wallet>` to stop tracking."
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="leaderboard", description="Show top Polymarket performers")
async def cmd_leaderboard(interaction: discord.Interaction):
    """Show leaderboard"""
    await interaction.response.defer()
    
    result = api_request("/api/leaderboard")
    
    if result.get("error"):
        await interaction.followup.send(f"❌ Error: {result['error']}")
        return
    
    wallets = result.get("wallets", [])[:10]
    
    if not wallets:
        await interaction.followup.send("Leaderboard is empty.")
        return
    
    embed = discord.Embed(
        title="🏆 PolyClaw Leaderboard",
        color=0xfbbf24
    )
    
    medals = ["🥇", "🥈", "🥉"]
    
    leaderboard_text = ""
    for i, w in enumerate(wallets):
        rank = medals[i] if i < 3 else f"#{i+1}"
        addr = shorten_address(w.get("address", w.get("wallet", "?")))
        pnl = w.get("pnl", 0)
        win_rate = w.get("win_rate", 0) * 100
        
        pnl_emoji = "🟢" if pnl >= 0 else "🔴"
        
        leaderboard_text += f"{rank} `{addr}`\n"
        leaderboard_text += f"   {pnl_emoji} ${pnl:,.0f} | {win_rate:.0f}% WR\n"
    
    embed.description = leaderboard_text
    embed.set_footer(text="Use /analyze <wallet> for details")
    
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="compare", description="Compare two wallets")
@app_commands.describe(
    wallet1="First wallet address",
    wallet2="Second wallet address"
)
async def cmd_compare(interaction: discord.Interaction, wallet1: str, wallet2: str):
    """Compare two wallets"""
    await interaction.response.defer()
    
    result = api_request(f"/api/compare?wallets={wallet1},{wallet2}")
    
    if result.get("error"):
        await interaction.followup.send(f"❌ Error: {result['error']}")
        return
    
    wallets = result.get("wallets", [])
    
    if len(wallets) < 2:
        await interaction.followup.send("Could not fetch data for both wallets.")
        return
    
    a, b = wallets[0], wallets[1]
    
    embed = discord.Embed(
        title="⚖️ Wallet Comparison",
        color=0xef4444
    )
    
    # Wallet A
    a_pnl = a.get("pnl", 0)
    a_wr = a.get("win_rate", 0) * 100
    embed.add_field(
        name=f"Wallet A: `{shorten_address(wallet1)}`",
        value=f"{'🟢' if a_pnl >= 0 else '🔴'} P&L: {format_currency(a_pnl)}\n"
              f"{'🟢' if a_wr >= 50 else '🔴'} Win Rate: {a_wr:.1f}%\n"
              f"📊 Trades: {a.get('total_trades', 0)}\n"
              f"💰 Volume: ${a.get('volume', 0):,.0f}",
        inline=True
    )
    
    # Wallet B
    b_pnl = b.get("pnl", 0)
    b_wr = b.get("win_rate", 0) * 100
    embed.add_field(
        name=f"Wallet B: `{shorten_address(wallet2)}`",
        value=f"{'🟢' if b_pnl >= 0 else '🔴'} P&L: {format_currency(b_pnl)}\n"
              f"{'🟢' if b_wr >= 50 else '🔴'} Win Rate: {b_wr:.1f}%\n"
              f"📊 Trades: {b.get('total_trades', 0)}\n"
              f"💰 Volume: ${b.get('volume', 0):,.0f}",
        inline=True
    )
    
    # Winner
    a_score = (1 if a_pnl > b_pnl else 0) + (1 if a_wr > b_wr else 0)
    if a_score > 1:
        winner = "🏆 **Wallet A wins!**"
    elif a_score < 1:
        winner = "🏆 **Wallet B wins!**"
    else:
        winner = "🤝 **It's a tie!**"
    
    embed.add_field(name="Result", value=winner, inline=False)
    
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="chat", description="Chat with PolyClaw AI assistant")
@app_commands.describe(message="Your message to PolyClaw")
async def cmd_chat(interaction: discord.Interaction, message: str):
    """Chat with AI"""
    await interaction.response.defer()
    
    result = api_request("/api/chat", method="POST", data={"message": message})
    
    if result.get("error"):
        await interaction.followup.send(f"❌ {result['error']}")
        return
    
    response = result.get("response", "No response from AI")
    
    # Truncate if too long
    if len(response) > 4000:
        response = response[:4000] + "\n\n*...response truncated*"
    
    embed = discord.Embed(
        title="🦞 PolyClaw",
        description=response,
        color=0xef4444
    )
    
    embed.set_footer(text=f"Asked by {interaction.user.display_name}")
    
    await interaction.followup.send(embed=embed)


# ============================================================
# VIEWS (Button UI)
# ============================================================

class AnalysisView(discord.ui.View):
    """View with buttons for wallet analysis"""
    
    def __init__(self, wallet: str):
        super().__init__(timeout=300)
        self.wallet = wallet
    
    @discord.ui.button(label="🔔 Track", style=discord.ButtonStyle.primary)
    async def track_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        channel_id = str(interaction.channel_id)
        
        tracking = load_tracking()
        
        if user_id not in tracking:
            tracking[user_id] = {"wallets": [], "channel_id": channel_id}
        
        if self.wallet in tracking[user_id]["wallets"]:
            await interaction.response.send_message(
                "You're already tracking this wallet.",
                ephemeral=True
            )
            return
        
        tracking[user_id]["wallets"].append(self.wallet)
        save_tracking(tracking)
        
        await interaction.response.send_message(
            f"✅ Now tracking `{shorten_address(self.wallet)}`",
            ephemeral=True
        )
    
    @discord.ui.button(label="📥 Export CSV", style=discord.ButtonStyle.secondary)
    async def export_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"📥 Download CSV:\n{GATEWAY_URL}/api/download/{self.wallet}/csv",
            ephemeral=True
        )


# ============================================================
# MESSAGE HANDLER
# ============================================================

@bot.event
async def on_message(message: discord.Message):
    """Handle regular messages"""
    if message.author.bot:
        return
    
    # Check if bot is mentioned
    if bot.user in message.mentions:
        content = message.content.replace(f"<@{bot.user.id}>", "").strip()
        
        if content:
            # Send to AI chat
            async with message.channel.typing():
                result = api_request("/api/chat", method="POST", data={"message": content})
            
            if result.get("error"):
                await message.reply(f"❌ {result['error']}")
            else:
                response = result.get("response", "No response")
                if len(response) > 2000:
                    response = response[:2000] + "\n\n*...truncated*"
                await message.reply(f"🦞 {response}")
    
    await bot.process_commands(message)


def main():
    """Start the bot"""
    if not DISCORD_BOT_TOKEN:
        print("❌ DISCORD_BOT_TOKEN not set in environment")
        print("   Add it to your .env file:")
        print("   DISCORD_BOT_TOKEN=your_bot_token_here")
        sys.exit(1)
    
    print("🦞 Starting PolyClaw Discord Bot...")
    print(f"   Gateway: {GATEWAY_URL}")
    print("✅ Bot is starting! Press Ctrl+C to stop.")
    
    bot.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
