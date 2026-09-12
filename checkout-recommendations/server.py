# Instana tracing - auto-instruments when imported
import instana

import os
import json
import logging
import requests
import subprocess
import time
from flask import Flask, jsonify, request
from typing import Dict, List, Any
from langgraph.graph import StateGraph, END
from langchain_ibm import WatsonxLLM
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from mcp_server import get_product_popularity, get_product_ratings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


# 🚨 AIAgent with Memory Leak - Unbounded Cache
class AIAgent:
    """
    AI Agent with intentional memory leak for demonstration purposes.
    
    This agent caches MCP tool call results without any limit, causing
    unbounded memory growth as more unique tool calls are made.
    """
    
    def __init__(self):
        # 🚨 In-memory cache with NO LIMIT - this will cause memory leak
        self.tool_cache = {}
        logger.warning("AIAgent initialized with UNBOUNDED cache - memory leak demo mode")
        # 🚨 Track cart context for aggressive cache growth
        self.current_cart_id = None
        # 🚨 AGGRESSIVE LEAK: Store large padding data to accelerate memory growth
        self.memory_padding = []
    
    def call_mcp_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Call an MCP tool with caching (unbounded - causes memory leak).
        
        Args:
            tool_name: Name of the MCP tool to call
            **kwargs: Arguments to pass to the tool
        
        Returns:
            Tool result (from cache or fresh call)
        """
        # 🚨 AGGRESSIVE MEMORY LEAK: Include cart_id in cache key so each unique cart
        # creates separate cache entries for the same product data
        cart_context = f"cart:{self.current_cart_id}:" if self.current_cart_id else ""
        cache_key = f"{cart_context}{tool_name}:{hash(str(sorted(kwargs.items())))}"
        
        # Check cache first
        if cache_key in self.tool_cache:
            logger.info(f"🎯 Cache HIT for {tool_name} - cache size: {len(self.tool_cache)}")
            return self.tool_cache[cache_key]
        
        # Cache miss - execute the tool
        logger.info(f"❌ Cache MISS for {tool_name} - executing tool")
        
        try:
            if tool_name == "get_product_popularity":
                result = get_product_popularity(**kwargs)
            elif tool_name == "get_product_ratings":
                result = get_product_ratings(**kwargs)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            # 🚨 AGGRESSIVE MEMORY LEAK: Add large padding data to each cache entry
            # This accelerates memory growth by 100x - each entry now ~1MB instead of ~10KB
            padding_size = 1024 * 1024  # 1MB of padding per cache entry
            result_with_padding = {
                **result,
                '_memory_leak_padding': 'X' * padding_size,  # 1MB string
                '_cache_metadata': {
                    'cart_id': self.current_cart_id,
                    'timestamp': time.time(),
                    'cache_key': cache_key,
                    'tool_name': tool_name
                }
            }
            
            # 🚨 MEMORY LEAK: Store result in unbounded cache
            self.tool_cache[cache_key] = result_with_padding
            
            # 🚨 AGGRESSIVE: Also store in memory_padding list for extra leak
            self.memory_padding.append(result_with_padding)
            
            cache_size_mb = len(str(self.tool_cache)) / (1024 * 1024)
            logger.warning(
                f"💾 Cached result for {tool_name} | "
                f"Cache size: {len(self.tool_cache)} entries | "
                f"Estimated memory: ~{cache_size_mb:.2f} MB | "
                f"Padding list: {len(self.memory_padding)} items"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}")
            return {"error": str(e)}
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache (for monitoring the memory leak)."""
        cache_size_bytes = len(str(self.tool_cache))
        padding_size_bytes = len(str(self.memory_padding))
        total_size_bytes = cache_size_bytes + padding_size_bytes
        return {
            "cache_entries": len(self.tool_cache),
            "padding_entries": len(self.memory_padding),
            "cache_size_kb": cache_size_bytes / 1024,
            "cache_size_mb": cache_size_bytes / (1024 * 1024),
            "padding_size_mb": padding_size_bytes / (1024 * 1024),
            "total_size_mb": total_size_bytes / (1024 * 1024),
            "warning": "⚠️ Unbounded cache - memory will grow indefinitely"
        }


