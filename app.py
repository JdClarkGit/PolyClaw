#!/usr/bin/env python3
"""
PolyEdge.io - Trade Analytics Platform
Full historical trade fetching with pattern detection and analytics.
"""

from flask import Flask, jsonify, request, send_from_directory, send_file, Response
import requests
import json
import csv
import io
import os
import time
from datetime import datetime, timezone
from typing import List, Dict, Set, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from analytics import (
    analyze_trades, generate_report, compare_wallets,
    PRICING_TIERS, get_tier_info, check_feature_access, calculate_overage
)
from ai_analysis import run_ai_analysis, get_available_providers
from terminal_analytics import run_terminal_analysis

app = Flask(__name__, static_folder='.')

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///polyedge.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
from models import db, init_db
init_db(app)

# Initialize authentication
from auth import init_auth
init_auth(app)

# Initialize payments
from payments import init_payments
init_payments(app)

DATA_API = "https://data-api.polymarket.com"
OUTPUT_DIR = "activity-exports"
BATCH_SIZE = 1000


def filter_trades_by_date(result: Dict, start_date: str = None, end_date: str = None) -> Dict:
    """Filter trades by date range. Dates should be in YYYY-MM-DD format."""
    if not result.get('trades'):
        return result
    
    filtered_trades = []
    start_ts = None
    end_ts = None
    
    if start_date:
        try:
            start_ts = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            pass
    
    if end_date:
        try:
            # End of day for end_date
            end_ts = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.utc).timestamp()
        except ValueError:
            pass
    
    for trade in result['trades']:
        ts = trade.get('timestamp', 0)
        if start_ts and ts < start_ts:
            continue
        if end_ts and ts > end_ts:
            continue
        filtered_trades.append(trade)
    
    # Update result with filtered trades
    result['trades'] = filtered_trades
    result['trade_count'] = len(filtered_trades)
    
    # Update stats if present
    if filtered_trades and result.get('stats'):
        oldest = min(t.get('timestamp', 0) for t in filtered_trades)
        newest = max(t.get('timestamp', 0) for t in filtered_trades)
        result['stats']['oldest_trade'] = datetime.fromtimestamp(oldest).strftime('%Y-%m-%d') if oldest else None
        result['stats']['newest_trade'] = datetime.fromtimestamp(newest).strftime('%Y-%m-%d') if newest else None
    
    return result


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

        # Retry logic with exponential backoff
        trades = None
        max_retries = 3
        for retry in range(max_retries):
            try:
                response = requests.get(f"{DATA_API}/activity", params=params, timeout=30)
                response.raise_for_status()
                trades = response.json()
                break
            except Exception as e:
                if retry < max_retries - 1:
                    time.sleep(2 ** retry)  # Exponential backoff: 1s, 2s, 4s
                    continue
                else:
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


def fetch_trades_stream(wallet: str, target_limit: int = None):
    """Generator function for SSE streaming progress during trade fetching."""
    all_trades = []
    seen_keys: Set[tuple] = set()
    end_ts = None
    username = None
    batch_num = 0
    start_time = time.time()

    while True:
        batch_num += 1

        # Build request
        params = {"user": wallet, "limit": BATCH_SIZE}
        if end_ts:
            params["end"] = end_ts

        # Send progress update
        elapsed = time.time() - start_time
        estimated_batches = max(batch_num, 10)  # Minimum estimate
        estimated_remaining = max(0, (elapsed / batch_num) * (estimated_batches - batch_num))
        
        progress_data = {
            "type": "progress",
            "batch": batch_num,
            "total_trades": len(all_trades),
            "elapsed_seconds": round(elapsed, 1),
            "estimated_remaining": round(estimated_remaining, 1)
        }
        yield f"data: {json.dumps(progress_data)}\n\n"

        # Retry logic with exponential backoff
        trades = None
        max_retries = 3
        for retry in range(max_retries):
            try:
                response = requests.get(f"{DATA_API}/activity", params=params, timeout=30)
                response.raise_for_status()
                trades = response.json()
                break
            except Exception as e:
                if retry < max_retries - 1:
                    time.sleep(2 ** retry)
                    continue
                else:
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

        # Check if we've hit target limit
        if target_limit and len(all_trades) >= target_limit:
            all_trades = all_trades[:target_limit]
            break

        # Set next end timestamp
        if oldest_ts != float('inf'):
            end_ts = oldest_ts
        else:
            break

        time.sleep(0.2)

        # Safety limit
        if batch_num > 5000:
            break

    # Sort by timestamp descending
    all_trades.sort(key=lambda t: t.get('timestamp', 0), reverse=True)

    # Send completion event
    complete_data = {
        "type": "complete",
        "wallet": wallet,
        "username": username,
        "trade_count": len(all_trades),
        "total_batches": batch_num,
        "elapsed_seconds": round(time.time() - start_time, 1)
    }
    yield f"data: {json.dumps(complete_data)}\n\n"


