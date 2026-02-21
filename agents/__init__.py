"""
PolyClaw Multi-Agent System

Different AI agent profiles/personalities for specialized tasks.
Similar to OpenClaw's agent configuration system.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

AGENTS_DIR = Path.home() / ".polyclaw" / "agents"
AGENTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# BUILT-IN AGENT PROFILES
# ============================================================

BUILT_IN_AGENTS = {
    "polyclaw": {
        "id": "polyclaw",
        "name": "PolyClaw",
        "emoji": "🦞",
        "description": "The main PolyClaw agent - your prediction market expert",
        "personality": """You are PolyClaw, an expert AI assistant for prediction market trading.

Your expertise includes:
- Polymarket, Kalshi, and other prediction platforms
- Trading strategies (momentum, mean reversion, value, arbitrage)
- Risk management and position sizing (Kelly criterion)
- Quantitative analysis (Sharpe ratio, drawdown, profit factor)
- Whale tracking and copy trading

You are sharp, analytical, data-driven, and slightly witty. You always back up claims with data.
End substantive analyses with 🦞""",
        "model": "anthropic/claude-opus-4-5",
        "temperature": 0.7,
        "tools": ["all"],
        "builtin": True,
    },
    
    "analyst": {
        "id": "analyst",
        "name": "Quant Analyst",
        "emoji": "📊",
        "description": "Pure quantitative analysis, no opinions",
        "personality": """You are a quantitative analyst focused purely on data and statistics.

Your role:
- Provide numerical analysis without speculation
- Calculate exact metrics and probabilities
- Present data in structured formats
- Never give trading advice, only analysis

You communicate in a precise, technical manner. You use numbers, not adjectives.""",
        "model": "anthropic/claude-opus-4-5",
        "temperature": 0.3,
        "tools": ["wallet_analysis", "compare_wallets", "kelly_criterion", "sharpe_ratio", "drawdown"],
        "builtin": True,
    },
    
    "scout": {
        "id": "scout",
        "name": "Market Scout",
        "emoji": "🔍",
        "description": "Finds opportunities and tracks market movements",
        "personality": """You are a market scout constantly looking for trading opportunities.

Your focus:
- Scan markets for momentum, value, and arbitrage
- Alert on unusual activity
- Track whale movements
- Identify upcoming catalysts

You're always hunting for alpha. You communicate with urgency when opportunities arise.""",
        "model": "anthropic/claude-opus-4-5",
        "temperature": 0.5,
        "tools": ["polymarket_markets", "polymarket_price", "scan_momentum", "scan_value", "leaderboard"],
        "builtin": True,
    },
    
    "risk_manager": {
        "id": "risk_manager",
        "name": "Risk Manager",
        "emoji": "⚠️",
        "description": "Focuses on risk management and capital preservation",
        "personality": """You are a conservative risk manager focused on capital preservation.

Your principles:
- Never risk more than you can afford to lose
- Position sizing is crucial
- Diversification reduces risk
- Drawdown limits must be respected

You're cautious and often push back on risky ideas. You'd rather miss gains than suffer losses.
Your job is to keep the portfolio safe.""",
        "model": "anthropic/claude-opus-4-5",
        "temperature": 0.4,
        "tools": ["kelly_criterion", "drawdown", "expected_value"],
        "builtin": True,
    },
    
    "teacher": {
        "id": "teacher",
        "name": "Trading Teacher",
        "emoji": "📚",
        "description": "Explains concepts and teaches prediction market trading",
        "personality": """You are a patient trading teacher who explains prediction market concepts.

Your approach:
- Start with fundamentals
- Use simple examples
- Build up to complex ideas
- Never assume knowledge
- Encourage questions

You're enthusiastic about helping people learn and never make them feel dumb for asking.""",
        "model": "anthropic/claude-opus-4-5",
        "temperature": 0.8,
        "tools": ["all"],
        "builtin": True,
    },
}


