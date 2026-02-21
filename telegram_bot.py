#!/usr/bin/env python3
"""
PolyClaw Telegram Bot - Interactive Telegram interface

This bot allows users to interact with PolyClaw via Telegram:
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
import logging
from pathlib import Path
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode, ChatAction
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8080")
ALLOWED_USERS = os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",")  # Comma-separated user IDs

# Paths
CONFIG_DIR = Path.home() / ".polyclaw"
USER_TRACKING_FILE = CONFIG_DIR / "telegram_tracking.json"

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def load_user_tracking():
    """Load per-user tracking preferences"""
    CONFIG_DIR.mkdir(exist_ok=True)
    if USER_TRACKING_FILE.exists():
        with open(USER_TRACKING_FILE) as f:
            return json.load(f)
    return {}


def save_user_tracking(data):
    """Save per-user tracking preferences"""
    with open(USER_TRACKING_FILE, 'w') as f:
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
    """Format currency with color emoji"""
    if amount >= 0:
        return f"🟢 +${amount:,.2f}"
    return f"🔴 -${abs(amount):,.2f}"


def format_percent(value):
    """Format percentage with color emoji"""
    pct = value * 100
    if pct >= 50:
        return f"🟢 {pct:.1f}%"
    return f"🔴 {pct:.1f}%"


def shorten_address(addr):
    """Shorten wallet address"""
    if len(addr) > 12:
        return f"{addr[:6]}...{addr[-4:]}"
    return addr


def is_allowed(user_id):
    """Check if user is allowed to use the bot"""
    if not ALLOWED_USERS or ALLOWED_USERS == [""]:
        return True  # No restrictions
    return str(user_id) in ALLOWED_USERS


# ============================================================
# COMMAND HANDLERS
# ============================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    welcome = f"""🦞 <b>Welcome to PolyClaw, {user.first_name}!</b>

I'm your Polymarket trading intelligence assistant. Here's what I can do:

<b>📊 Analysis</b>
/analyze &lt;wallet&gt; - Analyze any wallet
/compare &lt;w1&gt; &lt;w2&gt; - Compare two wallets
/leaderboard - See top performers

<b>🔔 Alerts</b>
/track &lt;wallet&gt; - Get alerts when a wallet trades
/untrack &lt;wallet&gt; - Stop getting alerts
/mywallets - See your tracked wallets

<b>🤖 AI Assistant</b>
/chat &lt;message&gt; - Ask me anything about trading

<b>ℹ️ Help</b>
/help - Show all commands

Let's get started! Try /leaderboard to see top traders."""

    await update.message.reply_text(welcome, parse_mode=ParseMode.HTML)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """🦞 <b>PolyClaw Commands</b>

<b>📊 Analysis Commands</b>
/analyze &lt;wallet&gt; - Full wallet analysis
/compare &lt;w1&gt; &lt;w2&gt; - Compare two wallets
/leaderboard - Top 10 performers

<b>🔔 Alert Commands</b>
/track &lt;wallet&gt; - Subscribe to trade alerts
/untrack &lt;wallet&gt; - Unsubscribe from alerts
/mywallets - List your tracked wallets

<b>🤖 AI Commands</b>
/chat &lt;message&gt; - Chat with AI assistant

<b>💡 Examples</b>
<code>/analyze 0x1234...abcd</code>
<code>/chat What strategies work for election markets?</code>
<code>/compare 0xabc... 0xdef...</code>

<b>🔗 Links</b>
• GitHub: github.com/polyclaw/polyclaw
• Docs: Full documentation on GitHub"""

    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /analyze command"""
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("⛔ You're not authorized to use this bot.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: /analyze <wallet_address>\n\n"
            "Example: <code>/analyze 0x1234567890abcdef...</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    wallet = context.args[0]
    
    # Show typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    # Fetch data
    result = api_request(f"/api/trades/{wallet}")
    
    if result.get("error"):
        await update.message.reply_text(f"❌ Error: {result['error']}")
        return
    
    trades = result.get("trades", [])
    
    if not trades:
        await update.message.reply_text("No trades found for this wallet.")
        return
    
    # Get analysis
    analysis = api_request(f"/api/analyze/{wallet}")
    
    # Format response
    total_trades = len(trades)
    buys = len([t for t in trades if t.get("side", "").upper() == "BUY"])
    sells = total_trades - buys
    total_volume = sum(float(t.get("amount", 0)) for t in trades)
    
    msg = f"""📊 <b>Wallet Analysis</b>

<b>Address:</b> <code>{shorten_address(wallet)}</code>
"""
    
    if analysis.get("analysis"):
        a = analysis["analysis"]
        msg += f"""
<b>Performance</b>
• P&L: {format_currency(a.get('pnl', 0))}
• Win Rate: {format_percent(a.get('win_rate', 0))}
• Sharpe Ratio: {a.get('sharpe_ratio', 0):.2f}

