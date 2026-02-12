"""
Agent Eagle - Arbitrage Transaction Handler
Manages middleman transactions for sourced services
"""
import requests
import json
from typing import Dict, Optional
from datetime import datetime


class ArbitrageHandler:
    """
    Handles transactions for arbitrage listings
    When a buyer purchases a sourced service:
    1. Receive purchase on Agent Eagle
    2. Purchase from source platform
    3. Deliver result to buyer
    4. Process payments and profit
    """
    
    def __init__(self, agent_eagle_api_url: str):
        self.api_url = agent_eagle_api_url
        self.platform_handlers = {
            'fiverr': self.handle_fiverr_purchase,
            'upwork': self.handle_upwork_purchase,
            'rapidapi': self.handle_rapidapi_purchase,
            'huggingface': self.handle_huggingface_purchase
        }
    
    def process_arbitrage_transaction(self, transaction: Dict) -> Dict:
        """
        Main arbitrage flow handler
        """
        print(f"\n=== Processing Arbitrage Transaction ===")
        print(f"Transaction ID: {transaction['id']}")
        
        # Get listing metadata
        listing = self.get_listing(transaction['listing_id'])
        
        if not listing.get('metadata', {}).get('arbitrage_listing'):
            print("[SKIP] Not an arbitrage listing")
            return {'status': 'not_arbitrage'}
        
        source_platform = listing['metadata']['source_platform']
        source_url = listing['metadata']['source_url']
        source_price = listing['metadata']['source_price']
        
        print(f"Source: {source_platform}")
        print(f"Buyer pays: ${transaction['amount_usd']:.2f}")
        print(f"Source cost: ${source_price:.2f}")
        print(f"Expected profit: ${transaction['amount_usd'] - source_price:.2f}")
        
        # Route to platform-specific handler
        handler = self.platform_handlers.get(source_platform)
        
        if not handler:
            return self.handle_error(transaction, f"No handler for platform: {source_platform}")
        
        try:
            result = handler(transaction, listing)
            return result
        except Exception as e:
            return self.handle_error(transaction, str(e))
    
    def handle_fiverr_purchase(self, transaction: Dict, listing: Dict) -> Dict:
        """
        Handle Fiverr arbitrage purchase
        
        Flow:
        1. Parse buyer's input requirements
        2. Create Fiverr order (via API or manual)
        3. Wait for Fiverr delivery
        4. Forward result to buyer
        5. Mark transaction complete
        """
        print("\n[Fiverr Handler]")
        
        source_url = listing['metadata']['source_url']
        input_data = transaction.get('input_data', {})
        
        # Note: Fiverr doesn't have public API for placing orders
        # Options:
        # 1. Manual intervention (notify human to place order)
        # 2. Use Fiverr affiliate links + manual fulfillment
        # 3. Direct seller contact if available
        
        print("[!] Fiverr requires manual order placement")
        print(f"    URL: {source_url}")
        print(f"    Requirements: {json.dumps(input_data, indent=2)}")
        
        # Create manual fulfillment task
        task = {
            'transaction_id': transaction['id'],
            'action': 'place_fiverr_order',
            'url': source_url,
            'requirements': input_data,
            'budget': listing['metadata']['source_price'],
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Save to manual fulfillment queue
        self.queue_manual_fulfillment(task)
        
        return {
            'status': 'pending_manual_fulfillment',
            'message': 'Order queued for manual placement on Fiverr',
            'task_id': task['transaction_id']
        }
    
    def handle_rapidapi_purchase(self, transaction: Dict, listing: Dict) -> Dict:
        """
        Handle RapidAPI arbitrage purchase
        
        RapidAPI has programmatic API access - can automate fully
        """
        print("\n[RapidAPI Handler]")
        
        # RapidAPI services can be called directly
        api_endpoint = listing['metadata'].get('api_endpoint')
        input_data = transaction.get('input_data', {})
        
        if not api_endpoint:
            return {'status': 'error', 'message': 'No API endpoint configured'}
        
        try:
            # Call RapidAPI service
            headers = {
                'X-RapidAPI-Key': self.get_rapidapi_key(),
                'X-RapidAPI-Host': self.extract_host(api_endpoint)
            }
            
            response = requests.post(api_endpoint, json=input_data, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                
                # Update transaction with result
                self.update_transaction_result(transaction['id'], result)
                
                return {
                    'status': 'completed',
                    'result': result,
                    'source': 'rapidapi'
                }
            else:
                return {
                    'status': 'error',
                    'message': f'RapidAPI call failed: {response.status_code}'
                }
                
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def handle_huggingface_purchase(self, transaction: Dict, listing: Dict) -> Dict:
        """
        Handle Hugging Face Spaces arbitrage
        
        HF Spaces have public APIs - can automate
        """
        print("\n[Hugging Face Handler]")
        
        space_url = listing['metadata']['source_url']
        input_data = transaction.get('input_data', {})
        
        # Hugging Face Spaces typically have /api/predict endpoint
        api_url = space_url.replace('/spaces/', '/') + '/api/predict'
        
        try:
            response = requests.post(api_url, json={'data': [input_data]})
            
            if response.status_code == 200:
                result = response.json()
                
                # Update transaction
                self.update_transaction_result(transaction['id'], result)
                
                return {
                    'status': 'completed',
                    'result': result,
                    'source': 'huggingface'
                }
            else:
                return {'status': 'error', 'message': f'HF API call failed'}
                
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def handle_upwork_purchase(self, transaction: Dict, listing: Dict) -> Dict:
        """
        Handle Upwork arbitrage (requires manual fulfillment)
        """
        print("\n[Upwork Handler]")
        print("[!] Upwork requires manual order placement")
        
        task = {
            'transaction_id': transaction['id'],
            'action': 'place_upwork_order',
            'url': listing['metadata']['source_url'],
            'requirements': transaction.get('input_data', {}),
            'budget': listing['metadata']['source_price']
        }
        
        self.queue_manual_fulfillment(task)
        
        return {
            'status': 'pending_manual_fulfillment',
            'message': 'Order queued for manual placement on Upwork'
        }
    
    def queue_manual_fulfillment(self, task: Dict):
        """
        Add task to manual fulfillment queue
        """
        queue_file = 'manual_fulfillment_queue.jsonl'
        
        with open(queue_file, 'a') as f:
            f.write(json.dumps(task) + '\n')
        
        print(f"[OK] Task queued: {queue_file}")
    
    def update_transaction_result(self, transaction_id: str, result: Dict):
        """
        Update transaction with output data
        """
        # Would call Agent Eagle API to update transaction
        print(f"[OK] Transaction {transaction_id} updated with result")
    
    def handle_error(self, transaction: Dict, error_message: str) -> Dict:
        """
        Handle transaction error
        """
        print(f"[ERROR] {error_message}")
        
        # Update transaction status
        # Potentially refund buyer
        # Log for review
        
        return {
            'status': 'error',
            'message': error_message,
            'transaction_id': transaction['id']
        }
    
    def get_listing(self, listing_id: str) -> Dict:
        """
        Fetch listing details from Agent Eagle
        """
        # Placeholder - would call Agent Eagle API
        return {}
    
    def get_rapidapi_key(self) -> str:
        """
        Get RapidAPI credentials
        """
        # Would load from secure config
        return "RAPIDAPI_KEY_HERE"
    
    def extract_host(self, url: str) -> str:
        """
        Extract host from URL
        """
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc


def calculate_arbitrage_profit(buyer_price: float, source_price: float, source_platform: str) -> Dict:
    """
    Calculate actual profit after all fees
    """
    # Platform fees (what we pay to source)
    platform_fees = {
        'fiverr': source_price * 0.20,  # Fiverr takes 20%
        'upwork': source_price * 0.10,
        'rapidapi': source_price * 0.15,
        'huggingface': 0  # Usually free
    }
    
    # Agent Eagle commission (6%)
    agent_eagle_commission = buyer_price * 0.06
    
    # Payment processing (Stripe ~3%)
    payment_processing = buyer_price * 0.03
    
    # Calculate
    gross_profit = buyer_price - source_price
    platform_fee = platform_fees.get(source_platform, 0)
    total_fees = agent_eagle_commission + payment_processing + platform_fee
    net_profit = gross_profit - total_fees
    
    return {
        'buyer_pays': buyer_price,
        'source_cost': source_price,
        'gross_profit': gross_profit,
        'fees': {
            'agent_eagle_commission': agent_eagle_commission,
            'platform_fee': platform_fee,
            'payment_processing': payment_processing,
            'total': total_fees
        },
        'net_profit': net_profit,
        'profit_margin_percent': (net_profit / buyer_price) * 100
    }


if __name__ == "__main__":
    # Example calculation
    print("=== Arbitrage Profit Calculation ===\n")
    
    example = calculate_arbitrage_profit(
        buyer_price=27.00,
        source_price=25.00,
        source_platform='fiverr'
    )
    
    print(f"Buyer pays: ${example['buyer_pays']:.2f}")
    print(f"Source cost: ${example['source_cost']:.2f}")
    print(f"Gross profit: ${example['gross_profit']:.2f}")
    print(f"\nFees:")
    print(f"  Agent Eagle (6%): ${example['fees']['agent_eagle_commission']:.2f}")
    print(f"  Platform fee: ${example['fees']['platform_fee']:.2f}")
    print(f"  Payment processing: ${example['fees']['payment_processing']:.2f}")
    print(f"  Total fees: ${example['fees']['total']:.2f}")
    print(f"\nNet profit: ${example['net_profit']:.2f}")
    print(f"Profit margin: {example['profit_margin_percent']:.1f}%")
