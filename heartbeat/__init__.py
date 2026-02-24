#!/usr/bin/env python3
"""
PolyClaw Heartbeat System

The Heartbeat transforms PolyClaw from a reactive tool into a proactive autonomous agent.
Every N minutes, the system wakes up, reads HEARTBEAT.md, and executes defined tasks.

Inspired by OpenClaw's heartbeat system.
"""

import os
import json
import time
import logging
import threading
import schedule
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger("polyclaw.heartbeat")

# Default paths
POLYCLAW_DIR = Path.home() / ".polyclaw"
HEARTBEAT_FILE = POLYCLAW_DIR / "HEARTBEAT.md"
HEARTBEAT_CONFIG = POLYCLAW_DIR / "heartbeat_config.json"
HEARTBEAT_LOG = POLYCLAW_DIR / "heartbeat_log.json"


class TaskFrequency(Enum):
    """Task execution frequency."""
    CONTINUOUS = "continuous"  # Every heartbeat
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"  # Cron expression


class HeartbeatResponse(Enum):
    """Possible heartbeat responses."""
    OK = "HEARTBEAT_OK"  # Nothing to do
    ACTION = "ACTION_TAKEN"  # Executed a task
    ALERT = "ALERT_SENT"  # Sent notification
    ERROR = "ERROR"  # Task failed


@dataclass
class HeartbeatTask:
    """A single heartbeat task."""
    id: str
    description: str
    frequency: TaskFrequency
    action: str  # The action to perform
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True
    category: str = "general"
    cron_expression: Optional[str] = None  # For custom frequency
    
    def should_run(self) -> bool:
        """Check if task should run based on frequency."""
        if not self.enabled:
            return False
        
        now = datetime.now()
        
        if self.frequency == TaskFrequency.CONTINUOUS:
            return True
        
        if self.last_run is None:
            return True
        
        elapsed = now - self.last_run
        
        if self.frequency == TaskFrequency.HOURLY:
            return elapsed >= timedelta(hours=1)
        elif self.frequency == TaskFrequency.DAILY:
            return elapsed >= timedelta(days=1)
        elif self.frequency == TaskFrequency.WEEKLY:
            return elapsed >= timedelta(weeks=1)
        
        return False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "frequency": self.frequency.value,
            "action": self.action,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "enabled": self.enabled,
            "category": self.category,
            "cron_expression": self.cron_expression
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "HeartbeatTask":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            description=data["description"],
            frequency=TaskFrequency(data.get("frequency", "continuous")),
            action=data["action"],
            last_run=datetime.fromisoformat(data["last_run"]) if data.get("last_run") else None,
            next_run=datetime.fromisoformat(data["next_run"]) if data.get("next_run") else None,
            enabled=data.get("enabled", True),
            category=data.get("category", "general"),
            cron_expression=data.get("cron_expression")
        )


@dataclass
class HeartbeatConfig:
    """Heartbeat configuration."""
    enabled: bool = True
    interval: int = 1800  # 30 minutes in seconds
    model: str = "gpt-4o-mini"  # Use cheap model for heartbeat
    max_tokens: int = 1024
    quiet_hours_start: str = "23:00"
    quiet_hours_end: str = "07:00"
    timezone: str = "UTC"
    notify_channels: List[str] = field(default_factory=lambda: ["discord", "telegram"])
    
    def is_quiet_hours(self) -> bool:
        """Check if currently in quiet hours."""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        start = self.quiet_hours_start
        end = self.quiet_hours_end
        
        # Handle overnight quiet hours (e.g., 23:00 - 07:00)
        if start > end:
            return current_time >= start or current_time < end
        else:
            return start <= current_time < end
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "HeartbeatConfig":
        return cls(**data)


