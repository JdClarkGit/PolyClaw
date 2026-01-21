#!/usr/bin/env python3
"""
PolyEdge Stripe Payment Integration
Subscription management and billing.
"""

from flask import Blueprint, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from models import db, User, StripeEvent
from datetime import datetime, timezone
import stripe
import os

payments_bp = Blueprint('payments', __name__, url_prefix='/api/payments')

# Stripe configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')

# Price IDs for each tier (set these in Stripe Dashboard)
STRIPE_PRICES = {
    'starter': os.environ.get('STRIPE_PRICE_STARTER'),     # $19/month
    'growth': os.environ.get('STRIPE_PRICE_GROWTH'),       # $79/month
    'scale': os.environ.get('STRIPE_PRICE_SCALE'),         # $299/month
}

# Tier mapping from Stripe price IDs
PRICE_TO_TIER = {v: k for k, v in STRIPE_PRICES.items() if v}

FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:8080')


@payments_bp.route('/config', methods=['GET'])
def get_stripe_config():
    """Get Stripe publishable key for frontend."""
    return jsonify({
        'publishable_key': STRIPE_PUBLISHABLE_KEY,
        'prices': {
            'starter': {'id': STRIPE_PRICES.get('starter'), 'amount': 1900, 'name': 'Starter'},
            'growth': {'id': STRIPE_PRICES.get('growth'), 'amount': 7900, 'name': 'Growth'},
            'scale': {'id': STRIPE_PRICES.get('scale'), 'amount': 29900, 'name': 'Scale'},
        }
    })


@payments_bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Create a Stripe Checkout session for subscription."""
    data = request.get_json()
    tier = data.get('tier')

    if tier not in STRIPE_PRICES:
        return jsonify({'error': 'Invalid tier'}), 400

    price_id = STRIPE_PRICES[tier]
    if not price_id:
        return jsonify({'error': 'Price not configured for this tier'}), 500

    try:
        # Create or get Stripe customer
        if not current_user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                metadata={'user_id': current_user.id}
            )
            current_user.stripe_customer_id = customer.id
            db.session.commit()

        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f'{FRONTEND_URL}/?payment=success&session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{FRONTEND_URL}/?payment=canceled',
            metadata={
                'user_id': current_user.id,
                'tier': tier,
            },
            subscription_data={
                'metadata': {
                    'user_id': current_user.id,
                    'tier': tier,
                }
            }
        )

        return jsonify({'checkout_url': session.url, 'session_id': session.id})

    except stripe.error.StripeError as e:
        return jsonify({'error': str(e)}), 400


@payments_bp.route('/create-portal-session', methods=['POST'])
@login_required
def create_portal_session():
    """Create a Stripe Customer Portal session for managing subscription."""
    if not current_user.stripe_customer_id:
        return jsonify({'error': 'No subscription found'}), 400

    try:
        session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=f'{FRONTEND_URL}/',
        )
        return jsonify({'portal_url': session.url})

    except stripe.error.StripeError as e:
        return jsonify({'error': str(e)}), 400


@payments_bp.route('/subscription', methods=['GET'])
@login_required
def get_subscription():
    """Get current subscription details."""
    if not current_user.stripe_subscription_id:
        return jsonify({
            'tier': current_user.tier,
            'status': 'inactive',
            'subscription': None
        })

    try:
        subscription = stripe.Subscription.retrieve(current_user.stripe_subscription_id)
        return jsonify({
            'tier': current_user.tier,
            'status': subscription.status,
            'current_period_end': subscription.current_period_end,
            'cancel_at_period_end': subscription.cancel_at_period_end,
            'subscription': {
                'id': subscription.id,
                'status': subscription.status,
                'current_period_start': subscription.current_period_start,
                'current_period_end': subscription.current_period_end,
            }
        })

    except stripe.error.StripeError as e:
        return jsonify({'error': str(e)}), 400


@payments_bp.route('/cancel', methods=['POST'])
@login_required
def cancel_subscription():
    """Cancel subscription at end of billing period."""
    if not current_user.stripe_subscription_id:
        return jsonify({'error': 'No active subscription'}), 400

    try:
        subscription = stripe.Subscription.modify(
            current_user.stripe_subscription_id,
            cancel_at_period_end=True
        )

        current_user.subscription_status = 'canceling'
        db.session.commit()

        return jsonify({
            'message': 'Subscription will be canceled at end of billing period',
            'cancel_at': subscription.current_period_end
        })

    except stripe.error.StripeError as e:
        return jsonify({'error': str(e)}), 400


@payments_bp.route('/reactivate', methods=['POST'])
@login_required
def reactivate_subscription():
    """Reactivate a canceled subscription."""
    if not current_user.stripe_subscription_id:
        return jsonify({'error': 'No subscription found'}), 400

    try:
        subscription = stripe.Subscription.modify(
            current_user.stripe_subscription_id,
            cancel_at_period_end=False
        )

        current_user.subscription_status = 'active'
        db.session.commit()

        return jsonify({'message': 'Subscription reactivated'})

    except stripe.error.StripeError as e:
        return jsonify({'error': str(e)}), 400


@payments_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events."""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    if not STRIPE_WEBHOOK_SECRET:
        # Skip signature verification in development
        event = stripe.Event.construct_from(
            request.get_json(), stripe.api_key
        )
    else:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return jsonify({'error': 'Invalid payload'}), 400
        except stripe.error.SignatureVerificationError:
            return jsonify({'error': 'Invalid signature'}), 400

    # Check for duplicate events
    if StripeEvent.query.filter_by(stripe_event_id=event.id).first():
        return jsonify({'status': 'already processed'})

    # Process the event
    event_type = event.type

    if event_type == 'checkout.session.completed':
        handle_checkout_completed(event.data.object)

    elif event_type == 'customer.subscription.updated':
        handle_subscription_updated(event.data.object)

    elif event_type == 'customer.subscription.deleted':
        handle_subscription_deleted(event.data.object)

    elif event_type == 'invoice.paid':
        handle_invoice_paid(event.data.object)

    elif event_type == 'invoice.payment_failed':
        handle_payment_failed(event.data.object)

    # Record the event
    stripe_event = StripeEvent(
        stripe_event_id=event.id,
        event_type=event_type
    )
    db.session.add(stripe_event)
    db.session.commit()

    return jsonify({'status': 'success'})