@app.route('/')
def index():
    return send_from_directory('.', 'trade-viewer.html')


@app.route('/dashboard')
def dashboard():
    return send_from_directory('.', 'trades-dashboard.html')


@app.route('/terminal')
def terminal_mode():
    return send_from_directory('.', 'terminal-mode.html')


@app.route('/api/terminal/<wallet>', methods=['GET', 'OPTIONS'])
def terminal_data(wallet):
    """Fetch trades + full terminal analysis for the wallet analyzer."""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        resp = app.make_default_options_response()
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    limit = request.args.get('limit', 200, type=int)
    result = fetch_trades_with_limit(wallet, min(limit, 500))
    trades = result.get('trades', [])

    # Run full analysis pipeline
    base_analysis = {}
    terminal = {}
    if trades:
        base_analysis = analyze_trades(trades)
        terminal = run_terminal_analysis(trades, base_analysis)

    # Slim trade objects for the feed
    slim_trades = []
    for t in trades[:100]:  # Cap feed at 100
        slim_trades.append({
            'ts': t.get('timestamp'),
            's': t.get('side'),
            'p': t.get('price'),
            'sz': t.get('size'),
            'v': t.get('usdcSize'),
            't': (t.get('title') or '')[:80],
            'o': t.get('outcome'),
            'tx': (t.get('transactionHash') or '')[:12],
        })

    # Extract key data from base analysis
    pnl = base_analysis.get('pnl', {}).get('summary', {})
    summary = base_analysis.get('summary', {})
    freq = base_analysis.get('frequency', {})

    payload = {
        "w": wallet,
        "u": result.get('username'),
        "n": len(trades),
        "trades": slim_trades,
        # Base metrics
        "pnl": pnl,
        "summary": summary,
        "freq": {
            "sub_second_pct": freq.get('gaps', {}).get('sub_second_percentage', 0),
            "is_bot": freq.get('is_bot_like', False),
            "bursts": freq.get('bursts', {}).get('total_bursts', 0),
        },
        # Terminal-specific metrics
        "kelly": terminal.get('kelly', {}),
        "risk": terminal.get('risk_adjusted', {}),
        "hc": terminal.get('high_confidence', {}),
        "flow": terminal.get('order_flow', {}),
        "phases": terminal.get('phases', {}),
        "exec": terminal.get('execution', {}),
        "tpnl": terminal.get('time_pnl', {}),
        "pos": terminal.get('positions', []),
        "fp": terminal.get('fingerprint', {}),
    }

    # JSONP support for proxy environments
    callback = request.args.get('callback')
    if callback:
        js = f"{callback}({json.dumps(payload)})"
        resp = Response(js, mimetype='application/javascript')
    else:
        resp = jsonify(payload)

    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


@app.route('/api/trades/<wallet>')
def get_trades(wallet):
    """Fetch trades - use mode=full for all history."""
    mode = request.args.get('mode', 'recent')
    limit = request.args.get('limit', 100, type=int)
    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')

    if mode == 'full':
        result = fetch_all_trades(wallet)
    elif limit > 1000:
        # Use paginated fetch for larger limits (5k, 10k, 50k)
        result = fetch_trades_with_limit(wallet, limit)
    else:
        result = fetch_recent_trades(wallet, limit)

    # Apply date filtering if provided
    if start_date or end_date:
        result = filter_trades_by_date(result, start_date, end_date)

    # Save to file
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    short_wallet = wallet[:10]
    suffix = '-full' if mode == 'full' else ''

    with open(f"{OUTPUT_DIR}/{short_wallet}{suffix}.json", 'w') as f:
        json.dump(result, f, indent=2)

    return jsonify(result)