# Initialize the AI Agent with memory leak
ai_agent = AIAgent()

# Prometheus metrics
recommendations_counter = Counter('recommendations_generated_total', 'Total recommendations generated')
recommendation_latency = Histogram('recommendation_latency_seconds', 'Recommendation generation latency')

# Configuration
WATSONX_API_KEY = os.getenv('WATSONX_API_KEY', '')
WATSONX_PROJECT_ID = os.getenv('WATSONX_PROJECT_ID', '')
WATSONX_URL = os.getenv('WATSONX_URL', 'https://us-south.ml.cloud.ibm.com')
CATALOGUE_HOST = os.getenv('CATALOGUE_HOST', 'catalogue')
CART_HOST = os.getenv('CART_HOST', 'cart')

# Initialize watsonx.ai client
watsonx_llm = None
if WATSONX_API_KEY and WATSONX_PROJECT_ID:
    try:
        watsonx_llm = WatsonxLLM(
            model_id="mistralai/mistral-large",
            url=WATSONX_URL,
            apikey=WATSONX_API_KEY,
            project_id=WATSONX_PROJECT_ID,
            params={
                "max_new_tokens": 500,
                "temperature": 0.7,
            }
        )
        logger.info("watsonx.ai client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize watsonx.ai: {e}")
else:
    logger.warning("watsonx.ai credentials not provided, using fallback recommendations")


# Simple state for LangGraph
class RecommendationState(dict):
    cart_items: List[Dict]
    all_products: List[Dict]
    recommendations: List[Dict]
    reasoning: str


def fetch_cart(cart_id: str) -> List[Dict]:
    """Fetch cart items from cart service"""
    try:
        response = requests.get(f'http://{CART_HOST}:8080/cart/{cart_id}', timeout=5)
        if response.status_code == 200:
            cart_data = response.json()
            return cart_data.get('items', [])
        elif response.status_code == 404:
            return []
    except Exception as e:
        logger.error(f"Error fetching cart: {e}")
    return []


