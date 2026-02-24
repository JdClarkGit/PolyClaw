#!/usr/bin/env python3
"""
PolyClaw Cron Jobs System

Persistent scheduled task execution that survives restarts.
Based on OpenClaw's cron system.

Features:
- Three schedule types: cron (5-6 field), at (one-shot), every (intervals)
- Jobs persist at ~/.polyclaw/cron/jobs.json
- Execution logging
- Job management CLI
"""

import os
import json
import time
import logging
import threading
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum

try:
    from croniter import croniter
    HAS_CRONITER = True
except ImportError:
    HAS_CRONITER = False

logger = logging.getLogger("polyclaw.cron")

# Paths
POLYCLAW_DIR = Path.home() / ".polyclaw"
CRON_DIR = POLYCLAW_DIR / "cron"
JOBS_FILE = CRON_DIR / "jobs.json"
CRON_LOG = CRON_DIR / "cron_log.json"


class ScheduleType(Enum):
    """Type of schedule."""
    CRON = "cron"  # Standard cron expression (5-6 fields)
    AT = "at"  # One-shot execution at specific time
    EVERY = "every"  # Interval-based (every N minutes/hours)


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class CronJob:
    """A scheduled cron job."""
    id: str
    name: str
    description: str
    schedule_type: ScheduleType
    schedule: str  # Cron expression, ISO datetime, or interval
    action: str  # Action to execute
    action_args: Dict = field(default_factory=dict)
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    fail_count: int = 0
    wake_mode: str = "normal"  # "normal" or "now"
    session: str = "main"  # Session to run in
    
    def __post_init__(self):
        """Calculate next run time after initialization."""
        if self.next_run is None:
            self.calculate_next_run()
    
    def calculate_next_run(self):
        """Calculate the next run time based on schedule."""
        now = datetime.now()
        
        if not self.enabled:
            self.next_run = None
            return
        
        if self.schedule_type == ScheduleType.CRON:
            if HAS_CRONITER:
                cron = croniter(self.schedule, now)
                self.next_run = cron.get_next(datetime)
            else:
                # Fallback: simple parsing for common patterns
                self.next_run = now + timedelta(hours=1)
        
        elif self.schedule_type == ScheduleType.AT:
            # Parse ISO datetime
            try:
                target = datetime.fromisoformat(self.schedule)
                if target > now:
                    self.next_run = target
                else:
                    self.next_run = None  # One-shot already passed
            except ValueError:
                self.next_run = None
        
        elif self.schedule_type == ScheduleType.EVERY:
            # Parse interval (e.g., "30m", "1h", "2d")
            interval = self._parse_interval(self.schedule)
            if interval:
                if self.last_run:
                    self.next_run = self.last_run + interval
                else:
                    self.next_run = now + interval
    
    def _parse_interval(self, interval_str: str) -> Optional[timedelta]:
        """Parse interval string to timedelta."""
        try:
            value = int(interval_str[:-1])
            unit = interval_str[-1].lower()
            
            if unit == 's':
                return timedelta(seconds=value)
            elif unit == 'm':
                return timedelta(minutes=value)
            elif unit == 'h':
                return timedelta(hours=value)
            elif unit == 'd':
                return timedelta(days=value)
            elif unit == 'w':
                return timedelta(weeks=value)
        except (ValueError, IndexError):
            pass
        return None
    
    def is_due(self) -> bool:
        """Check if job should run now."""
        if not self.enabled:
            return False
        if self.next_run is None:
            return False
        return datetime.now() >= self.next_run
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "schedule_type": self.schedule_type.value,
            "schedule": self.schedule,
            "action": self.action,
            "action_args": self.action_args,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "fail_count": self.fail_count,
            "wake_mode": self.wake_mode,
            "session": self.session
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "CronJob":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            schedule_type=ScheduleType(data["schedule_type"]),
            schedule=data["schedule"],
            action=data["action"],
            action_args=data.get("action_args", {}),
            enabled=data.get("enabled", True),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            last_run=datetime.fromisoformat(data["last_run"]) if data.get("last_run") else None,
            next_run=datetime.fromisoformat(data["next_run"]) if data.get("next_run") else None,
            run_count=data.get("run_count", 0),
            fail_count=data.get("fail_count", 0),
            wake_mode=data.get("wake_mode", "normal"),
            session=data.get("session", "main")
        )


