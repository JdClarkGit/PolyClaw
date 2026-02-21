#!/usr/bin/env python3
"""
PolyClaw TUI - Terminal User Interface with WebSocket connection

Like OpenClaw's TUI but specialized for prediction markets.
Features:
- Real-time WebSocket connection to gateway
- Persistent sessions with memory
- Slash commands
- Model switching
- Beautiful terminal UI
"""

import asyncio
import json
import sys
import os
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

CONFIG_DIR = Path.home() / ".polyclaw"
VERSION = "2026.2.21"


def logo():
    """Print PolyClaw logo"""
    print(f"""
{RED}▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄{RESET}
{RED}██░▄▄░██░▄▄▄░██░█████░██░██░▄▄▀██░████░▄▄▀██░███░███░▄▄░██░▄▄▀██{RESET}
{RED}██░▀▀░██░███░██░█████░▀▀░██░████░████░▀▀░██░█░█░███░▀▀░██░▀▀░██{RESET}
{RED}██░█████░▀▀▀░██░▀▀░█████░██░▀▀▄██░▀▀░█░██░██▄▀▄▀▄██░█████░██░██{RESET}
{RED}▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀{RESET}
                    {RED}🦞 POLYCLAW 🦞{RESET}                    
""")


def load_config():
    """Load configuration"""
    config_file = CONFIG_DIR / "config.json"
    if config_file.exists():
        with open(config_file) as f:
            return json.load(f)
    return {}


def get_token():
    """Get gateway token"""
    token_file = CONFIG_DIR / "default_token"
    if token_file.exists():
        return token_file.read_text().strip()
    return None


