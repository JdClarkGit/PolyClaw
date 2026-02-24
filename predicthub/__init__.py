#!/usr/bin/env python3
"""
PredictHub - PolyClaw's Skill Marketplace

Community skill marketplace for prediction market trading.
Inspired by OpenClaw's ClawHub.

Features:
- Browse and search skills
- Install/uninstall skills
- Publish your own skills
- Security scanning
- Version management
"""

import os
import json
import hashlib
import requests
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger("polyclaw.predicthub")

# Paths
POLYCLAW_DIR = Path.home() / ".polyclaw"
SKILLS_DIR = POLYCLAW_DIR / "skills"
INSTALLED_SKILLS_FILE = SKILLS_DIR / "installed.json"
SKILL_CACHE = SKILLS_DIR / "cache"

# PredictHub registry URL (would be a real server in production)
PREDICTHUB_URL = "https://predicthub.polyclaw.io"  # Placeholder


class SkillCategory(Enum):
    """Skill categories."""
    TRADING = "trading"
    ANALYSIS = "analysis"
    ALERTS = "alerts"
    DATA = "data"
    AUTOMATION = "automation"
    SOCIAL = "social"
    UTILITIES = "utilities"


class SkillStatus(Enum):
    """Skill verification status."""
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FLAGGED = "flagged"
    REMOVED = "removed"


