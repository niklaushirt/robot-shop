# Robot Shop Analytics MCP Server

This MCP (Model Context Protocol) server provides product analytics tools to enhance the AI recommendation agent's decision-making capabilities.

## Overview

The MCP server exposes two tools that provide real-time product data:

1. **get_product_popularity** - Returns trending/popular products based on stock levels
2. **get_product_ratings** - Fetches average ratings and review counts for products

These tools are integrated directly into the LangGraph agent workflow, allowing the AI to make data-driven recommendations.

## Tools

### 1. get_product_popularity

Returns a list of popular products sorted by stock level (higher stock = more popular).

**Parameters:**
- `limit` (int, optional): Maximum number of products to return (default: 10)

**Returns:**
```json
{
  "popular_products": [
    {
      "sku": "STAN-1",
      "name": "Stan",
      "description": "Observability guru",
      "price": 67,
      "instock": 1000,
      "categories": ["Robot", "Artificial Intelligence"],
      "popularity_score": 1000
    }
  ],
  "total_count": 10,
  "metric": "stock_level"
}
```

### 2. get_product_ratings

Fetches rating information for a specific product from the ratings service.

**Parameters:**
- `sku` (str, required): Product SKU to get ratings for

**Returns:**
```json
{
  "sku": "Watson",
  "avg_rating": 4.5,
  "rating_count": 42,
  "has_ratings": true,
  "rating_distribution": {
    "5": 25,
    "4": 10,
    "3": 5,
    "2": 1,
    "1": 1
  },
  "product_name": "Watson"
}
```

## Integration with AI Agent

The MCP tools are integrated into the [`server.py`](server.py:95) recommendation generation process:

1. **Fetch Popular Products**: Gets list of trending products
2. **Get Ratings**: Retrieves ratings for available products
3. **Enhance Prompt**: Adds popularity and rating data to the LLM prompt
4. **AI Decision**: watsonx.ai uses this data to make better recommendations

### Example Enhanced Prompt

```
Available products (with popularity and ratings data):
- Stan (SKU: STAN-1): Observability guru - €67 [POPULAR] [Rating: 4.8/5]
- Watson (SKU: Watson): Smartest AI on the planet - €2001 [Rating: 4.5/5]
- High-Powered Travel Droid (SKU: HPTD): Protection for space travel - €1200 [POPULAR]
```

## Architecture

```
┌─────────────────────┐
│  LangGraph Agent    │
│  (server.py)        │
└──────────┬──────────┘
           │
           ├─────────────────┐
           │                 │
           ▼                 ▼
┌──────────────────┐  ┌──────────────────┐
│  MCP Tool:       │  │  MCP Tool:       │
│  get_product_    │  │  get_product_    │
│  popularity()    │  │  ratings()       │
└────────┬─────────┘  └────────┬─────────┘
         │                     │
         ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│  Catalogue       │  │  Ratings         │
│  Service         │  │  Service         │
└──────────────────┘  └──────────────────┘
```

## Running the MCP Server

The MCP server is embedded within the recommendations service and runs automatically when the service starts.

### Standalone Testing

To test the MCP server independently:

```bash
cd recommendations
python mcp_server.py
```

### Environment Variables

- `CATALOGUE_HOST`: Catalogue service hostname (default: catalogue)
- `RATINGS_HOST`: Ratings service hostname (default: ratings)

## Error Handling

The MCP tools include comprehensive error handling:

- **Network Errors**: Returns empty results with error message
- **Service Unavailable**: Gracefully degrades to empty data
- **Invalid SKU**: Returns zero ratings with appropriate message
- **Timeout**: 5-second timeout on all HTTP requests

The AI agent continues to function even if MCP tools fail, falling back to rule-based recommendations.

## Logging

The MCP server logs all tool invocations:

```
INFO: Retrieved 10 popular products
INFO: Retrieved ratings for Watson: 4.5 (42 reviews)
INFO: MCP: Retrieved ratings for 8 products
```

## Performance

- **get_product_popularity**: ~50-100ms (fetches all products, sorts)
- **get_product_ratings**: ~20-50ms per product (HTTP call to ratings service)
- **Total overhead**: ~200-500ms for full MCP data enrichment

## Future Enhancements

Potential additional MCP tools:

1. **get_frequently_bought_together(sku)** - Products purchased together
2. **get_user_purchase_history(user_id)** - Personalization data
3. **get_product_compatibility(sku)** - Compatible products
4. **get_active_promotions()** - Current deals and discounts
5. **get_inventory_forecast(sku)** - Predicted stock levels

## Troubleshooting

### MCP Tools Not Working

**Check logs:**
```bash
docker-compose logs recommendations | grep MCP
```

**Common issues:**
- Catalogue service not accessible
- Ratings service not accessible
- Network connectivity issues

**Verify services:**
```bash
curl http://catalogue:8080/products
curl http://ratings:80/api/fetch/Watson
```

### No Rating Data

The ratings service may not have data for all products. This is normal - the MCP tool returns `has_ratings: false` for products without ratings.

### Performance Issues

If MCP tools are slow:
1. Reduce the number of products checked for ratings
2. Implement caching for popular products
3. Use async/await for parallel requests

## Testing

### Test get_product_popularity

```python
from mcp_server import get_product_popularity

result = get_product_popularity(limit=5)
print(f"Found {result['total_count']} popular products")
for product in result['popular_products']:
    print(f"- {product['name']}: {product['popularity_score']} in stock")
```

### Test get_product_ratings

```python
from mcp_server import get_product_ratings

result = get_product_ratings('Watson')
if result['has_ratings']:
    print(f"Watson: {result['avg_rating']}/5 ({result['rating_count']} reviews)")
else:
    print("No ratings available")
```

## Benefits

Using MCP tools provides:

1. **Data-Driven Decisions**: AI uses real product data, not just descriptions
2. **Better Recommendations**: Popular and highly-rated products are prioritized
3. **Transparency**: Clear why products are recommended (popularity, ratings)
4. **Flexibility**: Easy to add new tools without changing core agent logic
5. **Testability**: Tools can be tested independently

## Integration Example

Here's how the AI agent uses MCP data:

```python
# 1. Get popular products
popular_products_data = get_product_popularity(limit=10)
popular_skus = {p['sku'] for p in popular_products_data['popular_products']}

# 2. Get ratings for available products
product_ratings = {}
for product in available_products:
    ratings_data = get_product_ratings(product['sku'])
    if ratings_data['has_ratings']:
        product_ratings[product['sku']] = ratings_data['avg_rating']

# 3. Enhance prompt with MCP data
for product in available_products:
    info = f"{product['name']} - €{product['price']}"
    if product['sku'] in popular_skus:
        info += " [POPULAR]"
    if product['sku'] in product_ratings:
        info += f" [Rating: {product_ratings[product['sku']]:.1f}/5]"

# 4. AI makes decision with enriched data
recommendations = watsonx_llm.invoke(enhanced_prompt)
```

## Conclusion

The MCP server enhances the AI recommendation agent by providing real-time product analytics data, enabling more intelligent and data-driven product recommendations.