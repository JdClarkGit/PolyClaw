#!/usr/bin/env python3
"""
Simple web app to fetch and display Polymarket trades.
Enter a wallet address → see trades in UI + download JSON/CSV.
"""

from flask import Flask, jsonify, request, send_from_directory, send_file
import requests
import json
import csv
import io
from datetime import datetime, timezone

app = Flask(__name__, static_folder='.')

DATA_API = "https://data-api.polymarket.com"

def fetch_trades(wallet_address: str, limit: int = 100) -> dict:
    """Fetch recent trades for a wallet from Polymarket API."""
    url = f"{DATA_API}/activity"
    params = {"user": wallet_address, "limit": limit}

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Handle different response formats
        if isinstance(data, list):
            trades = data
        elif isinstance(data, dict) and 'history' in data:
            trades = data['history']
        elif isinstance(data, dict) and 'data' in data:
            trades = data['data']
        else:
            trades = data if isinstance(data, list) else []

        username = None
        if trades and isinstance(trades[0], dict):
            username = trades[0].get('name') or trades[0].get('pseudonym')

        return {
            "wallet": wallet_address,
            "username": username,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "trade_count": len(trades),
            "trades": trades[:limit]
        }
    except Exception as e:
        return {"wallet": wallet_address, "error": str(e), "trades": [], "trade_count": 0}

@app.route('/')
def index():
    return send_from_directory('.', 'trade-viewer.html')

@app.route('/api/trades/<wallet>')
def get_trades(wallet):
    """API endpoint to fetch trades for a wallet."""
    limit = request.args.get('limit', 100, type=int)
    result = fetch_trades(wallet, limit)

    # Save to file
    short_wallet = wallet[:10]
    filename = f"activity-exports/{short_wallet}-trades.json"
    with open(filename, 'w') as f:
        json.dump(result, f, indent=2)

    return jsonify(result)

@app.route('/api/download/<wallet>/<format>')
def download_trades(wallet, format):
    """Download trades as JSON or CSV."""
    limit = request.args.get('limit', 100, type=int)
    result = fetch_trades(wallet, limit)
    short_wallet = wallet[:10]

    if format == 'json':
        # Save and return JSON
        filename = f"activity-exports/{short_wallet}-trades.json"
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
        return send_file(filename, as_attachment=True, download_name=f"{short_wallet}-trades.json")

    elif format == 'csv':
        # Convert to CSV
        output = io.StringIO()
        if result['trades']:
            fieldnames = ['timestamp', 'type', 'side', 'title', 'outcome', 'price', 'size', 'usdcSize', 'transactionHash']
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for trade in result['trades']:
                writer.writerow(trade)

        # Save to file
        csv_filename = f"activity-exports/{short_wallet}-trades.csv"
        with open(csv_filename, 'w') as f:
            f.write(output.getvalue())

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f"{short_wallet}-trades.csv"
        )

    return jsonify({"error": "Invalid format. Use 'json' or 'csv'"}), 400

if __name__ == '__main__':
    print("\n🚀 Trade Viewer running at: http://localhost:8080")
    print("   Enter any Polymarket wallet address to fetch trades\n")
    app.run(debug=True, port=8080, host='0.0.0.0')
