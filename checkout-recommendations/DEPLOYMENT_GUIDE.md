# AI Agent Deployment Guide

This guide walks you through deploying the AI-powered recommendations service to Robot Shop.

## Prerequisites

- Docker and Docker Compose installed
- OR Kubernetes cluster with kubectl configured
- watsonx.ai account with API credentials
- Robot Shop repository cloned

## Quick Start (Docker Compose)

### 1. Get watsonx.ai Credentials

Sign up for watsonx.ai and obtain:
- API Key
- Project ID

### 2. Set Environment Variables

Create or update `.env` file in the root directory:

```bash
# Docker image settings
REPO=robotshop
TAG=latest

# watsonx.ai credentials
WATSONX_API_KEY=your-api-key-here
WATSONX_PROJECT_ID=your-project-id-here
WATSONX_URL=https://us-south.ml.cloud.ibm.com

# Optional: Instana
INSTANA_AGENT_KEY=your-instana-key
```

### 3. Build and Start Services

```bash
# Build all services including recommendations
docker-compose build

# Start all services
docker-compose up -d

# Check recommendations service is running
docker-compose ps recommendations
docker-compose logs -f recommendations
```

### 4. Verify Deployment

```bash
# Check health
curl http://localhost:8080/api/recommendations/health

# Test recommendations (will return empty if cart is empty)
curl http://localhost:8080/api/recommendations/test-user

# Open browser
open http://localhost:8080
```

### 5. Test the Feature

1. Navigate to http://localhost:8080
2. Add some products to your cart
3. Go to the cart page
4. Scroll down to see "🤖 AI Recommended for You" section
5. Click "Add to Cart" on a recommendation

## Kubernetes Deployment

### 1. Create watsonx.ai Secret

```bash
kubectl create secret generic watsonx-credentials \
  --from-literal=api-key=YOUR_API_KEY \
  --from-literal=project-id=YOUR_PROJECT_ID
```

### 2. Deploy with Helm

```bash
# Install or upgrade
helm install robot-shop K8s/helm \
  --set image.repo=robotshop \
  --set image.version=latest

# Or upgrade existing deployment
helm upgrade robot-shop K8s/helm
```

### 3. Verify Deployment

```bash
# Check pods
kubectl get pods | grep recommendations

# Check logs
kubectl logs -f deployment/recommendations

# Check service
kubectl get svc recommendations

# Port forward for testing
kubectl port-forward svc/web 8080:8080
```

### 4. Access Application

```bash
# If using NodePort
kubectl get svc web

# If using LoadBalancer
kubectl get svc web -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Open in browser
open http://<service-ip>:8080
```

## Configuration Options

### watsonx.ai Settings

Edit `K8s/helm/values.yaml`:

```yaml
recommendations:
  watsonx:
    secretName: watsonx-credentials  # Name of K8s secret
    url: https://us-south.ml.cloud.ibm.com  # watsonx.ai endpoint
```

### Resource Limits

Edit `K8s/helm/templates/recommendations-deployment.yaml`:

```yaml
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 200m
    memory: 256Mi
```

### Scaling

```bash
# Scale recommendations service
kubectl scale deployment recommendations --replicas=3

# Or use Helm
helm upgrade robot-shop K8s/helm \
  --set recommendations.replicas=3
```

## Monitoring

### View Logs

```bash
# Docker Compose
docker-compose logs -f recommendations

# Kubernetes
kubectl logs -f deployment/recommendations
```

### Check Metrics

```bash
# Docker Compose
curl http://localhost:8080/api/recommendations/metrics

# Kubernetes (port-forward first)
kubectl port-forward svc/recommendations 8080:8080
curl http://localhost:8080/metrics
```

### Instana Integration

If Instana is configured, the recommendations service will automatically send traces and metrics.

## Troubleshooting

### Service Won't Start

**Check logs:**
```bash
docker-compose logs recommendations
# or
kubectl logs deployment/recommendations
```

**Common issues:**
- Missing watsonx.ai credentials
- Invalid API key or project ID
- Network connectivity to watsonx.ai
- Port 8080 already in use

### No Recommendations Appearing

**1. Check service health:**
```bash
curl http://localhost:8080/api/recommendations/health
```

