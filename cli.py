#!/usr/bin/env python3
"""
PolyClaw CLI - Command line interface for Polymarket trading intelligence

Usage:
    polyclaw onboard                  Interactive setup wizard
    polyclaw tui                      Launch interactive TUI
    polyclaw status                   Show comprehensive system status
    polyclaw dashboard                Open web dashboard

    polyclaw analyze <wallet>         Analyze a wallet
    polyclaw track <wallet>           Start tracking a wallet
    polyclaw untrack <wallet>         Stop tracking a wallet
    polyclaw list                     List tracked wallets
    polyclaw leaderboard              Show top performers
    polyclaw compare <w1> <w2>        Compare two wallets
    polyclaw chat <message>           Chat with AI assistant
    polyclaw export <wallet>          Export trades to CSV

    polyclaw daemon start             Start background monitoring
    polyclaw daemon stop              Stop background monitoring
    polyclaw daemon status            Check daemon status
    polyclaw gateway start            Start WebSocket gateway
    polyclaw gateway stop             Stop WebSocket gateway  
    polyclaw gateway status           Gateway status & token
    polyclaw logs [-f] [-n 50]        View daemon logs

    polyclaw skills list              List all skills/plugins
    polyclaw skills enable <name>     Enable a skill
    polyclaw skills disable <name>    Disable a skill

    polyclaw sessions list            List chat sessions
    polyclaw sessions new [name]      Create new session

    polyclaw security audit           Run security audit
    polyclaw security audit --deep    Deep security scan

    polyclaw config get <key>         Get config value
    polyclaw config set <k> <v>       Set config value
    polyclaw doctor                   Run diagnostics
    polyclaw doctor --fix             Fix detected issues
    polyclaw history                  Show command history
    polyclaw version                  Show version
"""

import argparse
import json
import os
import sys
import signal
import time
import subprocess
import platform
import requests
from datetime import datetime
from pathlib import Path

# ANSI colors
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
MAGENTA = '\033[95m'
CYAN = '\033[96m'
WHITE = '\033[97m'
BOLD = '\033[1m'
DIM = '\033[2m'
RESET = '\033[0m'

VERSION = "2026.2.20"
CONFIG_DIR = Path.home() / ".polyclaw"
CONFIG_FILE = CONFIG_DIR / "config.json"
DAEMON_PID_FILE = CONFIG_DIR / "daemon.pid"
TRACKING_FILE = CONFIG_DIR / "tracking.json"
LOG_FILE = CONFIG_DIR / "daemon.log"
LAUNCHD_PLIST = Path.home() / "Library/LaunchAgents/io.polyclaw.daemon.plist"

DEFAULT_CONFIG = {
    "gateway_url": "http://localhost:8080",
    "gateway_port": 8080,
    "ai_provider": None,
    "openai_api_key": None,
    "anthropic_api_key": None,
    "telegram_bot_token": None,
    "discord_bot_token": None,
    "discord_webhook": None,
    "telegram_chat_id": None,
    "default_model": "anthropic/claude-opus-4-5",
    "daemon_installed": False,
}


def logo():
    """Print PolyClaw logo"""
    print(f"""
{RED}▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄{RESET}
{RED}██░▄▄░██░▄▄▄░██░█████░██░██░▄▄▀██░████░▄▄▀██░███░███░▄▄░██░▄▄▀██{RESET}
{RED}██░▀▀░██░███░██░█████░▀▀░██░████░████░▀▀░██░█░█░███░▀▀░██░▀▀░██{RESET}
{RED}██░█████░▀▀▀░██░▀▀░█████░██░▀▀▄██░▀▀░█░██░██▄▀▄▀▄██░█████░██░██{RESET}
{RED}▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀{RESET}
                    {RED}🦞 POLYCLAW 🦞{RESET}                    

{DIM}PolyClaw {VERSION} — Polymarket Trading Intelligence{RESET}
""")


def box(title, lines, color=CYAN):
    """Print a box with title and content"""
    width = max(len(title), max(len(l) for l in lines) if lines else 20) + 4
    print(f"│")
    print(f"◇  {color}{title}{RESET} {'─' * (width - len(title) - 2)}╮")
    print(f"│{' ' * (width + 2)}│")
    for line in lines:
        print(f"│  {line}{' ' * (width - len(line))}│")
    print(f"│{' ' * (width + 2)}│")
    print(f"├{'─' * (width + 2)}╯")


def status_box(items):
    """Print a status box with checkmarks"""
    width = max(len(k) + len(str(v)) + 4 for k, v in items) + 4
    print(f"│")
    print(f"◇  Status {'─' * (width - 7)}╮")
    print(f"│{' ' * (width + 2)}│")
    for key, value in items:
        status = f"{GREEN}✓{RESET}" if value else f"{DIM}○{RESET}"
        print(f"│  {status} {key}: {value}{' ' * (width - len(key) - len(str(value)) - 4)}│")
    print(f"│{' ' * (width + 2)}│")
    print(f"├{'─' * (width + 2)}╯")


def prompt(question, default=None, password=False):
    """Simple prompt"""
    if default:
        q = f"◇  {question} [{default}]: "
    else:
        q = f"◇  {question}: "
    
    if password:
        import getpass
        return getpass.getpass(q) or default
    
    return input(q) or default


def confirm(question, default=True):
    """Yes/No confirmation"""
    suffix = "[Y/n]" if default else "[y/N]"
    answer = input(f"◇  {question} {suffix}: ").strip().lower()
    if not answer:
        return default
    return answer in ('y', 'yes')


def select(question, options):
    """Selection menu"""
    print(f"◇  {question}")
    for i, opt in enumerate(options, 1):
        print(f"   {i}. {opt}")
    while True:
        try:
            choice = int(input(f"   Enter choice (1-{len(options)}): "))
            if 1 <= choice <= len(options):
                return options[choice - 1]
        except ValueError:
            pass
        print(f"   {RED}Invalid choice{RESET}")


def ensure_config():
    """Ensure config directory and files exist"""
    CONFIG_DIR.mkdir(exist_ok=True)
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
    if not TRACKING_FILE.exists():
        with open(TRACKING_FILE, 'w') as f:
            json.dump({"wallets": []}, f, indent=2)


def load_config():
    """Load configuration"""
    ensure_config()
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    # Merge with defaults
    for k, v in DEFAULT_CONFIG.items():
        if k not in config:
            config[k] = v
    return config


def save_config(config):
    """Save configuration"""
    ensure_config()
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def load_tracking():
    """Load tracked wallets"""
    ensure_config()
    with open(TRACKING_FILE) as f:
        return json.load(f)


def save_tracking(tracking):
    """Save tracked wallets"""
    with open(TRACKING_FILE, 'w') as f:
        json.dump(tracking, f, indent=2)


def api_request(endpoint, method="GET", data=None):
    """Make API request to gateway"""
    config = load_config()
    url = f"{config['gateway_url']}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=30)
        else:
            response = requests.post(url, json=data, timeout=30)
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": f"Cannot connect to gateway at {config['gateway_url']}"}
    except Exception as e:
        return {"error": str(e)}


def format_currency(amount):
    """Format currency amount"""
    if amount >= 0:
        return f"{GREEN}+${amount:,.2f}{RESET}"
    return f"{RED}-${abs(amount):,.2f}{RESET}"


def format_percent(value):
    """Format percentage"""
    pct = value * 100
    if pct >= 50:
        return f"{GREEN}{pct:.1f}%{RESET}"
    return f"{RED}{pct:.1f}%{RESET}"


def shorten_address(addr):
    """Shorten wallet address"""
    if len(addr) > 12:
        return f"{addr[:6]}...{addr[-4:]}"
    return addr


# ============================================================
# ONBOARD COMMAND
# ============================================================

