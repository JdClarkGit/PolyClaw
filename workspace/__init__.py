"""
PolyClaw Workspace

A scratchpad/workspace for the AI agent to read/write files,
store analysis results, and manage data.

Similar to OpenClaw's file workspace capability.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

WORKSPACE_DIR = Path.home() / ".polyclaw" / "workspace"
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)


class Workspace:
    """
    Agent workspace for file operations and data storage.
    
    The AI can use this to:
    - Save analysis results
    - Store research notes
    - Keep track of market data
    - Maintain a portfolio view
    """
    
    def __init__(self, name: str = "default"):
        self.name = name
        self.root = WORKSPACE_DIR / name
        self.root.mkdir(parents=True, exist_ok=True)
        
        # Standard directories
        (self.root / "analyses").mkdir(exist_ok=True)
        (self.root / "exports").mkdir(exist_ok=True)
        (self.root / "notes").mkdir(exist_ok=True)
        (self.root / "data").mkdir(exist_ok=True)
    
    def list_files(self, subdir: str = None) -> List[str]:
        """List files in workspace"""
        path = self.root / subdir if subdir else self.root
        files = []
        
        for item in path.rglob("*"):
            if item.is_file():
                files.append(str(item.relative_to(self.root)))
        
        return sorted(files)
    
    def read_file(self, filename: str) -> Optional[str]:
        """Read a file from workspace"""
        filepath = self.root / filename
        
        if not filepath.exists():
            return None
        
        return filepath.read_text()
    
    def write_file(self, filename: str, content: str) -> bool:
        """Write a file to workspace"""
        filepath = self.root / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content)
        return True
    
    def delete_file(self, filename: str) -> bool:
        """Delete a file from workspace"""
        filepath = self.root / filename
        
        if filepath.exists():
            filepath.unlink()
            return True
        return False
    
    def save_json(self, filename: str, data: Any) -> bool:
        """Save JSON data"""
        content = json.dumps(data, indent=2, default=str)
        return self.write_file(filename, content)
    
    def load_json(self, filename: str) -> Optional[Any]:
        """Load JSON data"""
        content = self.read_file(filename)
        if content:
            return json.loads(content)
        return None
    
    # ============================================================
    # SPECIALIZED STORAGE
    # ============================================================
    
    def save_analysis(self, wallet: str, analysis: Dict) -> str:
        """Save a wallet analysis"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_wallet = wallet[:8]
        filename = f"analyses/{short_wallet}_{timestamp}.json"
        
        analysis["_meta"] = {
            "wallet": wallet,
            "saved_at": datetime.now().isoformat(),
        }
        
        self.save_json(filename, analysis)
        return filename
    
    def get_recent_analyses(self, limit: int = 10) -> List[Dict]:
        """Get recent analyses"""
        analyses = []
        
        for filepath in (self.root / "analyses").glob("*.json"):
            try:
                data = json.loads(filepath.read_text())
                data["_filename"] = filepath.name
                analyses.append(data)
            except:
                continue
        
        # Sort by save time
        analyses.sort(
            key=lambda x: x.get("_meta", {}).get("saved_at", ""),
            reverse=True
        )
        
        return analyses[:limit]
    
    def add_note(self, title: str, content: str, tags: List[str] = None) -> str:
        """Add a research note"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c if c.isalnum() else "_" for c in title)[:30]
        filename = f"notes/{safe_title}_{timestamp}.md"
        
        note = f"""# {title}

*Created: {datetime.now().isoformat()}*

