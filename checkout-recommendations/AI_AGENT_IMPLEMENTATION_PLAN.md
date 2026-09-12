# AI Agent Implementation Plan for Robot Shop

## Overview
This document outlines the plan to add an AI-powered product recommendation agent to the Robot Shop demo application. The agent will provide intelligent product suggestions in the shopping cart view using LangGraph and watsonx.ai (mistral-medium model).

## Business Value
- **Demonstrates AI Integration**: Shows how customers can add AI capabilities to existing applications
- **Increases Engagement**: Smart recommendations encourage customers to explore more products
- **Modern Architecture**: Showcases microservices + AI agent pattern
- **Observable AI**: Leverages Instana for monitoring AI service performance

## Architecture Overview

### High-Level Design

```
┌─────────────┐
│   Browser   │
│  (Angular)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Web/Nginx  │
└──────┬──────┘
       │
       ├──────────────────┐
       │                  │
       ▼                  ▼
┌─────────────┐    ┌──────────────────┐
│    Cart     │───▶│ Recommendations  │
│  Service    │    │   AI Agent       │
│  (Node.js)  │    │   (Python)       │
└──────┬──────┘    └────────┬─────────┘
       │                    │
       ▼                    ▼
┌─────────────┐    ┌──────────────────┐
│    Redis    │    │   Catalogue      │
└─────────────┘    │   Service        │
                   └────────┬─────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │    MongoDB       │
                   └──────────────────┘
```

### New Microservice: Recommendations Service

**Technology Stack:**
- **Language**: Python 3.11+
- **Framework**: Flask (lightweight REST API)
- **AI Framework**: LangGraph (for agent orchestration)
- **LLM Provider**: watsonx.ai with mistral-medium model
- **Dependencies**: 
  - `langgraph` - Agent framework
  - `langchain` - LLM integration
  - `ibm-watsonx-ai` - watsonx.ai SDK
  - `flask` - Web framework
  - `requests` - HTTP client
  - `pino` - Logging (Python equivalent)
  - `@instana/collector` - Observability

## LangGraph Agent Design

### Agent Workflow

The recommendation agent uses a graph-based workflow with multiple decision nodes:

```
Start
  │
  ▼
[Analyze Cart Items]
  │
  ├─→ [Identify Categories]
  │
  ├─→ [Determine Intent]
  │     (complementary vs similar vs mixed)
  │
  ▼
[Fetch Available Products]
  │
  ▼
[LLM Reasoning Node]
  │ (watsonx.ai mistral-medium)
  │ - Analyzes cart context
  │ - Considers product relationships
  │ - Applies business rules
  │
  ▼
[Generate Recommendations]
  │
  ▼
[Rank & Filter]
  │ - Remove duplicates
  │ - Ensure in-stock
  │ - Limit to top 3-5
  │
  ▼
[Format Response]
  │
  ▼
End
```

### Agent States

```python
class RecommendationState(TypedDict):
    cart_items: List[Dict]
    available_products: List[Dict]
    categories: List[str]
    intent: str  # "complementary", "similar", "mixed"
    recommendations: List[Dict]
    reasoning: str
```

### LangGraph Nodes

1. **analyze_cart**: Extract product details, categories, price ranges
2. **determine_strategy**: Decide recommendation approach based on cart contents
3. **fetch_products**: Get available products from catalogue service
4. **llm_recommend**: Use watsonx.ai to generate intelligent recommendations
5. **rank_filter**: Apply business rules and ranking
6. **format_output**: Structure final response

## API Design

### Recommendations Service Endpoints

#### 1. Get Recommendations
```
GET /recommendations/:cartId
```

**Request:**
- Path parameter: `cartId` - The cart identifier

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
      "reason": "Complements your Watson AI with physical protection capabilities",
      "confidence": 0.92
    }
  ],
  "strategy": "complementary",
  "reasoning": "Based on your AI products, physical robots would complement your collection"
}
```

#### 2. Health Check
```
GET /health
```

**Response:**
```json
{
  "app": "OK",
  "watsonx": true,
  "catalogue": true
}
```

#### 3. Metrics (Prometheus)
```
GET /metrics
```

## Implementation Details

### Directory Structure

```
recommendations/
├── Dockerfile
├── requirements.txt
├── server.py                 # Flask application
├── agent/
│   ├── __init__.py
│   ├── graph.py             # LangGraph workflow definition
│   ├── nodes.py             # Individual node implementations
│   ├── state.py             # State definitions
│   └── prompts.py           # LLM prompts
├── services/
│   ├── __init__.py
│   ├── watsonx_client.py    # watsonx.ai integration
│   └── catalogue_client.py  # Catalogue service client
└── config/
    ├── __init__.py
    └── settings.py          # Configuration management
