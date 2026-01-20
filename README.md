# 🕵️ PolyTrade - Polymarket Wallet Scraper & Trade Analyzer

Scrape, analyze, and visualize trading activity from any Polymarket wallet address.

## Features

- **🚀 Async Turbo Mode** - 5-10x faster with concurrent requests
- **Wallet Scraping** - Fetch all trades and positions for any wallet
- **Batch Processing** - Scrape multiple wallets from CSV
- **Market Search** - Find and filter markets by query
- **Data Normalization** - Clean timestamps, prices, and trade data
- **Interactive Dashboard** - Chart.js powered visualization
- **Export Ready** - CSV/JSON exports for AI analysis

## Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate (Mac/Linux)
source venv/bin/activate

# Activate (Windows)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Scrape a Wallet

#### ⚡ TURBO MODE (Recommended - 5-10x Faster)

```bash
# Single wallet - blazing fast
python async_scraper.py 0xYOUR_WALLET_ADDRESS

# With turbo flag
python async_scraper.py --wallet 0x... --turbo

# Batch mode - multiple wallets from CSV
python async_scraper.py --wallets wallets.csv
```

#### Standard Mode

**Interactive Mode:**
```bash
python scrape_trades.py
```

**Command Line Mode:**
```bash
python scrape_trades.py --user 0xYOUR_WALLET_ADDRESS --limit 200
```

**With Market Search:**
```bash
python scrape_trades.py --query "Bitcoin Up or Down" --select all --user 0x... --limit 200
```

### 3. View Dashboard

Start a local server:
```bash
python3 -m http.server
```

Open browser to: [http://localhost:8000/trades-dashboard.html](http://localhost:8000/trades-dashboard.html)

Load the CSV file from `activity-exports/all-trades.csv`

## Command Line Options

### Async Scraper (async_scraper.py) - RECOMMENDED

| Option | Short | Description |
|--------|-------|-------------|
| `wallet` | | Wallet address as first argument |
| `--wallet` | `-w` | Wallet address to scrape (0x...) |
| `--wallets` | `-W` | CSV file with wallet addresses for batch mode |
| `--turbo` | | Enable turbo mode (faster, more aggressive) |
| `--output` | `-o` | Output filename prefix (default: turbo) |

### Standard Scraper (scrape_trades.py)

| Option | Short | Description |
|--------|-------|-------------|
| `--user` | `-u` | Wallet address to scrape (0x...) |
| `--query` | `-q` | Market search query |
| `--select` | `-s` | Market selection (number or 'all') |
| `--limit` | `-l` | Max records per request (default: 200) |
| `--output` | `-o` | Output filename prefix (default: all-trades) |

## Output Files

After running the scraper, check `activity-exports/`:

```
activity-exports/
├── all-trades.csv     # Normalized trade data
├── all-trades.json    # Raw JSON data
└── positions.csv      # Current positions
```

## Dashboard Features

- **Trade Timeline** - Scatter plot of all buys/sells over time
- **Cumulative Position** - Net shares held over time
- **Dollar Exposure** - USD at risk over time
- **Price Distribution** - Histogram of entry prices
- **Size Distribution** - Trade volume breakdown
- **Trade Table** - Searchable trade history

## 🤖 AI Analysis

Upload the exported files to ChatGPT/Claude for strategy analysis:

**Sample Prompts:**
- "Analyze this trading history. What is the win rate?"
- "What was the most profitable trade?"
- "Did they sell too early on any positions?"
- "What patterns do you see in their trading behavior?"

## API Endpoints Used

| API | Base URL | Purpose |
|-----|----------|---------|
| Gamma API | `gamma-api.polymarket.com` | Market metadata & search |
| Data API | `data-api.polymarket.com` | User activity & positions |
| CLOB API | `clob.polymarket.com` | Order book & trades |

## Rate Limiting

The scraper includes built-in rate limiting (1-2 req/sec) to avoid getting blocked. For heavy usage, consider:
- Adding delays between requests
- Using proxy rotation
- Caching results locally

## Project Structure

```
PolyTrade/
├── async_scraper.py       # ⚡ TURBO async scraper (5-10x faster)
├── scrape_trades.py       # Standard sync scraper
├── trades-dashboard.html  # Interactive visualization
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── activity-exports/     # Output directory (created on run)
    ├── all-trades.csv    # Dashboard compatible
    ├── turbo-0x123....csv
    ├── turbo-0x123....json
    └── positions.csv
```

## Speed Comparison

| Method | Single Wallet | 10 Wallets |
|--------|--------------|------------|
| `scrape_trades.py` | ~60s | ~10 min |
| `async_scraper.py` | ~6-10s | ~30-60s |

The async scraper uses concurrent requests, semaphore-controlled rate limiting, and connection pooling for maximum speed.

## Troubleshooting

**No data returned?**
- Verify the wallet address is correct (0x format, 42 chars)
- Some wallets may use proxy addresses
- Try with a known active trader address

**Rate limited?**
- Wait a few minutes and retry
- Reduce the `--limit` parameter

**Dashboard not loading CSV?**
- Make sure you're running via `http.server`, not opening the file directly
- Check browser console for errors

## License

MIT - Use freely, trade responsibly 📈
