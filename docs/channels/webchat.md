# WebChat Interface

PolyClaw includes a built-in chat interface accessible directly in your browser.

## Overview

WebChat is the primary interface for interacting with PolyClaw's AI assistant. It's built into the main web interface and provides:

- Conversational AI for strategy questions
- Context-aware responses based on loaded wallet/trades
- Quick action suggestions
- Markdown formatting for responses

## Accessing WebChat

1. Open PolyClaw at http://localhost:8080
2. Click the 🦞 chat button (bottom right)
3. Start chatting!

## Features

### Context-Aware Chat

WebChat knows about your current session:

- **Current wallet** — If you've loaded a wallet, the AI knows about it
- **Loaded trades** — The AI can reference specific trades
- **Analysis results** — Previous analysis is available for discussion

**Example:**
```
You: "What's the win rate for this wallet?"
AI: "Based on the 342 trades I see for 0x1234..., the win rate is 68%..."
```

### Quick Suggestions

The chat panel includes suggested prompts:

- "Analyze the trading pattern"
- "How can I improve my strategy?"
- "What markets should I focus on?"
- "Generate a bot config for this strategy"

Click any suggestion to send it.

### Markdown Responses

AI responses support rich formatting:

- **Bold** and *italic* text
- Code blocks for bot configs
- Tables for comparisons
- Lists for recommendations

## Example Conversations

### Strategy Analysis

```
You: "What patterns do you see in this wallet's trading?"

AI: "Looking at the trade history for 0x1234..., I see several patterns:

1. **Momentum Entry**: They tend to buy when prices are between 0.40-0.60
2. **Quick Exits**: Average hold time is just 2.3 days
3. **Market Focus**: 80% of trades are in political markets
4. **Position Sizing**: Consistent $500-$1000 per trade

This suggests a momentum-based swing trading strategy focused on political events."
```

### Bot Configuration

```
You: "Generate a bot config based on this strategy"

AI: "Here's a JSON configuration for a momentum bot based on this wallet's strategy:

{
  "name": "Political Momentum Bot",
  "strategy": "momentum",
  "markets": ["politics"],
  "entry": {
    "priceRange": [0.40, 0.60],
    "volumeMin": 50000
  },
  "exit": {
    "takeProfit": 0.80,
    "stopLoss": 0.30,
    "maxHoldDays": 5
  },
  "risk": {
    "positionSize": 750,
    "maxPositions": 3
  }
}
```

### Comparison Questions

```
You: "How does this wallet compare to the top performers?"

AI: "Compared to the leaderboard top 10:

| Metric | This Wallet | Top 10 Avg |
|--------|-------------|------------|
| Win Rate | 68% | 71% |
| Avg Trade | $750 | $1,200 |
| P&L | +$15K | +$45K |

This wallet has a competitive win rate but trades smaller positions. 
Consider increasing position size to improve returns."
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Shift + Enter` | New line |
| `Escape` | Close chat panel |

## Configuration

### AI Provider

WebChat uses the AI provider configured in your `.env`:

```env
# Preferred (better for analysis)
ANTHROPIC_API_KEY=sk-ant-...

# Alternative
OPENAI_API_KEY=sk-...
```

If both are configured, Anthropic is used by default.

### No AI Key?

Without an AI key, WebChat shows a message to configure one. Basic wallet analysis still works without AI.

## Tips

### Better Responses

1. **Be specific** — "What's the average hold time?" vs "Tell me about this wallet"
2. **Provide context** — Load a wallet first for context-aware responses
3. **Ask follow-ups** — Build on previous answers

### Common Queries

- "What's the win rate?"
- "Show me the biggest trades"
- "What markets does this wallet prefer?"
- "How risky is this trading style?"
- "What would you change about this strategy?"
- "Generate a copy-trade bot config"

## Troubleshooting

### "AI not available"

- Check your API key in `.env`
- Verify the key has billing enabled
- Restart PolyClaw after adding the key

### Slow responses

- AI responses can take 5-15 seconds for complex queries
- Large trade histories take longer to analyze
- Consider using a faster model if speed is critical

### Chat not opening

- Try refreshing the page
- Check browser console for errors
- Ensure JavaScript is enabled