<b>Activity</b>
• Total Trades: {total_trades}
• Volume: ${total_volume:,.2f}
• Avg Trade: ${total_volume/total_trades:,.2f}
"""
        if a.get("trading_style"):
            style = a["trading_style"].replace("_", " ").title()
            msg += f"• Style: {style}\n"
        
        if a.get("max_drawdown"):
            msg += f"• Max Drawdown: 🔴 ${abs(a['max_drawdown']):,.2f}\n"
    else:
        msg += f"""
<b>Activity</b>
• Total Trades: {total_trades}
• Buys: {buys}
• Sells: {sells}
• Volume: ${total_volume:,.2f}
"""
    
    # Add recent trades
    msg += "\n<b>Recent Trades</b>\n"
    for trade in trades[:3]:
        side = trade.get("side", "?").upper()
        emoji = "🟢" if side == "BUY" else "🔴"
        market = trade.get("market", trade.get("title", "?"))[:30]
        amount = float(trade.get("amount", 0))
        msg += f"{emoji} {side} ${amount:.2f} - {market}...\n"
    
    if len(trades) > 3:
        msg += f"<i>...and {len(trades) - 3} more</i>"
    
    # Add action buttons
    keyboard = [
        [
            InlineKeyboardButton("🔔 Track", callback_data=f"track:{wallet}"),
            InlineKeyboardButton("📥 Export", callback_data=f"export:{wallet}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup)


async def cmd_track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /track command"""
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("⛔ You're not authorized to use this bot.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: /track <wallet_address>\n\n"
            "You'll receive alerts when this wallet makes trades.",
            parse_mode=ParseMode.HTML
        )
        return
    
    wallet = context.args[0]
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    
    # Load tracking
    tracking = load_user_tracking()
    
    if user_id not in tracking:
        tracking[user_id] = {"wallets": [], "chat_id": chat_id}
    
    tracking[user_id]["chat_id"] = chat_id
    
    if wallet in tracking[user_id]["wallets"]:
        await update.message.reply_text(f"You're already tracking {shorten_address(wallet)}")
        return
    
    tracking[user_id]["wallets"].append(wallet)
    save_user_tracking(tracking)
    
    # Also add to gateway notifications
    api_request("/api/notifications/subscribe", method="POST", data={
        "wallet": wallet,
        "channels": [f"telegram:{user_id}"]
    })
    
    await update.message.reply_text(
        f"✅ Now tracking <code>{shorten_address(wallet)}</code>\n\n"
        f"You'll receive alerts when this wallet trades.",
        parse_mode=ParseMode.HTML
    )


async def cmd_untrack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /untrack command"""
    if not context.args:
        await update.message.reply_text("Usage: /untrack <wallet_address>")
        return
    
    wallet = context.args[0]
    user_id = str(update.effective_user.id)
    
    tracking = load_user_tracking()
    
    if user_id not in tracking or wallet not in tracking[user_id].get("wallets", []):
        await update.message.reply_text(f"You're not tracking {shorten_address(wallet)}")
        return
    
    tracking[user_id]["wallets"].remove(wallet)
    save_user_tracking(tracking)
    
    await update.message.reply_text(
        f"✅ Stopped tracking <code>{shorten_address(wallet)}</code>",
        parse_mode=ParseMode.HTML
    )


async def cmd_mywallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mywallets command"""
    user_id = str(update.effective_user.id)
    tracking = load_user_tracking()
    
    wallets = tracking.get(user_id, {}).get("wallets", [])
    
    if not wallets:
        await update.message.reply_text(
            "You're not tracking any wallets.\n\n"
            "Use /track <wallet> to start receiving alerts."
        )
        return
    
    msg = f"🔔 <b>Your Tracked Wallets ({len(wallets)})</b>\n\n"
    
    for i, wallet in enumerate(wallets, 1):
        msg += f"{i}. <code>{wallet}</code>\n"
    
    msg += "\nUse /untrack <wallet> to stop tracking."
    
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def cmd_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /leaderboard command"""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    result = api_request("/api/leaderboard")
    
    if result.get("error"):
        await update.message.reply_text(f"❌ Error: {result['error']}")
        return
    
    wallets = result.get("wallets", [])[:10]
    
    if not wallets:
        await update.message.reply_text("Leaderboard is empty. Submit wallets via /analyze")
        return
    
    medals = ["🥇", "🥈", "🥉"]
    
    msg = "🏆 <b>PolyClaw Leaderboard</b>\n\n"
    
    for i, w in enumerate(wallets):
        rank = medals[i] if i < 3 else f"{i+1}."
        addr = shorten_address(w.get("address", w.get("wallet", "?")))
        pnl = w.get("pnl", 0)
        win_rate = w.get("win_rate", 0) * 100
        
        pnl_emoji = "🟢" if pnl >= 0 else "🔴"
        
        msg += f"{rank} <code>{addr}</code>\n"
        msg += f"   {pnl_emoji} ${pnl:,.0f} | {win_rate:.0f}% win rate\n\n"
    
    msg += "<i>Use /analyze <wallet> for details</i>"
    
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def cmd_compare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /compare command"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /compare <wallet1> <wallet2>\n\n"
            "Example: <code>/compare 0xabc... 0xdef...</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    w1, w2 = context.args[0], context.args[1]
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    result = api_request(f"/api/compare?wallets={w1},{w2}")
    
    if result.get("error"):
        await update.message.reply_text(f"❌ Error: {result['error']}")
        return
    
    wallets = result.get("wallets", [])
    
    if len(wallets) < 2:
        await update.message.reply_text("Could not fetch data for both wallets.")
        return
    
    a, b = wallets[0], wallets[1]
    
    msg = f"""⚖️ <b>Wallet Comparison</b>

