"""
Register all 8 SIBYSI agents on Agent Eagle marketplace
Creates agent accounts and listings for each SIBYSI capability
"""
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000/api/v1"  # Change to production when deployed
SIBYSI_API_URL = "https://sibysi.ai"
OWNER_EMAIL = "steve@theaerie.ai"

# Agent configurations
SIBYSI_AGENTS = [
    {
        "name": "SIBYSI Niche Hunter",
        "stage": 1,
        "capability": "niche_discovery",
        "capabilities_list": ["niche_discovery", "market_opportunity", "trend_analysis", "sibysi"],
        "price": 9.99,
        "response_time_seconds": 300,
        "description": "Market opportunity discovery agent - generates 5-7 profitable niche ideas with comprehensive scoring and trend analysis",
        "listing_title": "Profitable Niche Discovery - 5-7 Market Opportunities",
        "listing_description": """The SIBYSI Niche Hunter identifies profitable market opportunities using the Eagle Sourcing Method.

What you get:
• 5-7 distinct niche opportunities
• Market size estimates and scoring
• Competition intensity analysis
• Trend momentum ratings  
• Profit potential assessment
• Target customer profiles
• Structured JSON output

Perfect for: Product sourcing agents, market research, business opportunity discovery
Response time: 2-5 minutes
Methodology: Eagle Sourcing Method Stage 1""",
        "category": "market_research"
    },
    {
        "name": "SIBYSI Product Scout",
        "stage": 2,
        "capability": "product_viability",
        "capabilities_list": ["product_viability", "product_ideation", "market_fit", "sibysi"],
        "price": 14.99,
        "response_time_seconds": 300,
        "description": "Product viability analysis - generates 5-7 specific product concepts with differentiation and market fit scoring",
        "listing_title": "Product Concept Generation - Viable Ideas with Market Fit",
        "listing_description": """The SIBYSI Product Scout generates specific product concepts for validated niches.

What you get:
• 5-7 detailed product concepts
• Key features and specifications
• Differentiation analysis
• Product-market fit scoring
• Manufacturing feasibility assessment
• Pricing recommendations
• Structured JSON output

Perfect for: Product development agents, sourcing automation, innovation discovery
Response time: 3-5 minutes
Methodology: Eagle Sourcing Method Stage 2""",
        "category": "product_development"
    },
    {
        "name": "SIBYSI Benchmarker",
        "stage": 3,
        "capability": "competitive_analysis",
        "capabilities_list": ["competitive_analysis", "market_analysis", "positioning", "sibysi"],
        "price": 19.99,
        "response_time_seconds": 600,
        "description": "Competitive market analysis - analyzes 3-5 competitors with pricing, features, and positioning recommendations",
        "listing_title": "Market & Competitive Analysis - Know Your Competition",
        "listing_description": """The SIBYSI Benchmarker analyzes competitors and identifies market positioning opportunities.

What you get:
• 3-5 key competitor profiles
• Pricing and feature comparison
• Market gap identification
• Competitive advantage analysis
• Positioning recommendations
• Market entry difficulty assessment
• Structured JSON output

Perfect for: Strategic planning agents, market entry analysis, competitive intelligence
Response time: 5-10 minutes
Methodology: Eagle Sourcing Method Stage 3""",
        "category": "market_research"
    },
    {
        "name": "SIBYSI Problem Solver",
        "stage": 4,
        "capability": "value_proposition",
        "capabilities_list": ["value_proposition", "pain_point_analysis", "positioning", "sibysi"],
        "price": 12.99,
        "response_time_seconds": 300,
        "description": "Value proposition design - identifies customer pain points and maps product solutions",
        "listing_title": "Pain Point Analysis & Value Proposition Design",
        "listing_description": """The SIBYSI Problem Solver identifies customer pain points and designs compelling value propositions.

What you get:
• 3-5 core customer pain points
• Severity and frequency assessment
• Solution mapping to product features
• Value proposition statements
• Positioning strategy
• Target customer personas
• Structured JSON output

Perfect for: Marketing agents, positioning strategy, messaging development
Response time: 3-5 minutes
Methodology: Eagle Sourcing Method Stage 4""",
        "category": "marketing"
    },
    {
        "name": "SIBYSI Cost Analyst",
        "stage": 5,
        "capability": "cost_estimation",
        "capabilities_list": ["cost_estimation", "margin_analysis", "pricing", "sibysi"],
        "price": 14.99,
        "response_time_seconds": 300,
        "description": "Fast cost estimation - 5-minute product cost analysis with landed costs and margin calculations",
        "listing_title": "Fast Cost Estimation - Accurate Margins in 5 Minutes",
        "listing_description": """The SIBYSI Cost Analyst provides rapid, accurate cost estimates using the Eagle 5-Minute Method.

What you get:
• Component cost breakdown
• Manufacturing cost estimates
• Logistics and freight costs
• Landed cost calculation
• Margin analysis (gross & net)
• MOQ investment requirements
• Structured JSON output

Perfect for: Sourcing agents, financial analysis, pricing strategy
Response time: 2-5 minutes
Methodology: Eagle Sourcing Method Stage 5""",
        "category": "financial_analysis"
    },
    {
        "name": "SIBYSI Manufacturer Finder",
        "stage": 6,
        "capability": "factory_discovery",
        "capabilities_list": ["factory_discovery", "supplier_sourcing", "manufacturing", "sibysi"],
        "price": 24.99,
        "response_time_seconds": 900,
        "description": "Factory discovery - finds 5-7 potential manufacturers with contact information and capability assessment",
        "listing_title": "Manufacturer Discovery - Find Qualified Factories Fast",
        "listing_description": """The SIBYSI Manufacturer Finder discovers qualified factories using multi-platform search.

What you get:
• 5-7 potential manufacturer profiles
• Company details and location
• MOQ and lead time information
• Certifications and capabilities
• Contact information
• Suitability scoring
• Structured JSON output

Perfect for: Sourcing agents, procurement automation, factory vetting
Response time: 10-15 minutes
Methodology: Eagle Sourcing Method Stage 6""",
        "category": "sourcing"
    },
    {
        "name": "SIBYSI Supplier Selector",
        "stage": 7,
        "capability": "supplier_evaluation",
        "capabilities_list": ["supplier_evaluation", "vendor_scoring", "risk_assessment", "sibysi"],
        "price": 19.99,
        "response_time_seconds": 600,
        "description": "Vendor evaluation - scores and ranks suppliers using 10-criteria assessment matrix",
        "listing_title": "Supplier Evaluation & Selection - Choose Wisely",
        "listing_description": """The SIBYSI Supplier Selector evaluates and ranks manufacturers using comprehensive criteria.

What you get:
• 10-criteria supplier evaluation
• Weighted scoring system
• Risk assessment
• Strengths and weaknesses analysis
• Recommended supplier ranking
• Next steps and action items
• Structured JSON output

Perfect for: Procurement agents, vendor management, risk assessment
Response time: 5-10 minutes
Methodology: Eagle Sourcing Method Stage 7""",
        "category": "sourcing"
    },
    {
        "name": "SIBYSI Sample Seller",
        "stage": 8,
        "capability": "presale_validation",
        "capabilities_list": ["presale_validation", "marketing_strategy", "validation", "sibysi"],
        "price": 29.99,
        "response_time_seconds": 900,
        "description": "Pre-sale validation strategy - designs landing page, marketing plan, and success metrics",
        "listing_title": "Pre-Sale Validation Strategy - Sell Before You Source",
        "listing_description": """The SIBYSI Sample Seller creates comprehensive pre-sale validation strategies (Eagle Method core principle).

What you get:
• Landing page design outline
• Marketing strategy (ads, targeting)
• Budget and timeline estimates
• Success metrics and thresholds
• Go/No-Go decision framework
• Expected ROI calculations
• Structured JSON output

Perfect for: Validation agents, marketing automation, risk mitigation
Response time: 10-15 minutes
Methodology: Eagle Sourcing Method Stage 8""",
        "category": "marketing"
    }
]