def handle_checkout_completed(session):
    """Handle successful checkout."""
    user_id = session.metadata.get('user_id')
    tier = session.metadata.get('tier')

    if not user_id:
        return

    user = User.query.get(int(user_id))
    if not user:
        return

    # Get subscription from checkout session
    subscription_id = session.subscription
    if subscription_id:
        user.stripe_subscription_id = subscription_id
        user.tier = tier
        user.subscription_status = 'active'
        user.reset_monthly_usage()  # Reset usage on new subscription
        db.session.commit()


def handle_subscription_updated(subscription):
    """Handle subscription changes."""
    customer_id = subscription.customer
    user = User.query.filter_by(stripe_customer_id=customer_id).first()

    if not user:
        return

    # Update subscription status
    user.subscription_status = subscription.status
    user.stripe_subscription_id = subscription.id

    # Update tier based on price
    if subscription.items.data:
        price_id = subscription.items.data[0].price.id
        tier = PRICE_TO_TIER.get(price_id)
        if tier:
            user.tier = tier

    # Update end date
    if subscription.current_period_end:
        user.subscription_end_date = datetime.fromtimestamp(
            subscription.current_period_end, tz=timezone.utc
        )

    db.session.commit()


def handle_subscription_deleted(subscription):
    """Handle subscription cancellation."""
    customer_id = subscription.customer
    user = User.query.filter_by(stripe_customer_id=customer_id).first()

    if not user:
        return

    user.tier = 'free'
    user.subscription_status = 'inactive'
    user.stripe_subscription_id = None
    db.session.commit()


def handle_invoice_paid(invoice):
    """Handle successful payment - reset monthly usage."""
    customer_id = invoice.customer
    user = User.query.filter_by(stripe_customer_id=customer_id).first()

    if not user:
        return

    # Reset usage on successful payment (new billing cycle)
    user.reset_monthly_usage()
    user.subscription_status = 'active'
    db.session.commit()


def handle_payment_failed(invoice):
    """Handle failed payment."""
    customer_id = invoice.customer
    user = User.query.filter_by(stripe_customer_id=customer_id).first()

    if not user:
        return

    user.subscription_status = 'past_due'
    db.session.commit()


def init_payments(app):
    """Initialize payments with app."""
    app.register_blueprint(payments_bp)
