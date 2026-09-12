# Quick Start Guide - AI Agent Implementation

## Prerequisites

Before starting implementation, ensure you have:

- [ ] watsonx.ai account with API access
- [ ] watsonx.ai API key
- [ ] watsonx.ai Project ID
- [ ] Python 3.11+ installed
- [ ] Docker and Docker Compose installed
- [ ] Node.js 16+ (for existing services)
- [ ] Access to Robot Shop repository

## Step-by-Step Implementation

### Phase 1: Setup watsonx.ai Access (15 minutes)

1. **Get watsonx.ai Credentials**
   ```bash
   # You'll need these three values:
   WATSONX_API_KEY=<your-api-key>
   WATSONX_PROJECT_ID=<your-project-id>
   WATSONX_URL=https://us-south.ml.cloud.ibm.com
   ```

2. **Test watsonx.ai Connection**
   ```python
   # test_watsonx.py
   from ibm_watsonx_ai import Credentials
   from ibm_watsonx_ai.foundation_models import Model
   
   credentials = Credentials(
       api_key="your-api-key",
       url="https://us-south.ml.cloud.ibm.com"
   )
   
   model = Model(
       model_id="mistralai/mistral-medium",
       credentials=credentials,
       project_id="your-project-id"
   )
   
   response = model.generate(prompt="Hello, world!")
   print(response)
   ```

### Phase 2: Create Recommendations Service (3-4 hours)

1. **Create Directory Structure**
   ```bash
   cd /path/to/robot-shop
   mkdir -p recommendations/{agent,services,config}
   touch recommendations/{server.py,requirements.txt,Dockerfile}
   touch recommendations/agent/{__init__.py,graph.py,nodes.py,state.py,prompts.py}
   touch recommendations/services/{__init__.py,watsonx_client.py,catalogue_client.py}
   touch recommendations/config/{__init__.py,settings.py}
   ```

2. **Install Dependencies**
   ```bash
   # requirements.txt
   flask==3.0.0
   langgraph==0.0.20
   langchain==0.1.0
   ibm-watsonx-ai==0.2.0
   requests==2.31.0
   python-dotenv==1.0.0
   pino-python==0.1.0
   prometheus-client==0.19.0
   ```

3. **Implement Core Files** (See AI_AGENT_IMPLEMENTATION_PLAN.md for details)
   - `server.py` - Flask application
   - `agent/graph.py` - LangGraph workflow
   - `agent/nodes.py` - Individual node implementations
   - `services/watsonx_client.py` - watsonx.ai integration
   - `services/catalogue_client.py` - Catalogue service client

### Phase 3: Frontend Integration (2-3 hours)

1. **Update Cart HTML**
   ```bash
   # Edit: web/static/cart.html
   # Add recommendations section after cart table
   ```

2. **Update Controller**
   ```bash
   # Edit: web/static/js/controller.js
   # Add loadRecommendations() function
   # Add addRecommendation() function
   ```

3. **Update Styles**
   ```bash
   # Edit: web/static/css/style.css
   # Add .recommendations-section styles
   ```

### Phase 4: Docker Integration (1-2 hours)

1. **Create Dockerfile**
   ```dockerfile
   # recommendations/Dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   EXPOSE 8080
   CMD ["python", "server.py"]
   ```

2. **Update docker-compose.yaml**
   ```yaml
   # Add recommendations service
   recommendations:
     build:
       context: recommendations
     image: ${REPO}/rs-recommendations:${TAG}
     environment:
       WATSONX_API_KEY: ${WATSONX_API_KEY}
       WATSONX_PROJECT_ID: ${WATSONX_PROJECT_ID}
       WATSONX_URL: ${WATSONX_URL}
   ```

3. **Update Nginx Configuration**
   ```nginx
   # web/default.conf.template
   location /api/recommendations/ {
       proxy_pass http://recommendations:8080/;
   }
   ```

### Phase 5: Testing (2-3 hours)

1. **Unit Tests**
   ```bash
   cd recommendations
   python -m pytest tests/
   ```

2. **Integration Test**
   ```bash
   # Start services
   docker-compose up -d
   
   # Test recommendations endpoint
   curl http://localhost:8080/api/recommendations/test-user-123
   ```

3. **End-to-End Test**
   - Open browser to http://localhost:8080
   - Add items to cart
   - Navigate to cart page
   - Verify recommendations appear
   - Click "Add to Cart" on recommendation
   - Verify item added successfully

## Environment Variables Setup

Create a `.env` file in the root directory:

```bash
# .env
REPO=robotshop
TAG=latest

# watsonx.ai Configuration
WATSONX_API_KEY=your-api-key-here
WATSONX_PROJECT_ID=your-project-id-here
WATSONX_URL=https://us-south.ml.cloud.ibm.com

# Optional: Instana
INSTANA_AGENT_KEY=your-instana-key
```

