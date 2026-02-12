"""
Stripe Payment Integration for Agent Exchange
Handles payments, commission splits, and payouts
"""
import stripe
import os
from typing import Dict, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')


class StripePaymentHandler:
    """
    Handles all Stripe payment operations for Agent Exchange
    """
    
    def __init__(self):
        self.api_key = stripe.api_key
    
    def create_payment_intent(
        self,
        amount_usd: float,
        buyer_agent_id: str,
        seller_agent_id: str,
        transaction_id: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create Stripe Payment Intent for agent-to-agent transaction
        
        Args:
            amount_usd: Total transaction amount
            buyer_agent_id: ID of agent making purchase
            seller_agent_id: ID of agent selling service
            transaction_id: Our internal transaction ID
            metadata: Additional data to attach
        
        Returns:
            Payment Intent details including client_secret
        """
        try:
            # Convert to cents for Stripe
            amount_cents = int(amount_usd * 100)
            
            # Create Payment Intent
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency='usd',
                metadata={
                    'transaction_id': transaction_id,
                    'buyer_agent_id': buyer_agent_id,
                    'seller_agent_id': seller_agent_id,
                    'platform': 'agent_exchange',
                    **(metadata or {})
                },
                description=f"Agent Exchange Transaction {transaction_id}",
                # Enable automatic payment methods
                automatic_payment_methods={'enabled': True},
            )
            
            return {
                'success': True,
                'payment_intent_id': intent.id,
                'client_secret': intent.client_secret,
                'amount': amount_usd,
                'status': intent.status
            }
            
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def confirm_payment(self, payment_intent_id: str) -> Dict:
        """
        Confirm payment was successful
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            return {
                'success': True,
                'status': intent.status,
                'amount_received': intent.amount_received / 100,
                'paid': intent.status == 'succeeded'
            }
            
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_transfer(
        self,
        amount_usd: float,
        destination_stripe_account: str,
        transaction_id: str,
        description: str
    ) -> Dict:
        """
        Transfer funds to seller's Stripe account
        
        Args:
            amount_usd: Amount to transfer
            destination_stripe_account: Seller's Stripe Connect account ID
            transaction_id: Our internal transaction ID
            description: Transfer description
        """
        try:
            amount_cents = int(amount_usd * 100)
            
            transfer = stripe.Transfer.create(
                amount=amount_cents,
                currency='usd',
                destination=destination_stripe_account,
                description=description,
                metadata={
                    'transaction_id': transaction_id,
                    'platform': 'agent_exchange'
                }
            )
            
            return {
                'success': True,
                'transfer_id': transfer.id,
                'amount': amount_usd,
                'destination': destination_stripe_account,
                'status': 'transferred'
            }
            
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_connected_account(
        self,
        agent_email: str,
        agent_name: str,
        country: str = 'US'
    ) -> Dict:
        """
        Create Stripe Connect account for agent to receive payouts
        
        This creates an Express account (easiest for agents)
        """
        try:
            account = stripe.Account.create(
                type='express',
                country=country,
                email=agent_email,
                capabilities={
                    'card_payments': {'requested': True},
                    'transfers': {'requested': True},
                },
                business_type='individual',
                metadata={
                    'platform': 'agent_exchange',
                    'agent_name': agent_name
                }
            )
            
            # Create account link for onboarding
            account_link = stripe.AccountLink.create(
                account=account.id,
                refresh_url=f"https://agentmarket.ai/connect/refresh",
                return_url=f"https://agentmarket.ai/connect/return",
                type='account_onboarding',
            )
            
            return {
                'success': True,
                'account_id': account.id,
                'onboarding_url': account_link.url,
                'message': 'Agent must complete onboarding to receive payments'
            }
            
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_agent_transaction(
        self,
        buyer_payment_method: str,
        seller_stripe_account: str,
        amount_usd: float,
        commission_rate: float,
        transaction_id: str,
        referral_commission: float = 0.0
    ) -> Dict:
        """
        Complete flow: charge buyer, split commission, pay seller
        
        Args:
            buyer_payment_method: Stripe payment method ID
            seller_stripe_account: Seller's Connect account
            amount_usd: Total transaction amount
            commission_rate: Platform commission (e.g., 0.06 for 6%)
            transaction_id: Internal transaction ID
            referral_commission: Commission to referrer if applicable
        
        Returns:
            Transaction result with payment and transfer IDs
        """
        try:
            # Step 1: Charge buyer
            amount_cents = int(amount_usd * 100)
            
            charge = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency='usd',
                payment_method=buyer_payment_method,
                confirm=True,
                automatic_payment_methods={'enabled': True},
                metadata={
                    'transaction_id': transaction_id,
                    'platform': 'agent_exchange'
                }
            )
            
            if charge.status != 'succeeded':
                return {
                    'success': False,
                    'error': f'Payment failed: {charge.status}'
                }
            
            # Step 2: Calculate amounts
            commission_amount = amount_usd * commission_rate
            referral_amount = referral_commission  # Already calculated
            seller_payout = amount_usd - commission_amount - referral_amount
            
            # Step 3: Transfer to seller
            transfer = stripe.Transfer.create(
                amount=int(seller_payout * 100),
                currency='usd',
                destination=seller_stripe_account,
                metadata={
                    'transaction_id': transaction_id,
                    'type': 'seller_payout'
                }
            )
            
            result = {
                'success': True,
                'payment_intent_id': charge.id,
                'transfer_id': transfer.id,
                'buyer_charged': amount_usd,
                'platform_commission': commission_amount,
                'referral_commission': referral_amount,
                'seller_received': seller_payout,
                'status': 'completed'
            }
            
            # Step 4: If referral commission, transfer that too
            # (Would need referrer's Stripe account)
            
            return result
            
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def create_payout(
        self,
        stripe_account_id: str,
        amount_usd: float,
        description: str
    ) -> Dict:
        """
        Create payout to agent's bank account
        """
        try:
            amount_cents = int(amount_usd * 100)
            
            payout = stripe.Payout.create(
                amount=amount_cents,
                currency='usd',
                description=description,
                stripe_account=stripe_account_id
            )
            
            return {
                'success': True,
                'payout_id': payout.id,
                'amount': amount_usd,
                'status': payout.status,
                'arrival_date': payout.arrival_date
            }
            
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def handle_webhook(self, payload: bytes, signature: str) -> Dict:
        """
        Handle Stripe webhook events
        
        Critical events:
        - payment_intent.succeeded: Payment received
        - payment_intent.payment_failed: Payment failed
        - transfer.created: Payout to seller started
        - transfer.failed: Payout failed
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, STRIPE_WEBHOOK_SECRET
            )
            
            event_type = event['type']
            event_data = event['data']['object']
            
            result = {
                'success': True,
                'event_type': event_type,
                'event_id': event['id'],
                'processed_at': datetime.utcnow().isoformat()
            }
            
            # Handle different event types
            if event_type == 'payment_intent.succeeded':
                result['action'] = 'update_transaction_status'
                result['transaction_id'] = event_data.get('metadata', {}).get('transaction_id')
                result['status'] = 'payment_received'
                result['amount'] = event_data['amount'] / 100
            
            elif event_type == 'payment_intent.payment_failed':
                result['action'] = 'mark_transaction_failed'
                result['transaction_id'] = event_data.get('metadata', {}).get('transaction_id')
                result['error'] = event_data.get('last_payment_error', {}).get('message')
            
            elif event_type == 'transfer.created':
                result['action'] = 'log_transfer'
                result['transfer_id'] = event_data['id']
                result['amount'] = event_data['amount'] / 100
            
            elif event_type == 'transfer.failed':
                result['action'] = 'handle_transfer_failure'
                result['transfer_id'] = event_data['id']
                result['error'] = event_data.get('failure_message')
            
            return result
            
        except stripe.error.SignatureVerificationError as e:
            return {
                'success': False,
                'error': 'Invalid webhook signature'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_balance(self) -> Dict:
        """
        Get platform Stripe balance
        """
        try:
            balance = stripe.Balance.retrieve()
            
            return {
                'success': True,
                'available': [
                    {
                        'amount': bal['amount'] / 100,
                        'currency': bal['currency']
                    }
                    for bal in balance['available']
                ],
                'pending': [
                    {
                        'amount': bal['amount'] / 100,
                        'currency': bal['currency']
                    }
                    for bal in balance['pending']
                ]
            }
            
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }


# Initialize global handler
stripe_handler = StripePaymentHandler()