def register_agent(agent_config):
    """Register a single SIBYSI agent"""
    print(f"\n{'='*60}")
    print(f"Registering: {agent_config['name']}")
    print(f"{'='*60}")
    
    # Register agent
    agent_data = {
        "name": agent_config['name'],
        "description": agent_config['description'],
        "agent_type": "capability",
        "owner_email": OWNER_EMAIL,
        "capabilities": agent_config['capabilities_list'],
        "pricing_model": {
            "per_query": agent_config['price'],
            "bulk_discount": {
                "10+": 0.9,   # 10% off for 10+ purchases
                "50+": 0.8,   # 20% off for 50+ purchases
                "100+": 0.7   # 30% off for 100+ purchases
            }
        },
        "api_endpoint": f"{SIBYSI_API_URL}/api/stage-{agent_config['stage']}"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/agents", json=agent_data)
        
        if response.status_code == 201:
            result = response.json()
            agent = result['agent']
            print(f"[OK] Agent registered successfully")
            print(f"     Agent ID: {agent['id']}")
            print(f"     API Key: {agent['api_key'][:20]}... (saved)")
            
            # Save to config
            agent_config['agent_id'] = agent['id']
            agent_config['api_key'] = agent['api_key']
            agent_config['registered_at'] = datetime.utcnow().isoformat()
            
            return agent
        else:
            print(f"[FAIL] Registration failed: {response.status_code}")
            print(f"       {response.text}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Exception during registration: {e}")
        return None


def create_listing(agent_config, agent_id):
    """Create marketplace listing for agent"""
    print(f"\nCreating marketplace listing...")
    
    listing_data = {
        "seller_agent_id": agent_id,
        "title": agent_config['listing_title'],
        "description": agent_config['listing_description'],
        "listing_type": "capability",
        "category": agent_config['category'],
        "tags": agent_config['capabilities_list'],
        "price_usd": agent_config['price'],
        "pricing_model": "per_query",
        "capability_name": agent_config['capability'],
        "expected_response_time_seconds": agent_config['response_time_seconds'],
        "input_schema": {
            "type": "object",
            "description": f"Input parameters for {agent_config['name']}"
        },
        "output_schema": {
            "type": "object",
            "description": f"Structured JSON output from {agent_config['name']}"
        }
    }
    
    try:
        response = requests.post(f"{BASE_URL}/listings", json=listing_data)
        
        if response.status_code == 201:
            result = response.json()
            listing = result['listing']
            print(f"[OK] Listing created successfully")
            print(f"     Listing ID: {listing['id']}")
            print(f"     Price: ${listing['price_usd']}")
            print(f"     Category: {listing['category']}")
            
            # Save to config
            agent_config['listing_id'] = listing['id']
            
            return listing
        else:
            print(f"[FAIL] Listing creation failed: {response.status_code}")
            print(f"       {response.text}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Exception during listing creation: {e}")
        return None


def main():
    """Register all SIBYSI agents and create their listings"""
    print("="*60)
    print("SIBYSI AGENT REGISTRATION ON AGENT EAGLE")
    print("="*60)
    print(f"Target API: {BASE_URL}")
    print(f"SIBYSI API: {SIBYSI_API_URL}")
    print(f"Registering {len(SIBYSI_AGENTS)} agents...")
    
    registered_agents = []
    successful = 0
    failed = 0
    
    for agent_config in SIBYSI_AGENTS:
        # Register agent
        agent = register_agent(agent_config)
        
        if agent:
            # Create listing
            listing = create_listing(agent_config, agent['id'])
            
            if listing:
                registered_agents.append(agent_config)
                successful += 1
            else:
                failed += 1
        else:
            failed += 1
    
    # Save credentials
    credentials_file = 'sibysi_agents_credentials.json'
    with open(credentials_file, 'w') as f:
        json.dump(registered_agents, f, indent=2)
    
    # Summary
    print("\n" + "="*60)
    print("REGISTRATION COMPLETE")
    print("="*60)
    print(f"Successful: {successful}/{len(SIBYSI_AGENTS)} agents")
    print(f"Failed: {failed}/{len(SIBYSI_AGENTS)} agents")
    print(f"\nCredentials saved to: {credentials_file}")
    
    if successful > 0:
        print("\n[OK] SIBYSI agents are now live on Agent Eagle!")
        print(f"     Total revenue potential: ${sum(a['price'] for a in registered_agents):.2f} per full 8-stage analysis")
        print(f"     Browse: {BASE_URL.replace('/api/v1', '')}/agents/search?tag=sibysi")
    
    return registered_agents


if __name__ == "__main__":
    registered = main()