```

### Key Implementation Files

#### 1. `server.py` - Flask Application
```python
from flask import Flask, jsonify, request
from agent.graph import create_recommendation_graph
import logging

app = Flask(__name__)
graph = create_recommendation_graph()

@app.route('/recommendations/<cart_id>', methods=['GET'])
def get_recommendations(cart_id):
    # Fetch cart from cart service
    # Run LangGraph agent
    # Return recommendations
    pass

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"app": "OK", "watsonx": True})
```

#### 2. `agent/graph.py` - LangGraph Workflow
```python
from langgraph.graph import StateGraph, END
from .nodes import (
    analyze_cart_node,
    determine_strategy_node,
    fetch_products_node,
    llm_recommend_node,
    rank_filter_node
)
from .state import RecommendationState

def create_recommendation_graph():
    workflow = StateGraph(RecommendationState)
    
    # Add nodes
    workflow.add_node("analyze_cart", analyze_cart_node)
    workflow.add_node("determine_strategy", determine_strategy_node)
    workflow.add_node("fetch_products", fetch_products_node)
    workflow.add_node("llm_recommend", llm_recommend_node)
    workflow.add_node("rank_filter", rank_filter_node)
    
    # Define edges
    workflow.set_entry_point("analyze_cart")
    workflow.add_edge("analyze_cart", "determine_strategy")
    workflow.add_edge("determine_strategy", "fetch_products")
    workflow.add_edge("fetch_products", "llm_recommend")
    workflow.add_edge("llm_recommend", "rank_filter")
    workflow.add_edge("rank_filter", END)
    
    return workflow.compile()
```

#### 3. `services/watsonx_client.py` - watsonx.ai Integration
```python
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import Model

class WatsonxClient:
    def __init__(self, api_key, project_id, url):
        self.credentials = Credentials(
            api_key=api_key,
            url=url
        )
        self.model = Model(
            model_id="mistralai/mistral-medium",
            credentials=self.credentials,
            project_id=project_id
        )
    
    def generate(self, prompt, max_tokens=500):
        response = self.model.generate(
            prompt=prompt,
            params={
                "max_new_tokens": max_tokens,
                "temperature": 0.7
            }
        )
        return response['results'][0]['generated_text']
```

### Environment Variables

```bash
# watsonx.ai Configuration
WATSONX_API_KEY=<your-api-key>
WATSONX_PROJECT_ID=<your-project-id>
WATSONX_URL=https://us-south.ml.cloud.ibm.com

# Service Configuration
RECOMMENDATIONS_PORT=8080
CATALOGUE_HOST=catalogue
CART_HOST=cart

# Instana (optional)
INSTANA_AGENT_KEY=<your-key>
```

## Frontend Integration

### 1. Update `cart.html`

Add recommendations section after cart items:

```html
<!-- Existing cart table -->
<table>
  <!-- ... existing cart items ... -->
</table>

<!-- NEW: AI Recommendations Section -->
<div ng-if="data.recommendations.length > 0" class="recommendations-section">
    <h3>🤖 AI Recommended for You</h3>
    <p class="recommendations-subtitle">{{ data.recommendations.reasoning }}</p>
    <div class="recommendations-grid">
        <div ng-repeat="item in data.recommendations" class="recommendation-card">
            <img ng-src="/static/images/{{ item.sku }}.png" alt="{{ item.name }}" />
            <h4>{{ item.name }}</h4>
            <p class="recommendation-reason">{{ item.reason }}</p>
            <p class="currency">&euro;{{ item.price.toFixed(2) }}</p>
            <button ng-click="addRecommendation(item.sku);">Add to Cart</button>
        </div>
    </div>
</div>
```

### 2. Update `controller.js`

Add recommendation loading in `cartform` controller:

```javascript
robotshop.controller('cartform', function($scope, $http, $location, currentUser) {
    // ... existing code ...
    
    $scope.data.recommendations = [];
    
    function loadRecommendations(id) {
        $http({
            url: '/api/recommendations/' + id,
            method: 'GET'
        }).then((res) => {
            console.log('recommendations', res.data);
            $scope.data.recommendations = res.data.recommendations;
        }).catch((e) => {
            console.log('Recommendations not available', e);
            // Fail gracefully - recommendations are optional
        });
    }
    
    $scope.addRecommendation = function(sku) {
        // Add recommended item to cart
        var url = '/api/cart/add/' + currentUser.uniqueid + '/' + sku + '/1';
        $http({
            url: url,
            method: 'GET'
        }).then((res) => {
            currentUser.cart = res.data;
            $scope.data.cart = res.data;
            // Reload recommendations with updated cart
            loadRecommendations($scope.data.uniqueid);
        }).catch((e) => {
            console.log('ERROR', e);
        });
    };
    
    // Load cart and recommendations
    loadCart($scope.data.uniqueid);
    loadRecommendations($scope.data.uniqueid);
});
```

### 3. Update `style.css`

Add styling for recommendations:

```css
.recommendations-section {
    margin-top: 30px;
    padding: 20px;
    background: #f8f9fa;
    border-radius: 8px;
}

