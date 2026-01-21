#!/usr/bin/env python3
"""
Polymarket Trade Analyzer - Web App
Full historical trade fetching with download capabilities.
"""

from flask import Flask, jsonify, request, send_from_directory, send_file
import requests
import json
import csv
import io
import os
import time
from datetime import datetime, timezone
from typing import List, Dict, Set, Optional

app = Flask(__name__, static_folder='.')

DATA_API = "https://data-api.polymarket.com"
OUTPUT_DIR = "activity-exports"
BATCH_SIZE = 1000


def fetch_all_trades(wallet: str, callback=None) -> Dict:
    """Fetch ALL trades using backward timestamp pagination."""

    all_trades = []
    seen_keys: Set[tuple] = set()
    end_ts = None
    username = None
    batch_num = 0

    while True:
        batch_num += 1

        # Build request
        params = {"user": wallet, "limit": BATCH_SIZE}
        if end_ts:
            params["end"] = end_ts

        try:
            response = requests.get(f"{DATA_API}/activity", params=params, timeout=30)
            response.raise_for_status()
            trades = response.json()
        except Exception as e:
            break

        if not trades or not isinstance(trades, list):
            break

        # Get username
        if not username and trades[0].get('name'):
            username = trades[0].get('name')

        # Deduplicate and add
        new_count = 0
        oldest_ts = float('inf')

        for t in trades:
            key = (t.get('transactionHash'), t.get('timestamp'), t.get('asset'))
            if key not in seen_keys:
                seen_keys.add(key)
                all_trades.append(t)
                new_count += 1

            ts = t.get('timestamp', 0)
            if ts and ts < oldest_ts:
                oldest_ts = ts

        # Check termination conditions
        if len(trades) < BATCH_SIZE or new_count == 0:
            break

        # Set next end timestamp
        if oldest_ts != float('inf'):
            end_ts = oldest_ts
        else:
            break

        # Small delay to be nice to API
        time.sleep(0.2)

        # Safety limit (prevent infinite loops)
        if batch_num > 5000:
            break

    # Sort by timestamp descending
    all_trades.sort(key=lambda t: t.get('timestamp', 0), reverse=True)

    # Calculate stats
    buys = sum(1 for t in all_trades if t.get('side') == 'BUY')
    sells = sum(1 for t in all_trades if t.get('side') == 'SELL')
    volume = sum(t.get('usdcSize', 0) or 0 for t in all_trades)

    timestamps = [t.get('timestamp', 0) for t in all_trades if t.get('timestamp')]
    oldest = datetime.fromtimestamp(min(timestamps)).strftime('%Y-%m-%d %H:%M') if timestamps else None
    newest = datetime.fromtimestamp(max(timestamps)).strftime('%Y-%m-%d %H:%M') if timestamps else None

    return {
        "wallet": wallet,
        "username": username,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "trade_count": len(all_trades),
        "stats": {
            "buys": buys,
            "sells": sells,
            "volume_usd": volume,
            "oldest_trade": oldest,
            "newest_trade": newest,
            "batches": batch_num
        },
        "trades": all_trades
    }


def fetch_recent_trades(wallet: str, limit: int = 100) -> Dict:
    """Fetch recent trades (quick mode)."""
    params = {"user": wallet, "limit": limit}

    try:
        response = requests.get(f"{DATA_API}/activity", params=params, timeout=30)
        response.raise_for_status()
        trades = response.json() if isinstance(response.json(), list) else []

        username = None
        if trades and trades[0].get('name'):
            username = trades[0].get('name')

        return {
            "wallet": wallet,
            "username": username,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "trade_count": len(trades),
            "trades": trades[:limit]
        }
    except Exception as e:
        return {"wallet": wallet, "error": str(e), "trades": [], "trade_count": 0}


@app.route('/')
def index():
    return send_from_directory('.', 'trade-viewer.html')


@app.route('/api/trades/<wallet>')
def get_trades(wallet):
    """Fetch trades - use mode=full for all history."""
    mode = request.args.get('mode', 'recent')
    limit = request.args.get('limit', 100, type=int)

    if mode == 'full':
        result = fetch_all_trades(wallet)
    else:
        result = fetch_recent_trades(wallet, limit)

    # Save to file
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    short_wallet = wallet[:10]
    suffix = '-full' if mode == 'full' else ''

    with open(f"{OUTPUT_DIR}/{short_wallet}{suffix}.json", 'w') as f:
        json.dump(result, f, indent=2)

    return jsonify(result)


@app.route('/api/download/<wallet>/<format>')
def download_trades(wallet, format):
    """Download trades as JSON or CSV."""
    mode = request.args.get('mode', 'recent')
    limit = request.args.get('limit', 100, type=int)

    if mode == 'full':
        result = fetch_all_trades(wallet)
    else:
        result = fetch_recent_trades(wallet, limit)

    short_wallet = wallet[:10]
    username = result.get('username') or short_wallet
    suffix = '-full' if mode == 'full' else ''

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if format == 'json':
        filename = f"{OUTPUT_DIR}/{username}{suffix}-trades.json"
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
        return send_file(filename, as_attachment=True, download_name=f"{username}{suffix}-trades.json")

    elif format == 'csv':
        output = io.StringIO()
        if result['trades']:
            fieldnames = ['timestamp', 'datetime', 'type', 'side', 'price', 'size',
                         'usdcSize', 'title', 'outcome', 'transactionHash']
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()

            for trade in result['trades']:
                ts = trade.get('timestamp', 0)
                trade['datetime'] = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S') if ts else ''
                writer.writerow(trade)

        csv_filename = f"{OUTPUT_DIR}/{username}{suffix}-trades.csv"
        with open(csv_filename, 'w') as f:
            f.write(output.getvalue())

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f"{username}{suffix}-trades.csv"
        )

    return jsonify({"error": "Invalid format. Use 'json' or 'csv'"}), 400


@app.route('/api/check/<wallet>')
def check_existing(wallet):
    """Check if we have existing data for a wallet."""
    short_wallet = wallet[:10]

    files = []
    for suffix in ['', '-full']:
        for ext in ['json', 'csv']:
            path = f"{OUTPUT_DIR}/{short_wallet}{suffix}.{ext}"
            if os.path.exists(path):
                size = os.path.getsize(path)
                files.append({"path": path, "size": size})

    return jsonify({"wallet": wallet, "files": files})


if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("\n🚀 Polymarket Trade Analyzer")
    print("   http://localhost:8080")
    print("\n   Quick fetch: /api/trades/{wallet}")
    print("   Full history: /api/trades/{wallet}?mode=full")
    print("   Download: /api/download/{wallet}/csv?mode=full\n")
    app.run(debug=True, port=8080, host='0.0.0.0')