def cmd_onboard(args):
    """Interactive onboarding wizard"""
    logo()
    
    install_daemon = args.install_daemon if hasattr(args, 'install_daemon') else False
    
    print(f"┌  {BOLD}PolyClaw Onboarding{RESET}")
    print(f"│")
    
    # Security warning
    box("Security", [
        "Security notice — please read.",
        "",
        "PolyClaw connects to Polymarket APIs and can",
        "send notifications to Discord/Telegram.",
        "",
        "Keep your API keys secure:",
        "- Never commit .env files to git",
        "- Use environment variables for production",
        "- Review docs/security.md",
    ], YELLOW)
    
    if not confirm("I understand. Continue?"):
        print(f"│")
        print(f"└  {DIM}Onboarding cancelled{RESET}")
        return
    
    config = load_config()
    
    # Check existing config
    if CONFIG_FILE.exists():
        box("Existing config detected", [
            f"workspace: {CONFIG_DIR}",
            f"gateway: {config.get('gateway_url', 'not set')}",
            f"AI: {config.get('ai_provider') or 'not configured'}",
        ])
        
        if not confirm("Reset configuration?", default=False):
            print(f"│")
            print(f"◇  {GREEN}Using existing configuration{RESET}")
        else:
            config = DEFAULT_CONFIG.copy()
    
    print(f"│")
    
    # Gateway configuration
    box("Gateway Configuration", [
        "The gateway is the local web server that serves",
        "the PolyClaw UI and API.",
        "",
        f"Default: http://localhost:8080",
    ])
    
    port = prompt("Gateway port", default="8080")
    config["gateway_port"] = int(port)
    config["gateway_url"] = f"http://localhost:{port}"
    
    print(f"│")
    
    # AI Provider
    box("AI Provider", [
        "Configure AI for strategy analysis and chat.",
        "",
        "Supported providers:",
        "  • Anthropic (Claude) - recommended",
        "  • OpenAI (GPT-4)",
        "",
        "You can configure both and switch between them.",
    ])
    
    provider = select("Select primary AI provider", ["Anthropic (Claude)", "OpenAI (GPT-4)", "Skip for now"])
    
    if provider == "Anthropic (Claude)":
        config["ai_provider"] = "anthropic"
        api_key = prompt("Anthropic API key (sk-ant-...)", password=True)
        if api_key:
            config["anthropic_api_key"] = api_key
        
        model = select("Default model", [
            "anthropic/claude-opus-4-5",
            "anthropic/claude-sonnet-4-20250514",
            "anthropic/claude-3-5-haiku-20241022",
        ])
        config["default_model"] = model
        
    elif provider == "OpenAI (GPT-4)":
        config["ai_provider"] = "openai"
        api_key = prompt("OpenAI API key (sk-...)", password=True)
        if api_key:
            config["openai_api_key"] = api_key
        config["default_model"] = "openai/gpt-4"
    
    print(f"│")
    
    # Notification channels
    box("Notification Channels", [
        "Configure alerts for wallet activity.",
        "",
        "Options:",
        "  • Discord webhook (one-way alerts)",
        "  • Telegram bot (one-way alerts)",
        "  • Interactive bots (two-way chat)",
    ])
    
    if confirm("Configure Discord webhook?", default=False):
        webhook = prompt("Discord webhook URL")
        if webhook:
            config["discord_webhook"] = webhook
    
    if confirm("Configure Telegram alerts?", default=False):
        token = prompt("Telegram bot token (from @BotFather)")
        chat_id = prompt("Telegram chat ID")
        if token and chat_id:
            config["telegram_bot_token"] = token
            config["telegram_chat_id"] = chat_id
    
    print(f"│")
    
    # Daemon installation
    if platform.system() == "Darwin":  # macOS
        box("Background Daemon", [
            "Install daemon as a system service?",
            "",
            "This runs PolyClaw monitoring in the background",
            "automatically on login.",
            "",
            "Uses macOS LaunchAgent.",
        ])
        
        if install_daemon or confirm("Install daemon as LaunchAgent?"):
            install_launchd_daemon(config)
            config["daemon_installed"] = True
    else:
        box("Background Daemon", [
            "Run 'polyclaw daemon start' to start monitoring.",
            "Run 'polyclaw daemon stop' to stop.",
        ])
    
    # Save config
    save_config(config)
    
    print(f"│")
    box("Setup Complete!", [
        f"Config saved to: {CONFIG_FILE}",
        "",
        "Next steps:",
        f"  1. Start gateway: python app.py",
        f"  2. Open: http://localhost:{config['gateway_port']}",
        "",
        "Or use the CLI:",
        "  polyclaw analyze <wallet>",
        "  polyclaw tui",
        "",
        "Run diagnostics:",
        "  polyclaw doctor",
    ], GREEN)
    
    print(f"│")
    print(f"└  {GREEN}🦞 Happy trading!{RESET}")
    print()


