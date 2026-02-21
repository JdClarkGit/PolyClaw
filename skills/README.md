# PolyClaw Skills

Skills are plugins that extend PolyClaw's capabilities.

## Built-in Skills

| Skill | Description | Status |
|-------|-------------|--------|
| `wallet-analyzer` | Deep wallet analysis | ✅ Enabled |
| `strategy-detector` | Detect trading patterns | ✅ Enabled |
| `leaderboard` | Public rankings | ✅ Enabled |
| `copy-trader` | Copy trade signals | ✅ Enabled |
| `alert-engine` | Price/trade alerts | ✅ Enabled |
| `data-export` | CSV/Excel/JSON export | ✅ Enabled |

## Community Skills (Coming Soon)

| Skill | Description |
|-------|-------------|
| `kalshi-connector` | Kalshi market integration |
| `hyperliquid-connector` | Hyperliquid integration |
| `technical-analysis` | TA indicators overlay |
| `sentiment-analyzer` | Social sentiment tracking |
| `arbitrage-finder` | Cross-market arbitrage |
| `kelly-calculator` | Optimal position sizing |

## Creating Skills

Skills are Python modules in the `skills/` directory:

```python
# skills/my_skill/__init__.py

SKILL_META = {
    "name": "my-skill",
    "version": "1.0.0",
    "description": "My custom skill",
    "author": "Your Name",
    "requires": ["requests"],
}

def setup(app):
    """Called when skill is loaded"""
    pass

def teardown(app):
    """Called when skill is unloaded"""
    pass

# Define commands
def cmd_mycommand(args):
    """My custom command"""
    return {"result": "Hello from my skill!"}

COMMANDS = {
    "mycommand": cmd_mycommand,
}
```

## Managing Skills

```bash
polyclaw skills list              # List all skills
polyclaw skills enable <name>     # Enable a skill
polyclaw skills disable <name>    # Disable a skill
polyclaw skills install <url>     # Install from URL
```