@app.route('/api/trades/<wallet>/stream')
def stream_trades(wallet):
    """
    Stream trade fetching progress via Server-Sent Events (SSE).
    Use this for large fetches to show real-time progress.
    """
    limit = request.args.get('limit', type=int)
    
    def generate():
        yield from fetch_trades_stream(wallet, limit)
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/api/download/<wallet>/<format>')
def download_trades(wallet, format):
    """Download trades as JSON, CSV, or TXT."""
    mode = request.args.get('mode', 'recent')
    limit = request.args.get('limit', 100, type=int)

    if mode == 'full':
        result = fetch_all_trades(wallet)
    elif limit > 1000:
        # Use paginated fetch for larger limits
        result = fetch_trades_with_limit(wallet, limit)
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

    elif format == 'txt':
        # Generate formatted text file
        lines = []
        lines.append("=" * 60)
        lines.append("POLYMARKET TRADE HISTORY")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Wallet: {wallet}")
        lines.append(f"Username: {username}")
        lines.append(f"Total Trades: {len(result.get('trades', []))}")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("")

        for i, trade in enumerate(result.get('trades', []), 1):
            ts = trade.get('timestamp', 0)
            dt = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S') if ts else 'N/A'
            side = trade.get('side', 'N/A')
            price = trade.get('price', 0)
            size = trade.get('size', 0)
            usdc = trade.get('usdcSize', 0)
            title = trade.get('title', 'N/A')
            outcome = trade.get('outcome', 'N/A')
            tx_hash = trade.get('transactionHash', 'N/A')

            lines.append(f"Trade #{i}")
            lines.append(f"  Time:     {dt}")
            lines.append(f"  Side:     {side}")
            lines.append(f"  Market:   {title}")
            lines.append(f"  Outcome:  {outcome}")
            lines.append(f"  Price:    {price:.4f}" if isinstance(price, (int, float)) else f"  Price:    {price}")
            lines.append(f"  Size:     {size:.2f}" if isinstance(size, (int, float)) else f"  Size:     {size}")
            lines.append(f"  Value:    ${usdc:.2f}" if isinstance(usdc, (int, float)) else f"  Value:    ${usdc}")
            lines.append(f"  Tx:       {tx_hash[:20]}..." if tx_hash and len(str(tx_hash)) > 20 else f"  Tx:       {tx_hash}")
            lines.append("")

        txt_content = "\n".join(lines)
        txt_filename = f"{OUTPUT_DIR}/{username}{suffix}-trades.txt"
        with open(txt_filename, 'w') as f:
            f.write(txt_content)

        return send_file(
            io.BytesIO(txt_content.encode()),
            mimetype='text/plain',
            as_attachment=True,
            download_name=f"{username}{suffix}-trades.txt"
        )

    elif format == 'xlsx':
        # Generate Excel file using openpyxl
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
        except ImportError:
            return jsonify({"error": "Excel export not available. Install openpyxl."}), 500

        wb = Workbook()
        ws = wb.active
        ws.title = "Trades"

        # Define styles
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="2E7D32", end_color="2E7D32", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # Headers
        headers = ['#', 'Date/Time', 'Side', 'Market', 'Outcome', 'Price', 'Size', 'Value (USDC)', 'Transaction Hash']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        # Data rows
        for row_num, trade in enumerate(result.get('trades', []), 2):
            ts = trade.get('timestamp', 0)
            dt = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S') if ts else 'N/A'
            
            row_data = [
                row_num - 1,
                dt,
                trade.get('side', 'N/A'),
                trade.get('title', 'N/A'),
                trade.get('outcome', 'N/A'),
                trade.get('price', 0),
                trade.get('size', 0),
                trade.get('usdcSize', 0),
                trade.get('transactionHash', 'N/A')
            ]
            
            for col, value in enumerate(row_data, 1):
                cell = ws.cell(row=row_num, column=col, value=value)
                cell.border = thin_border
                if col in [6, 7, 8]:  # Price, Size, Value columns
                    cell.number_format = '#,##0.0000' if col == 6 else '#,##0.00'

        # Adjust column widths
        column_widths = [6, 20, 8, 50, 15, 12, 12, 15, 45]
        for col, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(col)].width = width

        # Freeze header row
        ws.freeze_panes = 'A2'

        # Save to BytesIO
        excel_output = io.BytesIO()
        wb.save(excel_output)
        excel_output.seek(0)

        return send_file(
            excel_output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"{username}{suffix}-trades.xlsx"
        )

    return jsonify({"error": "Invalid format. Use 'json', 'csv', 'txt', or 'xlsx'"}), 400


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


