#!/bin/bash

# PolyClaw Setup Script
# Run this script to quickly set up PolyClaw on your machine

echo ""
echo "🦞 PolyClaw Setup"
echo "=================="
echo ""

# Check Python version
echo "Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
    PIP_CMD=pip3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
    PIP_CMD=pip
else
    echo "❌ Python not found. Please install Python 3.9+ first."
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Found Python $PYTHON_VERSION"

# Check if Python version is adequate
MAJOR_VERSION=$($PYTHON_CMD -c 'import sys; print(sys.version_info[0])')
MINOR_VERSION=$($PYTHON_CMD -c 'import sys; print(sys.version_info[1])')

if [ "$MAJOR_VERSION" -lt 3 ] || ([ "$MAJOR_VERSION" -eq 3 ] && [ "$MINOR_VERSION" -lt 9 ]); then
    echo "❌ Python 3.9+ required. You have Python $PYTHON_VERSION"
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi
echo "✅ Virtual environment activated"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt
echo "✅ Dependencies installed"

# Create .env file if it doesn't exist
echo ""
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    
    # Generate a random secret key
    SECRET_KEY=$($PYTHON_CMD -c "import secrets; print(secrets.token_hex(32))")
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/change-this-to-a-random-string/$SECRET_KEY/" .env
    else
        sed -i "s/change-this-to-a-random-string/$SECRET_KEY/" .env
    fi
    echo "✅ .env file created with random secret key"
else
    echo "✅ .env file already exists"
fi

# Create empty config files
touch notifications_config.json 2>/dev/null
touch leaderboard_data.json 2>/dev/null

# Create config directory
echo ""
echo "Setting up CLI..."
mkdir -p ~/.polyclaw
echo "✅ Config directory created at ~/.polyclaw"

# Create CLI alias
CLI_PATH="$(pwd)/cli.py"
chmod +x "$CLI_PATH"

# Suggest alias
echo ""
echo "🎉 Setup complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📌 QUICK START"
echo ""
echo "1. Start the gateway (web interface):"
echo "   source venv/bin/activate"
echo "   python app.py"
echo ""
echo "2. Open http://localhost:8080 in your browser"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📌 CLI USAGE (optional)"
echo ""
echo "Add this alias to your shell profile (~/.bashrc or ~/.zshrc):"
echo ""
echo "   alias polyclaw='$CLI_PATH'"
echo ""
echo "Then you can use:"
echo "   polyclaw analyze <wallet>"
echo "   polyclaw leaderboard"
echo "   polyclaw chat \"What strategies work?\""
echo "   polyclaw daemon start"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📌 BOTS (optional)"
echo ""
echo "Telegram Bot: Add TELEGRAM_BOT_TOKEN to .env, then:"
echo "   python telegram_bot.py"
echo ""
echo "Discord Bot: Add DISCORD_BOT_TOKEN to .env, then:"
echo "   python discord_bot.py"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🦞 Happy trading!"