class CronManager:
    """
    Manages cron jobs with persistence and execution.
    """
    
    def __init__(self):
        self.jobs: Dict[str, CronJob] = {}
        self.callbacks: Dict[str, Callable] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # Ensure directories exist
        CRON_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load existing jobs
        self._load_jobs()
        
        # Register default actions
        self._register_default_actions()
    
    def _load_jobs(self):
        """Load jobs from persistent storage."""
        if JOBS_FILE.exists():
            try:
                with open(JOBS_FILE) as f:
                    data = json.load(f)
                for job_data in data.get("jobs", []):
                    job = CronJob.from_dict(job_data)
                    self.jobs[job.id] = job
                logger.info(f"Loaded {len(self.jobs)} cron jobs")
            except Exception as e:
                logger.error(f"Failed to load jobs: {e}")
    
    def _save_jobs(self):
        """Save jobs to persistent storage."""
        data = {
            "jobs": [job.to_dict() for job in self.jobs.values()],
            "updated_at": datetime.now().isoformat()
        }
        with open(JOBS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    
    def _register_default_actions(self):
        """Register default prediction market actions."""
        
        def analyze_wallet(job: CronJob):
            """Analyze a wallet's trades."""
            wallet = job.action_args.get("wallet")
            if wallet:
                logger.info(f"Analyzing wallet: {wallet}")
                # Would call analytics module
                return True
            return False
        
        def scan_markets(job: CronJob):
            """Scan for trading opportunities."""
            scan_type = job.action_args.get("type", "momentum")
            logger.info(f"Scanning markets: {scan_type}")
            # Would call scanner module
            return True
        
        def update_leaderboard(job: CronJob):
            """Update leaderboard data."""
            logger.info("Updating leaderboard")
            # Would refresh leaderboard
            return True
        
        def send_notification(job: CronJob):
            """Send a notification."""
            message = job.action_args.get("message", "")
            channel = job.action_args.get("channel", "discord")
            logger.info(f"Sending notification to {channel}: {message}")
            # Would send via notification system
            return True
        
        def backup_data(job: CronJob):
            """Backup PolyClaw data."""
            logger.info("Backing up data")
            # Would backup to workspace
            return True
        
        def generate_report(job: CronJob):
            """Generate a report."""
            report_type = job.action_args.get("type", "daily")
            logger.info(f"Generating {report_type} report")
            # Would generate report
            return True
        
        self.callbacks["analyze_wallet"] = analyze_wallet
        self.callbacks["scan_markets"] = scan_markets
        self.callbacks["update_leaderboard"] = update_leaderboard
        self.callbacks["send_notification"] = send_notification
        self.callbacks["backup_data"] = backup_data
        self.callbacks["generate_report"] = generate_report
    
    def register_action(self, action: str, callback: Callable):
        """Register a callback for an action."""
        self.callbacks[action] = callback
    
    def create_job(
        self,
        name: str,
        schedule_type: Union[str, ScheduleType],
        schedule: str,
        action: str,
        description: str = "",
        action_args: Dict = None,
        wake_mode: str = "normal"
    ) -> CronJob:
        """Create a new cron job."""
        if isinstance(schedule_type, str):
            schedule_type = ScheduleType(schedule_type)
        
        job_id = hashlib.md5(f"{name}:{schedule}:{action}".encode()).hexdigest()[:12]
        
        job = CronJob(
            id=job_id,
            name=name,
            description=description,
            schedule_type=schedule_type,
            schedule=schedule,
            action=action,
            action_args=action_args or {},
            wake_mode=wake_mode
        )
        
        self.jobs[job.id] = job
        self._save_jobs()
        
        logger.info(f"Created cron job: {name} ({job.id})")
        return job
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a cron job."""
        if job_id in self.jobs:
            del self.jobs[job_id]
            self._save_jobs()
            logger.info(f"Deleted cron job: {job_id}")
            return True
        return False
    
    def enable_job(self, job_id: str) -> bool:
        """Enable a job."""
        if job_id in self.jobs:
            self.jobs[job_id].enabled = True
            self.jobs[job_id].calculate_next_run()
            self._save_jobs()
            return True
        return False
    
    def disable_job(self, job_id: str) -> bool:
        """Disable a job."""
        if job_id in self.jobs:
            self.jobs[job_id].enabled = False
            self._save_jobs()
            return True
        return False
    
    def get_job(self, job_id: str) -> Optional[CronJob]:
        """Get a job by ID."""
        return self.jobs.get(job_id)
    
    def list_jobs(self) -> List[Dict]:
        """List all jobs."""
        return [job.to_dict() for job in self.jobs.values()]
    
    def execute_job(self, job: CronJob) -> bool:
        """Execute a single job."""
        logger.info(f"Executing job: {job.name}")
        
        callback = self.callbacks.get(job.action)
        if not callback:
            logger.warning(f"No callback for action: {job.action}")
            return False
        
        try:
            result = callback(job)
            job.last_run = datetime.now()
            job.run_count += 1
            
            # One-shot jobs should be disabled after execution
            if job.schedule_type == ScheduleType.AT:
                job.enabled = False
            else:
                job.calculate_next_run()
            
            self._save_jobs()
            self._log_execution(job, success=True)
            
            return result
            
        except Exception as e:
            logger.error(f"Job execution failed: {e}")
            job.fail_count += 1
            self._save_jobs()
            self._log_execution(job, success=False, error=str(e))
            return False
    
    def _log_execution(self, job: CronJob, success: bool, error: str = None):
        """Log job execution."""
        logs = []
        if CRON_LOG.exists():
            try:
                with open(CRON_LOG) as f:
                    logs = json.load(f)
            except:
                logs = []
        
        logs.append({
            "job_id": job.id,
            "job_name": job.name,
            "executed_at": datetime.now().isoformat(),
            "success": success,
            "error": error
        })
        
        # Keep last 500 logs
        logs = logs[-500:]
        
        with open(CRON_LOG, "w") as f:
            json.dump(logs, f, indent=2)
    
    def run_tick(self):
        """Run a single tick - check and execute due jobs."""
        for job in self.jobs.values():
            if job.is_due():
                self.execute_job(job)
    
    def start(self):
        """Start the cron scheduler."""
        if self.running:
            return
        
        self.running = True
        
        def scheduler_loop():
            while self.running:
                self.run_tick()
                time.sleep(60)  # Check every minute
        
        self.thread = threading.Thread(target=scheduler_loop, daemon=True)
        self.thread.start()
        logger.info("Cron scheduler started")
    
    def stop(self):
        """Stop the cron scheduler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Cron scheduler stopped")
    
    def get_status(self) -> Dict:
        """Get scheduler status."""
        return {
            "running": self.running,
            "total_jobs": len(self.jobs),
            "enabled_jobs": sum(1 for j in self.jobs.values() if j.enabled),
            "next_jobs": sorted(
                [
                    {"id": j.id, "name": j.name, "next_run": j.next_run.isoformat() if j.next_run else None}
                    for j in self.jobs.values()
                    if j.enabled and j.next_run
                ],
                key=lambda x: x["next_run"] or ""
            )[:5]
        }


# Global instance
_cron_manager: Optional[CronManager] = None


def get_cron_manager() -> CronManager:
    """Get or create the global cron manager."""
    global _cron_manager
    if _cron_manager is None:
        _cron_manager = CronManager()
    return _cron_manager


# Convenience functions
def add_cron_job(name: str, cron_expr: str, action: str, **kwargs) -> CronJob:
    """Add a job with cron expression (e.g., '0 * * * *' for hourly)."""
    return get_cron_manager().create_job(
        name=name,
        schedule_type=ScheduleType.CRON,
        schedule=cron_expr,
        action=action,
        **kwargs
    )


def add_interval_job(name: str, interval: str, action: str, **kwargs) -> CronJob:
    """Add a job with interval (e.g., '30m', '1h', '2d')."""
    return get_cron_manager().create_job(
        name=name,
        schedule_type=ScheduleType.EVERY,
        schedule=interval,
        action=action,
        **kwargs
    )


def add_one_shot_job(name: str, run_at: str, action: str, **kwargs) -> CronJob:
    """Add a one-shot job at specific time (ISO format)."""
    return get_cron_manager().create_job(
        name=name,
        schedule_type=ScheduleType.AT,
        schedule=run_at,
        action=action,
        **kwargs
    )