<b>Wallet A:</b> <code>{shorten_address(w1)}</code>
<b>Wallet B:</b> <code>{shorten_address(w2)}</code>

<b>P&L</b>
A: {format_currency(a.get('pnl', 0))}
B: {format_currency(b.get('pnl', 0))}

<b>Win Rate</b>
A: {format_percent(a.get('win_rate', 0))}
B: {format_percent(b.get('win_rate', 0))}

<b>Trades</b>
A: {a.get('total_trades', 0)}
B: {b.get('total_trades', 0)}

<b>Volume</b>
A: ${a.get('volume', 0):,.0f}
B: ${b.get('volume', 0):,.0f}
"""
    
    # Determine winner
    a_score = (1 if a.get('pnl', 0) > b.get('pnl', 0) else 0) + \
              (1 if a.get('win_rate', 0) > b.get('win_rate', 0) else 0)
    
    if a_score > 1:
        msg += f"\n🏆 <b>Wallet A wins!</b>"
    elif a_score < 1:
        msg += f"\n🏆 <b>Wallet B wins!</b>"
    else:
        msg += f"\n🤝 <b>It's a tie!</b>"
    
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def cmd_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /chat command - AI chat"""
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("⛔ You're not authorized to use this bot.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: /chat <your message>\n\n"
            "Example: <code>/chat What strategies work for election markets?</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    message = " ".join(context.args)
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    result = api_request("/api/chat", method="POST", data={"message": message})
    
    if result.get("error"):
        await update.message.reply_text(f"❌ {result['error']}")
        return
    
    response = result.get("response", "No response from AI")
    
    # Truncate if too long for Telegram
    if len(response) > 4000:
        response = response[:4000] + "\n\n<i>...response truncated</i>"
    
    await update.message.reply_text(
        f"🦞 <b>PolyClaw:</b>\n\n{response}",
        parse_mode=ParseMode.HTML
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("track:"):
        wallet = data.split(":", 1)[1]
        user_id = str(update.effective_user.id)
        chat_id = str(update.effective_chat.id)
        
        tracking = load_user_tracking()
        
        if user_id not in tracking:
            tracking[user_id] = {"wallets": [], "chat_id": chat_id}
        
        if wallet not in tracking[user_id]["wallets"]:
            tracking[user_id]["wallets"].append(wallet)
            save_user_tracking(tracking)
            await query.edit_message_reply_markup(reply_markup=None)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ Now tracking <code>{shorten_address(wallet)}</code>",
                parse_mode=ParseMode.HTML
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Already tracking this wallet."
            )
    
    elif data.startswith("export:"):
        wallet = data.split(":", 1)[1]
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"📥 Export available at:\n{GATEWAY_URL}/api/download/{wallet}/csv"
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plain text messages as chat"""
    if not is_allowed(update.effective_user.id):
        return
    
    message = update.message.text
    
    # Treat as chat if it looks like a question
    if "?" in message or len(message.split()) > 3:
        context.args = message.split()
        await cmd_chat(update, context)


def main():
    """Start the bot"""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set in environment")
        print("   Add it to your .env file:")
        print("   TELEGRAM_BOT_TOKEN=your_bot_token_here")
        sys.exit(1)
    
    print("🦞 Starting PolyClaw Telegram Bot...")
    print(f"   Gateway: {GATEWAY_URL}")
    
    # Create application
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("analyze", cmd_analyze))
    app.add_handler(CommandHandler("track", cmd_track))
    app.add_handler(CommandHandler("untrack", cmd_untrack))
    app.add_handler(CommandHandler("mywallets", cmd_mywallets))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    app.add_handler(CommandHandler("compare", cmd_compare))
    app.add_handler(CommandHandler("chat", cmd_chat))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start polling
    print("✅ Bot is running! Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
