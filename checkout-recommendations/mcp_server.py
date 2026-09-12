"""
Product Analytics MCP Server for Robot Shop Checkout Recommendations
Provides product popularity and ratings data to the AI recommendation agent

⚠️  MEMORY LEAK DEMO: This MCP server provides tools that will be cached
    without limits in the checkout-recommendations service, causing unbounded
    memory growth.
"""

import asyncio
import logging
from typing import Any
from fastmcp import FastMCP
import requests
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server for checkout-recommendations
mcp = FastMCP("checkout-recommendations-analytics")

# Configuration
CATALOGUE_HOST = os.getenv('CATALOGUE_HOST', 'catalogue')
RATINGS_HOST = os.getenv('RATINGS_HOST', 'ratings')


@mcp.tool()
def get_product_popularity(limit: int = 10) -> dict[str, Any]:
    """
    Get trending/popular products based on stock levels and availability.
    Products with higher stock levels are considered more popular.
    
    Args:
        limit: Maximum number of products to return (default: 10)
    
    Returns:
        Dictionary containing list of popular products with their details
    """
    try:
        # Fetch all products from catalogue
        response = requests.get(
            f'http://{CATALOGUE_HOST}:8080/products',
            timeout=5
        )
        
        if response.status_code != 200:
            return {
                "error": "Failed to fetch products",
                "status_code": response.status_code
            }
        
        products = response.json()
        
        # Filter in-stock products and sort by stock level (popularity proxy)
        in_stock_products = [
            p for p in products 
            if p.get('instock', 0) > 0
        ]
        
        # Sort by stock level (higher stock = more popular)
        popular_products = sorted(
            in_stock_products,
            key=lambda x: x.get('instock', 0),
            reverse=True
        )[:limit]
        
        # Format response
        result = {
            "popular_products": [
                {
                    "sku": p['sku'],
                    "name": p['name'],
                    "description": p['description'],
                    "price": p['price'],
                    "instock": p['instock'],
                    "categories": p.get('categories', []),
                    "popularity_score": p['instock']  # Using stock as popularity metric
                }
                for p in popular_products
            ],
            "total_count": len(popular_products),
            "metric": "stock_level"
        }
        
        logger.info(f"Retrieved {len(popular_products)} popular products")
        return result
        
    except requests.RequestException as e:
        logger.error(f"Error fetching popular products: {e}")
        return {
            "error": str(e),
            "popular_products": []
        }
    except Exception as e:
        logger.error(f"Unexpected error in get_product_popularity: {e}")
        return {
            "error": str(e),
            "popular_products": []
        }


@mcp.tool()
def get_product_ratings(sku: str) -> dict[str, Any]:
    """
    Fetch average ratings and review counts for a specific product.
    
    Args:
        sku: Product SKU to get ratings for
    
    Returns:
        Dictionary containing rating information including average rating,
        rating count, and rating distribution
    """
    try:
        # Fetch ratings from ratings service
        response = requests.get(
            f'http://{RATINGS_HOST}:80/api/fetch/{sku}',
            timeout=5
        )
        
        if response.status_code == 404:
            # Product has no ratings yet
            return {
                "sku": sku,
                "avg_rating": 0.0,
                "rating_count": 0,
                "has_ratings": False,
                "message": "No ratings available for this product"
            }
        
        if response.status_code != 200:
            return {
                "error": "Failed to fetch ratings",
                "status_code": response.status_code,
                "sku": sku
            }
        
        ratings_data = response.json()
        
        # Format response
        result = {
            "sku": sku,
            "avg_rating": ratings_data.get('avg_rating', 0.0),
            "rating_count": ratings_data.get('rating_count', 0),
            "has_ratings": ratings_data.get('rating_count', 0) > 0,
            "rating_distribution": ratings_data.get('rating_distribution', {}),
            "product_name": ratings_data.get('product_name', '')
        }
        
        logger.info(f"Retrieved ratings for {sku}: {result['avg_rating']} ({result['rating_count']} reviews)")
        return result
        
    except requests.RequestException as e:
        logger.error(f"Error fetching ratings for {sku}: {e}")
        return {
            "error": str(e),
            "sku": sku,
            "avg_rating": 0.0,
            "rating_count": 0,
            "has_ratings": False
        }
    except Exception as e:
        logger.error(f"Unexpected error in get_product_ratings: {e}")
        return {
            "error": str(e),
            "sku": sku,
            "avg_rating": 0.0,
            "rating_count": 0,
            "has_ratings": False
        }


if __name__ == "__main__":
    # Run the MCP server
    logger.info("Starting Checkout Recommendations Analytics MCP Server...")
    logger.warning("⚠️  Results from this server will be cached without limits")
    mcp.run()

# Made with Bob