class HeartbeatEngine:
    """
    The Heartbeat Engine - PolyClaw's autonomous task scheduler.
    
    This is what makes PolyClaw proactive like OpenClaw.
    """
    
    def __init__(self):
        self.config = self._load_config()
        self.tasks: List[HeartbeatTask] = []
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.callbacks: Dict[str, Callable] = {}
        self.last_heartbeat: Optional[datetime] = None
        self.heartbeat_count = 0
        
        # Ensure directories exist
        POLYCLAW_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create default HEARTBEAT.md if not exists
        if not HEARTBEAT_FILE.exists():
            self._create_default_heartbeat_file()
        
        # Load tasks from HEARTBEAT.md
        self._parse_heartbeat_file()
    
    def _load_config(self) -> HeartbeatConfig:
        """Load configuration from file."""
        if HEARTBEAT_CONFIG.exists():
            try:
                with open(HEARTBEAT_CONFIG) as f:
                    return HeartbeatConfig.from_dict(json.load(f))
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        return HeartbeatConfig()
    
    def _save_config(self):
        """Save configuration to file."""
        with open(HEARTBEAT_CONFIG, "w") as f:
            json.dump(self.config.to_dict(), f, indent=2)
    
    def _create_default_heartbeat_file(self):
        """Create default HEARTBEAT.md with prediction market tasks."""
        default_content = """# PolyClaw Heartbeat Tasks

## Continuous (every heartbeat)
- Check tracked wallets for new trades
- Monitor whale activity on Polymarket
- Check for significant price movements (>5%)

## Hourly
- Scan for new high-volume markets
- Check leaderboard for position changes
- Update market momentum indicators

## Daily (morning)
- Generate daily market summary
- Check for markets closing today
- Review portfolio P&L

## Weekly (Monday)
- Generate weekly performance report
- Analyze top performing strategies
- Clean up old trade cache data

---

## Task Configuration

### Wallet Monitoring
- wallets: [] # Add wallet addresses to track
- threshold: 100 # Minimum trade size to alert (USDC)

### Price Alerts
- markets: [] # Add market slugs to watch
- price_change_threshold: 0.05 # 5% change

### Whale Tracking
- min_trade_size: 1000 # Minimum USDC for whale alert
- notify: true

"""
        with open(HEARTBEAT_FILE, "w") as f:
            f.write(default_content)
        logger.info(f"Created default HEARTBEAT.md at {HEARTBEAT_FILE}")
    
    def _parse_heartbeat_file(self):
        """Parse HEARTBEAT.md to extract tasks."""
        if not HEARTBEAT_FILE.exists():
            return
        
        with open(HEARTBEAT_FILE) as f:
            content = f.read()
        
        self.tasks = []
        current_frequency = None
        task_id = 0
        
        for line in content.split("\n"):
            line = line.strip()
            
            # Detect frequency headers
            if "## Continuous" in line:
                current_frequency = TaskFrequency.CONTINUOUS
            elif "## Hourly" in line:
                current_frequency = TaskFrequency.HOURLY
            elif "## Daily" in line:
                current_frequency = TaskFrequency.DAILY
            elif "## Weekly" in line:
                current_frequency = TaskFrequency.WEEKLY
            elif line.startswith("- ") and current_frequency:
                # Extract task
                task_desc = line[2:].strip()
                if task_desc and not task_desc.startswith("#"):
                    task_id += 1
                    task = HeartbeatTask(
                        id=f"task_{task_id}",
                        description=task_desc,
                        frequency=current_frequency,
                        action=self._infer_action(task_desc),
                        category=self._infer_category(task_desc)
                    )
                    self.tasks.append(task)
        
        logger.info(f"Loaded {len(self.tasks)} tasks from HEARTBEAT.md")
    
    def _infer_action(self, description: str) -> str:
        """Infer the action type from task description."""
        desc_lower = description.lower()
        
        if "wallet" in desc_lower or "track" in desc_lower:
            return "check_wallets"
        elif "whale" in desc_lower:
            return "check_whales"
        elif "price" in desc_lower or "movement" in desc_lower:
            return "check_prices"
        elif "leaderboard" in desc_lower:
            return "update_leaderboard"
        elif "market" in desc_lower and "new" in desc_lower:
            return "scan_new_markets"
        elif "summary" in desc_lower or "report" in desc_lower:
            return "generate_report"
        elif "momentum" in desc_lower:
            return "check_momentum"
        elif "portfolio" in desc_lower or "p&l" in desc_lower:
            return "check_portfolio"
        elif "closing" in desc_lower:
            return "check_closing_markets"
        elif "clean" in desc_lower:
            return "cleanup"
        else:
            return "custom"
    
    def _infer_category(self, description: str) -> str:
        """Infer task category from description."""
        desc_lower = description.lower()
        
        if any(w in desc_lower for w in ["wallet", "track", "whale"]):
            return "monitoring"
        elif any(w in desc_lower for w in ["price", "movement", "momentum"]):
            return "market_analysis"
        elif any(w in desc_lower for w in ["summary", "report"]):
            return "reporting"
        elif any(w in desc_lower for w in ["leaderboard", "ranking"]):
            return "leaderboard"
        elif any(w in desc_lower for w in ["clean", "cache"]):
            return "maintenance"
        else:
            return "general"
    
    def register_callback(self, action: str, callback: Callable):
        """Register a callback for a specific action type."""
        self.callbacks[action] = callback
        logger.info(f"Registered callback for action: {action}")
    
    def execute_task(self, task: HeartbeatTask) -> HeartbeatResponse:
        """Execute a single heartbeat task."""
        logger.info(f"Executing task: {task.description}")
        
        try:
            # Get callback for this action
            callback = self.callbacks.get(task.action)
            
            if callback:
                result = callback(task)
                task.last_run = datetime.now()
                
                if result:
                    return HeartbeatResponse.ACTION
                return HeartbeatResponse.OK
            else:
                logger.warning(f"No callback registered for action: {task.action}")
                return HeartbeatResponse.OK
                
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return HeartbeatResponse.ERROR
    
    def run_heartbeat(self, force: bool = False) -> Dict[str, Any]:
        """
        Execute a single heartbeat cycle.
        
        This is the core function that makes PolyClaw autonomous.
        """
        if not self.config.enabled and not force:
            return {"status": "disabled", "tasks_run": 0}
        
        if self.config.is_quiet_hours() and not force:
            logger.info("Skipping heartbeat - quiet hours")
            return {"status": "quiet_hours", "tasks_run": 0}
        
        logger.info("💓 Heartbeat starting...")
        self.heartbeat_count += 1
        self.last_heartbeat = datetime.now()
        
        results = {
            "status": "completed",
            "heartbeat_id": self.heartbeat_count,
            "timestamp": self.last_heartbeat.isoformat(),
            "tasks_run": 0,
            "tasks_skipped": 0,
            "errors": 0,
            "actions": []
        }
        
        for task in self.tasks:
            if task.should_run():
                response = self.execute_task(task)
                results["tasks_run"] += 1
                results["actions"].append({
                    "task_id": task.id,
                    "description": task.description,
                    "response": response.value
                })
                
                if response == HeartbeatResponse.ERROR:
                    results["errors"] += 1
            else:
                results["tasks_skipped"] += 1
        
        # Log heartbeat
        self._log_heartbeat(results)
        
        logger.info(f"💓 Heartbeat complete: {results['tasks_run']} tasks run")
        return results
    
    def _log_heartbeat(self, results: Dict):
        """Log heartbeat results to file."""
        logs = []
        if HEARTBEAT_LOG.exists():
            try:
                with open(HEARTBEAT_LOG) as f:
                    logs = json.load(f)
            except:
                logs = []
        
        logs.append(results)
        
        # Keep only last 100 heartbeats
        logs = logs[-100:]
        
        with open(HEARTBEAT_LOG, "w") as f:
            json.dump(logs, f, indent=2)
    
    def start(self):
        """Start the heartbeat scheduler."""
        if self.running:
            logger.warning("Heartbeat already running")
            return
        
        self.running = True
        
        # Schedule heartbeat at configured interval
        interval_minutes = self.config.interval // 60
        schedule.every(interval_minutes).minutes.do(self.run_heartbeat)
        
        # Run scheduler in background thread
        def run_scheduler():
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        
        self.thread = threading.Thread(target=run_scheduler, daemon=True)
        self.thread.start()
        
        logger.info(f"💓 Heartbeat started (interval: {interval_minutes} minutes)")
    
    def stop(self):
        """Stop the heartbeat scheduler."""
        self.running = False
        schedule.clear()
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("💓 Heartbeat stopped")
    
    def get_status(self) -> Dict:
        """Get heartbeat status."""
        return {
            "enabled": self.config.enabled,
            "running": self.running,
            "interval_minutes": self.config.interval // 60,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "heartbeat_count": self.heartbeat_count,
            "tasks_count": len(self.tasks),
            "quiet_hours": self.config.is_quiet_hours(),
            "quiet_hours_config": {
                "start": self.config.quiet_hours_start,
                "end": self.config.quiet_hours_end
            }
        }
    
    def list_tasks(self) -> List[Dict]:
        """List all heartbeat tasks."""
        return [task.to_dict() for task in self.tasks]
    
    def reload_tasks(self):
        """Reload tasks from HEARTBEAT.md."""
        self._parse_heartbeat_file()


