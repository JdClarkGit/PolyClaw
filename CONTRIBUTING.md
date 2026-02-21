# Contributing to PolyClaw

First off, thank you for considering contributing to PolyClaw! 🦞

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Style Guidelines](#style-guidelines)

## Code of Conduct

This project and everyone participating in it is governed by our commitment to creating a welcoming environment. Please be respectful and constructive in all interactions.

## How Can I Contribute?

### ⭐ Star the Repository

The easiest way to contribute is to star the repo! It helps others discover PolyClaw.

### 🐛 Report Bugs

Found a bug? Please open an issue with:
- A clear title and description
- Steps to reproduce the bug
- Expected vs actual behavior
- Screenshots if applicable
- Your environment (OS, Python version, browser)

### 💡 Suggest Features

Have an idea? Open an issue with:
- A clear description of the feature
- Why it would be useful
- Any implementation ideas you have

### 📝 Improve Documentation

Documentation improvements are always welcome:
- Fix typos or unclear explanations
- Add examples
- Translate to other languages

### 🔧 Submit Code

Ready to code? Here's how:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test your changes
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Development Setup

### Prerequisites

- Python 3.9+
- pip
- Git

### Local Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/polyclaw.git
cd polyclaw

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run the development server
python app.py
```

### Project Structure

```
polyclaw/
├── app.py                 # Main Flask application - API routes
├── analytics.py           # Trade analysis functions
├── ai_analysis.py         # AI integration (OpenAI/Anthropic)
├── strategy_engine.py     # Strategy detection and generation
├── notifications.py       # Discord/Telegram notifications
├── terminal_analytics.py  # Terminal mode analytics
├── trade-viewer.html      # Main frontend
├── terminal-mode.html     # Terminal interface
├── leaderboard.html       # Leaderboard page
└── polyClaw/              # AI agent configuration
```

### Running Tests

```bash
# Run tests (when available)
python -m pytest tests/
```

## Pull Request Process

1. **Update documentation** - If you're adding features, update the README
2. **Follow style guidelines** - See below
3. **One feature per PR** - Keep PRs focused
4. **Write clear commit messages** - Describe what and why
5. **Test your changes** - Make sure nothing breaks
6. **Be responsive** - Address review feedback promptly

### PR Title Format

```
feat: Add new feature
fix: Fix bug in X
docs: Update README
style: Format code
refactor: Refactor X for clarity
test: Add tests for X
```

## Style Guidelines

### Python

- Follow PEP 8
- Use meaningful variable names
- Add docstrings to functions
- Keep functions focused and small

```python
def analyze_trades(trades: List[Dict]) -> Dict:
    """
    Analyze a list of trades and return metrics.
    
    Args:
        trades: List of trade dictionaries
        
    Returns:
        Dictionary containing analysis metrics
    """
    # Implementation
```

### JavaScript

- Use modern ES6+ syntax
- Use meaningful variable names
- Add comments for complex logic

### HTML/CSS

- Use semantic HTML
- Follow existing class naming conventions
- Keep CSS organized by component

### Commits

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor" not "Moves cursor")
- Keep first line under 72 characters
- Reference issues when applicable

```
feat: Add Discord notification support

- Add webhook configuration endpoint
- Create notification formatting
- Add settings UI for webhook management

Closes #123
```

## Questions?

Feel free to open an issue or start a discussion. We're happy to help!

---

Thank you for contributing! 🦞