@app.route('/api/analyze/<wallet>')
def analyze_wallet(wallet):
    """Analyze trades and return pattern insights."""
    limit = request.args.get('limit', 1000, type=int)
    mode = request.args.get('mode', 'recent')
    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')

    # Fetch trades
    if mode == 'full':
        result = fetch_all_trades(wallet)
    else:
        # Use limit for scalable fetching
        result = fetch_trades_with_limit(wallet, limit)

    # Apply date filtering if provided
    if start_date or end_date:
        result = filter_trades_by_date(result, start_date, end_date)

    trades = result.get('trades', [])
    if not trades:
        return jsonify({"error": "No trades found", "wallet": wallet})

    # Run analysis
    analysis = analyze_trades(trades)

    return jsonify({
        "wallet": wallet,
        "username": result.get('username'),
        "trade_count": len(trades),
        "analysis": analysis
    })


@app.route('/api/analyze/<wallet>/report')
def get_analysis_report(wallet):
    """Generate and download markdown analysis report."""
    limit = request.args.get('limit', 1000, type=int)
    mode = request.args.get('mode', 'recent')

    # Fetch trades
    if mode == 'full':
        result = fetch_all_trades(wallet)
    else:
        result = fetch_trades_with_limit(wallet, limit)

    trades = result.get('trades', [])
    if not trades:
        return jsonify({"error": "No trades found"}), 404

    # Run analysis
    analysis = analyze_trades(trades)

    # Generate report
    report = generate_report(analysis, wallet, result.get('username'))

    # Return as downloadable markdown
    username = result.get('username') or wallet[:10]
    return Response(
        report,
        mimetype='text/markdown',
        headers={'Content-Disposition': f'attachment; filename={username}-analysis.md'}
    )


# =============================================================================
# AI ANALYSIS ENDPOINTS
# =============================================================================

@app.route('/api/ai-analyze/<wallet>', methods=['POST'])
def ai_analyze_wallet(wallet):
    """
    AI-powered trade analysis using OpenAI or Anthropic.
    
    Request body:
    {
        "provider": "openai" | "anthropic",
        "prompt_type": "strategy" | "risk" | "performance" | "custom",
        "custom_prompt": "optional custom question",
        "limit": 1000
    }
    """
    data = request.get_json() or {}
    provider = data.get('provider', 'openai')
    prompt_type = data.get('prompt_type', 'strategy')
    custom_prompt = data.get('custom_prompt')
    limit = data.get('limit', 1000)
    
    # Validate provider
    if provider not in ['openai', 'anthropic']:
        return jsonify({"error": "Invalid provider. Use 'openai' or 'anthropic'"}), 400
    
    # Validate prompt type
    valid_types = ['strategy', 'risk', 'performance', 'custom']
    if prompt_type not in valid_types:
        return jsonify({"error": f"Invalid prompt_type. Use one of: {valid_types}"}), 400
    
    # Fetch trades
    result = fetch_trades_with_limit(wallet, limit)
    trades = result.get('trades', [])
    
    if not trades:
        return jsonify({"error": "No trades found for this wallet"}), 404
    
    # Run pattern analysis first (for context)
    analysis = analyze_trades(trades)
    
    # Run AI analysis
    ai_result = run_ai_analysis(
        trades=trades,
        analysis=analysis,
        provider=provider,
        prompt_type=prompt_type,
        custom_prompt=custom_prompt
    )
    
    if ai_result.get('error'):
        return jsonify(ai_result), 500
    
    # Add wallet info
    ai_result['wallet'] = wallet
    ai_result['username'] = result.get('username')
    
    return jsonify(ai_result)


@app.route('/api/ai-providers')
def get_ai_providers():
    """Check which AI providers are available and configured."""
    providers = get_available_providers()
    return jsonify(providers)


def fetch_trades_with_limit(wallet: str, limit: int) -> Dict:
    """Fetch trades up to a specific limit using pagination."""
    all_trades = []
    seen_keys: Set[tuple] = set()
    end_ts = None
    username = None

    while len(all_trades) < limit:
        batch_limit = min(BATCH_SIZE, limit - len(all_trades))
        params = {"user": wallet, "limit": batch_limit}
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

        if not username and trades[0].get('name'):
            username = trades[0].get('name')

        oldest_ts = float('inf')
        new_count = 0

        for t in trades:
            if len(all_trades) >= limit:
                break
            key = (t.get('transactionHash'), t.get('timestamp'), t.get('asset'))
            if key not in seen_keys:
                seen_keys.add(key)
                all_trades.append(t)
                new_count += 1

            ts = t.get('timestamp', 0)
            if ts and ts < oldest_ts:
                oldest_ts = ts

        if len(trades) < batch_limit or new_count == 0:
            break

        if oldest_ts != float('inf'):
            end_ts = oldest_ts
        else:
            break

        time.sleep(0.1)

    all_trades.sort(key=lambda t: t.get('timestamp', 0), reverse=True)

    return {
        "wallet": wallet,
        "username": username,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "trade_count": len(all_trades),
        "trades": all_trades
    }


