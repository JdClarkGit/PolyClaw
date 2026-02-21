"""
PolyClaw Memory System

Persistent agent memory for context, preferences, and learned information.
Similar to OpenClaw's memory system but specialized for prediction markets.
"""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

MEMORY_DIR = Path.home() / ".polyclaw" / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# Memory stores
CONVERSATIONS_FILE = MEMORY_DIR / "conversations.json"
ENTITIES_FILE = MEMORY_DIR / "entities.json"
PREFERENCES_FILE = MEMORY_DIR / "preferences.json"
FACTS_FILE = MEMORY_DIR / "facts.json"
WALLET_PROFILES_FILE = MEMORY_DIR / "wallet_profiles.json"
MARKET_CONTEXT_FILE = MEMORY_DIR / "market_context.json"


class MemoryStore:
    """Base class for memory stores"""
    
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self._data = self._load()
    
    def _load(self) -> Dict:
        if self.filepath.exists():
            try:
                with open(self.filepath) as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save(self):
        with open(self.filepath, 'w') as f:
            json.dump(self._data, f, indent=2, default=str)
    
    def get(self, key: str, default=None):
        return self._data.get(key, default)
    
    def set(self, key: str, value: Any):
        self._data[key] = value
        self._save()
    
    def delete(self, key: str):
        if key in self._data:
            del self._data[key]
            self._save()
    
    def all(self) -> Dict:
        return self._data.copy()


