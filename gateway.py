"""
PolyClaw Gateway - WebSocket server for real-time TUI connections

Like OpenClaw's gateway but specialized for prediction markets.
Handles:
- WebSocket connections for TUI clients
- Authentication via tokens
- Message routing between clients and AI
- Real-time trade alerts
- Session management
"""

import json
import asyncio
import logging
import secrets
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, Optional
import threading

# WebSocket support
try:
    import websockets
    from websockets.server import serve
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

# Memory system
from memory import get_memory

# Configuration
CONFIG_DIR = Path.home() / ".polyclaw"
CONFIG_FILE = CONFIG_DIR / "config.json"
TOKENS_FILE = CONFIG_DIR / "tokens.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("polyclaw.gateway")


class TokenManager:
    """Manages authentication tokens"""
    
    def __init__(self):
        self.tokens_file = TOKENS_FILE
        self._tokens = self._load()
    
    def _load(self) -> Dict:
        if self.tokens_file.exists():
            with open(self.tokens_file) as f:
                return json.load(f)
        return {"tokens": {}}
    
    def _save(self):
        with open(self.tokens_file, 'w') as f:
            json.dump(self._tokens, f, indent=2)
    
    def generate_token(self, name: str = "default") -> str:
        """Generate a new authentication token"""
        token = secrets.token_hex(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        self._tokens["tokens"][token_hash] = {
            "name": name,
            "created": datetime.now().isoformat(),
            "last_used": None,
        }
        self._save()
        
        return token
    
    def validate_token(self, token: str) -> bool:
        """Validate a token"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        if token_hash in self._tokens["tokens"]:
            self._tokens["tokens"][token_hash]["last_used"] = datetime.now().isoformat()
            self._save()
            return True
        return False
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a token"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        if token_hash in self._tokens["tokens"]:
            del self._tokens["tokens"][token_hash]
            self._save()
            return True
        return False
    
    def list_tokens(self) -> list:
        """List all tokens (without revealing the actual tokens)"""
        return [
            {"name": v["name"], "created": v["created"], "last_used": v["last_used"]}
            for v in self._tokens["tokens"].values()
        ]
    
    def get_or_create_default(self) -> str:
        """Get existing default token or create one"""
        # Check if we have a stored default token
        default_file = CONFIG_DIR / "default_token"
        if default_file.exists():
            token = default_file.read_text().strip()
            if self.validate_token(token):
                return token
        
        # Create new default token
        token = self.generate_token("default")
        default_file.write_text(token)
        return token


class Client:
    """Represents a connected client"""
    
    def __init__(self, websocket, client_id: str, session_id: str = None):
        self.websocket = websocket
        self.client_id = client_id
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.authenticated = False
        self.connected_at = datetime.now()
        self.last_activity = datetime.now()
        self.metadata = {}


class GatewayServer:
    """
    WebSocket gateway server for PolyClaw.
    Handles real-time communication with TUI clients.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 18790):
        self.host = host
        self.port = port
        self.clients: Dict[str, Client] = {}
        self.token_manager = TokenManager()
        self.memory = get_memory()
        self.running = False
        self._server = None
        
        # Message handlers
        self.handlers = {
            "auth": self._handle_auth,
            "chat": self._handle_chat,
            "analyze": self._handle_analyze,
            "track": self._handle_track,
            "untrack": self._handle_untrack,
            "list": self._handle_list,
            "leaderboard": self._handle_leaderboard,
            "status": self._handle_status,
            "memory": self._handle_memory,
            "ping": self._handle_ping,
        }
    
    async def _handle_connection(self, websocket):
        """Handle a new WebSocket connection"""
        client_id = secrets.token_hex(8)
        client = Client(websocket, client_id)
        self.clients[client_id] = client
        
        logger.info(f"Client connected: {client_id}")
        
        try:
            # Send welcome message
            await self._send(client, {
                "type": "welcome",
                "client_id": client_id,
                "version": "2026.2.21",
                "message": "🦞 Welcome to PolyClaw Gateway",
            })
            
            # Handle messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(client, data)
                except json.JSONDecodeError:
                    await self._send_error(client, "Invalid JSON")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    await self._send_error(client, str(e))
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        finally:
            del self.clients[client_id]
    
    async def _handle_message(self, client: Client, data: Dict):
        """Route message to appropriate handler"""
        msg_type = data.get("type", "")
        client.last_activity = datetime.now()
        
        # Require auth for most operations
        if msg_type != "auth" and msg_type != "ping" and not client.authenticated:
            await self._send_error(client, "Not authenticated", code="AUTH_REQUIRED")
            return
        
        handler = self.handlers.get(msg_type)
        if handler:
            await handler(client, data)
        else:
            await self._send_error(client, f"Unknown message type: {msg_type}")
    
    async def _send(self, client: Client, data: Dict):
        """Send message to client"""
        try:
            await client.websocket.send(json.dumps(data))
        except Exception as e:
            logger.error(f"Error sending to client {client.client_id}: {e}")
    
    async def _send_error(self, client: Client, message: str, code: str = "ERROR"):
        """Send error message to client"""
        await self._send(client, {
            "type": "error",
            "code": code,
            "message": message,
        })
    
    async def _handle_auth(self, client: Client, data: Dict):
        """Handle authentication"""
        token = data.get("token", "")
        
        if self.token_manager.validate_token(token):
            client.authenticated = True
            client.session_id = data.get("session_id", client.session_id)
            
            await self._send(client, {
                "type": "auth_success",
                "session_id": client.session_id,
                "message": "Authenticated successfully",
            })
            
            logger.info(f"Client {client.client_id} authenticated")
        else:
            await self._send_error(client, "Invalid token", code="AUTH_FAILED")
    
    async def _handle_chat(self, client: Client, data: Dict):
        """Handle chat message"""
        message = data.get("message", "")
        
        if not message:
            await self._send_error(client, "No message provided")
            return
        
        # Store in memory
        self.memory.remember_conversation(client.session_id, "user", message)
        
        # Send thinking indicator
        await self._send(client, {"type": "thinking"})
        
        # Get AI response (this would call the actual AI)
        try:
            import requests
            
            # Get context from memory
            context = self.memory.get_context_for_prompt(client.session_id)
            
            # Call the local gateway API
            response = requests.post(
                "http://localhost:8080/api/chat",
                json={
                    "message": message,
                    "context": context,
                    "session_id": client.session_id,
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result.get("response", "No response")
                
                # Store AI response in memory
                self.memory.remember_conversation(client.session_id, "assistant", ai_response)
                
                await self._send(client, {
                    "type": "chat_response",
                    "response": ai_response,
                    "session_id": client.session_id,
                })
            else:
                await self._send_error(client, "AI request failed")
        
        except Exception as e:
            await self._send_error(client, f"Chat error: {str(e)}")
    
    async def _handle_analyze(self, client: Client, data: Dict):
        """Handle wallet analysis request"""
        wallet = data.get("wallet", "")
        
        if not wallet:
            await self._send_error(client, "No wallet provided")
            return
        
        await self._send(client, {"type": "analyzing", "wallet": wallet})
        
        try:
            import requests
            
            response = requests.get(f"http://localhost:8080/api/analyze/{wallet}", timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                analysis = result.get("analysis", {})
                
                # Store in memory
                self.memory.remember_wallet(wallet, analysis=analysis)
                
                await self._send(client, {
                    "type": "analysis_result",
                    "wallet": wallet,
                    "analysis": analysis,
                })
            else:
                await self._send_error(client, "Analysis failed")
        
        except Exception as e:
            await self._send_error(client, f"Analysis error: {str(e)}")
    
    async def _handle_track(self, client: Client, data: Dict):
        """Handle track wallet request"""
        wallet = data.get("wallet", "")
        
        if not wallet:
            await self._send_error(client, "No wallet provided")
            return
        
        try:
            import requests
            response = requests.post(
                "http://localhost:8080/api/tracking/add",
                json={"wallet": wallet},
                timeout=10
            )
            
            if response.status_code == 200:
                self.memory.remember_wallet(wallet, tags=["tracked"])
                await self._send(client, {
                    "type": "track_success",
                    "wallet": wallet,
                })
            else:
                await self._send_error(client, "Track failed")
        except Exception as e:
            await self._send_error(client, f"Track error: {str(e)}")
    
    async def _handle_untrack(self, client: Client, data: Dict):
        """Handle untrack wallet request"""
        wallet = data.get("wallet", "")
        
        try:
            import requests
            response = requests.post(
                "http://localhost:8080/api/tracking/remove",
                json={"wallet": wallet},
                timeout=10
            )
            
            if response.status_code == 200:
                await self._send(client, {
                    "type": "untrack_success",
                    "wallet": wallet,
                })
        except Exception as e:
            await self._send_error(client, f"Untrack error: {str(e)}")
    
    async def _handle_list(self, client: Client, data: Dict):
        """Handle list tracked wallets request"""
        try:
            import requests
            response = requests.get("http://localhost:8080/api/tracking/list", timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                await self._send(client, {
                    "type": "list_result",
                    "wallets": result.get("wallets", []),
                })
        except Exception as e:
            await self._send_error(client, f"List error: {str(e)}")
    
    async def _handle_leaderboard(self, client: Client, data: Dict):
        """Handle leaderboard request"""
        try:
            import requests
            response = requests.get("http://localhost:8080/api/leaderboard", timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                await self._send(client, {
                    "type": "leaderboard_result",
                    "wallets": result.get("wallets", []),
                })
        except Exception as e:
            await self._send_error(client, f"Leaderboard error: {str(e)}")
    
    async def _handle_status(self, client: Client, data: Dict):
        """Handle status request"""
        memory_stats = self.memory.get_stats()
        
        await self._send(client, {
            "type": "status_result",
            "connected_clients": len(self.clients),
            "memory": memory_stats,
            "uptime": str(datetime.now() - client.connected_at),
        })
    
    async def _handle_memory(self, client: Client, data: Dict):
        """Handle memory operations"""
        action = data.get("action", "")
        
        if action == "stats":
            stats = self.memory.get_stats()
            await self._send(client, {"type": "memory_stats", "stats": stats})
        
        elif action == "search":
            query = data.get("query", "")
            results = self.memory.search(query)
            await self._send(client, {"type": "memory_search", "results": results})
        
        elif action == "context":
            context = self.memory.get_context_for_prompt(client.session_id)
            await self._send(client, {"type": "memory_context", "context": context})
        
        elif action == "remember_fact":
            fact = data.get("fact", "")
            self.memory.remember_fact(fact, source="user")
            await self._send(client, {"type": "fact_remembered", "fact": fact})
        
        else:
            await self._send_error(client, f"Unknown memory action: {action}")
    
    async def _handle_ping(self, client: Client, data: Dict):
        """Handle ping (heartbeat)"""
        await self._send(client, {
            "type": "pong",
            "timestamp": datetime.now().isoformat(),
        })
    
    async def broadcast(self, data: Dict, exclude_client: str = None):
        """Broadcast message to all authenticated clients"""
        for client_id, client in self.clients.items():
            if client.authenticated and client_id != exclude_client:
                await self._send(client, data)
    
    async def start(self):
        """Start the gateway server"""
        if not HAS_WEBSOCKETS:
            logger.error("websockets package not installed")
            return
        
        self.running = True
        
        logger.info(f"Starting PolyClaw Gateway on ws://{self.host}:{self.port}")
        
        # Ensure we have a default token
        token = self.token_manager.get_or_create_default()
        logger.info(f"Gateway token: {token[:16]}...")
        
        async with serve(self._handle_connection, self.host, self.port):
            while self.running:
                await asyncio.sleep(1)
    
    def stop(self):
        """Stop the gateway server"""
        self.running = False


def run_gateway(host: str = "127.0.0.1", port: int = 18790):
    """Run the gateway server"""
    server = GatewayServer(host, port)
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Gateway shutting down")
        server.stop()


if __name__ == "__main__":
    run_gateway()