# Trade count presets for UI
TRADE_PRESETS = [100, 1000, 5000, 10000, 50000, 100000]


@app.route('/api/presets')
def get_presets():
    """Return available trade count presets."""
    return jsonify({"presets": TRADE_PRESETS})


# =============================================================================
# COMPARISON MODE
# =============================================================================

@app.route('/api/compare', methods=['POST'])
def compare_wallets_endpoint():
    """Compare multiple wallets side-by-side."""
    data = request.get_json()
    wallets = data.get('wallets', [])
    limit = data.get('limit', 1000)
    tier = data.get('tier', 'free')

    if not wallets:
        return jsonify({"error": "No wallets provided"}), 400

    # Check tier access
    tier_info = get_tier_info(tier)
    max_wallets = tier_info.get("comparison_wallets", 0)

    if len(wallets) > max_wallets and tier != 'scale':
        return jsonify({
            "error": f"Your plan allows comparing up to {max_wallets} wallets. Upgrade to compare more.",
            "tier": tier,
            "max_wallets": max_wallets,
            "upgrade_needed": True
        }), 403

    # Fetch and analyze each wallet
    wallet_analyses = []
    for wallet in wallets[:max_wallets or len(wallets)]:
        result = fetch_trades_with_limit(wallet, limit)
        trades = result.get('trades', [])

        if trades:
            analysis = analyze_trades(trades)
            wallet_analyses.append({
                "wallet": wallet,
                "username": result.get('username'),
                "trade_count": len(trades),
                "analysis": analysis,
                "pnl": analysis.get("pnl", {})
            })

    # Run comparison
    comparison = compare_wallets(wallet_analyses)

    return jsonify({
        "comparison": comparison,
        "wallet_data": wallet_analyses,
        "tier": tier
    })


# =============================================================================
# PRICING ENDPOINTS
# =============================================================================

@app.route('/api/pricing')
def get_pricing():
    """Return pricing tier information."""
    return jsonify({
        "tiers": PRICING_TIERS,
        "overage_rate": 0.01,
        "currency": "USD"
    })


@app.route('/api/pricing/<tier>')
def get_tier(tier):
    """Get specific tier information."""
    tier_info = get_tier_info(tier)
    if tier_info:
        return jsonify(tier_info)
    return jsonify({"error": "Invalid tier"}), 404


@app.route('/api/usage/check', methods=['POST'])
def check_usage():
    """Check if usage is within tier limits."""
    data = request.get_json()
    tier = data.get('tier', 'free')
    trades_used = data.get('trades_used', 0)

    tier_info = get_tier_info(tier)
    limit = tier_info.get("trades_per_month", 100)
    overage = calculate_overage(tier, trades_used)

    return jsonify({
        "tier": tier,
        "limit": limit,
        "used": trades_used,
        "remaining": max(0, limit - trades_used),
        "percentage_used": round(trades_used / limit * 100, 1),
        "overage": overage,
        "within_limit": trades_used <= limit
    })


@app.route('/api/features/<feature>')
def check_feature(feature):
    """Check which tiers have access to a feature."""
    tiers_with_access = []
    for tier_id, tier_info in PRICING_TIERS.items():
        if feature in tier_info.get("features", []):
            tiers_with_access.append({
                "tier": tier_id,
                "name": tier_info["name"],
                "price": tier_info["price"]
            })

    return jsonify({
        "feature": feature,
        "available_in": tiers_with_access,
        "minimum_tier": tiers_with_access[0]["tier"] if tiers_with_access else None
    })


if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("\n🚀 Polymarket Trade Analyzer")
    print("   http://localhost:8080")
    print("\n   Quick fetch: /api/trades/{wallet}")
    print("   Full history: /api/trades/{wallet}?mode=full")
    print("   Download: /api/download/{wallet}/csv?mode=full\n")
    app.run(debug=True, port=8080, host='0.0.0.0')