class PolyClawTUI:
    """
    Terminal User Interface for PolyClaw.
    Connects to the gateway via WebSocket for real-time communication.
    """
    
    def __init__(self, gateway_ws: str = None, session_id: str = None):
        self.config = load_config()
        self.gateway_ws = gateway_ws or f"ws://127.0.0.1:18790"
        self.gateway_http = self.config.get("gateway_url", "http://localhost:8080")
        self.session_id = session_id or f"tui_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.token = get_token()
        self.model = self.config.get("default_model", "anthropic/claude-opus-4-5")
        self.connected = False
        self.websocket = None
        self.running = False
        
        # Commands
        self.commands = {
            "/help": self.cmd_help,
            "/analyze": self.cmd_analyze,
            "/track": self.cmd_track,
            "/untrack": self.cmd_untrack,
            "/list": self.cmd_list,
            "/leaderboard": self.cmd_leaderboard,
            "/compare": self.cmd_compare,
            "/export": self.cmd_export,
            "/model": self.cmd_model,
            "/session": self.cmd_session,
            "/memory": self.cmd_memory,
            "/status": self.cmd_status,
            "/clear": self.cmd_clear,
            "/new": self.cmd_new,
            "/quit": self.cmd_quit,
            "/exit": self.cmd_quit,
            "/q": self.cmd_quit,
        }
    
    async def connect_websocket(self):
        """Connect to gateway via WebSocket"""
        try:
            import websockets
            
            print(f"{DIM}Connecting to {self.gateway_ws}...{RESET}")
            
            self.websocket = await websockets.connect(self.gateway_ws)
            
            # Wait for welcome
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if data.get("type") == "welcome":
                print(f"{GREEN}✓ Connected to gateway{RESET}")
                
                # Authenticate
                if self.token:
                    await self.websocket.send(json.dumps({
                        "type": "auth",
                        "token": self.token,
                        "session_id": self.session_id,
                    }))
                    
                    auth_response = await self.websocket.recv()
                    auth_data = json.loads(auth_response)
                    
                    if auth_data.get("type") == "auth_success":
                        self.connected = True
                        print(f"{GREEN}✓ Authenticated{RESET}")
                        return True
                    else:
                        print(f"{RED}✗ Authentication failed{RESET}")
                else:
                    print(f"{YELLOW}⚠ No token found. Run: polyclaw onboard{RESET}")
            
            return False
            
        except ImportError:
            print(f"{YELLOW}WebSocket mode requires: pip install websockets{RESET}")
            return False
        except Exception as e:
            print(f"{DIM}WebSocket connection failed: {e}{RESET}")
            return False
    
    async def send_message(self, msg_type: str, data: dict = None):
        """Send message to gateway"""
        if not self.websocket:
            return None
        
        message = {"type": msg_type}
        if data:
            message.update(data)
        
        await self.websocket.send(json.dumps(message))
        
        # Wait for response
        response = await self.websocket.recv()
        return json.loads(response)
    
    def run_http(self, endpoint: str, method: str = "GET", data: dict = None):
        """Fallback to HTTP API"""
        import requests
        
        url = f"{self.gateway_http}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, timeout=30)
            else:
                response = requests.post(url, json=data, timeout=30)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def print_header(self):
        """Print TUI header"""
        print()
        print(f"{BOLD}{'─' * 70}{RESET}")
        status = f"{GREEN}connected{RESET}" if self.connected else f"{DIM}offline{RESET}"
        print(f" {status} | session {self.session_id} | {self.model}")
        print(f"{BOLD}{'─' * 70}{RESET}")
        print()
    
    def print_commands(self):
        """Print available commands"""
        print(f"{BOLD}Commands:{RESET}")
        print(f"  {CYAN}/analyze <wallet>{RESET}  - Analyze a wallet")
        print(f"  {CYAN}/track <wallet>{RESET}    - Track wallet for alerts")
        print(f"  {CYAN}/untrack <wallet>{RESET}  - Stop tracking")
        print(f"  {CYAN}/list{RESET}              - List tracked wallets")
        print(f"  {CYAN}/leaderboard{RESET}       - Show top performers")
        print(f"  {CYAN}/compare <w1> <w2>{RESET} - Compare wallets")
        print(f"  {CYAN}/export <wallet>{RESET}   - Export to CSV")
        print(f"  {CYAN}/model <name>{RESET}      - Switch AI model")
        print(f"  {CYAN}/memory{RESET}            - Show memory stats")
        print(f"  {CYAN}/status{RESET}            - System status")
        print(f"  {CYAN}/new{RESET}               - New session")
        print(f"  {CYAN}/help{RESET}              - Show this help")
        print(f"  {CYAN}/quit{RESET}              - Exit")
        print()
        print(f"{DIM}Or just type to chat with AI about strategies...{RESET}")
        print()
    
    # ============================================================
    # COMMANDS
    # ============================================================
    
    async def cmd_help(self, args: list):
        """Show help"""
        self.print_commands()
    
    async def cmd_analyze(self, args: list):
        """Analyze a wallet"""
        if not args:
            print(f"{YELLOW}Usage: /analyze <wallet>{RESET}")
            return
        
        wallet = args[0]
        print(f"\n{CYAN}🔍 Analyzing {wallet[:10]}...{RESET}")
        
        if self.connected:
            result = await self.send_message("analyze", {"wallet": wallet})
        else:
            result = self.run_http(f"/api/analyze/{wallet}")
        
        if "error" in result:
            print(f"{RED}✗ {result['error']}{RESET}")
            return
        
        analysis = result.get("analysis", {})
        
        print(f"\n{BOLD}Analysis Results:{RESET}")
        print(f"  P&L:       {GREEN}${analysis.get('pnl', 0):,.2f}{RESET}")
        print(f"  Win Rate:  {analysis.get('win_rate', 0)*100:.1f}%")
        print(f"  Trades:    {analysis.get('total_trades', 0)}")
        if analysis.get('trading_style'):
            print(f"  Style:     {MAGENTA}{analysis['trading_style']}{RESET}")
        print()
    
    async def cmd_track(self, args: list):
        """Track a wallet"""
        if not args:
            print(f"{YELLOW}Usage: /track <wallet>{RESET}")
            return
        
        wallet = args[0]
        
        if self.connected:
            result = await self.send_message("track", {"wallet": wallet})
        else:
            result = self.run_http("/api/tracking/add", "POST", {"wallet": wallet})
        
        if result.get("type") == "track_success" or result.get("success"):
            print(f"{GREEN}✓ Now tracking {wallet[:10]}...{RESET}")
        else:
            print(f"{RED}✗ Track failed{RESET}")
    
    async def cmd_untrack(self, args: list):
        """Untrack a wallet"""
        if not args:
            print(f"{YELLOW}Usage: /untrack <wallet>{RESET}")
            return
        
        wallet = args[0]
        
        if self.connected:
            result = await self.send_message("untrack", {"wallet": wallet})
        else:
            result = self.run_http("/api/tracking/remove", "POST", {"wallet": wallet})
        
        print(f"{GREEN}✓ Stopped tracking {wallet[:10]}...{RESET}")
    
    async def cmd_list(self, args: list):
        """List tracked wallets"""
        if self.connected:
            result = await self.send_message("list", {})
        else:
            result = self.run_http("/api/tracking/list")
        
        wallets = result.get("wallets", [])
        
        if wallets:
            print(f"\n{BOLD}Tracked Wallets ({len(wallets)}):{RESET}")
            for w in wallets:
                print(f"  • {w}")
        else:
            print(f"{DIM}No wallets tracked{RESET}")
        print()
    
    async def cmd_leaderboard(self, args: list):
        """Show leaderboard"""
        print(f"\n{CYAN}🏆 Loading leaderboard...{RESET}")
        
        if self.connected:
            result = await self.send_message("leaderboard", {})
        else:
            result = self.run_http("/api/leaderboard")
        
        wallets = result.get("wallets", [])[:10]
        
        if wallets:
            print(f"\n{BOLD}Top Performers:{RESET}")
            medals = ["🥇", "🥈", "🥉"]
            for i, w in enumerate(wallets):
                rank = medals[i] if i < 3 else f"{i+1}."
                addr = w.get('address', w.get('wallet', '?'))[:12]
                pnl = w.get('pnl', 0)
                color = GREEN if pnl >= 0 else RED
                print(f"  {rank} {addr}...  {color}${pnl:,.2f}{RESET}")
        else:
            print(f"{DIM}Leaderboard is empty{RESET}")
        print()
    
    async def cmd_compare(self, args: list):
        """Compare wallets"""
        if len(args) < 2:
            print(f"{YELLOW}Usage: /compare <wallet1> <wallet2>{RESET}")
            return
        
        w1, w2 = args[0], args[1]
        print(f"\n{CYAN}⚖️ Comparing wallets...{RESET}")
        
        result = self.run_http(f"/api/compare?wallets={w1},{w2}")
        
        wallets = result.get("wallets", [])
        if len(wallets) >= 2:
            print(f"\n{BOLD}Comparison:{RESET}")
            print(f"  {CYAN}{w1[:10]}{RESET} vs {MAGENTA}{w2[:10]}{RESET}")
            print(f"  P&L: ${wallets[0].get('pnl', 0):,.2f} vs ${wallets[1].get('pnl', 0):,.2f}")
        else:
            print(f"{RED}✗ Could not compare{RESET}")
        print()
    
    async def cmd_export(self, args: list):
        """Export trades"""
        if not args:
            print(f"{YELLOW}Usage: /export <wallet>{RESET}")
            return
        
        wallet = args[0]
        print(f"{CYAN}📥 Exporting...{RESET}")
        
        import requests
        try:
            response = requests.get(f"{self.gateway_http}/api/download/{wallet}/csv", timeout=60)
            if response.status_code == 200:
                filename = f"trades_{wallet[:8]}.csv"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"{GREEN}✓ Exported to {filename}{RESET}")
        except Exception as e:
            print(f"{RED}✗ Export failed: {e}{RESET}")
    
    async def cmd_model(self, args: list):
        """Switch AI model"""
        if not args:
            print(f"{BOLD}Current model:{RESET} {self.model}")
            print(f"\n{DIM}Available models:{RESET}")
            print(f"  anthropic/claude-opus-4-5")
            print(f"  anthropic/claude-sonnet-4-20250514")
            print(f"  openai/gpt-4")
            print(f"  openai/gpt-4-turbo")
            return
        
        self.model = args[0]
        print(f"{GREEN}✓ Switched to {self.model}{RESET}")
    
    async def cmd_session(self, args: list):
        """Session management"""
        print(f"{BOLD}Current session:{RESET} {self.session_id}")
    
    async def cmd_memory(self, args: list):
        """Show memory stats"""
        if self.connected:
            result = await self.send_message("memory", {"action": "stats"})
            stats = result.get("stats", {})
        else:
            from memory import get_memory
            stats = get_memory().get_stats()
        
        print(f"\n{BOLD}Memory Stats:{RESET}")
        print(f"  Sessions: {stats.get('sessions', 0)}")
        print(f"  Wallets known: {stats.get('wallets_known', 0)}")
        print(f"  Facts stored: {stats.get('facts_stored', 0)}")
        print(f"  Strategies: {stats.get('strategies_stored', 0)}")
        print()
    
    async def cmd_status(self, args: list):
        """Show system status"""
        if self.connected:
            result = await self.send_message("status", {})
            print(f"\n{BOLD}Status:{RESET}")
            print(f"  Gateway: {GREEN}connected{RESET}")
            print(f"  Session: {self.session_id}")
            print(f"  Model: {self.model}")
        else:
            print(f"\n{BOLD}Status:{RESET}")
            print(f"  Gateway: {YELLOW}HTTP fallback{RESET}")
            print(f"  Session: {self.session_id}")
            print(f"  Model: {self.model}")
        print()
    
    async def cmd_clear(self, args: list):
        """Clear screen"""
        os.system('clear' if os.name != 'nt' else 'cls')
        logo()
        self.print_header()
    
    async def cmd_new(self, args: list):
        """Start new session"""
        self.session_id = f"tui_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"{GREEN}✓ New session: {self.session_id}{RESET}")
    
    async def cmd_quit(self, args: list):
        """Exit TUI"""
        self.running = False
        print(f"\n{DIM}Goodbye! 🦞{RESET}")
    
    async def chat(self, message: str):
        """Chat with AI"""
        print(f"\n{CYAN}🦞 Thinking...{RESET}")
        
        if self.connected:
            result = await self.send_message("chat", {"message": message})
            if result.get("type") == "chat_response":
                response = result.get("response", "")
            else:
                response = result.get("error", "No response")
        else:
            result = self.run_http("/api/chat", "POST", {"message": message})
            response = result.get("response", result.get("error", "No response"))
        
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
        print()
    
    async def run(self):
        """Main TUI loop"""
        logo()
        
        # Try WebSocket connection
        await self.connect_websocket()
        
        self.print_header()
        self.print_commands()
        
        self.running = True
        
        while self.running:
            try:
                # Get input
                user_input = input(f"{CYAN}>{RESET} ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith('/'):
                    parts = user_input.split()
                    cmd = parts[0].lower()
                    args = parts[1:]
                    
                    if cmd in self.commands:
                        await self.commands[cmd](args)
                    else:
                        print(f"{YELLOW}Unknown command. Type /help{RESET}")
                else:
                    # Chat with AI
                    await self.chat(user_input)
            
            except KeyboardInterrupt:
                print(f"\n\n{DIM}Goodbye! 🦞{RESET}")
                break
            except EOFError:
                break
        
        # Cleanup
        if self.websocket:
            await self.websocket.close()


def main():
    """Entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="PolyClaw TUI")
    parser.add_argument("--gateway", "-g", help="Gateway WebSocket URL")
    parser.add_argument("--session", "-s", help="Session ID")
    args = parser.parse_args()
    
    tui = PolyClawTUI(
        gateway_ws=args.gateway,
        session_id=args.session,
    )
    
    asyncio.run(tui.run())


if __name__ == "__main__":
    main()