def install_launchd_daemon(config):
    """Install daemon as macOS LaunchAgent"""
    script_path = Path(__file__).parent / "daemon.py"
    python_path = sys.executable
    
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>io.polyclaw.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{script_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{LOG_FILE}</string>
    <key>StandardErrorPath</key>
    <string>{LOG_FILE}</string>
    <key>WorkingDirectory</key>
    <string>{script_path.parent}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>POLYCLAW_GATEWAY_URL</key>
        <string>{config['gateway_url']}</string>
    </dict>
</dict>
</plist>
"""
    
    LAUNCHD_PLIST.parent.mkdir(parents=True, exist_ok=True)
    
    # Unload if exists
    if LAUNCHD_PLIST.exists():
        subprocess.run(["launchctl", "unload", str(LAUNCHD_PLIST)], 
                      capture_output=True)
    
    with open(LAUNCHD_PLIST, 'w') as f:
        f.write(plist_content)
    
    # Load the agent
    result = subprocess.run(["launchctl", "load", str(LAUNCHD_PLIST)], 
                           capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"│  {GREEN}✓ LaunchAgent installed{RESET}")
        print(f"│    {DIM}Daemon will start automatically on login{RESET}")
    else:
        print(f"│  {YELLOW}⚠ LaunchAgent install failed: {result.stderr}{RESET}")


def uninstall_launchd_daemon():
    """Uninstall macOS LaunchAgent"""
    if LAUNCHD_PLIST.exists():
        subprocess.run(["launchctl", "unload", str(LAUNCHD_PLIST)], 
                      capture_output=True)
        LAUNCHD_PLIST.unlink()
        return True
    return False


# ============================================================
# TUI COMMAND
# ============================================================

def cmd_tui(args):
    """Launch interactive TUI"""
    logo()
    
    config = load_config()
    
    print(f"{DIM}Gateway: {config['gateway_url']}{RESET}")
    print(f"{DIM}Model: {config.get('default_model', 'not configured')}{RESET}")
    print(f"{DIM}Press Ctrl+C to exit{RESET}")
    print()
    print(f"{BOLD}{'═' * 70}{RESET}")
    print()
    
    # Check gateway
    result = api_request("/")
    if "error" in result:
        print(f"{RED}✗ Gateway not running at {config['gateway_url']}{RESET}")
        print(f"{DIM}  Start with: python app.py{RESET}")
        return
    
    print(f"{GREEN}✓ Connected to PolyClaw gateway{RESET}")
    print()
    
    tracking = load_tracking()
    print(f"{DIM}Tracking {len(tracking['wallets'])} wallet(s){RESET}")
    print()
    
    print(f"{BOLD}Commands:{RESET}")
    print(f"  {CYAN}/analyze <wallet>{RESET}  - Analyze a wallet")
    print(f"  {CYAN}/track <wallet>{RESET}    - Track a wallet")
    print(f"  {CYAN}/untrack <wallet>{RESET}  - Untrack a wallet")
    print(f"  {CYAN}/list{RESET}              - List tracked wallets")
    print(f"  {CYAN}/leaderboard{RESET}       - Show leaderboard")
    print(f"  {CYAN}/compare <w1> <w2>{RESET} - Compare wallets")
    print(f"  {CYAN}/export <wallet>{RESET}   - Export to CSV")
    print(f"  {CYAN}/help{RESET}              - Show commands")
    print(f"  {CYAN}/quit{RESET}              - Exit TUI")
    print()
    print(f"{DIM}Or just type a message to chat with AI{RESET}")
    print()
    print(f"{BOLD}{'─' * 70}{RESET}")
    
    while True:
        try:
            user_input = input(f"\n{CYAN}>{RESET} ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['/quit', '/exit', '/q']:
                print(f"\n{DIM}Goodbye! 🦞{RESET}")
                break
            
            if user_input.startswith('/'):
                handle_tui_command(user_input)
            else:
                # Chat with AI
                handle_tui_chat(user_input)
                
        except KeyboardInterrupt:
            print(f"\n\n{DIM}Goodbye! 🦞{RESET}")
            break
        except EOFError:
            break


def handle_tui_command(cmd):
    """Handle TUI slash command"""
    parts = cmd.split()
    command = parts[0].lower()
    args = parts[1:]
    
    if command == '/help':
        print(f"\n{BOLD}Available Commands:{RESET}")
        print(f"  /analyze <wallet>   - Analyze wallet performance")
        print(f"  /track <wallet>     - Track wallet for alerts")
        print(f"  /untrack <wallet>   - Stop tracking wallet")
        print(f"  /list               - List tracked wallets")
        print(f"  /leaderboard        - Show top performers")
        print(f"  /compare <w1> <w2>  - Compare two wallets")
        print(f"  /export <wallet>    - Export trades to CSV")
        print(f"  /status             - Show system status")
        print(f"  /quit               - Exit TUI")
        
    elif command == '/analyze' and args:
        wallet = args[0]
        print(f"\n{CYAN}🔍 Analyzing {shorten_address(wallet)}...{RESET}")
        
        result = api_request(f"/api/analyze/{wallet}")
        if "error" in result:
            print(f"{RED}✗ {result['error']}{RESET}")
            return
        
        analysis = result.get("analysis", {})
        print(f"\n{BOLD}Analysis Results:{RESET}")
        print(f"  P&L:       {format_currency(analysis.get('pnl', 0))}")
        print(f"  Win Rate:  {format_percent(analysis.get('win_rate', 0))}")
        print(f"  Trades:    {analysis.get('total_trades', 0)}")
        if analysis.get('trading_style'):
            print(f"  Style:     {MAGENTA}{analysis['trading_style']}{RESET}")
            
    elif command == '/track' and args:
        wallet = args[0]
        tracking = load_tracking()
        if wallet not in tracking['wallets']:
            tracking['wallets'].append(wallet)
            save_tracking(tracking)
            print(f"{GREEN}✓ Now tracking {shorten_address(wallet)}{RESET}")
        else:
            print(f"{YELLOW}Already tracking {shorten_address(wallet)}{RESET}")
            
    elif command == '/untrack' and args:
        wallet = args[0]
        tracking = load_tracking()
        if wallet in tracking['wallets']:
            tracking['wallets'].remove(wallet)
            save_tracking(tracking)
            print(f"{GREEN}✓ Stopped tracking {shorten_address(wallet)}{RESET}")
        else:
            print(f"{YELLOW}Not tracking {shorten_address(wallet)}{RESET}")
            
    elif command == '/list':
        tracking = load_tracking()
        if tracking['wallets']:
            print(f"\n{BOLD}Tracked Wallets ({len(tracking['wallets'])}):{RESET}")
            for w in tracking['wallets']:
                print(f"  • {w}")
        else:
            print(f"{DIM}No wallets tracked{RESET}")
            
    elif command == '/leaderboard':
        print(f"\n{CYAN}🏆 Loading leaderboard...{RESET}")
        result = api_request("/api/leaderboard")
        
        wallets = result.get("wallets", [])[:5]
        if wallets:
            print(f"\n{BOLD}Top Performers:{RESET}")
            medals = ["🥇", "🥈", "🥉", "4.", "5."]
            for i, w in enumerate(wallets):
                addr = shorten_address(w.get('address', w.get('wallet', '?')))
                pnl = format_currency(w.get('pnl', 0))
                print(f"  {medals[i]} {addr}  {pnl}")
        else:
            print(f"{DIM}Leaderboard is empty{RESET}")
            
    elif command == '/compare' and len(args) >= 2:
        w1, w2 = args[0], args[1]
        print(f"\n{CYAN}⚖️ Comparing wallets...{RESET}")
        result = api_request(f"/api/compare?wallets={w1},{w2}")
        
        wallets = result.get("wallets", [])
        if len(wallets) >= 2:
            print(f"\n{BOLD}Comparison:{RESET}")
            print(f"  {CYAN}{shorten_address(w1)}{RESET} vs {MAGENTA}{shorten_address(w2)}{RESET}")
            print(f"  P&L: {format_currency(wallets[0].get('pnl', 0))} vs {format_currency(wallets[1].get('pnl', 0))}")
            print(f"  Win: {format_percent(wallets[0].get('win_rate', 0))} vs {format_percent(wallets[1].get('win_rate', 0))}")
        else:
            print(f"{RED}✗ Could not compare wallets{RESET}")
            
    elif command == '/export' and args:
        wallet = args[0]
        print(f"\n{CYAN}📥 Exporting {shorten_address(wallet)}...{RESET}")
        config = load_config()
        try:
            response = requests.get(f"{config['gateway_url']}/api/download/{wallet}/csv", timeout=60)
            if response.status_code == 200:
                filename = f"trades_{wallet[:8]}_{datetime.now().strftime('%Y%m%d')}.csv"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"{GREEN}✓ Exported to {filename}{RESET}")
            else:
                print(f"{RED}✗ Export failed{RESET}")
        except Exception as e:
            print(f"{RED}✗ Error: {e}{RESET}")
            
    elif command == '/status':
        config = load_config()
        print(f"\n{BOLD}System Status:{RESET}")
        print(f"  Gateway: {config['gateway_url']}")
        print(f"  Model: {config.get('default_model', 'not set')}")
        
        # Check daemon
        if DAEMON_PID_FILE.exists():
            with open(DAEMON_PID_FILE) as f:
                pid = int(f.read().strip())
            try:
                os.kill(pid, 0)
                print(f"  Daemon: {GREEN}running (PID {pid}){RESET}")
            except:
                print(f"  Daemon: {YELLOW}crashed{RESET}")
        else:
            print(f"  Daemon: {DIM}not running{RESET}")
            
        tracking = load_tracking()
        print(f"  Tracked: {len(tracking['wallets'])} wallet(s)")
        
    else:
        print(f"{YELLOW}Unknown command. Type /help for available commands.{RESET}")


def handle_tui_chat(message):
    """Handle chat message in TUI"""
    print(f"\n{CYAN}🦞 Thinking...{RESET}")
    
    result = api_request("/api/chat", method="POST", data={"message": message})
    
    if "error" in result:
        print(f"{RED}✗ {result['error']}{RESET}")
        return
    
    response = result.get("response", "No response")
    
    print(f"\n{BOLD}PolyClaw:{RESET}")
    # Word wrap
    words = response.split()
    line = ""
    for word in words:
        if len(line) + len(word) > 70:
            print(f"  {line}")
            line = word
        else:
            line = f"{line} {word}" if line else word
    if line:
        print(f"  {line}")


# ============================================================
# STANDARD COMMANDS
# ============================================================

def cmd_analyze(args):
    """Analyze a wallet"""
    wallet = args.wallet
    print(f"\n{CYAN}🔍 Analyzing wallet {shorten_address(wallet)}...{RESET}\n")
    
    result = api_request(f"/api/trades/{wallet}")
    
    if "error" in result:
        print(f"{RED}✗ {result['error']}{RESET}")
        return
    
    trades = result.get("trades", [])
    
    if not trades:
        print(f"{YELLOW}No trades found for this wallet{RESET}")
        return
    
    total_trades = len(trades)
    buys = [t for t in trades if t.get("side", "").upper() == "BUY"]
    sells = [t for t in trades if t.get("side", "").upper() == "SELL"]
    total_volume = sum(float(t.get("amount", 0)) for t in trades)
    
    analysis = api_request(f"/api/analyze/{wallet}")
    
    print(f"{BOLD}═══════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}  WALLET ANALYSIS{RESET}")
    print(f"{BOLD}═══════════════════════════════════════════════════════════{RESET}")
    print(f"  {DIM}Address:{RESET}  {wallet}")
    print(f"{BOLD}───────────────────────────────────────────────────────────{RESET}")
    
    if analysis.get("analysis"):
        a = analysis["analysis"]
        print(f"  {DIM}P&L:{RESET}         {format_currency(a.get('pnl', 0))}")
        print(f"  {DIM}Win Rate:{RESET}    {format_percent(a.get('win_rate', 0))}")
        print(f"  {DIM}Total Trades:{RESET} {total_trades}")
        print(f"  {DIM}Volume:{RESET}      ${total_volume:,.2f}")
        if total_trades > 0:
            print(f"  {DIM}Avg Trade:{RESET}   ${total_volume/total_trades:,.2f}")
        
        if a.get("trading_style"):
            style = a["trading_style"].replace("_", " ").title()
            print(f"  {DIM}Style:{RESET}       {MAGENTA}{style}{RESET}")
        
        if a.get("sharpe_ratio"):
            print(f"  {DIM}Sharpe:{RESET}      {a['sharpe_ratio']:.2f}")
        
        if a.get("max_drawdown"):
            print(f"  {DIM}Max DD:{RESET}      {RED}${abs(a['max_drawdown']):,.2f}{RESET}")
    else:
        print(f"  {DIM}Total Trades:{RESET} {total_trades}")
        print(f"  {DIM}Buys:{RESET}        {len(buys)}")
        print(f"  {DIM}Sells:{RESET}       {len(sells)}")
        print(f"  {DIM}Volume:{RESET}      ${total_volume:,.2f}")
    
    print(f"{BOLD}═══════════════════════════════════════════════════════════{RESET}")
    
    print(f"\n{BOLD}  RECENT TRADES{RESET}")
    print(f"{BOLD}───────────────────────────────────────────────────────────{RESET}")
    
    for trade in trades[:5]:
        side = trade.get("side", "?").upper()
        side_color = GREEN if side == "BUY" else RED
        market = trade.get("market", trade.get("title", "Unknown"))[:40]
        amount = float(trade.get("amount", 0))
        price = float(trade.get("price", 0))
        
        print(f"  {side_color}{side:4}{RESET}  ${amount:>8.2f}  @{price:.2f}  {DIM}{market}{RESET}")
    
    if len(trades) > 5:
        print(f"  {DIM}... and {len(trades) - 5} more trades{RESET}")
    
    print()


def cmd_track(args):
    """Start tracking a wallet"""
    wallet = args.wallet
    tracking = load_tracking()
    
    if wallet in tracking["wallets"]:
        print(f"{YELLOW}⚠ Wallet {shorten_address(wallet)} is already being tracked{RESET}")
        return
    
    tracking["wallets"].append(wallet)
    save_tracking(tracking)
    
    print(f"{GREEN}✓ Now tracking {shorten_address(wallet)}{RESET}")
    print(f"{DIM}  You'll receive alerts when this wallet trades{RESET}")
    print(f"{DIM}  Make sure the daemon is running: polyclaw daemon start{RESET}")


def cmd_untrack(args):
    """Stop tracking a wallet"""
    wallet = args.wallet
    tracking = load_tracking()
    
    if wallet not in tracking["wallets"]:
        print(f"{YELLOW}⚠ Wallet {shorten_address(wallet)} is not being tracked{RESET}")
        return
    
    tracking["wallets"].remove(wallet)
    save_tracking(tracking)
    
    print(f"{GREEN}✓ Stopped tracking {shorten_address(wallet)}{RESET}")


def cmd_list(args):
    """List tracked wallets"""
    tracking = load_tracking()
    
    if not tracking["wallets"]:
        print(f"{DIM}No wallets are being tracked{RESET}")
        print(f"{DIM}Track a wallet: polyclaw track <wallet>{RESET}")
        return
    
    print(f"\n{BOLD}Tracked Wallets ({len(tracking['wallets'])}){RESET}")
    print(f"{BOLD}{'─' * 50}{RESET}")
    
    for wallet in tracking["wallets"]:
        print(f"  • {wallet}")
    
    print()


def cmd_leaderboard(args):
    """Show leaderboard"""
    print(f"\n{CYAN}🏆 Loading leaderboard...{RESET}\n")
    
    result = api_request("/api/leaderboard")
    
    if "error" in result:
        print(f"{RED}✗ {result['error']}{RESET}")
        return
    
    if not result.get("wallets"):
        print(f"{DIM}Leaderboard is empty{RESET}")
        print(f"{DIM}Submit a wallet: polyclaw analyze <wallet>{RESET}")
        return
    
    wallets = result["wallets"][:10]
    
    print(f"{BOLD}═══════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}  🏆 POLYCLAW LEADERBOARD{RESET}")
    print(f"{BOLD}═══════════════════════════════════════════════════════════════════{RESET}")
    print(f"  {DIM}Rank  Wallet              P&L           Win Rate   Trades{RESET}")
    print(f"{BOLD}───────────────────────────────────────────────────────────────────{RESET}")
    
    medals = ["🥇", "🥈", "🥉"]
    
    for i, w in enumerate(wallets):
        rank = medals[i] if i < 3 else f"{i+1:2}."
        addr = shorten_address(w.get("address", w.get("wallet", "?")))
        pnl = w.get("pnl", 0)
        win_rate = w.get("win_rate", 0)
        trades = w.get("total_trades", w.get("trades", 0))
        
        pnl_str = format_currency(pnl)
        wr_str = format_percent(win_rate)
        
        print(f"  {rank}   {addr:<18}  {pnl_str:<20}  {wr_str:<10}  {trades}")
    
    print(f"{BOLD}═══════════════════════════════════════════════════════════════════{RESET}\n")


def cmd_compare(args):
    """Compare two wallets"""
    w1, w2 = args.wallet1, args.wallet2
    
    print(f"\n{CYAN}⚖️  Comparing wallets...{RESET}\n")
    
    result = api_request(f"/api/compare?wallets={w1},{w2}")
    
    if "error" in result:
        print(f"{RED}✗ {result['error']}{RESET}")
        return
    
    if not result.get("wallets"):
        print(f"{RED}✗ Failed to compare wallets{RESET}")
        return
    
    wallets = result["wallets"]
    if len(wallets) < 2:
        print(f"{RED}✗ Could not fetch data for both wallets{RESET}")
        return
    
    a, b = wallets[0], wallets[1]
    
    print(f"{BOLD}═══════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}  WALLET COMPARISON{RESET}")
    print(f"{BOLD}═══════════════════════════════════════════════════════════════════{RESET}")
    print(f"  {DIM}Metric{RESET}         {CYAN}{shorten_address(w1):<18}{RESET}  {MAGENTA}{shorten_address(w2):<18}{RESET}")
    print(f"{BOLD}───────────────────────────────────────────────────────────────────{RESET}")
    
    metrics = [
        ("P&L", "pnl", format_currency),
        ("Win Rate", "win_rate", format_percent),
        ("Trades", "total_trades", lambda x: str(x)),
        ("Volume", "volume", lambda x: f"${x:,.0f}"),
    ]
    
    for name, key, fmt in metrics:
        v1 = a.get(key, 0)
        v2 = b.get(key, 0)
        
        if v1 > v2:
            print(f"  {name:<12}   {BOLD}{fmt(v1):<18}{RESET}  {fmt(v2):<18}")
        elif v2 > v1:
            print(f"  {name:<12}   {fmt(v1):<18}  {BOLD}{fmt(v2):<18}{RESET}")
        else:
            print(f"  {name:<12}   {fmt(v1):<18}  {fmt(v2):<18}")
    
    print(f"{BOLD}═══════════════════════════════════════════════════════════════════{RESET}\n")


def cmd_chat(args):
    """Chat with AI assistant"""
    message = " ".join(args.message)
    
    if not message:
        print(f"{YELLOW}Usage: polyclaw chat <message>{RESET}")
        return
    
    print(f"\n{CYAN}🦞 Thinking...{RESET}\n")
    
    result = api_request("/api/chat", method="POST", data={"message": message})
    
    if result.get("error"):
        print(f"{RED}✗ {result['error']}{RESET}")
        return
    
    response = result.get("response", "No response")
    
    print(f"{BOLD}PolyClaw:{RESET}")
    print(f"{response}\n")


def cmd_export(args):
    """Export trades to CSV"""
    wallet = args.wallet
    
    print(f"\n{CYAN}📥 Exporting trades for {shorten_address(wallet)}...{RESET}")
    
    config = load_config()
    url = f"{config['gateway_url']}/api/download/{wallet}/csv"
    
    try:
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200:
            filename = f"trades_{wallet[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"{GREEN}✓ Exported to {filename}{RESET}")
        else:
            print(f"{RED}✗ Export failed{RESET}")
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")


def cmd_daemon_start(args):
    """Start background monitoring daemon"""
    if DAEMON_PID_FILE.exists():
        with open(DAEMON_PID_FILE) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, 0)
            print(f"{YELLOW}⚠ Daemon is already running (PID: {pid}){RESET}")
            return
        except OSError:
            DAEMON_PID_FILE.unlink()
    
    print(f"{CYAN}🚀 Starting PolyClaw daemon...{RESET}")
    
    # Fork to background
    pid = os.fork()
    if pid > 0:
        print(f"{GREEN}✓ Daemon started (PID: {pid}){RESET}")
        print(f"{DIM}  Monitoring tracked wallets for new trades{RESET}")
        print(f"{DIM}  Check status: polyclaw daemon status{RESET}")
        return
    
    os.setsid()
    
    with open(DAEMON_PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    
    from daemon import run_daemon
    run_daemon()


def cmd_daemon_stop(args):
    """Stop background monitoring daemon"""
    if not DAEMON_PID_FILE.exists():
        print(f"{YELLOW}⚠ Daemon is not running{RESET}")
        return
    
    with open(DAEMON_PID_FILE) as f:
        pid = int(f.read().strip())
    
    try:
        os.kill(pid, signal.SIGTERM)
        DAEMON_PID_FILE.unlink()
        print(f"{GREEN}✓ Daemon stopped{RESET}")
    except OSError:
        DAEMON_PID_FILE.unlink()
        print(f"{YELLOW}⚠ Daemon was not running (cleaned up stale PID file){RESET}")


def cmd_daemon_status(args):
    """Check daemon status"""
    config = load_config()
    
    print(f"\n{BOLD}Daemon Status{RESET}")
    print(f"{BOLD}{'─' * 50}{RESET}")
    
    # Check LaunchAgent
    if platform.system() == "Darwin" and LAUNCHD_PLIST.exists():
        print(f"  {GREEN}✓{RESET} LaunchAgent installed")
        print(f"    {DIM}Will auto-start on login{RESET}")
    
    # Check PID
    if DAEMON_PID_FILE.exists():
        with open(DAEMON_PID_FILE) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, 0)
            print(f"  {GREEN}✓{RESET} Daemon running (PID: {pid})")
        except OSError:
            DAEMON_PID_FILE.unlink()
            print(f"  {RED}✗{RESET} Daemon crashed (cleaned up)")
    else:
        print(f"  {DIM}○{RESET} Daemon not running")
        print(f"    {DIM}Start with: polyclaw daemon start{RESET}")
    
    tracking = load_tracking()
    print(f"  {DIM}○{RESET} Tracking {len(tracking['wallets'])} wallet(s)")
    
    # Check log file
    if LOG_FILE.exists():
        print(f"  {DIM}○{RESET} Log: {LOG_FILE}")
    
    print()


# ============================================================
# GATEWAY COMMANDS
# ============================================================

GATEWAY_PID_FILE = CONFIG_DIR / "gateway.pid"
GATEWAY_LOG_FILE = CONFIG_DIR / "gateway.log"


def cmd_gateway_start(args):
    """Start WebSocket gateway"""
    if GATEWAY_PID_FILE.exists():
        with open(GATEWAY_PID_FILE) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, 0)
            print(f"{YELLOW}⚠ Gateway is already running (PID: {pid}){RESET}")
            return
        except OSError:
            GATEWAY_PID_FILE.unlink()
    
    print(f"{CYAN}🚀 Starting PolyClaw Gateway...{RESET}")
    
    # Fork to background
    pid = os.fork()
    if pid > 0:
        # Get token
        token_file = CONFIG_DIR / "default_token"
        token = token_file.read_text().strip() if token_file.exists() else "not set"
        
        print(f"{GREEN}✓ Gateway started (PID: {pid}){RESET}")
        print(f"{DIM}  WebSocket: ws://127.0.0.1:18790{RESET}")
        print(f"{DIM}  Token: {token[:16]}...{RESET}")
        return
    
    os.setsid()
    
    with open(GATEWAY_PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    
    # Redirect output
    sys.stdout = open(GATEWAY_LOG_FILE, 'a')
    sys.stderr = sys.stdout
    
    from gateway import run_gateway
    run_gateway()


def cmd_gateway_stop(args):
    """Stop WebSocket gateway"""
    if not GATEWAY_PID_FILE.exists():
        print(f"{YELLOW}⚠ Gateway is not running{RESET}")
        return
    
    with open(GATEWAY_PID_FILE) as f:
        pid = int(f.read().strip())
    
    try:
        os.kill(pid, signal.SIGTERM)
        GATEWAY_PID_FILE.unlink()
        print(f"{GREEN}✓ Gateway stopped{RESET}")
    except OSError:
        GATEWAY_PID_FILE.unlink()
        print(f"{YELLOW}⚠ Gateway was not running (cleaned up stale PID file){RESET}")


def cmd_gateway_status(args):
    """Check gateway status and show token"""
    config = load_config()
    
    print(f"\n{BOLD}Gateway Status{RESET}")
    print(f"{BOLD}{'─' * 50}{RESET}")
    
    # Check HTTP gateway
    try:
        response = requests.get(f"{config['gateway_url']}/", timeout=2)
        print(f"  {GREEN}✓{RESET} HTTP Gateway: {config['gateway_url']}")
    except:
        print(f"  {RED}✗{RESET} HTTP Gateway: not running")
        print(f"    {DIM}Start with: python app.py{RESET}")
    
    # Check WebSocket gateway
    ws_running = False
    if GATEWAY_PID_FILE.exists():
        with open(GATEWAY_PID_FILE) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, 0)
            ws_running = True
            print(f"  {GREEN}✓{RESET} WebSocket Gateway: ws://127.0.0.1:18790 (PID: {pid})")
        except OSError:
            GATEWAY_PID_FILE.unlink()
            print(f"  {RED}✗{RESET} WebSocket Gateway: crashed")
    else:
        print(f"  {DIM}○{RESET} WebSocket Gateway: not running")
        print(f"    {DIM}Start with: polyclaw gateway start{RESET}")
    
    # Show token
    token_file = CONFIG_DIR / "default_token"
    if token_file.exists():
        token = token_file.read_text().strip()
        print(f"\n  {BOLD}Token:{RESET} {token[:24]}...")
        print(f"  {DIM}Use this token to connect TUI or external clients{RESET}")
    else:
        print(f"\n  {YELLOW}No token configured{RESET}")
        print(f"  {DIM}Run: polyclaw gateway start{RESET}")
    
    print()


def cmd_gateway_token(args):
    """Generate new gateway token"""
    from gateway import TokenManager
    
    manager = TokenManager()
    token = manager.generate_token(args.name if hasattr(args, 'name') else "cli")
    
    # Save as default
    token_file = CONFIG_DIR / "default_token"
    token_file.write_text(token)
    
    print(f"{GREEN}✓ New token generated{RESET}")
    print(f"\n  {BOLD}{token}{RESET}")
    print(f"\n  {DIM}This token is now the default for TUI connections{RESET}")


def cmd_config_get(args):
    """Get config value"""
    key = args.key
    config = load_config()
    
    if key in config:
        value = config[key]
        if key.endswith("_key") or key.endswith("_token"):
            value = value[:8] + "..." if value else None
        print(f"{key}: {value}")
    else:
        print(f"{YELLOW}Unknown config key: {key}{RESET}")
        print(f"{DIM}Available keys: {', '.join(config.keys())}{RESET}")


def cmd_config_set(args):
    """Set config value"""
    key = args.key
    value = args.value
    config = load_config()
    
    if key not in DEFAULT_CONFIG:
        print(f"{YELLOW}Warning: '{key}' is not a standard config key{RESET}")
    
    # Type conversion
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
    elif value.isdigit():
        value = int(value)
    
    config[key] = value
    save_config(config)
    
    print(f"{GREEN}✓ Set {key} = {value}{RESET}")


def cmd_doctor(args):
    """Run diagnostics"""
    logo()
    
    fix_mode = args.fix if hasattr(args, 'fix') else False
    
    print(f"{BOLD}Running diagnostics...{RESET}\n")
    
    checks = []
    fixes = []
    
    # Check config directory
    if CONFIG_DIR.exists():
        checks.append((True, "Config directory exists", str(CONFIG_DIR)))
    else:
        checks.append((False, "Config directory missing", str(CONFIG_DIR)))
        fixes.append(("Create config directory", lambda: CONFIG_DIR.mkdir(exist_ok=True)))
    
    # Check config file
    if CONFIG_FILE.exists():
        checks.append((True, "Config file exists", str(CONFIG_FILE)))
    else:
        checks.append((False, "Config file missing", str(CONFIG_FILE)))
        fixes.append(("Create config file", ensure_config))
    
    # Check gateway connection
    config = load_config()
    try:
        response = requests.get(f"{config['gateway_url']}/", timeout=5)
        checks.append((True, "Gateway is running", config['gateway_url']))
    except:
        checks.append((False, "Gateway not reachable", config['gateway_url']))
    
    # Check AI providers
    if config.get("openai_api_key") or config.get("anthropic_api_key"):
        checks.append((True, "AI provider configured", config.get("ai_provider", "unknown")))
    else:
        checks.append((None, "No AI provider configured", "Run: polyclaw onboard"))
    
    # Check tracking file
    tracking = load_tracking()
    checks.append((True, f"Tracking {len(tracking['wallets'])} wallet(s)", str(TRACKING_FILE)))
    
    # Check daemon
    if DAEMON_PID_FILE.exists():
        with open(DAEMON_PID_FILE) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, 0)
            checks.append((True, f"Daemon running", f"PID: {pid}"))
        except:
            checks.append((False, "Daemon crashed", "Stale PID file"))
            fixes.append(("Clean up PID file", lambda: DAEMON_PID_FILE.unlink()))
    else:
        checks.append((None, "Daemon not running", "Optional"))
    
    # Check LaunchAgent (macOS)
    if platform.system() == "Darwin":
        if LAUNCHD_PLIST.exists():
            checks.append((True, "LaunchAgent installed", str(LAUNCHD_PLIST)))
        else:
            checks.append((None, "LaunchAgent not installed", "Run: polyclaw onboard --install-daemon"))
    
    # Print results
    print(f"{BOLD}{'─' * 60}{RESET}")
    for status, message, detail in checks:
        if status is True:
            icon = f"{GREEN}✓{RESET}"
        elif status is False:
            icon = f"{RED}✗{RESET}"
        else:
            icon = f"{YELLOW}○{RESET}"
        
        print(f"  {icon}  {message}")
        print(f"     {DIM}{detail}{RESET}")
    print(f"{BOLD}{'─' * 60}{RESET}")
    
    # Apply fixes
    if fix_mode and fixes:
        print(f"\n{BOLD}Applying fixes...{RESET}\n")
        for name, fix_fn in fixes:
            try:
                fix_fn()
                print(f"  {GREEN}✓{RESET} {name}")
            except Exception as e:
                print(f"  {RED}✗{RESET} {name}: {e}")
    elif fixes:
        print(f"\n{YELLOW}Found {len(fixes)} issue(s) that can be fixed.{RESET}")
        print(f"{DIM}Run: polyclaw doctor --fix{RESET}")
    
    print()


def cmd_version(args):
    """Show version"""
    logo()


# ============================================================
# NEW OPENCLAW-LIKE COMMANDS
# ============================================================

SESSIONS_DIR = CONFIG_DIR / "sessions"
HISTORY_FILE = CONFIG_DIR / "history.json"


def cmd_skills_list(args):
    """List all skills"""
    print(f"\n{BOLD}PolyClaw Skills{RESET}")
    print(f"{BOLD}{'─' * 60}{RESET}")
    
    try:
        from skills import list_skills
        skills = list_skills()
        
        enabled = [s for s in skills if s.get("enabled")]
        disabled = [s for s in skills if not s.get("enabled")]
        
        print(f"\n  {GREEN}Enabled ({len(enabled)}){RESET}")
        for s in enabled:
            builtin = f" {DIM}(builtin){RESET}" if s.get("builtin") else ""
            print(f"    {GREEN}✓{RESET} {s['name']}{builtin}")
            print(f"      {DIM}{s.get('description', '')}{RESET}")
        
        if disabled:
            print(f"\n  {DIM}Disabled ({len(disabled)}){RESET}")
            for s in disabled:
                print(f"    {DIM}○ {s['name']}{RESET}")
        
    except ImportError:
        print(f"  {DIM}Skills system not initialized{RESET}")
    
    print()


def cmd_skills_enable(args):
    """Enable a skill"""
    from skills import enable_skill, list_skills
    
    name = args.name
    if enable_skill(name):
        print(f"{GREEN}✓ Enabled skill: {name}{RESET}")
    else:
        print(f"{YELLOW}Skill '{name}' is already enabled{RESET}")


def cmd_skills_disable(args):
    """Disable a skill"""
    from skills import disable_skill
    
    name = args.name
    if disable_skill(name):
        print(f"{GREEN}✓ Disabled skill: {name}{RESET}")
    else:
        print(f"{YELLOW}Skill '{name}' is already disabled{RESET}")


def cmd_security_audit(args):
    """Run security audit"""
    logo()
    
    deep = args.deep if hasattr(args, 'deep') else False
    fix = args.fix if hasattr(args, 'fix') else False
    
    print(f"{BOLD}🔒 Security Audit{RESET}")
    if deep:
        print(f"{DIM}Running deep scan...{RESET}")
    print()
    
    issues = []
    warnings = []
    
    config = load_config()
    
    # Check for exposed API keys
    print(f"{BOLD}Checking credentials...{RESET}")
    
    if config.get("openai_api_key"):
        print(f"  {GREEN}✓{RESET} OpenAI API key configured")
        if not config["openai_api_key"].startswith("sk-"):
            warnings.append("OpenAI key doesn't start with 'sk-'")
    
    if config.get("anthropic_api_key"):
        print(f"  {GREEN}✓{RESET} Anthropic API key configured")
        if not config["anthropic_api_key"].startswith("sk-ant-"):
            warnings.append("Anthropic key doesn't start with 'sk-ant-'")
    
    if config.get("discord_webhook"):
        print(f"  {GREEN}✓{RESET} Discord webhook configured")
        if "discord.com/api/webhooks" not in config["discord_webhook"]:
            warnings.append("Discord webhook URL looks invalid")
    
    if config.get("telegram_bot_token"):
        print(f"  {GREEN}✓{RESET} Telegram bot token configured")
    
    print()
    
    # Check .env file
    print(f"{BOLD}Checking file security...{RESET}")
    
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        print(f"  {GREEN}✓{RESET} .env file exists")
        
        # Check if .env is in .gitignore
        gitignore = Path(__file__).parent / ".gitignore"
        if gitignore.exists():
            with open(gitignore) as f:
                if ".env" in f.read():
                    print(f"  {GREEN}✓{RESET} .env is in .gitignore")
                else:
                    issues.append(".env is NOT in .gitignore - secrets may be exposed!")
    
    # Check config file permissions
    if CONFIG_FILE.exists():
        mode = oct(CONFIG_FILE.stat().st_mode)[-3:]
        if mode in ["600", "700"]:
            print(f"  {GREEN}✓{RESET} Config file has secure permissions ({mode})")
        else:
            warnings.append(f"Config file has permissive permissions ({mode})")
    
    print()
    
    # Deep scan
    if deep:
        print(f"{BOLD}Deep scan...{RESET}")
        
        # Check for hardcoded secrets in source files
        source_dir = Path(__file__).parent
        secret_patterns = ["sk-", "sk-ant-", "discord.com/api/webhooks"]
        
        for py_file in source_dir.glob("*.py"):
            if py_file.name in ["cli.py"]:
                continue
            with open(py_file) as f:
                content = f.read()
                for pattern in secret_patterns:
                    if pattern in content and "example" not in content.lower():
                        warnings.append(f"Possible hardcoded secret in {py_file.name}")
        
        print(f"  {GREEN}✓{RESET} Source files scanned")
        print()
    
    # Network security
    print(f"{BOLD}Checking network security...{RESET}")
    
    gateway_url = config.get("gateway_url", "")
    if "localhost" in gateway_url or "127.0.0.1" in gateway_url:
        print(f"  {GREEN}✓{RESET} Gateway bound to localhost (safe)")
    else:
        issues.append(f"Gateway exposed to network: {gateway_url}")
    
    print()
    
    # Summary
    print(f"{BOLD}{'─' * 60}{RESET}")
    
    if issues:
        print(f"\n{RED}Issues ({len(issues)}):{RESET}")
        for issue in issues:
            print(f"  {RED}✗{RESET} {issue}")
    
    if warnings:
        print(f"\n{YELLOW}Warnings ({len(warnings)}):{RESET}")
        for warning in warnings:
            print(f"  {YELLOW}⚠{RESET} {warning}")
    
    if not issues and not warnings:
        print(f"\n{GREEN}✓ No security issues found{RESET}")
    
    if fix and (issues or warnings):
        print(f"\n{BOLD}Applying fixes...{RESET}")
        # Set secure permissions on config
        if CONFIG_FILE.exists():
            os.chmod(CONFIG_FILE, 0o600)
            print(f"  {GREEN}✓{RESET} Set secure permissions on config file")
    
    print()


def cmd_sessions_list(args):
    """List chat sessions"""
    SESSIONS_DIR.mkdir(exist_ok=True)
    
    sessions = list(SESSIONS_DIR.glob("*.json"))
    
    print(f"\n{BOLD}Chat Sessions{RESET}")
    print(f"{BOLD}{'─' * 60}{RESET}")
    
    if not sessions:
        print(f"  {DIM}No sessions found{RESET}")
        print(f"  {DIM}Start a chat: polyclaw tui{RESET}")
    else:
        for session_file in sorted(sessions, key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
            with open(session_file) as f:
                session = json.load(f)
            
            name = session.get("name", session_file.stem)
            msgs = len(session.get("messages", []))
            modified = datetime.fromtimestamp(session_file.stat().st_mtime)
            age = (datetime.now() - modified).total_seconds() / 60
            
            if age < 60:
                age_str = f"{int(age)}m ago"
            elif age < 1440:
                age_str = f"{int(age/60)}h ago"
            else:
                age_str = f"{int(age/1440)}d ago"
            
            print(f"  • {name} ({msgs} msgs, {age_str})")
    
    print()


def cmd_sessions_new(args):
    """Create new session"""
    SESSIONS_DIR.mkdir(exist_ok=True)
    
    name = args.name if hasattr(args, 'name') and args.name else f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    session = {
        "name": name,
        "created": datetime.now().isoformat(),
        "messages": [],
    }
    
    session_file = SESSIONS_DIR / f"{name}.json"
    with open(session_file, 'w') as f:
        json.dump(session, f, indent=2)
    
    # Set as active session
    config = load_config()
    config["active_session"] = name
    save_config(config)
    
    print(f"{GREEN}✓ Created session: {name}{RESET}")


def cmd_dashboard(args):
    """Open web dashboard"""
    config = load_config()
    url = config.get("gateway_url", "http://localhost:8080")
    
    no_open = args.no_open if hasattr(args, 'no_open') else False
    
    print(f"\n{BOLD}PolyClaw Dashboard{RESET}")
    print(f"{BOLD}{'─' * 50}{RESET}")
    print(f"  URL: {CYAN}{url}{RESET}")
    
    # Check if gateway is running
    try:
        requests.get(url, timeout=2)
        print(f"  Status: {GREEN}Running{RESET}")
    except:
        print(f"  Status: {RED}Not running{RESET}")
        print(f"  {DIM}Start with: python app.py{RESET}")
        return
    
    if not no_open:
        import webbrowser
        webbrowser.open(url)
        print(f"\n{GREEN}✓ Opened in browser{RESET}")
    
    print()


def cmd_history(args):
    """Show command history"""
    if not HISTORY_FILE.exists():
        print(f"{DIM}No history yet{RESET}")
        return
    
    with open(HISTORY_FILE) as f:
        history = json.load(f)
    
    entries = history.get("entries", [])[-20:]  # Last 20
    
    print(f"\n{BOLD}Recent Commands{RESET}")
    print(f"{BOLD}{'─' * 60}{RESET}")
    
    for entry in reversed(entries):
        cmd = entry.get("command", "?")
        ts = entry.get("timestamp", "")
        if ts:
            dt = datetime.fromisoformat(ts)
            age = (datetime.now() - dt).total_seconds() / 60
            if age < 60:
                age_str = f"{int(age)}m"
            else:
                age_str = f"{int(age/60)}h"
        else:
            age_str = "?"
        
        print(f"  {DIM}{age_str:>4}{RESET}  {cmd}")
    
    print()


def log_command(command):
    """Log a command to history"""
    if not HISTORY_FILE.exists():
        history = {"entries": []}
    else:
        with open(HISTORY_FILE) as f:
            history = json.load(f)
    
    history["entries"].append({
        "command": command,
        "timestamp": datetime.now().isoformat(),
    })
    
    # Keep last 100
    history["entries"] = history["entries"][-100:]
    
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


def cmd_logs(args):
    """View daemon logs"""
    if not LOG_FILE.exists():
        print(f"{DIM}No logs yet{RESET}")
        print(f"{DIM}Start daemon: polyclaw daemon start{RESET}")
        return
    
    lines = args.lines if hasattr(args, 'lines') else 50
    follow = args.follow if hasattr(args, 'follow') else False
    
    print(f"{BOLD}Daemon Logs{RESET} ({LOG_FILE})")
    print(f"{BOLD}{'─' * 60}{RESET}")
    
    with open(LOG_FILE) as f:
        all_lines = f.readlines()
        for line in all_lines[-lines:]:
            print(line.rstrip())
    
    if follow:
        print(f"\n{DIM}Following... (Ctrl+C to stop){RESET}\n")
        import time
        try:
            with open(LOG_FILE) as f:
                f.seek(0, 2)  # End of file
                while True:
                    line = f.readline()
                    if line:
                        print(line.rstrip())
                    else:
                        time.sleep(0.5)
        except KeyboardInterrupt:
            pass


def cmd_status(args):
    """Comprehensive system status"""
    logo()
    
    config = load_config()
    tracking = load_tracking()
    
    # Gateway status
    print(f"│")
    gateway_ok = False
    try:
        result = api_request("/api/system/info")
        gateway_ok = "error" not in result
    except:
        pass
    
    gateway_status = f"{GREEN}running{RESET}" if gateway_ok else f"{RED}stopped{RESET}"
    
    box("Gateway", [
        f"URL: {config.get('gateway_url', '?')}",
        f"Status: {gateway_status}",
    ])
    
    # Daemon status
    daemon_running = False
    daemon_pid = None
    if DAEMON_PID_FILE.exists():
        with open(DAEMON_PID_FILE) as f:
            daemon_pid = int(f.read().strip())
        try:
            os.kill(daemon_pid, 0)
            daemon_running = True
        except:
            pass
    
    daemon_status = f"{GREEN}running (PID {daemon_pid}){RESET}" if daemon_running else f"{DIM}stopped{RESET}"
    launchd = "installed" if LAUNCHD_PLIST.exists() else "not installed"
    
    box("Daemon", [
        f"Status: {daemon_status}",
        f"LaunchAgent: {launchd}",
        f"Tracking: {len(tracking['wallets'])} wallet(s)",
    ])
    
    # AI providers
    ai_lines = []
    if config.get("anthropic_api_key"):
        ai_lines.append(f"Anthropic: {GREEN}configured{RESET}")
    else:
        ai_lines.append(f"Anthropic: {DIM}not configured{RESET}")
    
    if config.get("openai_api_key"):
        ai_lines.append(f"OpenAI: {GREEN}configured{RESET}")
    else:
        ai_lines.append(f"OpenAI: {DIM}not configured{RESET}")
    
    ai_lines.append(f"Model: {config.get('default_model', 'not set')}")
    
    box("AI Providers", ai_lines)
    
    # Notifications
    notif_lines = []
    if config.get("discord_webhook"):
        notif_lines.append(f"Discord: {GREEN}configured{RESET}")
    else:
        notif_lines.append(f"Discord: {DIM}not configured{RESET}")
    
    if config.get("telegram_bot_token"):
        notif_lines.append(f"Telegram: {GREEN}configured{RESET}")
    else:
        notif_lines.append(f"Telegram: {DIM}not configured{RESET}")
    
    box("Notifications", notif_lines)
    
    # Skills
    try:
        from skills import list_skills
        skills = list_skills()
        enabled = len([s for s in skills if s.get("enabled")])
        box("Skills", [
            f"Enabled: {enabled}",
            f"Total: {len(skills)}",
        ])
    except:
        pass
    
    print(f"│")
    print(f"└  {DIM}Run 'polyclaw doctor' for diagnostics{RESET}")
    print()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="PolyClaw - Polymarket Trading Intelligence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{BOLD}Examples:{RESET}
  polyclaw onboard              Interactive setup wizard
  polyclaw tui                  Launch interactive TUI
  polyclaw analyze 0x1234...    Analyze a wallet
  polyclaw track 0x1234...      Track wallet for alerts
  polyclaw leaderboard          Show top performers
  polyclaw chat "What strategies work?"
  polyclaw daemon start         Start background monitoring
  polyclaw doctor --fix         Fix detected issues

{DIM}More info: https://github.com/JdClarkGit/PolyClaw{RESET}
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # onboard
    p_onboard = subparsers.add_parser("onboard", help="Interactive setup wizard")
    p_onboard.add_argument("--install-daemon", action="store_true", help="Also install daemon")
    p_onboard.set_defaults(func=cmd_onboard)
    
    # tui
    p_tui = subparsers.add_parser("tui", help="Launch interactive TUI")
    p_tui.set_defaults(func=cmd_tui)
    
    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Analyze a wallet")
    p_analyze.add_argument("wallet", help="Wallet address")
    p_analyze.set_defaults(func=cmd_analyze)
    
    # track
    p_track = subparsers.add_parser("track", help="Track a wallet for alerts")
    p_track.add_argument("wallet", help="Wallet address")
    p_track.set_defaults(func=cmd_track)
    
    # untrack
    p_untrack = subparsers.add_parser("untrack", help="Stop tracking a wallet")
    p_untrack.add_argument("wallet", help="Wallet address")
    p_untrack.set_defaults(func=cmd_untrack)
    
    # list
    p_list = subparsers.add_parser("list", help="List tracked wallets")
    p_list.set_defaults(func=cmd_list)
    
    # leaderboard
    p_lb = subparsers.add_parser("leaderboard", help="Show leaderboard")
    p_lb.set_defaults(func=cmd_leaderboard)
    
    # compare
    p_compare = subparsers.add_parser("compare", help="Compare two wallets")
    p_compare.add_argument("wallet1", help="First wallet")
    p_compare.add_argument("wallet2", help="Second wallet")
    p_compare.set_defaults(func=cmd_compare)
    
    # chat
    p_chat = subparsers.add_parser("chat", help="Chat with AI assistant")
    p_chat.add_argument("message", nargs="+", help="Your message")
    p_chat.set_defaults(func=cmd_chat)
    
    # export
    p_export = subparsers.add_parser("export", help="Export trades to CSV")
    p_export.add_argument("wallet", help="Wallet address")
    p_export.set_defaults(func=cmd_export)
    
    # daemon
    p_daemon = subparsers.add_parser("daemon", help="Background monitoring daemon")
    daemon_sub = p_daemon.add_subparsers(dest="daemon_cmd")
    
    p_daemon_start = daemon_sub.add_parser("start", help="Start daemon")
    p_daemon_start.set_defaults(func=cmd_daemon_start)
    
    p_daemon_stop = daemon_sub.add_parser("stop", help="Stop daemon")
    p_daemon_stop.set_defaults(func=cmd_daemon_stop)
    
    p_daemon_status = daemon_sub.add_parser("status", help="Check daemon status")
    p_daemon_status.set_defaults(func=cmd_daemon_status)
    
    # gateway
    p_gateway = subparsers.add_parser("gateway", help="WebSocket gateway management")
    gateway_sub = p_gateway.add_subparsers(dest="gateway_cmd")
    
    p_gateway_start = gateway_sub.add_parser("start", help="Start gateway")
    p_gateway_start.set_defaults(func=cmd_gateway_start)
    
    p_gateway_stop = gateway_sub.add_parser("stop", help="Stop gateway")
    p_gateway_stop.set_defaults(func=cmd_gateway_stop)
    
    p_gateway_status = gateway_sub.add_parser("status", help="Gateway status & token")
    p_gateway_status.set_defaults(func=cmd_gateway_status)
    
    p_gateway_token = gateway_sub.add_parser("token", help="Generate new token")
    p_gateway_token.add_argument("name", nargs="?", default="cli", help="Token name")
    p_gateway_token.set_defaults(func=cmd_gateway_token)
    
    # config
    p_config = subparsers.add_parser("config", help="Configuration management")
    config_sub = p_config.add_subparsers(dest="config_cmd")
    
    p_config_get = config_sub.add_parser("get", help="Get config value")
    p_config_get.add_argument("key", help="Config key")
    p_config_get.set_defaults(func=cmd_config_get)
    
    p_config_set = config_sub.add_parser("set", help="Set config value")
    p_config_set.add_argument("key", help="Config key")
    p_config_set.add_argument("value", help="Config value")
    p_config_set.set_defaults(func=cmd_config_set)
    
    # doctor
    p_doctor = subparsers.add_parser("doctor", help="Run diagnostics")
    p_doctor.add_argument("--fix", action="store_true", help="Fix detected issues")
    p_doctor.set_defaults(func=cmd_doctor)
    
    # version
    p_version = subparsers.add_parser("version", help="Show version")
    p_version.set_defaults(func=cmd_version)
    
    # skills
    p_skills = subparsers.add_parser("skills", help="Manage skills/plugins")
    skills_sub = p_skills.add_subparsers(dest="skills_cmd")
    
    p_skills_list = skills_sub.add_parser("list", help="List all skills")
    p_skills_list.set_defaults(func=cmd_skills_list)
    
    p_skills_enable = skills_sub.add_parser("enable", help="Enable a skill")
    p_skills_enable.add_argument("name", help="Skill name")
    p_skills_enable.set_defaults(func=cmd_skills_enable)
    
    p_skills_disable = skills_sub.add_parser("disable", help="Disable a skill")
    p_skills_disable.add_argument("name", help="Skill name")
    p_skills_disable.set_defaults(func=cmd_skills_disable)
    
    # security
    p_security = subparsers.add_parser("security", help="Security commands")
    security_sub = p_security.add_subparsers(dest="security_cmd")
    
    p_security_audit = security_sub.add_parser("audit", help="Run security audit")
    p_security_audit.add_argument("--deep", action="store_true", help="Deep scan")
    p_security_audit.add_argument("--fix", action="store_true", help="Fix issues")
    p_security_audit.set_defaults(func=cmd_security_audit)
    
    # sessions
    p_sessions = subparsers.add_parser("sessions", help="Manage chat sessions")
    sessions_sub = p_sessions.add_subparsers(dest="sessions_cmd")
    
    p_sessions_list = sessions_sub.add_parser("list", help="List sessions")
    p_sessions_list.set_defaults(func=cmd_sessions_list)
    
    p_sessions_new = sessions_sub.add_parser("new", help="Create new session")
    p_sessions_new.add_argument("name", nargs="?", help="Session name")
    p_sessions_new.set_defaults(func=cmd_sessions_new)
    
    # dashboard
    p_dashboard = subparsers.add_parser("dashboard", help="Open web dashboard")
    p_dashboard.add_argument("--no-open", action="store_true", help="Don't open browser")
    p_dashboard.set_defaults(func=cmd_dashboard)
    
    # history
    p_history = subparsers.add_parser("history", help="Show command history")
    p_history.set_defaults(func=cmd_history)
    
    # logs
    p_logs = subparsers.add_parser("logs", help="View daemon logs")
    p_logs.add_argument("-n", "--lines", type=int, default=50, help="Number of lines")
    p_logs.add_argument("-f", "--follow", action="store_true", help="Follow log output")
    p_logs.set_defaults(func=cmd_logs)
    
    # status (comprehensive)
    p_status = subparsers.add_parser("status", help="Show system status")
    p_status.set_defaults(func=cmd_status)
    
    args = parser.parse_args()
    
    if args.command is None:
        logo()
        parser.print_help()
        return
    
    if args.command == "daemon" and not hasattr(args, 'func'):
        print("Usage: polyclaw daemon {start|stop|status}")
        return
    
    if args.command == "gateway" and not hasattr(args, 'func'):
        cmd_gateway_status(args)
        return
    
    if args.command == "config" and not hasattr(args, 'func'):
        print("Usage: polyclaw config {get|set} <key> [value]")
        return
    
    if args.command == "skills" and not hasattr(args, 'func'):
        cmd_skills_list(args)
        return
    
    if args.command == "security" and not hasattr(args, 'func'):
        print("Usage: polyclaw security audit [--deep] [--fix]")
        return
    
    if args.command == "sessions" and not hasattr(args, 'func'):
        cmd_sessions_list(args)
        return
    
    # Log command to history
    log_command(" ".join(sys.argv[1:]))
    
    args.func(args)


if __name__ == "__main__":
    main()