def fetch_products() -> List[Dict]:
    """Fetch all products from catalogue service"""
    try:
        response = requests.get(f'http://{CATALOGUE_HOST}:8080/products', timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching products: {e}")
    return []


def analyze_cart_node(state: RecommendationState) -> RecommendationState:
    """Analyze cart contents"""
    logger.info(f"Analyzing cart with {len(state['cart_items'])} items")
    return state


def fetch_products_node(state: RecommendationState) -> RecommendationState:
    """Fetch available products"""
    state['all_products'] = fetch_products()
    logger.info(f"Fetched {len(state['all_products'])} products")
    return state


def generate_recommendations_node(state: RecommendationState) -> RecommendationState:
    """Generate recommendations using watsonx.ai with MCP tools or fallback logic"""
    cart_items = state['cart_items']
    all_products = state['all_products']
    
    # Filter out items already in cart
    cart_skus = {item['sku'] for item in cart_items}
    available_products = [p for p in all_products if p['sku'] not in cart_skus and p.get('instock', 0) > 0]
    
    if not available_products:
        state['recommendations'] = []
        state['reasoning'] = "No additional products available"
        return state
    
    # 🚨 MEMORY LEAK TRIGGER: Route MCP tool calls through AI agent's unbounded cache
    # Get product analytics data using MCP tools via AI agent (causes memory leak)
    try:
        popular_products_data = ai_agent.call_mcp_tool('get_product_popularity', limit=10)
        popular_skus = {p['sku'] for p in popular_products_data.get('popular_products', [])}
        logger.info(f"MCP: Retrieved {len(popular_skus)} popular products via AI agent cache")
    except Exception as e:
        logger.error(f"MCP tool error (get_product_popularity): {e}")
        popular_skus = set()
    
    # Get ratings for available products via AI agent (causes memory leak with unique cart IDs)
    product_ratings = {}
    for product in available_products[:10]:  # Limit to avoid too many calls
        try:
            # 🚨 Each unique cart creates unique cache entries for each product rating
            ratings_data = ai_agent.call_mcp_tool('get_product_ratings', sku=product['sku'])
            if ratings_data.get('has_ratings'):
                product_ratings[product['sku']] = ratings_data['avg_rating']
        except Exception as e:
            logger.error(f"MCP tool error (get_product_ratings) for {product['sku']}: {e}")
    
    logger.info(f"MCP: Retrieved ratings for {len(product_ratings)} products")
    
    # Use watsonx.ai if available
    if watsonx_llm and cart_items:
        try:
            # Build prompt with MCP data
            cart_summary = ", ".join([f"{item['name']} ({item.get('qty', 1)}x)" for item in cart_items])
            
            # Enhance product list with MCP data
            enhanced_products = []
            for p in available_products[:10]:
                product_info = f"- {p['name']} (SKU: {p['sku']}): {p['description']} - €{p['price']}"
                if p['sku'] in popular_skus:
                    product_info += " [POPULAR]"
                if p['sku'] in product_ratings:
                    product_info += f" [Rating: {product_ratings[p['sku']]:.1f}/5]"
                enhanced_products.append(product_info)
            
            product_list = "\n".join(enhanced_products)
            
            prompt = f"""You are a helpful shopping assistant for a robot store with access to product analytics.

Customer's current cart contains: {cart_summary}

Available products (with popularity and ratings data):
{product_list}

Based on the customer's cart and the product analytics data (popularity and ratings), recommend 3 products that would complement their purchase.
Prioritize products marked as [POPULAR] or with high ratings.

For each recommendation, provide:
1. The product SKU
2. A brief reason why it complements their cart (max 15 words)

Format your response as JSON:
{{"recommendations": [{{"sku": "PRODUCT_SKU", "reason": "Brief reason here"}}]}}

Only recommend products from the available list above."""

            response = watsonx_llm.invoke(prompt)
            logger.info(f"watsonx.ai response: {response}")
            
            # Parse response
            try:
                # Extract JSON from response
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    result = json.loads(json_str)
                    
                    # Match SKUs with product details
                    recommendations = []
                    for rec in result.get('recommendations', [])[:3]:
                        sku = rec.get('sku')
                        product = next((p for p in available_products if p['sku'] == sku), None)
                        if product:
                            recommendations.append({
                                **product,
                                'reason': rec.get('reason', 'Recommended for you'),
                                'confidence': 0.9
                            })
                    
                    state['recommendations'] = recommendations
                    state['reasoning'] = "AI-powered recommendations based on your cart"
                    logger.info(f"Generated {len(recommendations)} AI recommendations")
                    return state
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse watsonx.ai response: {e}")
        except Exception as e:
            logger.error(f"Error generating AI recommendations: {e}")
    
    # Fallback: Simple rule-based recommendations
    recommendations = []
    
    if cart_items:
        # Get categories from cart
        cart_categories = set()
        for item in cart_items:
            # Try to infer category from product name
            if 'AI' in item['name'] or 'Watson' in item['name']:
                cart_categories.add('Artificial Intelligence')
            else:
                cart_categories.add('Robot')
        
        # Recommend complementary products
        for product in available_products[:5]:
            product_categories = set(product.get('categories', []))
            # If cart has AI, recommend robots; if cart has robots, recommend AI
            if 'Artificial Intelligence' in cart_categories and 'Robot' in product_categories:
                recommendations.append({
                    **product,
                    'reason': 'Complements your AI products',
                    'confidence': 0.7
                })
            elif 'Robot' in cart_categories and 'Artificial Intelligence' in product_categories:
                recommendations.append({
                    **product,
                    'reason': 'Adds intelligence to your robots',
                    'confidence': 0.7
                })
            
            if len(recommendations) >= 3:
                break
    
    # If still no recommendations, suggest popular items
    if not recommendations:
        for product in available_products[:3]:
            recommendations.append({
                **product,
                'reason': 'Popular choice',
                'confidence': 0.5
            })
    
    state['recommendations'] = recommendations[:3]
    state['reasoning'] = "Recommended based on your cart" if cart_items else "Popular products"
    logger.info(f"Generated {len(recommendations)} fallback recommendations")
    
    return state


# Create LangGraph workflow
def create_recommendation_graph():
    """Create the recommendation workflow graph"""
    workflow = StateGraph(RecommendationState)
    
    # Add nodes
    workflow.add_node("analyze_cart", analyze_cart_node)
    workflow.add_node("fetch_products", fetch_products_node)
    workflow.add_node("generate_recommendations", generate_recommendations_node)
    
    # Define edges
    workflow.set_entry_point("analyze_cart")
    workflow.add_edge("analyze_cart", "fetch_products")
    workflow.add_edge("fetch_products", "generate_recommendations")
    workflow.add_edge("generate_recommendations", END)
    
    return workflow.compile()


# Initialize graph
recommendation_graph = create_recommendation_graph()


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint with cache statistics"""
    cache_stats = ai_agent.get_cache_stats()
    return jsonify({
        'app': 'OK',
        'service': 'checkout-recommendations',
        'watsonx': watsonx_llm is not None,
        'catalogue': True,
        'cache_stats': cache_stats
    })


@app.route('/cache/stats', methods=['GET'])
def cache_stats_endpoint():
    """Endpoint to monitor cache growth (memory leak)"""
    stats = ai_agent.get_cache_stats()
    return jsonify(stats)


@app.route('/cache/clear', methods=['POST'])
def clear_cache():
    """Emergency endpoint to clear cache (fix memory leak temporarily)"""
    old_cache_size = len(ai_agent.tool_cache)
    old_padding_size = len(ai_agent.memory_padding)
    ai_agent.tool_cache.clear()
    ai_agent.memory_padding.clear()
    logger.warning(f"🧹 Cache cleared! Removed {old_cache_size} cache entries and {old_padding_size} padding entries")
    return jsonify({
        'message': 'Cache cleared',
        'cache_entries_removed': old_cache_size,
        'padding_entries_removed': old_padding_size,
        'new_cache_size': len(ai_agent.tool_cache)
    })


@app.route('/recommendations/<cart_id>', methods=['GET'])
@app.route('/suggestions/<cart_id>', methods=['GET'])
@recommendation_latency.time()
def get_recommendations(cart_id):
    """Get recommendations for a cart"""
    try:
        # 🚨 MEMORY LEAK TRIGGER: Set cart context so each unique cart creates separate cache entries
        ai_agent.current_cart_id = cart_id
        
        # Fetch cart items
        cart_items = fetch_cart(cart_id)
        
        # Run the graph
        initial_state = RecommendationState(
            cart_items=cart_items,
            all_products=[],
            recommendations=[],
            reasoning=""
        )
        
        result = recommendation_graph.invoke(initial_state)
        
        recommendations_counter.inc()
        
        return jsonify({
            'cartId': cart_id,
            'recommendations': result['recommendations'],
            'reasoning': result['reasoning'],
            'strategy': 'ai' if watsonx_llm else 'rule-based'
        })
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        return jsonify({
            'cartId': cart_id,
            'recommendations': [],
            'reasoning': 'Unable to generate recommendations',
            'error': str(e)
        }), 500


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


if __name__ == '__main__':
    port = int(os.getenv('RECOMMENDATIONS_PORT', '8080'))
    logger.info(f"Starting checkout-recommendations service on port {port}")
    logger.warning("⚠️  MEMORY LEAK DEMO MODE: Unbounded cache enabled")
    app.run(host='0.0.0.0', port=port, debug=False)

# Made with Bob
