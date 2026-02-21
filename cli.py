#!/usr/bin/env python3
"""
PolyClaw CLI - Command line interface for Polymarket trading intelligence

Usage:
    polyclaw analyze <wallet>       Analyze a wallet
    polyclaw track <wallet>         Start tracking a wallet for alerts
    polyclaw untrack <wallet>       Stop tracking a wallet
    polyclaw list                   List tracked wallets
    polyclaw leaderboard            Show top performers
    polyclaw compare <w1> <w2>      Compare two wallets
    polyclaw chat <message>         Chat with AI assistant
    polyclaw export <wallet>        Export trades to CSV
    polyclaw daemon start           Start background monitoring
    polyclaw daemon stop            Stop background monitoring
    polyclaw daemon status          Check daemon status
    polyclaw doctor                 Run diagnostics
    polyclaw version                Show version
"""

import argparse
import json
import os
import sys
import signal
import time
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

VERSION = "1.0.0"
CONFIG_DIR = Path.home() / ".polyclaw"
CONFIG_FILE = CONFIG_DIR / "config.json"
DAEMON_PID_FILE = CONFIG_DIR / "daemon.pid"
TRACKING_FILE = CONFIG_DIR / "tracking.json"

DEFAULT_CONFIG = {
    "gateway_url": "http://localhost:8080",
    "ai_provider": None,
    "telegram_enabled": False,
    "discord_enabled": False,
}


def logo():
    """Print PolyClaw logo"""
    print(f"""
{RED}██████╗  ██████╗ ██╗  ██╗   ██╗ ██████╗██╗      █████╗ ██╗    ██╗{RESET}
{RED}██╔══██╗██╔═══██╗██║  ╚██╗ ██╔╝██╔════╝██║     ██╔══██╗██║    ██║{RESET}
{RED}██████╔╝██║   ██║██║   ╚████╔╝ ██║     ██║     ███████║██║ █╗ ██║{RESET}
{RED}██╔═══╝ ██║   ██║██║    ╚██╔╝  ██║     ██║     ██╔══██║██║███╗██║{RESET}
{RED}██║     ╚██████╔╝███████╗██║   ╚██████╗███████╗██║  ██║╚███╔███╔╝{RESET}
{RED}╚═╝      ╚═════╝ ╚══════╝╚═╝    ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝ {RESET}
{DIM}Polymarket Trading Intelligence{RESET}                        {DIM}v{VERSION}{RESET}
""")


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
        return json.load(f)


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
        print(f"{RED}✗ Cannot connect to PolyClaw gateway at {config['gateway_url']}{RESET}")
        print(f"{DIM}  Make sure the gateway is running: python app.py{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        sys.exit(1)


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
# COMMANDS
# ============================================================

def cmd_analyze(args):
    """Analyze a wallet"""
    wallet = args.wallet
    print(f"\n{CYAN}🔍 Analyzing wallet {shorten_address(wallet)}...{RESET}\n")
    
    # Fetch trades
    result = api_request(f"/api/trades/{wallet}")
    
    if not result.get("success", True) or "error" in result:
        print(f"{RED}✗ {result.get('error', 'Failed to fetch trades')}{RESET}")
        return
    
    trades = result.get("trades", [])
    
    if not trades:
        print(f"{YELLOW}No trades found for this wallet{RESET}")
        return
    
    # Calculate metrics
    total_trades = len(trades)
    buys = [t for t in trades if t.get("side", "").upper() == "BUY"]
    sells = [t for t in trades if t.get("side", "").upper() == "SELL"]
    
    total_volume = sum(float(t.get("amount", 0)) for t in trades)
    
    # Try to get analysis
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
        print(f"  {DIM}Avg Trade:{RESET}   ${total_volume/total_trades:,.2f}" if total_trades > 0 else "")
        
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
    
    # Show recent trades
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
        
        # Highlight winner
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
        # Parent
        print(f"{GREEN}✓ Daemon started (PID: {pid}){RESET}")
        print(f"{DIM}  Monitoring tracked wallets for new trades{RESET}")
        print(f"{DIM}  Check status: polyclaw daemon status{RESET}")
        return
    
    # Child process - daemon
    os.setsid()
    
    # Write PID file
    with open(DAEMON_PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    
    # Import and run daemon
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
    if not DAEMON_PID_FILE.exists():
        print(f"{DIM}Daemon is not running{RESET}")
        print(f"{DIM}Start it: polyclaw daemon start{RESET}")
        return
    
    with open(DAEMON_PID_FILE) as f:
        pid = int(f.read().strip())
    
    try:
        os.kill(pid, 0)
        tracking = load_tracking()
        print(f"{GREEN}✓ Daemon is running (PID: {pid}){RESET}")
        print(f"{DIM}  Tracking {len(tracking['wallets'])} wallet(s){RESET}")
    except OSError:
        DAEMON_PID_FILE.unlink()
        print(f"{YELLOW}⚠ Daemon crashed (cleaned up stale PID file){RESET}")


def cmd_doctor(args):
    """Run diagnostics"""
    logo()
    print(f"{BOLD}Running diagnostics...{RESET}\n")
    
    checks = []
    
    # Check config directory
    if CONFIG_DIR.exists():
        checks.append((True, "Config directory exists", str(CONFIG_DIR)))
    else:
        checks.append((False, "Config directory missing", str(CONFIG_DIR)))
    
    # Check gateway connection
    config = load_config()
    try:
        response = requests.get(f"{config['gateway_url']}/", timeout=5)
        checks.append((True, "Gateway is running", config['gateway_url']))
    except:
        checks.append((False, "Gateway not reachable", config['gateway_url']))
    
    # Check AI providers
    try:
        result = api_request("/api/ai-providers")
        providers = result.get("providers", [])
        if providers:
            checks.append((True, f"AI providers configured", ", ".join(providers)))
        else:
            checks.append((None, "No AI providers configured", "Optional for AI features"))
    except:
        checks.append((None, "Could not check AI providers", "Gateway may be down"))
    
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
    else:
        checks.append((None, "Daemon not running", "Optional"))
    
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
    print(f"{BOLD}{'─' * 60}{RESET}\n")


def cmd_version(args):
    """Show version"""
    print(f"PolyClaw v{VERSION}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="PolyClaw - Polymarket Trading Intelligence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  polyclaw analyze 0x1234...      Analyze a wallet
  polyclaw track 0x1234...        Start tracking alerts
  polyclaw leaderboard            Show top performers
  polyclaw chat "What strategies work?"
  polyclaw daemon start           Start background monitoring

More info: https://github.com/polyclaw/polyclaw
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
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
    
    # doctor
    p_doctor = subparsers.add_parser("doctor", help="Run diagnostics")
    p_doctor.set_defaults(func=cmd_doctor)
    
    # version
    p_version = subparsers.add_parser("version", help="Show version")
    p_version.set_defaults(func=cmd_version)
    
    args = parser.parse_args()
    
    if args.command is None:
        logo()
        parser.print_help()
        return
    
    if args.command == "daemon" and args.daemon_cmd is None:
        print("Usage: polyclaw daemon {start|stop|status}")
        return
    
    args.func(args)


if __name__ == "__main__":
    main()
