"""
Agent Eagle - Web Crawler for AI Agent Services
Finds existing AI agents/services across platforms and lists them on Agent Eagle marketplace
Arbitrage strategy: List with small markup, act as middleman
"""
import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
import re


class AgentServiceCrawler:
    """
    Crawls various platforms to find AI agent services
    """
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.found_services = []
        self.platforms = {
            'fiverr': self.crawl_fiverr,
            'upwork': self.crawl_upwork,
            'rapidapi': self.crawl_rapidapi,
            'huggingface': self.crawl_huggingface
        }
    
    def crawl_fiverr(self, keywords: List[str]) -> List[Dict]:
        """
        Crawl Fiverr for AI/automation services
        """
        print(f"\n=== Crawling Fiverr for AI services ===")
        services = []
        
        for keyword in keywords:
            print(f"Searching: {keyword}")
            url = f"https://www.fiverr.com/search/gigs?query={keyword.replace(' ', '%20')}&source=top-bar&search_in=everywhere"
            
            try:
                response = requests.get(url, headers=self.headers)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find gig cards (Fiverr's structure - may need updating)
                gigs = soup.find_all('div', class_='gig-card-layout')[:10]  # First 10 results
                
                for gig in gigs:
                    try:
                        # Extract service details
                        title_elem = gig.find('a', class_='gig-link')
                        price_elem = gig.find('span', class_='price')
                        rating_elem = gig.find('span', class_='rating-score')
                        
                        if title_elem and price_elem:
                            service = {
                                'platform': 'fiverr',
                                'title': title_elem.text.strip(),
                                'url': 'https://www.fiverr.com' + title_elem.get('href', ''),
                                'price': self.extract_price(price_elem.text),
                                'rating': self.extract_rating(rating_elem.text if rating_elem else '0'),
                                'capability': self.infer_capability(title_elem.text),
                                'category': keyword,
                                'discovered_at': datetime.utcnow().isoformat()
                            }
                            services.append(service)
                            print(f"  [+] Found: {service['title']} - ${service['price']}")
                    except Exception as e:
                        continue
                
                time.sleep(2)  # Rate limiting
                
            except Exception as e:
                print(f"  [!] Error crawling Fiverr: {e}")
        
        return services
    
    def crawl_upwork(self, keywords: List[str]) -> List[Dict]:
        """
        Crawl Upwork for AI freelancers (requires API access for full data)
        """
        print(f"\n=== Crawling Upwork (Limited without API) ===")
        services = []
        
        # Note: Upwork requires authentication for most data
        # This would need Upwork API integration for production
        
        print("  [!] Upwork requires API access - returning placeholder")
        return services
    
    def crawl_rapidapi(self, keywords: List[str]) -> List[Dict]:
        """
        Crawl RapidAPI marketplace for AI APIs
        """
        print(f"\n=== Crawling RapidAPI for AI APIs ===")
        services = []
        
        for keyword in keywords:
            print(f"Searching: {keyword}")
            url = f"https://rapidapi.com/search/{keyword.replace(' ', '-')}"
            
            try:
                response = requests.get(url, headers=self.headers)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # RapidAPI structure (simplified - may need updating)
                apis = soup.find_all('div', class_='api-card')[:10]
                
                for api in apis:
                    try:
                        title_elem = api.find('h3')
                        price_elem = api.find('span', class_='price')
                        
                        if title_elem:
                            service = {
                                'platform': 'rapidapi',
                                'title': title_elem.text.strip(),
                                'url': url,
                                'price': self.extract_price(price_elem.text if price_elem else 'Free'),
                                'capability': self.infer_capability(title_elem.text),
                                'category': 'api',
                                'discovered_at': datetime.utcnow().isoformat()
                            }
                            services.append(service)
                            print(f"  [+] Found: {service['title']}")
                    except:
                        continue
                
                time.sleep(2)
                
            except Exception as e:
                print(f"  [!] Error crawling RapidAPI: {e}")
        
        return services
    
    def crawl_huggingface(self, keywords: List[str]) -> List[Dict]:
        """
        Crawl Hugging Face Spaces for deployed AI models
        """
        print(f"\n=== Crawling Hugging Face Spaces ===")
        services = []
        
        try:
            # Hugging Face has a public API
            url = "https://huggingface.co/api/spaces"
            response = requests.get(url, headers=self.headers)
            spaces = response.json()[:20]  # First 20 spaces
            
            for space in spaces:
                try:
                    service = {
                        'platform': 'huggingface',
                        'title': space.get('id', '').replace('/', ' - '),
                        'url': f"https://huggingface.co/spaces/{space.get('id')}",
                        'price': 0,  # Most HF spaces are free
                        'capability': self.infer_capability(space.get('id', '')),
                        'category': 'ai_model',
                        'discovered_at': datetime.utcnow().isoformat()
                    }
                    services.append(service)
                    print(f"  [+] Found: {service['title']}")
                except:
                    continue
            
        except Exception as e:
            print(f"  [!] Error crawling Hugging Face: {e}")
        
        return services
    
    def extract_price(self, price_text: str) -> float:
        """Extract numeric price from text"""
        try:
            # Remove currency symbols and extract number
            numbers = re.findall(r'\d+\.?\d*', price_text)
            return float(numbers[0]) if numbers else 0.0
        except:
            return 0.0
    
    def extract_rating(self, rating_text: str) -> float:
        """Extract numeric rating"""
        try:
            numbers = re.findall(r'\d+\.?\d*', rating_text)
            return float(numbers[0]) if numbers else 0.0
        except:
            return 0.0
    
    def infer_capability(self, title: str) -> str:
        """
        Infer agent capability from service title
        """
        title_lower = title.lower()
        
        capability_keywords = {
            'research': ['research', 'analysis', 'market', 'data'],
            'writing': ['writing', 'content', 'copy', 'article'],
            'coding': ['code', 'programming', 'development', 'software'],
            'design': ['design', 'graphic', 'logo', 'ui', 'ux'],
            'translation': ['translate', 'translation', 'language'],
            'data_analysis': ['data', 'analytics', 'visualization', 'excel'],
            'ai_automation': ['ai', 'automation', 'bot', 'chatbot', 'gpt'],
            'image_generation': ['image', 'generate', 'art', 'stable diffusion'],
            'text_generation': ['text', 'generate', 'gpt', 'writing'],
            'sentiment_analysis': ['sentiment', 'emotion', 'opinion'],
            'recommendation': ['recommend', 'suggestion', 'matching'],
            'classification': ['classify', 'categorize', 'label'],
            'prediction': ['predict', 'forecast', 'estimate']
        }
        
        for capability, keywords in capability_keywords.items():
            if any(keyword in title_lower for keyword in keywords):
                return capability
        
        return 'general'
    
    def calculate_markup_price(self, source_price: float, platform: str) -> float:
        """
        Calculate Agent Eagle listing price with small markup
        
        Strategy:
        - Very low margin to be competitive
        - Enough to cover platform fees + small profit
        """
        if source_price == 0:
            return 9.99  # Default for free services
        
        # Platform fees (estimate)
        platform_fees = {
            'fiverr': 0.20,  # Fiverr takes 20%
            'upwork': 0.10,  # Upwork takes 10%
            'rapidapi': 0.15,  # Varies
            'huggingface': 0.05  # Minimal (mostly free)
        }
        
        platform_fee_rate = platform_fees.get(platform, 0.10)
        
        # Our markup: 8% above source price
        our_markup = 0.08
        
        # Calculate: source + platform fees + our markup
        agent_eagle_price = source_price * (1 + platform_fee_rate + our_markup)
        
        # Round to .99
        return round(agent_eagle_price) - 0.01
    
    def create_listing_data(self, service: Dict) -> Dict:
        """
        Convert crawled service to Agent Eagle listing format
        """
        agent_eagle_price = self.calculate_markup_price(
            service['price'],
            service['platform']
        )
        
        return {
            'title': f"{service['title']} (via {service['platform'].title()})",
            'description': f"""AI service sourced from {service['platform'].title()} marketplace.

Original service: {service['url']}
Capability: {service['capability']}
Category: {service['category']}

This is an arbitrage listing - Agent Eagle acts as middleman to provide access to this service. 
Small markup covers platform fees and ensures reliable delivery.

Response time may vary based on source platform availability.
""",
            'listing_type': 'capability',
            'category': service['category'],
            'tags': [service['capability'], service['platform'], 'arbitrage', 'sourced'],
            'price_usd': agent_eagle_price,
            'pricing_model': 'per_query',
            'capability_name': service['capability'],
            'expected_response_time_seconds': 3600,  # Conservative 1 hour
            'metadata': {
                'source_platform': service['platform'],
                'source_url': service['url'],
                'source_price': service['price'],
                'arbitrage_listing': True,
                'discovered_at': service['discovered_at'],
                'rating': service.get('rating', 0)
            }
        }
    
    def crawl_all_platforms(self, keywords: List[str]) -> List[Dict]:
        """
        Crawl all configured platforms
        """
        all_services = []
        
        for platform_name, crawler_func in self.platforms.items():
            try:
                services = crawler_func(keywords)
                all_services.extend(services)
            except Exception as e:
                print(f"[ERROR] Failed to crawl {platform_name}: {e}")
        
        return all_services


def main():
    """
    Main crawler execution
    """
    print("="*60)
    print("AGENT EAGLE - WEB CRAWLER FOR AI SERVICES")
    print("="*60)
    print("Strategy: Find AI agents/services, list with small markup")
    print("Goal: Build massive catalog quickly via arbitrage")
    print("="*60)
    
    # Keywords to search for
    AI_SERVICE_KEYWORDS = [
        'ai agent',
        'chatbot',
        'gpt automation',
        'data analysis',
        'market research',
        'content writing ai',
        'image generation',
        'code generation',
        'translation ai',
        'sentiment analysis',
        'recommendation engine',
        'ai automation',
        'machine learning service'
    ]
    
    crawler = AgentServiceCrawler()
    
    print(f"\nSearching {len(AI_SERVICE_KEYWORDS)} keywords across platforms...")
    
    # Crawl all platforms
    found_services = crawler.crawl_all_platforms(AI_SERVICE_KEYWORDS)
    
    print("\n" + "="*60)
    print(f"CRAWL COMPLETE: Found {len(found_services)} services")
    print("="*60)
    
    # Convert to listings
    listings = []
    for service in found_services:
        listing_data = crawler.create_listing_data(service)
        listings.append(listing_data)
    
    # Save results
    output_file = 'discovered_agent_services.json'
    with open(output_file, 'w') as f:
        json.dump({
            'discovered_at': datetime.utcnow().isoformat(),
            'total_services': len(found_services),
            'services': found_services,
            'listings_ready': listings
        }, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    print(f"Ready to list: {len(listings)} services")
    
    # Summary by platform
    platform_counts = {}
    for service in found_services:
        platform = service['platform']
        platform_counts[platform] = platform_counts.get(platform, 0) + 1
    
    print("\nPlatform Summary:")
    for platform, count in platform_counts.items():
        print(f"  {platform}: {count} services")
    
    # Price range
    prices = [s['price'] for s in found_services if s['price'] > 0]
    if prices:
        print(f"\nPrice Range:")
        print(f"  Source: ${min(prices):.2f} - ${max(prices):.2f}")
        markup_prices = [crawler.calculate_markup_price(p, 'fiverr') for p in prices]
        print(f"  Agent Eagle: ${min(markup_prices):.2f} - ${max(markup_prices):.2f}")
        print(f"  Average Markup: 8% + platform fees")
    
    return found_services, listings


if __name__ == "__main__":
    services, listings = main()