"""
        if tags:
            note += f"Tags: {', '.join(tags)}\n\n"
        
        note += content
        
        self.write_file(filename, note)
        return filename
    
    def search_notes(self, query: str) -> List[Dict]:
        """Search notes by content"""
        results = []
        query = query.lower()
        
        for filepath in (self.root / "notes").glob("*.md"):
            content = filepath.read_text()
            if query in content.lower():
                results.append({
                    "filename": filepath.name,
                    "preview": content[:200] + "..." if len(content) > 200 else content,
                })
        
        return results
    
    def save_market_data(self, market_id: str, data: Dict) -> str:
        """Save market data snapshot"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/market_{market_id}_{timestamp}.json"
        
        data["_meta"] = {
            "market_id": market_id,
            "captured_at": datetime.now().isoformat(),
        }
        
        self.save_json(filename, data)
        return filename
    
    def save_export(self, name: str, content: str, format: str = "csv") -> str:
        """Save an export file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"exports/{name}_{timestamp}.{format}"
        self.write_file(filename, content)
        return filename
    
    def get_stats(self) -> Dict:
        """Get workspace statistics"""
        def count_files(subdir: str) -> int:
            path = self.root / subdir
            if path.exists():
                return len(list(path.glob("*")))
            return 0
        
        def dir_size(subdir: str) -> int:
            path = self.root / subdir
            if path.exists():
                return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            return 0
        
        return {
            "name": self.name,
            "root": str(self.root),
            "analyses_count": count_files("analyses"),
            "notes_count": count_files("notes"),
            "exports_count": count_files("exports"),
            "data_count": count_files("data"),
            "total_size_bytes": dir_size("."),
        }


class Portfolio:
    """
    Track a paper portfolio for strategy testing.
    """
    
    def __init__(self, workspace: Workspace = None):
        self.workspace = workspace or get_workspace()
        self.portfolio_file = "data/portfolio.json"
        self._data = self._load()
    
    def _load(self) -> Dict:
        data = self.workspace.load_json(self.portfolio_file)
        if not data:
            data = {
                "cash": 10000.0,
                "positions": {},
                "history": [],
                "created_at": datetime.now().isoformat(),
            }
            self.workspace.save_json(self.portfolio_file, data)
        return data
    
    def _save(self):
        self.workspace.save_json(self.portfolio_file, self._data)
    
    @property
    def cash(self) -> float:
        return self._data.get("cash", 0)
    
    @property
    def positions(self) -> Dict:
        return self._data.get("positions", {})
    
    def deposit(self, amount: float) -> float:
        """Add cash to portfolio"""
        self._data["cash"] += amount
        self._data["history"].append({
            "type": "deposit",
            "amount": amount,
            "timestamp": datetime.now().isoformat(),
        })
        self._save()
        return self._data["cash"]
    
    def withdraw(self, amount: float) -> float:
        """Remove cash from portfolio"""
        if amount > self._data["cash"]:
            raise ValueError("Insufficient funds")
        
        self._data["cash"] -= amount
        self._data["history"].append({
            "type": "withdraw",
            "amount": amount,
            "timestamp": datetime.now().isoformat(),
        })
        self._save()
        return self._data["cash"]
    
    def buy(self, market_id: str, outcome: str, amount: float, price: float) -> Dict:
        """Buy a position"""
        cost = amount * price
        
        if cost > self._data["cash"]:
            raise ValueError(f"Insufficient funds: need ${cost:.2f}, have ${self._data['cash']:.2f}")
        
        position_key = f"{market_id}:{outcome}"
        
        if position_key not in self._data["positions"]:
            self._data["positions"][position_key] = {
                "market_id": market_id,
                "outcome": outcome,
                "shares": 0,
                "avg_cost": 0,
            }
        
        pos = self._data["positions"][position_key]
        total_cost = (pos["shares"] * pos["avg_cost"]) + cost
        pos["shares"] += amount
        pos["avg_cost"] = total_cost / pos["shares"] if pos["shares"] > 0 else 0
        
        self._data["cash"] -= cost
        
        trade = {
            "type": "buy",
            "market_id": market_id,
            "outcome": outcome,
            "shares": amount,
            "price": price,
            "cost": cost,
            "timestamp": datetime.now().isoformat(),
        }
        self._data["history"].append(trade)
        self._save()
        
        return trade
    
    def sell(self, market_id: str, outcome: str, amount: float, price: float) -> Dict:
        """Sell a position"""
        position_key = f"{market_id}:{outcome}"
        
        if position_key not in self._data["positions"]:
            raise ValueError(f"No position in {market_id}:{outcome}")
        
        pos = self._data["positions"][position_key]
        
        if amount > pos["shares"]:
            raise ValueError(f"Insufficient shares: have {pos['shares']}, selling {amount}")
        
        proceeds = amount * price
        cost_basis = amount * pos["avg_cost"]
        pnl = proceeds - cost_basis
        
        pos["shares"] -= amount
        if pos["shares"] == 0:
            del self._data["positions"][position_key]
        
        self._data["cash"] += proceeds
        
        trade = {
            "type": "sell",
            "market_id": market_id,
            "outcome": outcome,
            "shares": amount,
            "price": price,
            "proceeds": proceeds,
            "pnl": pnl,
            "timestamp": datetime.now().isoformat(),
        }
        self._data["history"].append(trade)
        self._save()
        
        return trade
    
    def get_value(self, current_prices: Dict[str, float] = None) -> Dict:
        """Calculate portfolio value"""
        current_prices = current_prices or {}
        
        positions_value = 0
        for key, pos in self._data["positions"].items():
            price = current_prices.get(key, pos["avg_cost"])  # Use avg cost if no current price
            positions_value += pos["shares"] * price
        
        total_value = self._data["cash"] + positions_value
        
        # Calculate cost basis
        cost_basis = sum(
            pos["shares"] * pos["avg_cost"]
            for pos in self._data["positions"].values()
        )
        
        return {
            "cash": self._data["cash"],
            "positions_value": positions_value,
            "total_value": total_value,
            "cost_basis": cost_basis,
            "unrealized_pnl": positions_value - cost_basis,
        }
    
    def get_history(self, limit: int = 50) -> List[Dict]:
        """Get trade history"""
        return self._data.get("history", [])[-limit:]
    
    def reset(self, starting_cash: float = 10000.0):
        """Reset portfolio"""
        self._data = {
            "cash": starting_cash,
            "positions": {},
            "history": [{
                "type": "reset",
                "starting_cash": starting_cash,
                "timestamp": datetime.now().isoformat(),
            }],
            "created_at": datetime.now().isoformat(),
        }
        self._save()


# Singleton
_workspace = None


def get_workspace(name: str = "default") -> Workspace:
    global _workspace
    if _workspace is None or _workspace.name != name:
        _workspace = Workspace(name)
    return _workspace
