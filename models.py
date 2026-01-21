#!/usr/bin/env python3
"""
PolyEdge Database Models
User accounts, subscriptions, and usage tracking.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User account model."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=True)

    # Subscription info
    tier = db.Column(db.String(20), default='free')  # free, starter, growth, scale
    stripe_customer_id = db.Column(db.String(255), nullable=True)
    stripe_subscription_id = db.Column(db.String(255), nullable=True)
    subscription_status = db.Column(db.String(50), default='inactive')  # active, canceled, past_due
    subscription_end_date = db.Column(db.DateTime, nullable=True)

    # Usage tracking
    trades_used_this_month = db.Column(db.Integer, default=0)
    usage_reset_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime, nullable=True)

    # API key for Scale tier
    api_key = db.Column(db.String(64), unique=True, nullable=True)

    # Relationships
    saved_wallets = db.relationship('SavedWallet', backref='user', lazy=True, cascade='all, delete-orphan')
    analyses = db.relationship('SavedAnalysis', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_api_key(self):
        self.api_key = secrets.token_hex(32)
        return self.api_key

    def get_tier_limits(self):
        """Get usage limits for user's tier."""
        limits = {
            'free': {'trades': 100, 'comparisons': 0, 'api': False},
            'starter': {'trades': 1000, 'comparisons': 0, 'api': False},
            'growth': {'trades': 10000, 'comparisons': 3, 'api': True},
            'scale': {'trades': 100000, 'comparisons': 10, 'api': True},
        }
        return limits.get(self.tier, limits['free'])

    def can_use_feature(self, feature):
        """Check if user can use a specific feature."""
        tier_features = {
            'free': ['basic_analytics'],
            'starter': ['basic_analytics', 'win_loss_tracking'],
            'growth': ['basic_analytics', 'win_loss_tracking', 'comparison_mode', 'advanced_analytics'],
            'scale': ['basic_analytics', 'win_loss_tracking', 'comparison_mode', 'advanced_analytics',
                     'api_access', 'white_label', 'webhooks'],
        }
        return feature in tier_features.get(self.tier, [])

    def check_usage(self, trades_requested):
        """Check if user has enough quota."""
        limits = self.get_tier_limits()
        remaining = limits['trades'] - self.trades_used_this_month
        return trades_requested <= remaining

    def record_usage(self, trades_count):
        """Record trade usage."""
        self.trades_used_this_month += trades_count

    def reset_monthly_usage(self):
        """Reset usage at start of billing cycle."""
        self.trades_used_this_month = 0
        self.usage_reset_date = datetime.now(timezone.utc)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'tier': self.tier,
            'subscription_status': self.subscription_status,
            'trades_used': self.trades_used_this_month,
            'tier_limits': self.get_tier_limits(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class SavedWallet(db.Model):
    """Saved/bookmarked wallets for tracking."""
    __tablename__ = 'saved_wallets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    wallet_address = db.Column(db.String(255), nullable=False)
    nickname = db.Column(db.String(100), nullable=True)
    polymarket_username = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # Tracking settings
    alert_on_trade = db.Column(db.Boolean, default=False)
    alert_threshold_usd = db.Column(db.Float, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_checked = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'wallet_address', name='unique_user_wallet'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'wallet_address': self.wallet_address,
            'nickname': self.nickname,
            'polymarket_username': self.polymarket_username,
            'notes': self.notes,
            'alert_on_trade': self.alert_on_trade,
            'alert_threshold_usd': self.alert_threshold_usd,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class SavedAnalysis(db.Model):
    """Saved analysis reports."""
    __tablename__ = 'saved_analyses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    wallet_address = db.Column(db.String(255), nullable=False)
    polymarket_username = db.Column(db.String(100), nullable=True)

    # Analysis data (JSON)
    trade_count = db.Column(db.Integer, default=0)
    analysis_json = db.Column(db.Text, nullable=True)  # Full analysis as JSON

    # Share settings
    is_public = db.Column(db.Boolean, default=False)
    share_token = db.Column(db.String(32), unique=True, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def generate_share_token(self):
        self.share_token = secrets.token_urlsafe(16)
        self.is_public = True
        return self.share_token

    def to_dict(self):
        return {
            'id': self.id,
            'wallet_address': self.wallet_address,
            'polymarket_username': self.polymarket_username,
            'trade_count': self.trade_count,
            'is_public': self.is_public,
            'share_token': self.share_token,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class StripeEvent(db.Model):
    """Track processed Stripe webhook events to prevent duplicates."""
    __tablename__ = 'stripe_events'

    id = db.Column(db.Integer, primary_key=True)
    stripe_event_id = db.Column(db.String(255), unique=True, nullable=False)
    event_type = db.Column(db.String(100), nullable=False)
    processed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


def init_db(app):
    """Initialize database with app."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