**2. Test API directly:**
```bash
# Add items to cart first, then:
curl http://localhost:8080/api/recommendations/your-user-id
```

**3. Check browser console:**
- Open DevTools (F12)
- Look for errors in Console tab
- Check Network tab for failed requests

**4. Verify nginx proxy:**
```bash
# Check nginx config
docker-compose exec web cat /etc/nginx/conf.d/default.conf | grep recommendations
```

### watsonx.ai Connection Errors

**Verify credentials:**
```bash
echo $WATSONX_API_KEY
echo $WATSONX_PROJECT_ID
```

**Test connection:**
```python
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import Model

credentials = Credentials(
    api_key="your-key",
    url="https://us-south.ml.cloud.ibm.com"
)

model = Model(
    model_id="mistralai/mistral-large",
    credentials=credentials,
    project_id="your-project-id"
)

response = model.generate(prompt="Hello")
print(response)
```

**Fallback mode:**
The service will work without watsonx.ai using rule-based recommendations. Check logs for:
```
watsonx.ai credentials not provided, using fallback recommendations
```

### Performance Issues

**1. Enable caching:**
Add caching layer in `recommendations/server.py`

**2. Increase resources:**
```yaml
# K8s/helm/templates/recommendations-deployment.yaml
resources:
  limits:
    cpu: 1000m
    memory: 1Gi
```

**3. Scale horizontally:**
```bash
kubectl scale deployment recommendations --replicas=3
```

## Updating the Service

### Docker Compose

```bash
# Rebuild and restart
docker-compose build recommendations
docker-compose up -d recommendations
```

### Kubernetes

```bash
# Update image
docker build -t robotshop/rs-recommendations:v2 recommendations/
docker push robotshop/rs-recommendations:v2

# Update deployment
kubectl set image deployment/recommendations \
  recommendations=robotshop/rs-recommendations:v2

# Or use Helm
helm upgrade robot-shop K8s/helm \
  --set image.version=v2
```

## Rollback

### Docker Compose

```bash
# Stop and remove recommendations service
docker-compose stop recommendations
docker-compose rm -f recommendations

# Restart without recommendations
docker-compose up -d
```

### Kubernetes

```bash
# Rollback deployment
kubectl rollout undo deployment/recommendations

# Or delete deployment
kubectl delete deployment recommendations
kubectl delete svc recommendations
```

## Security Best Practices

1. **Never commit credentials:**
   - Use `.env` file (add to `.gitignore`)
   - Use Kubernetes secrets
   - Use secret management tools (Vault, etc.)

2. **Rotate credentials regularly:**
   ```bash
   kubectl create secret generic watsonx-credentials \
     --from-literal=api-key=NEW_KEY \
     --from-literal=project-id=PROJECT_ID \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

3. **Use RBAC in Kubernetes:**
   - Limit service account permissions
   - Use network policies

4. **Monitor API usage:**
   - Track watsonx.ai API calls
   - Set up alerts for unusual activity

## Performance Tuning

### Optimize watsonx.ai Calls

Edit `recommendations/server.py`:

```python
watsonx_llm = WatsonxLLM(
    model_id="mistralai/mistral-large",
    url=WATSONX_URL,
    apikey=WATSONX_API_KEY,
    project_id=WATSONX_PROJECT_ID,
    params={
        "max_new_tokens": 300,  # Reduce for faster responses
        "temperature": 0.5,      # Lower for more consistent results
    }
)
```

### Add Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_recommendations_cached(cart_id, cart_hash):
    # Implementation
    pass
```

### Batch Processing

For high-traffic scenarios, consider batching recommendation requests.

## Next Steps

1. **Monitor performance** using Instana or Prometheus
2. **Collect feedback** on recommendation quality
3. **A/B test** different strategies
4. **Tune prompts** for better results
5. **Add personalization** based on user history

## Support

For issues or questions:
- Check logs first
- Review troubleshooting section
- Test API endpoints directly
- Verify watsonx.ai connectivity

## Additional Resources

- [watsonx.ai Documentation](https://www.ibm.com/docs/en/watsonx-as-a-service)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Robot Shop Repository](https://github.com/instana/robot-shop)
- [Instana Documentation](https://www.ibm.com/docs/en/instana-observability)