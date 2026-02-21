"""
PolyClaw Skills System

Skills are plugins that extend PolyClaw's capabilities.
"""

import os
import json
import importlib
from pathlib import Path

SKILLS_DIR = Path(__file__).parent
CONFIG_FILE = SKILLS_DIR / "skills_config.json"

# Built-in skills
BUILTIN_SKILLS = {
    "wallet-analyzer": {
        "name": "wallet-analyzer",
        "version": "1.0.0",
        "description": "Deep wallet analysis with P&L, win rate, and strategy detection",
        "enabled": True,
        "builtin": True,
    },
    "strategy-detector": {
        "name": "strategy-detector",
        "version": "1.0.0",
        "description": "Detect and classify trading patterns and strategies",
        "enabled": True,
        "builtin": True,
    },
    "leaderboard": {
        "name": "leaderboard",
        "version": "1.0.0",
        "description": "Public wallet rankings by performance",
        "enabled": True,
        "builtin": True,
    },
    "copy-trader": {
        "name": "copy-trader",
        "version": "1.0.0",
        "description": "Generate copy trade signals from tracked wallets",
        "enabled": True,
        "builtin": True,
    },
    "alert-engine": {
        "name": "alert-engine",
        "version": "1.0.0",
        "description": "Real-time trade and price alerts via Discord/Telegram",
        "enabled": True,
        "builtin": True,
    },
    "data-export": {
        "name": "data-export",
        "version": "1.0.0",
        "description": "Export trades to CSV, Excel, and JSON formats",
        "enabled": True,
        "builtin": True,
    },
    "ai-chat": {
        "name": "ai-chat",
        "version": "1.0.0",
        "description": "AI-powered strategy chat and analysis",
        "enabled": True,
        "builtin": True,
    },
}


def load_config():
    """Load skills configuration"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"skills": {}, "disabled": []}


def save_config(config):
    """Save skills configuration"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def list_skills():
    """List all available skills"""
    config = load_config()
    skills = []
    
    # Built-in skills
    for name, skill in BUILTIN_SKILLS.items():
        skill_info = skill.copy()
        skill_info["enabled"] = name not in config.get("disabled", [])
        skills.append(skill_info)
    
    # Custom skills
    for name, skill in config.get("skills", {}).items():
        if name not in BUILTIN_SKILLS:
            skills.append(skill)
    
    return skills


def enable_skill(name):
    """Enable a skill"""
    config = load_config()
    if name in config.get("disabled", []):
        config["disabled"].remove(name)
        save_config(config)
        return True
    return False


def disable_skill(name):
    """Disable a skill"""
    config = load_config()
    if "disabled" not in config:
        config["disabled"] = []
    if name not in config["disabled"]:
        config["disabled"].append(name)
        save_config(config)
        return True
    return False


def is_enabled(name):
    """Check if a skill is enabled"""
    config = load_config()
    return name not in config.get("disabled", [])