class ConversationMemory(MemoryStore):
    """
    Stores conversation history with summarization.
    Keeps recent messages in full, older ones as summaries.
    """
    
    def __init__(self):
        super().__init__(CONVERSATIONS_FILE)
        if "sessions" not in self._data:
            self._data["sessions"] = {}
        if "summaries" not in self._data:
            self._data["summaries"] = []
    
    def add_message(self, session_id: str, role: str, content: str, metadata: Dict = None):
        """Add a message to a session"""
        if session_id not in self._data["sessions"]:
            self._data["sessions"][session_id] = {
                "created": datetime.now().isoformat(),
                "messages": [],
            }
        
        self._data["sessions"][session_id]["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        })
        
        self._data["sessions"][session_id]["updated"] = datetime.now().isoformat()
        self._save()
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get a session by ID"""
        return self._data["sessions"].get(session_id)
    
    def get_recent_messages(self, session_id: str, limit: int = 20) -> List[Dict]:
        """Get recent messages from a session"""
        session = self.get_session(session_id)
        if not session:
            return []
        return session["messages"][-limit:]
    
    def get_context_window(self, session_id: str, max_tokens: int = 4000) -> List[Dict]:
        """Get messages that fit within a token budget (approximate)"""
        messages = self.get_recent_messages(session_id, limit=50)
        
        # Rough token estimation: 4 chars per token
        context = []
        total_chars = 0
        max_chars = max_tokens * 4
        
        for msg in reversed(messages):
            msg_chars = len(msg["content"])
            if total_chars + msg_chars > max_chars:
                break
            context.insert(0, msg)
            total_chars += msg_chars
        
        return context
    
    def add_summary(self, session_id: str, summary: str):
        """Add a conversation summary"""
        self._data["summaries"].append({
            "session_id": session_id,
            "summary": summary,
            "timestamp": datetime.now().isoformat(),
        })
        self._save()
    
    def get_all_summaries(self) -> List[Dict]:
        """Get all conversation summaries"""
        return self._data["summaries"]
    
    def list_sessions(self) -> List[Dict]:
        """List all sessions with metadata"""
        sessions = []
        for sid, data in self._data["sessions"].items():
            sessions.append({
                "id": sid,
                "created": data.get("created"),
                "updated": data.get("updated"),
                "message_count": len(data.get("messages", [])),
            })
        return sorted(sessions, key=lambda x: x.get("updated", ""), reverse=True)


class EntityMemory(MemoryStore):
    """
    Stores information about entities (wallets, markets, users).
    Builds up knowledge over time.
    """
    
    def __init__(self):
        super().__init__(ENTITIES_FILE)
        if "wallets" not in self._data:
            self._data["wallets"] = {}
        if "markets" not in self._data:
            self._data["markets"] = {}
        if "users" not in self._data:
            self._data["users"] = {}
    
    def remember_wallet(self, address: str, info: Dict):
        """Store/update wallet information"""
        address = address.lower()
        if address not in self._data["wallets"]:
            self._data["wallets"][address] = {
                "first_seen": datetime.now().isoformat(),
                "analyses": [],
                "notes": [],
                "tags": [],
            }
        
        wallet = self._data["wallets"][address]
        wallet["last_seen"] = datetime.now().isoformat()
        
        # Merge info
        for key, value in info.items():
            if key == "analysis":
                wallet["analyses"].append({
                    "timestamp": datetime.now().isoformat(),
                    "data": value,
                })
                # Keep last 10 analyses
                wallet["analyses"] = wallet["analyses"][-10:]
            elif key == "note":
                wallet["notes"].append({
                    "timestamp": datetime.now().isoformat(),
                    "text": value,
                })
            elif key == "tags":
                wallet["tags"] = list(set(wallet.get("tags", []) + value))
            else:
                wallet[key] = value
        
        self._save()
    
    def get_wallet(self, address: str) -> Optional[Dict]:
        """Get stored wallet information"""
        return self._data["wallets"].get(address.lower())
    
    def get_wallet_history(self, address: str) -> List[Dict]:
        """Get analysis history for a wallet"""
        wallet = self.get_wallet(address)
        if wallet:
            return wallet.get("analyses", [])
        return []
    
    def search_wallets(self, query: str = None, tags: List[str] = None) -> List[Dict]:
        """Search wallets by query or tags"""
        results = []
        for addr, wallet in self._data["wallets"].items():
            if tags:
                if not any(t in wallet.get("tags", []) for t in tags):
                    continue
            if query:
                # Search in notes and tags
                found = False
                for note in wallet.get("notes", []):
                    if query.lower() in note.get("text", "").lower():
                        found = True
                        break
                if not found and query.lower() not in " ".join(wallet.get("tags", [])).lower():
                    continue
            results.append({"address": addr, **wallet})
        return results
    
    def remember_market(self, market_id: str, info: Dict):
        """Store market information"""
        if market_id not in self._data["markets"]:
            self._data["markets"][market_id] = {
                "first_seen": datetime.now().isoformat(),
            }
        
        market = self._data["markets"][market_id]
        market["last_seen"] = datetime.now().isoformat()
        market.update(info)
        self._save()
    
    def get_market(self, market_id: str) -> Optional[Dict]:
        """Get stored market information"""
        return self._data["markets"].get(market_id)


class PreferenceMemory(MemoryStore):
    """
    Stores user preferences and settings learned over time.
    """
    
    def __init__(self):
        super().__init__(PREFERENCES_FILE)
        if "settings" not in self._data:
            self._data["settings"] = {}
        if "learned" not in self._data:
            self._data["learned"] = []
    
    def set_preference(self, key: str, value: Any, source: str = "user"):
        """Set a preference"""
        self._data["settings"][key] = {
            "value": value,
            "source": source,
            "updated": datetime.now().isoformat(),
        }
        self._save()
    
    def get_preference(self, key: str, default=None):
        """Get a preference value"""
        pref = self._data["settings"].get(key)
        if pref:
            return pref["value"]
        return default
    
    def learn_preference(self, observation: str, inferred_preference: str):
        """Record a learned preference from user behavior"""
        self._data["learned"].append({
            "observation": observation,
            "inferred": inferred_preference,
            "timestamp": datetime.now().isoformat(),
        })
        self._save()
    
    def get_all_preferences(self) -> Dict:
        """Get all preferences"""
        return {k: v["value"] for k, v in self._data["settings"].items()}


class FactMemory(MemoryStore):
    """
    Stores facts and knowledge learned during conversations.
    Can be used to build up domain knowledge.
    """
    
    def __init__(self):
        super().__init__(FACTS_FILE)
        if "facts" not in self._data:
            self._data["facts"] = []
        if "strategies" not in self._data:
            self._data["strategies"] = []
    
    def add_fact(self, fact: str, source: str = None, confidence: float = 1.0):
        """Add a fact to memory"""
        fact_hash = hashlib.md5(fact.lower().encode()).hexdigest()[:8]
        
        # Check for duplicates
        for existing in self._data["facts"]:
            if existing.get("hash") == fact_hash:
                existing["mentions"] = existing.get("mentions", 1) + 1
                existing["last_mentioned"] = datetime.now().isoformat()
                self._save()
                return
        
        self._data["facts"].append({
            "hash": fact_hash,
            "fact": fact,
            "source": source,
            "confidence": confidence,
            "mentions": 1,
            "created": datetime.now().isoformat(),
            "last_mentioned": datetime.now().isoformat(),
        })
        self._save()
    
    def get_facts(self, limit: int = 50) -> List[Dict]:
        """Get facts sorted by relevance"""
        facts = sorted(
            self._data["facts"],
            key=lambda x: (x.get("mentions", 1), x.get("confidence", 1)),
            reverse=True
        )
        return facts[:limit]
    
    def search_facts(self, query: str) -> List[Dict]:
        """Search facts by keyword"""
        query = query.lower()
        return [
            f for f in self._data["facts"]
            if query in f["fact"].lower()
        ]
    
    def add_strategy(self, name: str, description: str, performance: Dict = None):
        """Add a trading strategy to memory"""
        self._data["strategies"].append({
            "name": name,
            "description": description,
            "performance": performance or {},
            "created": datetime.now().isoformat(),
        })
        self._save()
    
    def get_strategies(self) -> List[Dict]:
        """Get all remembered strategies"""
        return self._data["strategies"]


class WalletProfileMemory(MemoryStore):
    """
    Detailed wallet profiles built up over time.
    Includes trading patterns, performance history, classifications.
    """
    
    def __init__(self):
        super().__init__(WALLET_PROFILES_FILE)
    
    def update_profile(self, address: str, profile_data: Dict):
        """Update or create a wallet profile"""
        address = address.lower()
        
        if address not in self._data:
            self._data[address] = {
                "created": datetime.now().isoformat(),
                "performance_history": [],
                "classifications": [],
                "notes": [],
            }
        
        profile = self._data[address]
        profile["updated"] = datetime.now().isoformat()
        
        # Update performance history
        if "performance" in profile_data:
            profile["performance_history"].append({
                "timestamp": datetime.now().isoformat(),
                **profile_data["performance"],
            })
            # Keep last 30 days
            profile["performance_history"] = profile["performance_history"][-30:]
        
        # Update classification
        if "classification" in profile_data:
            profile["current_classification"] = profile_data["classification"]
            profile["classifications"].append({
                "timestamp": datetime.now().isoformat(),
                "classification": profile_data["classification"],
            })
        
        # Update other fields
        for key in ["nickname", "tags", "strategy", "risk_level"]:
            if key in profile_data:
                profile[key] = profile_data[key]
        
        self._save()
    
    def get_profile(self, address: str) -> Optional[Dict]:
        """Get a wallet profile"""
        return self._data.get(address.lower())
    
    def get_top_performers(self, limit: int = 10) -> List[Dict]:
        """Get top performing wallets from profiles"""
        profiles = []
        for addr, profile in self._data.items():
            if profile.get("performance_history"):
                latest = profile["performance_history"][-1]
                profiles.append({
                    "address": addr,
                    "pnl": latest.get("pnl", 0),
                    "win_rate": latest.get("win_rate", 0),
                    "classification": profile.get("current_classification"),
                    "nickname": profile.get("nickname"),
                })
        
        return sorted(profiles, key=lambda x: x.get("pnl", 0), reverse=True)[:limit]


class MarketContextMemory(MemoryStore):
    """
    Stores market context and conditions over time.
    Helps understand market regime and trends.
    """
    
    def __init__(self):
        super().__init__(MARKET_CONTEXT_FILE)
        if "snapshots" not in self._data:
            self._data["snapshots"] = []
        if "events" not in self._data:
            self._data["events"] = []
    
    def add_snapshot(self, snapshot: Dict):
        """Add a market context snapshot"""
        self._data["snapshots"].append({
            "timestamp": datetime.now().isoformat(),
            **snapshot,
        })
        # Keep last 100 snapshots
        self._data["snapshots"] = self._data["snapshots"][-100:]
        self._save()
    
    def add_event(self, event_type: str, description: str, metadata: Dict = None):
        """Record a market event"""
        self._data["events"].append({
            "type": event_type,
            "description": description,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        })
        self._save()
    
    def get_recent_context(self, hours: int = 24) -> Dict:
        """Get recent market context"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        recent_snapshots = [
            s for s in self._data["snapshots"]
            if datetime.fromisoformat(s["timestamp"]) > cutoff
        ]
        
        recent_events = [
            e for e in self._data["events"]
            if datetime.fromisoformat(e["timestamp"]) > cutoff
        ]
        
        return {
            "snapshots": recent_snapshots,
            "events": recent_events,
        }