@dataclass
class Skill:
    """A PredictHub skill."""
    id: str
    name: str
    version: str
    description: str
    author: str
    category: SkillCategory
    status: SkillStatus = SkillStatus.UNVERIFIED
    downloads: int = 0
    rating: float = 0.0
    rating_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    source_url: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    readme: str = ""
    code: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "category": self.category.value,
            "status": self.status.value,
            "downloads": self.downloads,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            "source_url": self.source_url,
            "dependencies": self.dependencies,
            "permissions": self.permissions,
            "tags": self.tags,
            "readme": self.readme
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Skill":
        return cls(
            id=data["id"],
            name=data["name"],
            version=data["version"],
            description=data.get("description", ""),
            author=data.get("author", "unknown"),
            category=SkillCategory(data.get("category", "utilities")),
            status=SkillStatus(data.get("status", "unverified")),
            downloads=data.get("downloads", 0),
            rating=data.get("rating", 0.0),
            rating_count=data.get("rating_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
            source_url=data.get("source_url"),
            dependencies=data.get("dependencies", []),
            permissions=data.get("permissions", []),
            tags=data.get("tags", []),
            readme=data.get("readme", ""),
            code=data.get("code", "")
        )


# Built-in community skills (would be fetched from server)
COMMUNITY_SKILLS = [
    {
        "id": "whale-tracker-pro",
        "name": "Whale Tracker Pro",
        "version": "1.2.0",
        "description": "Advanced whale tracking with customizable alerts for large trades on Polymarket",
        "author": "polytrader",
        "category": "alerts",
        "status": "verified",
        "downloads": 1523,
        "rating": 4.8,
        "rating_count": 89,
        "tags": ["whale", "alerts", "tracking"],
        "permissions": ["notifications", "api_read"],
        "readme": """# Whale Tracker Pro

Track large trades on Polymarket in real-time.

## Features
- Customizable trade size thresholds
- Multi-wallet tracking
- Discord/Telegram notifications
- Historical whale activity

## Usage
```
polyclaw skill whale-tracker-pro --threshold 1000 --notify discord
```
"""
    },
    {
        "id": "momentum-scanner",
        "name": "Momentum Scanner",
        "version": "2.0.1",
        "description": "Scan Polymarket for momentum opportunities based on price and volume",
        "author": "quantclaw",
        "category": "analysis",
        "status": "verified",
        "downloads": 892,
        "rating": 4.5,
        "rating_count": 56,
        "tags": ["momentum", "scanner", "opportunities"],
        "permissions": ["api_read"],
        "readme": """# Momentum Scanner

Find momentum opportunities on Polymarket.

## Features
- Price momentum detection
- Volume spike alerts
- Configurable thresholds
- Market filtering

## Usage
```
polyclaw skill momentum-scanner --threshold 0.05 --volume-min 10000
```
"""
    },
    {
        "id": "portfolio-optimizer",
        "name": "Portfolio Optimizer",
        "version": "1.0.0",
        "description": "Optimize your prediction market portfolio using Kelly criterion and risk management",
        "author": "riskmaster",
        "category": "trading",
        "status": "verified",
        "downloads": 654,
        "rating": 4.7,
        "rating_count": 42,
        "tags": ["portfolio", "kelly", "risk", "optimization"],
        "permissions": ["api_read", "workspace_write"],
        "readme": """# Portfolio Optimizer

Optimize your prediction market positions.

## Features
- Kelly criterion sizing
- Risk-adjusted returns
- Correlation analysis
- Rebalancing suggestions
"""
    },
    {
        "id": "social-sentiment",
        "name": "Social Sentiment Analyzer",
        "version": "1.1.0",
        "description": "Analyze social media sentiment for prediction market events",
        "author": "sentimentai",
        "category": "analysis",
        "status": "verified",
        "downloads": 1102,
        "rating": 4.3,
        "rating_count": 78,
        "tags": ["sentiment", "social", "twitter", "reddit"],
        "permissions": ["api_read", "full_network"],
        "readme": """# Social Sentiment Analyzer

Track social sentiment for market events.

## Features
- Twitter/X sentiment tracking
- Reddit discussion analysis
- Sentiment scoring
- Historical trends
"""
    },
    {
        "id": "copy-trader",
        "name": "Copy Trader",
        "version": "1.3.0",
        "description": "Copy trades from successful Polymarket traders automatically",
        "author": "copycat",
        "category": "trading",
        "status": "verified",
        "downloads": 2341,
        "rating": 4.6,
        "rating_count": 156,
        "tags": ["copy", "trading", "automation"],
        "permissions": ["api_read", "notifications", "wallet_track"],
        "readme": """# Copy Trader

Follow and copy successful traders.

## Features
- Leaderboard integration
- Selective copying
- Risk limits
- Trade notifications
"""
    },
    {
        "id": "market-maker-lite",
        "name": "Market Maker Lite",
        "version": "0.9.0",
        "description": "Simple market making strategy for prediction markets",
        "author": "mmdev",
        "category": "trading",
        "status": "unverified",
        "downloads": 234,
        "rating": 4.0,
        "rating_count": 12,
        "tags": ["market-making", "liquidity", "strategy"],
        "permissions": ["api_read", "api_write", "wallet_access"],
        "readme": """# Market Maker Lite

Basic market making for prediction markets.

## Warning
Requires API write access. Use with caution.
"""
    },
    {
        "id": "election-tracker",
        "name": "Election Tracker",
        "version": "2.1.0",
        "description": "Specialized tracking for political prediction markets",
        "author": "politiclaw",
        "category": "data",
        "status": "verified",
        "downloads": 3421,
        "rating": 4.9,
        "rating_count": 234,
        "tags": ["politics", "elections", "tracking"],
        "permissions": ["api_read"],
        "readme": """# Election Tracker

Track political prediction markets.

## Features
- Real-time polling integration
- Historical accuracy tracking
- State-by-state breakdowns
- Alert on significant moves
"""
    },
    {
        "id": "arb-finder",
        "name": "Arbitrage Finder",
        "version": "1.0.2",
        "description": "Find arbitrage opportunities across prediction market platforms",
        "author": "arbbot",
        "category": "trading",
        "status": "verified",
        "downloads": 1876,
        "rating": 4.4,
        "rating_count": 98,
        "tags": ["arbitrage", "cross-platform", "opportunities"],
        "permissions": ["api_read", "full_network"],
        "readme": """# Arbitrage Finder

Find cross-platform arbitrage.

## Supported Platforms
- Polymarket
- Kalshi
- PredictIt
- Metaculus
"""
    },
    {
        "id": "ai-analyst",
        "name": "AI Market Analyst",
        "version": "1.5.0",
        "description": "AI-powered market analysis and predictions using LLMs",
        "author": "aitrader",
        "category": "analysis",
        "status": "verified",
        "downloads": 2987,
        "rating": 4.7,
        "rating_count": 187,
        "tags": ["ai", "analysis", "predictions", "llm"],
        "permissions": ["api_read", "llm_access"],
        "readme": """# AI Market Analyst

AI-powered analysis for prediction markets.

## Features
- GPT/Claude integration
- Market summaries
- Trade recommendations
- Risk assessments
"""
    },
    {
        "id": "discord-alerts",
        "name": "Discord Alert Bot",
        "version": "1.2.1",
        "description": "Send customizable alerts to Discord channels",
        "author": "discorddev",
        "category": "alerts",
        "status": "verified",
        "downloads": 1543,
        "rating": 4.6,
        "rating_count": 89,
        "tags": ["discord", "alerts", "notifications"],
        "permissions": ["notifications", "discord_webhook"],
        "readme": """# Discord Alert Bot

Send alerts to Discord.

## Features
- Customizable triggers
- Rich embeds
- Multiple channels
- Rate limiting
"""
    }
]


class PredictHub:
    """
    PredictHub marketplace client.
    
    Browse, install, and publish prediction market skills.
    """
    
    def __init__(self):
        # Ensure directories exist
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        SKILL_CACHE.mkdir(parents=True, exist_ok=True)
        
        self.installed: Dict[str, Skill] = {}
        self._load_installed()
    
    def _load_installed(self):
        """Load installed skills from disk."""
        if INSTALLED_SKILLS_FILE.exists():
            try:
                with open(INSTALLED_SKILLS_FILE) as f:
                    data = json.load(f)
                for skill_data in data.get("skills", []):
                    skill = Skill.from_dict(skill_data)
                    self.installed[skill.id] = skill
                logger.info(f"Loaded {len(self.installed)} installed skills")
            except Exception as e:
                logger.error(f"Failed to load installed skills: {e}")
    
    def _save_installed(self):
        """Save installed skills to disk."""
        data = {
            "skills": [skill.to_dict() for skill in self.installed.values()],
            "updated_at": datetime.now().isoformat()
        }
        with open(INSTALLED_SKILLS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    
    def search(self, query: str = "", category: str = None) -> List[Skill]:
        """Search for skills in the marketplace."""
        results = []
        
        for skill_data in COMMUNITY_SKILLS:
            skill = Skill.from_dict(skill_data)
            
            # Filter by category
            if category and skill.category.value != category:
                continue
            
            # Filter by search query
            if query:
                query_lower = query.lower()
                if (query_lower not in skill.name.lower() and
                    query_lower not in skill.description.lower() and
                    not any(query_lower in tag for tag in skill.tags)):
                    continue
            
            results.append(skill)
        
        # Sort by downloads
        results.sort(key=lambda s: s.downloads, reverse=True)
        return results
    
    def browse(self, category: str = None, sort_by: str = "downloads") -> List[Skill]:
        """Browse skills by category."""
        skills = [Skill.from_dict(s) for s in COMMUNITY_SKILLS]
        
        if category:
            skills = [s for s in skills if s.category.value == category]
        
        if sort_by == "downloads":
            skills.sort(key=lambda s: s.downloads, reverse=True)
        elif sort_by == "rating":
            skills.sort(key=lambda s: s.rating, reverse=True)
        elif sort_by == "recent":
            skills.sort(key=lambda s: s.updated_at, reverse=True)
        
        return skills
    
    def info(self, skill_id: str) -> Optional[Skill]:
        """Get detailed info about a skill."""
        for skill_data in COMMUNITY_SKILLS:
            if skill_data["id"] == skill_id:
                return Skill.from_dict(skill_data)
        return None
    
    def install(self, skill_id: str, version: str = None) -> bool:
        """Install a skill from PredictHub."""
        # Find skill in registry
        skill = self.info(skill_id)
        if not skill:
            logger.error(f"Skill not found: {skill_id}")
            return False
        
        # Check if already installed
        if skill_id in self.installed:
            installed_version = self.installed[skill_id].version
            if version is None or version == installed_version:
                logger.info(f"Skill already installed: {skill_id}@{installed_version}")
                return True
        
        # Security check
        if skill.status == SkillStatus.FLAGGED:
            logger.warning(f"⚠️ Skill {skill_id} has been flagged for security issues!")
            return False
        
        if skill.status == SkillStatus.REMOVED:
            logger.error(f"Skill {skill_id} has been removed from PredictHub")
            return False
        
        # Download and install
        logger.info(f"Installing {skill.name}@{skill.version}...")
        
        # Save skill file
        skill_dir = SKILLS_DIR / skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)
        
        # Save skill metadata
        with open(skill_dir / "SKILL.json", "w") as f:
            json.dump(skill.to_dict(), f, indent=2)
        
        # Save README
        with open(skill_dir / "README.md", "w") as f:
            f.write(skill.readme)
        
        # Add to installed
        self.installed[skill_id] = skill
        self._save_installed()
        
        logger.info(f"✅ Installed {skill.name}@{skill.version}")
        return True
    
    def uninstall(self, skill_id: str) -> bool:
        """Uninstall a skill."""
        if skill_id not in self.installed:
            logger.error(f"Skill not installed: {skill_id}")
            return False
        
        # Remove from installed
        skill = self.installed.pop(skill_id)
        self._save_installed()
        
        # Remove skill directory
        skill_dir = SKILLS_DIR / skill_id
        if skill_dir.exists():
            import shutil
            shutil.rmtree(skill_dir)
        
        logger.info(f"✅ Uninstalled {skill.name}")
        return True
    
    def list_installed(self) -> List[Skill]:
        """List installed skills."""
        return list(self.installed.values())
    
    def check_updates(self) -> List[Dict]:
        """Check for skill updates."""
        updates = []
        
        for skill_id, installed in self.installed.items():
            latest = self.info(skill_id)
            if latest and latest.version != installed.version:
                updates.append({
                    "skill_id": skill_id,
                    "name": installed.name,
                    "current": installed.version,
                    "latest": latest.version
                })
        
        return updates
    
    def update_skill(self, skill_id: str) -> bool:
        """Update a skill to latest version."""
        if skill_id not in self.installed:
            return False
        
        # Uninstall and reinstall
        self.uninstall(skill_id)
        return self.install(skill_id)
    
    def update_all(self) -> List[str]:
        """Update all skills."""
        updates = self.check_updates()
        updated = []
        
        for update in updates:
            if self.update_skill(update["skill_id"]):
                updated.append(update["skill_id"])
        
        return updated
    
    def security_report(self, skill_id: str) -> Dict:
        """Get security report for a skill."""
        skill = self.info(skill_id)
        if not skill:
            return {"error": "Skill not found"}
        
        return {
            "skill_id": skill_id,
            "name": skill.name,
            "status": skill.status.value,
            "verified": skill.status == SkillStatus.VERIFIED,
            "permissions": skill.permissions,
            "risk_level": self._assess_risk(skill),
            "last_scanned": datetime.now().isoformat(),
            "warnings": self._get_warnings(skill)
        }
    
    def _assess_risk(self, skill: Skill) -> str:
        """Assess risk level of a skill."""
        high_risk_perms = ["api_write", "wallet_access", "full_network"]
        
        if any(p in skill.permissions for p in high_risk_perms):
            return "high"
        elif skill.status == SkillStatus.UNVERIFIED:
            return "medium"
        elif len(skill.permissions) > 3:
            return "medium"
        else:
            return "low"
    
    def _get_warnings(self, skill: Skill) -> List[str]:
        """Get security warnings for a skill."""
        warnings = []
        
        if skill.status == SkillStatus.UNVERIFIED:
            warnings.append("Skill has not been verified by PredictHub")
        
        if "api_write" in skill.permissions:
            warnings.append("Skill can write to APIs - potential for unauthorized trades")
        
        if "wallet_access" in skill.permissions:
            warnings.append("Skill has wallet access - handle with care")
        
        if "full_network" in skill.permissions:
            warnings.append("Skill has unrestricted network access")
        
        if skill.downloads < 100:
            warnings.append("Low download count - limited community testing")
        
        return warnings
    
    def get_categories(self) -> List[Dict]:
        """Get available skill categories."""
        categories = {}
        for skill_data in COMMUNITY_SKILLS:
            cat = skill_data["category"]
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1
        
        return [
            {"id": cat, "name": cat.title(), "count": count}
            for cat, count in sorted(categories.items(), key=lambda x: -x[1])
        ]


# Global instance
_predicthub: Optional[PredictHub] = None


def get_predicthub() -> PredictHub:
    """Get or create the global PredictHub client."""
    global _predicthub
    if _predicthub is None:
        _predicthub = PredictHub()
    return _predicthub