## Running the Application

### Local Development

```bash
# 1. Start all services
docker-compose up -d

# 2. View logs
docker-compose logs -f recommendations

# 3. Access application
open http://localhost:8080

# 4. Stop services
docker-compose down
```

### With Load Generation

```bash
docker-compose -f docker-compose.yaml -f docker-compose-load.yaml up
```

## Verification Checklist

- [ ] Recommendations service starts successfully
- [ ] Health check endpoint responds: `curl http://localhost:8080/api/recommendations/health`
- [ ] watsonx.ai connection works (check logs)
- [ ] Cart page loads without errors
- [ ] Recommendations section appears in cart view
- [ ] Recommendations are relevant to cart items
- [ ] "Add to Cart" button works for recommendations
- [ ] Service is observable in Instana (if configured)

## Troubleshooting

### Issue: watsonx.ai Connection Failed

**Solution:**
```bash
# Check credentials
echo $WATSONX_API_KEY
echo $WATSONX_PROJECT_ID

# Test connection
python test_watsonx.py

# Check service logs
docker-compose logs recommendations
```

### Issue: Recommendations Not Appearing

**Solution:**
```bash
# Check if service is running
docker-compose ps recommendations

# Check browser console for errors
# Open DevTools > Console

# Test API directly
curl http://localhost:8080/api/recommendations/test-user
```

### Issue: LangGraph Import Error

**Solution:**
```bash
# Rebuild container with updated dependencies
docker-compose build recommendations
docker-compose up -d recommendations
```

## Performance Optimization Tips

1. **Enable Caching**
   ```python
   # In server.py
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   def get_recommendations(cart_id):
       # Implementation
   ```

2. **Batch Requests**
   - Group multiple recommendation requests
   - Use async/await for parallel processing

3. **Monitor Performance**
   ```bash
   # Check metrics
   curl http://localhost:8080/api/recommendations/metrics
   ```

## Next Steps After Implementation

1. **Monitor Performance**
   - Set up Instana dashboards
   - Track recommendation acceptance rate
   - Monitor watsonx.ai API usage

2. **Gather Feedback**
   - A/B test different recommendation strategies
   - Collect user interaction data
   - Iterate on prompts and logic

3. **Enhance Features**
   - Add personalization based on user history
   - Implement real-time learning
   - Add explanation for recommendations

4. **Scale for Production**
   - Add rate limiting
   - Implement circuit breakers
   - Set up horizontal scaling

## Useful Commands

```bash
# View all service logs
docker-compose logs -f

# Restart recommendations service
docker-compose restart recommendations

# Rebuild and restart
docker-compose up -d --build recommendations

# Check service health
curl http://localhost:8080/api/recommendations/health

# Test recommendation endpoint
curl http://localhost:8080/api/recommendations/anonymous-user-123

# View Prometheus metrics
curl http://localhost:8080/api/recommendations/metrics

# Access MongoDB (for debugging)
docker-compose exec mongodb mongosh catalogue

# Access Redis (for debugging)
docker-compose exec redis redis-cli
```

## Resources

- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
- **watsonx.ai Documentation**: https://www.ibm.com/docs/en/watsonx-as-a-service
- **Robot Shop Repository**: https://github.com/instana/robot-shop
- **Instana Documentation**: https://www.ibm.com/docs/en/instana-observability

## Support

For issues or questions:
1. Check the logs: `docker-compose logs recommendations`
2. Review the implementation plan: `AI_AGENT_IMPLEMENTATION_PLAN.md`
3. Check architecture diagrams: `AI_AGENT_ARCHITECTURE.md`
4. Test watsonx.ai connection independently

## Success Metrics

Track these metrics to measure success:

- **Technical Metrics**
  - Response time < 500ms (p95)
  - Error rate < 1%
  - Cache hit rate > 70%
  - Service availability > 99.5%

- **Business Metrics**
  - Recommendation acceptance rate > 25%
  - Average cart value increase
  - User engagement with recommendations
  - Conversion rate improvement

## Timeline Summary

| Phase | Duration | Status |
|-------|----------|--------|
| Setup watsonx.ai | 15 min | ⏳ Pending |
| Create Service | 3-4 hours | ⏳ Pending |
| Frontend Integration | 2-3 hours | ⏳ Pending |
| Docker Integration | 1-2 hours | ⏳ Pending |
| Testing | 2-3 hours | ⏳ Pending |
| **Total** | **11-16 hours** | ⏳ Pending |

---

**Ready to implement?** Start with Phase 1 and work through each phase sequentially. Good luck! 🚀