# Global instance
_heartbeat_engine: Optional[HeartbeatEngine] = None


def get_heartbeat_engine() -> HeartbeatEngine:
    """Get or create the global heartbeat engine."""
    global _heartbeat_engine
    if _heartbeat_engine is None:
        _heartbeat_engine = HeartbeatEngine()
    return _heartbeat_engine


# Default task callbacks for prediction markets
def setup_default_callbacks(engine: HeartbeatEngine):
    """Set up default callbacks for prediction market tasks."""
    
    def check_wallets(task):
        """Check tracked wallets for new trades."""
        from pathlib import Path
        tracking_file = Path.home() / ".polyclaw" / "tracking.json"
        if tracking_file.exists():
            import json
            with open(tracking_file) as f:
                tracking = json.load(f)
            wallets = tracking.get("wallets", [])
            # Would trigger wallet check here
            return len(wallets) > 0
        return False
    
    def check_whales(task):
        """Check for whale activity."""
        # Placeholder - would check Polymarket API for large trades
        return False
    
    def check_prices(task):
        """Check for significant price movements."""
        # Placeholder - would check market prices
        return False
    
    def update_leaderboard(task):
        """Update leaderboard rankings."""
        # Placeholder - would refresh leaderboard data
        return False
    
    def scan_new_markets(task):
        """Scan for new markets."""
        # Placeholder - would use scanner module
        return False
    
    def generate_report(task):
        """Generate summary report."""
        # Placeholder - would generate report
        return False
    
    def check_momentum(task):
        """Check market momentum."""
        # Placeholder - would check momentum indicators
        return False
    
    def check_portfolio(task):
        """Check portfolio P&L."""
        # Placeholder - would check workspace portfolio
        return False
    
    def check_closing_markets(task):
        """Check for markets closing soon."""
        # Placeholder - would check closing markets
        return False
    
    def cleanup(task):
        """Clean up old data."""
        # Clean up old cache files
        cache_dir = Path.home() / ".polyclaw"
        return True
    
    # Register callbacks
    engine.register_callback("check_wallets", check_wallets)
    engine.register_callback("check_whales", check_whales)
    engine.register_callback("check_prices", check_prices)
    engine.register_callback("update_leaderboard", update_leaderboard)
    engine.register_callback("scan_new_markets", scan_new_markets)
    engine.register_callback("generate_report", generate_report)
    engine.register_callback("check_momentum", check_momentum)
    engine.register_callback("check_portfolio", check_portfolio)
    engine.register_callback("check_closing_markets", check_closing_markets)
    engine.register_callback("cleanup", cleanup)
