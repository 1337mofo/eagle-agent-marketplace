"""
Automated Arbitrage Fulfillment System
Auto-purchase from source platforms and forward to buyers
"""
import requests
import json
import os
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import asyncio
from urllib.parse import urlparse, urljoin

from sqlalchemy.orm import Session
from models.transaction import Transaction, TransactionStatus
from models.listing import Listing
from payments.stripe_handler import stripe_handler


class FulfillmentStatus(str, Enum):
    """Fulfillment status stages"""
    PENDING = "pending"
    PURCHASING = "purchasing"
    PURCHASED = "purchased"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    FAILED = "failed"
    REFUNDED = "refunded"


class ArbitrageFulfillmentEngine:
    """
    Complete arbitrage fulfillment automation
    
    Handles entire flow:
    1. Buyer purchases on Agent Directory
    2. System auto-purchases from source (Fiverr/RapidAPI/etc)
    3. Credentials/results forwarded to buyer
    4. Transaction marked complete
    5. Profit retained
    """
    
    def __init__(self, db: Session):
        self.db = db
        
        # Platform API credentials
        self.rapidapi_key = os.getenv('RAPIDAPI_KEY')
        self.huggingface_token = os.getenv('HUGGINGFACE_TOKEN')
        
        # Manual fulfillment tracking
        self.manual_queue_file = 'data/manual_fulfillment_queue.jsonl'
        self.fulfillment_log_file = 'data/fulfillment_log.jsonl'
        
        # Platform handlers
        self.handlers = {
            'rapidapi': self.fulfill_rapidapi,
            'huggingface': self.fulfill_huggingface,
            'github': self.fulfill_github,
            'fiverr': self.fulfill_fiverr_manual,
            'upwork': self.fulfill_upwork_manual,
            'default': self.fulfill_generic_api
        }
    
    # ==========================================
    # Main Fulfillment Flow
    # ==========================================
    
    async def process_transaction(self, transaction_id: str) -> Dict:
        """
        Main entry point - process arbitrage transaction
        """
        print(f"\n{'='*50}")
        print(f"Processing Arbitrage Transaction: {transaction_id}")
        print(f"{'='*50}\n")
        
        # Get transaction and listing
        transaction = self.db.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()
        
        if not transaction:
            return {'success': False, 'error': 'Transaction not found'}
        
        listing = self.db.query(Listing).filter(
            Listing.id == transaction.listing_id
        ).first()
        
        if not listing:
            return {'success': False, 'error': 'Listing not found'}
        
        # Verify it's an arbitrage listing
        if not listing.metadata.get('arbitrage_listing'):
            return {
                'success': False,
                'error': 'Not an arbitrage listing',
                'action': 'skip'
            }
        
        # Extract source info
        source_platform = listing.metadata.get('source_platform')
        source_url = listing.metadata.get('source_url')
        source_price = listing.metadata.get('source_price')
        
        print(f"Source: {source_platform}")
        print(f"URL: {source_url}")
        print(f"Buyer paid: ${transaction.amount_usd:.2f}")
        print(f"Source cost: ${source_price:.2f}")
        print(f"Expected profit: ${transaction.amount_usd - source_price:.2f}\n")
        
        # Update transaction status
        transaction.status = TransactionStatus.PROCESSING
        transaction.metadata = transaction.metadata or {}
        transaction.metadata['fulfillment_status'] = FulfillmentStatus.PURCHASING
        transaction.metadata['fulfillment_started_at'] = datetime.utcnow().isoformat()
        self.db.commit()
        
        # Route to appropriate handler
        handler = self.handlers.get(source_platform, self.handlers['default'])
        
        try:
            result = await handler(transaction, listing)
            
            if result['success']:
                # Mark transaction complete
                transaction.status = TransactionStatus.COMPLETED
                transaction.metadata['fulfillment_status'] = FulfillmentStatus.DELIVERED
                transaction.metadata['fulfillment_completed_at'] = datetime.utcnow().isoformat()
                transaction.metadata['fulfillment_result'] = result.get('delivery')
                self.db.commit()
                
                # Log success
                self.log_fulfillment(transaction_id, 'success', result)
                
                print(f"\n✅ Transaction {transaction_id} completed successfully")
                
                return result
            else:
                # Handle failure
                return await self.handle_fulfillment_failure(transaction, result)
        
        except Exception as e:
            return await self.handle_fulfillment_failure(
                transaction,
                {'success': False, 'error': str(e)}
            )
    
    # ==========================================
    # Platform-Specific Handlers
    # ==========================================
    
    async def fulfill_rapidapi(self, transaction: Transaction, listing: Listing) -> Dict:
        """
        RapidAPI - Full automation via API
        """
        print("[RapidAPI Handler] Automated fulfillment\n")
        
        api_endpoint = listing.metadata.get('api_endpoint')
        api_method = listing.metadata.get('api_method', 'POST')
        
        if not api_endpoint:
            return {'success': False, 'error': 'No API endpoint configured'}
        
        if not self.rapidapi_key:
            return {'success': False, 'error': 'RapidAPI key not configured'}
        
        # Extract buyer's input
        buyer_input = transaction.metadata.get('input_data', {})
        
        # Prepare request
        headers = {
            'X-RapidAPI-Key': self.rapidapi_key,
            'X-RapidAPI-Host': urlparse(api_endpoint).netloc,
            'Content-Type': 'application/json'
        }
        
        print(f"Calling: {api_method} {api_endpoint}")
        print(f"Input: {json.dumps(buyer_input, indent=2)}\n")
        
        try:
            if api_method.upper() == 'POST':
                response = requests.post(api_endpoint, json=buyer_input, headers=headers, timeout=30)
            else:
                response = requests.get(api_endpoint, params=buyer_input, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result_data = response.json()
                
                print(f"✅ RapidAPI call successful")
                print(f"Result: {json.dumps(result_data, indent=2)[:200]}...\n")
                
                return {
                    'success': True,
                    'platform': 'rapidapi',
                    'delivery': {
                        'type': 'api_result',
                        'data': result_data,
                        'delivered_at': datetime.utcnow().isoformat()
                    }
                }
            else:
                return {
                    'success': False,
                    'error': f'RapidAPI error: {response.status_code}',
                    'details': response.text
                }
        
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'RapidAPI call timeout'}
        except Exception as e:
            return {'success': False, 'error': f'RapidAPI exception: {str(e)}'}
    
    async def fulfill_huggingface(self, transaction: Transaction, listing: Listing) -> Dict:
        """
        Hugging Face Spaces - API automation
        """
        print("[Hugging Face Handler] Automated fulfillment\n")
        
        space_url = listing.metadata.get('source_url')
        buyer_input = transaction.metadata.get('input_data', {})
        
        # Hugging Face Spaces typically expose /api/predict
        api_url = self.construct_hf_api_url(space_url)
        
        headers = {}
        if self.huggingface_token:
            headers['Authorization'] = f'Bearer {self.huggingface_token}'
        
        print(f"Calling: {api_url}")
        print(f"Input: {json.dumps(buyer_input, indent=2)}\n")
        
        try:
            # HF Spaces expect data wrapped in 'data' array
            payload = {'data': [buyer_input]}
            
            response = requests.post(api_url, json=payload, headers=headers, timeout=60)
            
            if response.status_code == 200:
                result_data = response.json()
                
                print(f"✅ Hugging Face call successful\n")
                
                return {
                    'success': True,
                    'platform': 'huggingface',
                    'delivery': {
                        'type': 'api_result',
                        'data': result_data,
                        'delivered_at': datetime.utcnow().isoformat()
                    }
                }
            else:
                return {
                    'success': False,
                    'error': f'Hugging Face error: {response.status_code}'
                }
        
        except Exception as e:
            return {'success': False, 'error': f'HF exception: {str(e)}'}
    
    async def fulfill_github(self, transaction: Transaction, listing: Listing) -> Dict:
        """
        GitHub Marketplace - Deliver repository access
        """
        print("[GitHub Handler] Repository access delivery\n")
        
        repo_url = listing.metadata.get('source_url')
        
        # For GitHub repos, delivery is typically just the URL + instructions
        delivery = {
            'type': 'repository_access',
            'repository_url': repo_url,
            'clone_command': f'git clone {repo_url}',
            'instructions': listing.metadata.get('usage_instructions', 'See README.md'),
            'delivered_at': datetime.utcnow().isoformat()
        }
        
        print(f"✅ GitHub repository access delivered: {repo_url}\n")
        
        return {
            'success': True,
            'platform': 'github',
            'delivery': delivery
        }
    
    async def fulfill_generic_api(self, transaction: Transaction, listing: Listing) -> Dict:
        """
        Generic API service - Try standard REST call
        """
        print("[Generic API Handler] Attempting automated fulfillment\n")
        
        api_endpoint = listing.metadata.get('api_endpoint') or listing.metadata.get('source_url')
        buyer_input = transaction.metadata.get('input_data', {})
        
        if not api_endpoint:
            return await self.fulfill_manual(transaction, listing)
        
        try:
            response = requests.post(api_endpoint, json=buyer_input, timeout=30)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'platform': 'generic_api',
                    'delivery': {
                        'type': 'api_result',
                        'data': response.json(),
                        'delivered_at': datetime.utcnow().isoformat()
                    }
                }
            else:
                # API failed - try manual
                return await self.fulfill_manual(transaction, listing)
        
        except:
            # API failed - try manual
            return await self.fulfill_manual(transaction, listing)
    
    # ==========================================
    # Manual Fulfillment (Fiverr, Upwork)
    # ==========================================
    
    async def fulfill_fiverr_manual(self, transaction: Transaction, listing: Listing) -> Dict:
        """
        Fiverr - Queue for manual fulfillment
        """
        print("[Fiverr Handler] Manual fulfillment required\n")
        return await self.fulfill_manual(transaction, listing)
    
    async def fulfill_upwork_manual(self, transaction: Transaction, listing: Listing) -> Dict:
        """
        Upwork - Queue for manual fulfillment
        """
        print("[Upwork Handler] Manual fulfillment required\n")
        return await self.fulfill_manual(transaction, listing)
    
    async def fulfill_manual(self, transaction: Transaction, listing: Listing) -> Dict:
        """
        Queue transaction for manual fulfillment
        """
        manual_task = {
            'transaction_id': str(transaction.id),
            'buyer_agent_id': str(transaction.buyer_agent_id),
            'listing_id': str(listing.id),
            'service_name': listing.name,
            'source_platform': listing.metadata.get('source_platform'),
            'source_url': listing.metadata.get('source_url'),
            'source_price': listing.metadata.get('source_price'),
            'buyer_paid': transaction.amount_usd,
            'buyer_input': transaction.metadata.get('input_data', {}),
            'created_at': datetime.utcnow().isoformat(),
            'status': 'pending_human_action',
            'instructions': self.generate_manual_instructions(listing)
        }
        
        # Save to manual queue
        os.makedirs('data', exist_ok=True)
        with open(self.manual_queue_file, 'a') as f:
            f.write(json.dumps(manual_task) + '\n')
        
        # Update transaction
        transaction.metadata['fulfillment_status'] = 'pending_manual'
        transaction.metadata['manual_task_queued_at'] = datetime.utcnow().isoformat()
        self.db.commit()
        
        print(f"✅ Task queued for manual fulfillment")
        print(f"Queue: {self.manual_queue_file}\n")
        
        return {
            'success': True,
            'requires_manual': True,
            'platform': listing.metadata.get('source_platform'),
            'message': 'Queued for manual fulfillment',
            'task': manual_task
        }
    
    def generate_manual_instructions(self, listing: Listing) -> str:
        """
        Generate human-readable fulfillment instructions
        """
        platform = listing.metadata.get('source_platform')
        url = listing.metadata.get('source_url')
        price = listing.metadata.get('source_price')
        
        instructions = f"""
MANUAL FULFILLMENT REQUIRED

Platform: {platform}
Service: {listing.name}
URL: {url}
Budget: ${price:.2f}

STEPS:
1. Visit {url}
2. Purchase service (budget: ${price:.2f})
3. Provide buyer's requirements (see buyer_input)
4. Wait for delivery from seller
5. Forward results to buyer via Agent Directory
6. Mark transaction complete

DO NOT exceed budget of ${price:.2f}
"""
        return instructions.strip()
    
    # ==========================================
    # Delivery to Buyer
    # ==========================================
    
    async def deliver_to_buyer(self, transaction_id: str, delivery_data: Dict) -> Dict:
        """
        Forward fulfillment results to buyer
        """
        transaction = self.db.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()
        
        if not transaction:
            return {'success': False, 'error': 'Transaction not found'}
        
        # Store delivery data
        transaction.metadata['delivery'] = delivery_data
        transaction.metadata['delivered_at'] = datetime.utcnow().isoformat()
        
        # In production, would also:
        # 1. Send email notification to buyer
        # 2. Update buyer's dashboard
        # 3. Generate delivery receipt
        
        self.db.commit()
        
        print(f"✅ Results delivered to buyer (transaction {transaction_id})")
        
        return {'success': True, 'delivered': True}
    
    # ==========================================
    # Error Handling
    # ==========================================
    
    async def handle_fulfillment_failure(self, transaction: Transaction, error_result: Dict) -> Dict:
        """
        Handle fulfillment failure - potentially refund buyer
        """
        print(f"\n❌ Fulfillment failed: {error_result.get('error')}\n")
        
        transaction.status = TransactionStatus.FAILED
        transaction.metadata['fulfillment_status'] = FulfillmentStatus.FAILED
        transaction.metadata['fulfillment_error'] = error_result.get('error')
        transaction.metadata['failed_at'] = datetime.utcnow().isoformat()
        
        # Initiate refund
        if transaction.stripe_payment_intent_id:
            print("Initiating refund...")
            
            # Refund via Stripe
            try:
                import stripe
                refund = stripe.Refund.create(
                    payment_intent=transaction.stripe_payment_intent_id,
                    reason='failed_fulfillment'
                )
                
                transaction.status = TransactionStatus.REFUNDED
                transaction.metadata['fulfillment_status'] = FulfillmentStatus.REFUNDED
                transaction.metadata['refund_id'] = refund.id
                transaction.metadata['refunded_at'] = datetime.utcnow().isoformat()
                
                print(f"✅ Refund issued: {refund.id}\n")
            
            except Exception as e:
                print(f"❌ Refund failed: {str(e)}\n")
                transaction.metadata['refund_error'] = str(e)
        
        self.db.commit()
        
        # Log failure
        self.log_fulfillment(str(transaction.id), 'failed', error_result)
        
        return {
            'success': False,
            'refunded': transaction.status == TransactionStatus.REFUNDED,
            **error_result
        }
    
    # ==========================================
    # Helpers
    # ==========================================
    
    def construct_hf_api_url(self, space_url: str) -> str:
        """
        Convert Hugging Face Space URL to API endpoint
        """
        # https://huggingface.co/spaces/username/space-name
        # → https://username-space-name.hf.space/api/predict
        
        if '/spaces/' in space_url:
            parts = space_url.split('/spaces/')[-1].split('/')
            username = parts[0]
            space_name = parts[1] if len(parts) > 1 else parts[0]
            
            return f"https://{username}-{space_name}.hf.space/api/predict"
        
        return space_url
    
    def log_fulfillment(self, transaction_id: str, status: str, details: Dict):
        """
        Log fulfillment event for analytics
        """
        log_entry = {
            'transaction_id': transaction_id,
            'timestamp': datetime.utcnow().isoformat(),
            'status': status,
            'details': details
        }
        
        os.makedirs('data', exist_ok=True)
        with open(self.fulfillment_log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    # ==========================================
    # Manual Queue Management
    # ==========================================
    
    def get_manual_queue(self) -> List[Dict]:
        """
        Get all pending manual fulfillment tasks
        """
        if not os.path.exists(self.manual_queue_file):
            return []
        
        tasks = []
        with open(self.manual_queue_file, 'r') as f:
            for line in f:
                if line.strip():
                    task = json.loads(line)
                    if task.get('status') == 'pending_human_action':
                        tasks.append(task)
        
        return tasks
    
    def mark_manual_task_complete(self, transaction_id: str, delivery_data: Dict) -> Dict:
        """
        Mark manual task as complete and deliver to buyer
        """
        # Update transaction
        transaction = self.db.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()
        
        if not transaction:
            return {'success': False, 'error': 'Transaction not found'}
        
        transaction.status = TransactionStatus.COMPLETED
        transaction.metadata['fulfillment_status'] = FulfillmentStatus.DELIVERED
        transaction.metadata['fulfillment_completed_at'] = datetime.utcnow().isoformat()
        transaction.metadata['delivery'] = delivery_data
        self.db.commit()
        
        # Remove from queue (rewrite file without this task)
        self.remove_from_manual_queue(transaction_id)
        
        # Log success
        self.log_fulfillment(transaction_id, 'manual_complete', delivery_data)
        
        return {'success': True, 'completed': True}
    
    def remove_from_manual_queue(self, transaction_id: str):
        """
        Remove task from manual queue
        """
        if not os.path.exists(self.manual_queue_file):
            return
        
        tasks = []
        with open(self.manual_queue_file, 'r') as f:
            for line in f:
                if line.strip():
                    task = json.loads(line)
                    if task.get('transaction_id') != transaction_id:
                        tasks.append(task)
        
        with open(self.manual_queue_file, 'w') as f:
            for task in tasks:
                f.write(json.dumps(task) + '\n')


# ==========================================
# Profit Calculator
# ==========================================

def calculate_net_profit(
    buyer_paid: float,
    source_cost: float,
    platform: str = 'fiverr'
) -> Dict:
    """
    Calculate actual profit after all fees
    """
    # Platform fees (what they charge us)
    platform_fees = {
        'fiverr': source_cost * 0.05,  # Fiverr processing fee ~5%
        'upwork': source_cost * 0.03,
        'rapidapi': 0,  # RapidAPI usage is pay-per-call (already in source_cost)
        'huggingface': 0,  # Usually free
        'github': 0
    }
    
    # Our platform commission (6%)
    our_commission = buyer_paid * 0.06
    
    # Stripe fees (2.9% + $0.30)
    stripe_fee = (buyer_paid * 0.029) + 0.30
    
    # Calculate
    gross_profit = buyer_paid - source_cost
    platform_fee = platform_fees.get(platform, 0)
    total_costs = source_cost + our_commission + stripe_fee + platform_fee
    net_profit = buyer_paid - total_costs
    
    return {
        'buyer_paid': buyer_paid,
        'costs': {
            'source_purchase': source_cost,
            'our_commission': our_commission,
            'stripe_fee': stripe_fee,
            'platform_fee': platform_fee,
            'total_costs': total_costs
        },
        'gross_profit': gross_profit,
        'net_profit': net_profit,
        'profit_margin_percent': (net_profit / buyer_paid) * 100 if buyer_paid > 0 else 0
    }
