#!/usr/bin/env python3
"""
PolyEdge Authentication
User registration, login, and session management.
"""

from flask import Blueprint, request, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User
from datetime import datetime, timezone, timedelta
from functools import wraps
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401


def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password):
    """Validate password strength."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, None


def api_key_required(f):
    """Decorator to require API key authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key required', 'code': 'API_KEY_REQUIRED'}), 401

        user = User.query.filter_by(api_key=api_key).first()
        if not user:
            return jsonify({'error': 'Invalid API key', 'code': 'INVALID_API_KEY'}), 401

        if user.tier not in ['growth', 'scale']:
            return jsonify({'error': 'API access requires Growth or Scale tier', 'code': 'TIER_REQUIRED'}), 403

        # Set current user context
        request.api_user = user
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.get_json()

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    username = data.get('username', '').strip()

    # Validation
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400

    valid, msg = validate_password(password)
    if not valid:
        return jsonify({'error': msg}), 400

    # Check if email exists
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    # Check if username exists (if provided)
    if username and User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already taken'}), 409

    # Create user
    user = User(email=email, username=username or None)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    # Auto login after registration
    login_user(user)

    return jsonify({
        'message': 'Registration successful',
        'user': user.to_dict()
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user."""
    data = request.get_json()

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.session.commit()

    login_user(user, remember=True)

    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict()
    })


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout current user."""
    logout_user()
    return jsonify({'message': 'Logged out successfully'})


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current user info."""
    return jsonify({
        'user': current_user.to_dict(),
        'usage': {
            'trades_used': current_user.trades_used_this_month,
            'trades_limit': current_user.get_tier_limits()['trades'],
            'remaining': current_user.get_tier_limits()['trades'] - current_user.trades_used_this_month,
            'reset_date': current_user.usage_reset_date.isoformat() if current_user.usage_reset_date else None,
        }
    })


@auth_bp.route('/me', methods=['PATCH'])
@login_required
def update_user():
    """Update current user info."""
    data = request.get_json()

    if 'username' in data:
        username = data['username'].strip()
        if username:
            existing = User.query.filter(User.username == username, User.id != current_user.id).first()
            if existing:
                return jsonify({'error': 'Username already taken'}), 409
            current_user.username = username
        else:
            current_user.username = None

    if 'password' in data:
        valid, msg = validate_password(data['password'])
        if not valid:
            return jsonify({'error': msg}), 400
        current_user.set_password(data['password'])

    db.session.commit()
    return jsonify({'message': 'Profile updated', 'user': current_user.to_dict()})


@auth_bp.route('/api-key', methods=['POST'])
@login_required
def generate_api_key():
    """Generate or regenerate API key (Growth/Scale only)."""
    if current_user.tier not in ['growth', 'scale']:
        return jsonify({'error': 'API keys require Growth or Scale tier'}), 403

    api_key = current_user.generate_api_key()
    db.session.commit()

    return jsonify({
        'message': 'API key generated',
        'api_key': api_key,
        'warning': 'Save this key securely. It will not be shown again.'
    })


@auth_bp.route('/api-key', methods=['DELETE'])
@login_required
def revoke_api_key():
    """Revoke API key."""
    current_user.api_key = None
    db.session.commit()
    return jsonify({'message': 'API key revoked'})


# Saved wallets endpoints
@auth_bp.route('/wallets', methods=['GET'])
@login_required
def get_saved_wallets():
    """Get user's saved wallets."""
    from models import SavedWallet
    wallets = SavedWallet.query.filter_by(user_id=current_user.id).all()
    return jsonify({'wallets': [w.to_dict() for w in wallets]})


@auth_bp.route('/wallets', methods=['POST'])
@login_required
def save_wallet():
    """Save a wallet to track."""
    from models import SavedWallet
    data = request.get_json()

    wallet_address = data.get('wallet_address', '').strip()
    if not wallet_address:
        return jsonify({'error': 'Wallet address required'}), 400

    # Check if already saved
    existing = SavedWallet.query.filter_by(
        user_id=current_user.id,
        wallet_address=wallet_address
    ).first()

    if existing:
        return jsonify({'error': 'Wallet already saved'}), 409

    wallet = SavedWallet(
        user_id=current_user.id,
        wallet_address=wallet_address,
        nickname=data.get('nickname'),
        polymarket_username=data.get('polymarket_username'),
        notes=data.get('notes'),
        alert_on_trade=data.get('alert_on_trade', False),
        alert_threshold_usd=data.get('alert_threshold_usd'),
    )

    db.session.add(wallet)
    db.session.commit()

    return jsonify({'message': 'Wallet saved', 'wallet': wallet.to_dict()}), 201


@auth_bp.route('/wallets/<int:wallet_id>', methods=['DELETE'])
@login_required
def delete_saved_wallet(wallet_id):
    """Delete a saved wallet."""
    from models import SavedWallet
    wallet = SavedWallet.query.filter_by(id=wallet_id, user_id=current_user.id).first()

    if not wallet:
        return jsonify({'error': 'Wallet not found'}), 404

    db.session.delete(wallet)
    db.session.commit()

    return jsonify({'message': 'Wallet removed'})


def init_auth(app):
    """Initialize authentication with app."""
    app.config['SECRET_KEY'] = app.config.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SESSION_COOKIE_SECURE'] = app.config.get('ENV') == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)

    login_manager.init_app(app)
    app.register_blueprint(auth_bp)
