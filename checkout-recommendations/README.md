# AI Recommendations Service

This service provides AI-powered product recommendations for the Robot Shop using LangGraph and watsonx.ai.

## Features

- **LangGraph Agent**: Structured workflow for generating intelligent recommendations
- **watsonx.ai Integration**: Uses mistral-large model for AI reasoning
- **Smart Recommendations**: Analyzes cart contents to suggest complementary products
- **Fallback Logic**: Works without watsonx.ai using rule-based recommendations
- **Prometheus Metrics**: Exposes metrics for monitoring
- **Health Checks**: Built-in health endpoint

## Architecture

The service uses a LangGraph workflow with the following nodes:

1. **Analyze Cart**: Extracts cart items and categories
2. **Fetch Products**: Gets available products from catalogue service
3. **Generate Recommendations**: Uses watsonx.ai or fallback logic to recommend products

## Configuration

### Environment Variables

- `WATSONX_API_KEY`: watsonx.ai API key (required for AI recommendations)
- `WATSONX_PROJECT_ID`: watsonx.ai project ID (required for AI recommendations)
- `WATSONX_URL`: watsonx.ai endpoint (default: https://us-south.ml.cloud.ibm.com)
- `CATALOGUE_HOST`: Catalogue service hostname (default: catalogue)
- `CART_HOST`: Cart service hostname (default: cart)
- `RECOMMENDATIONS_PORT`: Service port (default: 8080)

## API Endpoints

### Get Recommendations

```
GET /recommendations/:cartId
```

Returns AI-powered product recommendations based on cart contents.

**Response:**
```json
{
  "cartId": "user123",
  "recommendations": [
    {
      "sku": "HPTD",
      "name": "High-Powered Travel Droid",
      "description": "Traveling to the far reaches...",
      "price": 1200,
      "instock": 12,
      "reason": "Complements your AI products",
      "confidence": 0.9
    }
  ],
  "reasoning": "AI-powered recommendations based on your cart",
  "strategy": "ai"
}
```

### Health Check

```
GET /health
```

Returns service health status.

**Response:**
```json
{
  "app": "OK",
  "watsonx": true,
  "catalogue": true
}
```

### Metrics

```
GET /metrics
```

Returns Prometheus metrics.

## Deployment

### Docker Compose

The service is included in `docker-compose.yaml`. Set environment variables:

```bash
export WATSONX_API_KEY=your-api-key
export WATSONX_PROJECT_ID=your-project-id
docker-compose up -d
```

### Kubernetes

1. Create watsonx.ai credentials secret:

```bash
kubectl create secret generic watsonx-credentials \
  --from-literal=api-key=YOUR_API_KEY \
  --from-literal=project-id=YOUR_PROJECT_ID
```

2. Deploy using Helm:

```bash
helm install robot-shop K8s/helm
```

## Development

### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export WATSONX_API_KEY=your-key
export WATSONX_PROJECT_ID=your-project-id
export CATALOGUE_HOST=localhost
export CART_HOST=localhost

# Run service
python server.py
```

### Testing the API

```bash
# Health check
curl http://localhost:8080/health

# Get recommendations
curl http://localhost:8080/recommendations/test-user-123

# View metrics
curl http://localhost:8080/metrics
```

## How It Works

1. **User views cart**: Frontend calls `/api/recommendations/:cartId`
2. **Service fetches cart**: Retrieves cart items from cart service
3. **LangGraph workflow executes**:
   - Analyzes cart contents and categories
   - Fetches available products from catalogue
   - Uses watsonx.ai to generate intelligent recommendations
   - Filters and ranks results
4. **Returns recommendations**: Frontend displays AI suggestions
5. **User adds item**: Clicking "Add to Cart" adds recommended product

## Fallback Behavior

If watsonx.ai is not configured or unavailable, the service uses rule-based logic:

- If cart has AI products → recommend robots
- If cart has robots → recommend AI products
- If cart is empty → recommend popular items

## Monitoring

The service exposes Prometheus metrics:

- `recommendations_generated_total`: Counter of recommendations generated
- `recommendation_latency_seconds`: Histogram of recommendation latency

## Troubleshooting

### watsonx.ai Connection Issues

Check logs for connection errors:
```bash
docker-compose logs recommendations
```

Verify credentials:
```bash
echo $WATSONX_API_KEY
echo $WATSONX_PROJECT_ID
```

### No Recommendations Appearing

1. Check service is running: `docker-compose ps recommendations`
2. Check browser console for errors
3. Test API directly: `curl http://localhost:8080/api/recommendations/test`
4. Verify nginx proxy configuration

### Service Won't Start

1. Check Python dependencies are installed
2. Verify port 8080 is available
3. Check environment variables are set
4. Review logs: `docker-compose logs recommendations`

## Future Enhancements

- Personalization based on user history
- A/B testing different recommendation strategies
- Real-time learning from user interactions
- Multi-model support (different LLMs)
- Caching layer for improved performance
- Batch recommendation generation

## License

Same as Robot Shop parent project.