# ============================================================
# UNIFIED MEMORY INTERFACE
# ============================================================

class AgentMemory:
    """
    Unified interface for all memory systems.
    This is the main class to use for memory operations.
    """
    
    def __init__(self):
        self.conversations = ConversationMemory()
        self.entities = EntityMemory()
        self.preferences = PreferenceMemory()
        self.facts = FactMemory()
        self.wallet_profiles = WalletProfileMemory()
        self.market_context = MarketContextMemory()
    
    def remember_conversation(self, session_id: str, role: str, content: str):
        """Remember a conversation message"""
        self.conversations.add_message(session_id, role, content)
    
    def remember_wallet(self, address: str, analysis: Dict = None, note: str = None, tags: List[str] = None):
        """Remember wallet information"""
        info = {}
        if analysis:
            info["analysis"] = analysis
        if note:
            info["note"] = note
        if tags:
            info["tags"] = tags
        self.entities.remember_wallet(address, info)
        
        # Also update profile
        if analysis:
            self.wallet_profiles.update_profile(address, {
                "performance": analysis,
                "classification": analysis.get("trading_style"),
            })
    
    def remember_fact(self, fact: str, source: str = None):
        """Remember a fact"""
        self.facts.add_fact(fact, source)
    
    def remember_strategy(self, name: str, description: str, performance: Dict = None):
        """Remember a trading strategy"""
        self.facts.add_strategy(name, description, performance)
    
    def set_preference(self, key: str, value: Any):
        """Set a user preference"""
        self.preferences.set_preference(key, value)
    
    def get_preference(self, key: str, default=None):
        """Get a user preference"""
        return self.preferences.get_preference(key, default)
    
    def get_context_for_prompt(self, session_id: str = None) -> str:
        """
        Build context string for AI prompts.
        Includes relevant memories, facts, and preferences.
        """
        context_parts = []
        
        # Recent conversation context
        if session_id:
            messages = self.conversations.get_context_window(session_id, max_tokens=2000)
            if messages:
                context_parts.append("## Recent Conversation")
                for msg in messages[-5:]:
                    context_parts.append(f"{msg['role']}: {msg['content'][:200]}...")
        
        # User preferences
        prefs = self.preferences.get_all_preferences()
        if prefs:
            context_parts.append("\n## User Preferences")
            for k, v in list(prefs.items())[:5]:
                context_parts.append(f"- {k}: {v}")
        
        # Top wallets they track
        top_wallets = self.wallet_profiles.get_top_performers(5)
        if top_wallets:
            context_parts.append("\n## Tracked Performers")
            for w in top_wallets:
                name = w.get("nickname") or w["address"][:10]
                context_parts.append(f"- {name}: ${w.get('pnl', 0):,.0f} P&L")
        
        # Recent facts
        facts = self.facts.get_facts(5)
        if facts:
            context_parts.append("\n## Learned Facts")
            for f in facts:
                context_parts.append(f"- {f['fact']}")
        
        # Strategies
        strategies = self.facts.get_strategies()[:3]
        if strategies:
            context_parts.append("\n## Known Strategies")
            for s in strategies:
                context_parts.append(f"- {s['name']}: {s['description'][:100]}")
        
        return "\n".join(context_parts)
    
    def search(self, query: str) -> Dict:
        """Search across all memory stores"""
        return {
            "wallets": self.entities.search_wallets(query),
            "facts": self.facts.search_facts(query),
        }
    
    def get_stats(self) -> Dict:
        """Get memory statistics"""
        return {
            "sessions": len(self.conversations.list_sessions()),
            "wallets_known": len(self.entities._data.get("wallets", {})),
            "markets_known": len(self.entities._data.get("markets", {})),
            "facts_stored": len(self.facts._data.get("facts", [])),
            "strategies_stored": len(self.facts._data.get("strategies", [])),
            "preferences_set": len(self.preferences._data.get("settings", {})),
        }


# Singleton instance
_memory = None

def get_memory() -> AgentMemory:
    """Get the global memory instance"""
    global _memory
    if _memory is None:
        _memory = AgentMemory()
    return _memory