class AgentProfile:
    """An AI agent profile with personality and capabilities"""
    
    def __init__(
        self,
        id: str,
        name: str,
        emoji: str,
        description: str,
        personality: str,
        model: str = "anthropic/claude-opus-4-5",
        temperature: float = 0.7,
        tools: List[str] = None,
        builtin: bool = False,
    ):
        self.id = id
        self.name = name
        self.emoji = emoji
        self.description = description
        self.personality = personality
        self.model = model
        self.temperature = temperature
        self.tools = tools or ["all"]
        self.builtin = builtin
        self.created_at = datetime.now()
    
    def get_system_prompt(self) -> str:
        """Get the full system prompt for this agent"""
        return self.personality
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "emoji": self.emoji,
            "description": self.description,
            "personality": self.personality,
            "model": self.model,
            "temperature": self.temperature,
            "tools": self.tools,
            "builtin": self.builtin,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "AgentProfile":
        return cls(**{k: v for k, v in data.items() if k != "created_at"})


class AgentManager:
    """Manage agent profiles"""
    
    def __init__(self):
        self.config_file = AGENTS_DIR / "agents.json"
        self._agents = self._load()
        self._current_agent = "polyclaw"
    
    def _load(self) -> Dict[str, AgentProfile]:
        """Load agents from config"""
        agents = {}
        
        # Load built-in agents
        for agent_id, data in BUILT_IN_AGENTS.items():
            agents[agent_id] = AgentProfile(**data)
        
        # Load custom agents
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    custom = json.load(f)
                for agent_id, data in custom.get("agents", {}).items():
                    if agent_id not in BUILT_IN_AGENTS:
                        agents[agent_id] = AgentProfile.from_dict(data)
            except:
                pass
        
        return agents
    
    def _save(self):
        """Save custom agents"""
        custom = {
            "agents": {
                agent_id: agent.to_dict()
                for agent_id, agent in self._agents.items()
                if not agent.builtin
            }
        }
        with open(self.config_file, 'w') as f:
            json.dump(custom, f, indent=2)
    
    def list_agents(self) -> List[Dict]:
        """List all available agents"""
        return [
            {
                "id": agent.id,
                "name": agent.name,
                "emoji": agent.emoji,
                "description": agent.description,
                "model": agent.model,
                "builtin": agent.builtin,
            }
            for agent in self._agents.values()
        ]
    
    def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
        """Get an agent by ID"""
        return self._agents.get(agent_id)
    
    def get_current_agent(self) -> AgentProfile:
        """Get the currently active agent"""
        return self._agents.get(self._current_agent, self._agents["polyclaw"])
    
    def set_current_agent(self, agent_id: str) -> bool:
        """Set the active agent"""
        if agent_id in self._agents:
            self._current_agent = agent_id
            return True
        return False
    
    def create_agent(
        self,
        id: str,
        name: str,
        emoji: str,
        description: str,
        personality: str,
        model: str = "anthropic/claude-opus-4-5",
        temperature: float = 0.7,
        tools: List[str] = None,
    ) -> AgentProfile:
        """Create a custom agent"""
        if id in BUILT_IN_AGENTS:
            raise ValueError(f"Cannot overwrite built-in agent: {id}")
        
        agent = AgentProfile(
            id=id,
            name=name,
            emoji=emoji,
            description=description,
            personality=personality,
            model=model,
            temperature=temperature,
            tools=tools or ["all"],
            builtin=False,
        )
        
        self._agents[id] = agent
        self._save()
        
        return agent
    
    def delete_agent(self, agent_id: str) -> bool:
        """Delete a custom agent"""
        if agent_id in BUILT_IN_AGENTS:
            raise ValueError(f"Cannot delete built-in agent: {agent_id}")
        
        if agent_id in self._agents:
            del self._agents[agent_id]
            self._save()
            return True
        return False
    
    def update_agent(self, agent_id: str, updates: Dict) -> Optional[AgentProfile]:
        """Update an agent's configuration"""
        if agent_id in BUILT_IN_AGENTS:
            raise ValueError(f"Cannot modify built-in agent: {agent_id}")
        
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        
        for key, value in updates.items():
            if hasattr(agent, key):
                setattr(agent, key, value)
        
        self._save()
        return agent


# Singleton
_manager = None


def get_agent_manager() -> AgentManager:
    global _manager
    if _manager is None:
        _manager = AgentManager()
    return _manager


def get_current_agent() -> AgentProfile:
    """Get the currently active agent"""
    return get_agent_manager().get_current_agent()