.recommendations-section h3 {
    color: #333;
    margin-bottom: 10px;
}

.recommendations-subtitle {
    color: #666;
    font-style: italic;
    margin-bottom: 20px;
}

.recommendations-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 20px;
}

.recommendation-card {
    background: white;
    padding: 15px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    text-align: center;
}

.recommendation-card img {
    max-width: 100%;
    height: 150px;
    object-fit: contain;
}

.recommendation-reason {
    font-size: 0.9em;
    color: #666;
    margin: 10px 0;
    min-height: 40px;
}

.recommendation-card button {
    background: #007bff;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
}

.recommendation-card button:hover {
    background: #0056b3;
}
```

## Docker & Deployment

### 1. `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=10s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run application
CMD ["python", "server.py"]
```

### 2. Update `docker-compose.yaml`

Add recommendations service:

```yaml
  recommendations:
    build:
      context: recommendations
    image: ${REPO}/rs-recommendations:${TAG}
    depends_on:
      - catalogue
    networks:
      - robot-shop
    environment:
      WATSONX_API_KEY: ${WATSONX_API_KEY}
      WATSONX_PROJECT_ID: ${WATSONX_PROJECT_ID}
      WATSONX_URL: ${WATSONX_URL}
      CATALOGUE_HOST: catalogue
      CART_HOST: cart
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 10s
      timeout: 10s
      retries: 3
    logging:
      <<: *logging
```

### 3. Update `web/default.conf.template`

Add proxy for recommendations service:

```nginx
location /api/recommendations/ {
    proxy_pass http://recommendations:8080/;
}
```

## Kubernetes/Helm Integration

### Create Helm Templates

1. **`recommendations-deployment.yaml`**
2. **`recommendations-service.yaml`**

Similar structure to existing services with watsonx.ai secrets.

## Testing Strategy

### Unit Tests
- Test individual LangGraph nodes
- Mock watsonx.ai responses
- Test recommendation logic

### Integration Tests
- Test full agent workflow
- Test API endpoints
- Test with real catalogue data

### End-to-End Tests
- Test complete user flow
- Verify recommendations appear in cart
- Test adding recommended items

## Monitoring & Observability

### Instana Integration
- Add Instana Python collector
- Track recommendation latency
- Monitor watsonx.ai API calls
- Track recommendation acceptance rate

### Custom Metrics
- `recommendations_generated_total` - Counter
- `recommendation_latency_seconds` - Histogram
- `watsonx_api_calls_total` - Counter
- `recommendation_acceptance_rate` - Gauge

## Documentation

### User Documentation
- How to configure watsonx.ai credentials
- How recommendations work
- Customization options

### Developer Documentation
- LangGraph agent architecture
- Adding new recommendation strategies
- Extending the agent

## Timeline Estimate

1. **Setup & Infrastructure** (2-3 hours)
   - Create service structure
   - Setup watsonx.ai integration
   - Basic Flask app

2. **LangGraph Agent** (4-5 hours)
   - Design workflow
   - Implement nodes
   - Test agent logic

3. **Frontend Integration** (2-3 hours)
   - Update cart.html
   - Update controller.js
   - Add CSS styling

4. **Docker & Deployment** (1-2 hours)
   - Dockerfile
   - docker-compose updates
   - Kubernetes templates

5. **Testing & Documentation** (2-3 hours)
   - Write tests
   - Create documentation
   - End-to-end testing

**Total: 11-16 hours**

## Success Criteria

✅ Recommendations service runs as microservice
✅ LangGraph agent successfully generates recommendations
✅ watsonx.ai integration works with mistral-medium
✅ Recommendations appear in cart view
✅ Users can add recommended items to cart
✅ Service is observable via Instana
✅ Graceful degradation if service unavailable
✅ Documentation complete

## Future Enhancements

1. **Personalization**: Track user history for better recommendations
2. **A/B Testing**: Test different recommendation strategies
3. **Real-time Learning**: Update recommendations based on user behavior
4. **Multi-model Support**: Allow switching between different LLMs
5. **Recommendation Explanations**: Show detailed reasoning to users
6. **Performance Optimization**: Cache recommendations, batch processing

## Conclusion

This implementation adds a modern AI agent to Robot Shop, demonstrating how customers can enhance existing applications with AI capabilities. The LangGraph-based architecture provides flexibility for future enhancements while maintaining the microservices pattern that Robot Shop exemplifies.