# AI Agent for Robot Shop

This directory contains an AI-powered product recommendation system added to Robot Shop, demonstrating how to integrate AI capabilities into existing applications.

## 🎯 What's New

An intelligent recommendation agent that suggests products to customers based on their shopping cart contents, using:
- **LangGraph** for structured AI workflows
- **watsonx.ai** (mistral-large) for intelligent reasoning
- **FastMCP** for real-time product analytics
- **Real behavioral data** (popularity, ratings) to enhance recommendations

## 📁 Documentation

All AI Agent documentation is organized in the [`recommendations/`](recommendations/) folder:

### Quick Start
- **[QUICK_START_GUIDE.md](recommendations/QUICK_START_GUIDE.md)** - Get started in 5 minutes
- **[DEPLOYMENT_GUIDE.md](recommendations/DEPLOYMENT_GUIDE.md)** - Complete deployment instructions
- **[AI_IMPLEMENTATION_SUMMARY.md](recommendations/AI_IMPLEMENTATION_SUMMARY.md)** - Implementation overview

### Technical Documentation
- **[AI_AGENT_IMPLEMENTATION_PLAN.md](recommendations/AI_AGENT_IMPLEMENTATION_PLAN.md)** - Detailed technical specification
- **[AI_AGENT_ARCHITECTURE.md](recommendations/AI_AGENT_ARCHITECTURE.md)** - Architecture diagrams and design
- **[README.md](recommendations/README.md)** - Service documentation
- **[MCP_SERVER_README.md](recommendations/MCP_SERVER_README.md)** - MCP tools documentation

## 🚀 Quick Start

### 1. Set watsonx.ai Credentials

```bash
export WATSONX_API_KEY=your-api-key
export WATSONX_PROJECT_ID=your-project-id
```

### 2. Start Services

```bash
docker-compose up -d
```

### 3. Test

Open http://localhost:8080, add items to cart, and see AI recommendations!

## 🏗️ Architecture

```
Browser → Nginx → Recommendations Service
                  ├── LangGraph Agent
                  │   └── watsonx.ai (mistral-large)
                  ├── MCP Tools
                  │   ├── get_product_popularity()
                  │   └── get_product_ratings()
                  └── Catalogue & Ratings Services
```

## ✨ Key Features

- **AI-Powered**: Uses watsonx.ai for intelligent product recommendations
- **Data-Driven**: MCP tools provide real popularity and ratings data
- **Smart Fallback**: Works without AI using rule-based logic
- **Production Ready**: Health checks, metrics, K8s deployment
- **Modern UI**: Clean product cards in shopping cart

## 📦 What's Included

### New Service
- `recommendations/` - Complete AI recommendation microservice
  - Python Flask application
  - LangGraph workflow
  - FastMCP server with analytics tools
  - Docker and Kubernetes deployment

### Frontend Updates
- Shopping cart displays AI recommendations
- One-click "Add to Cart" for suggested products
- Responsive design with hover effects

### Infrastructure
- Docker Compose integration
- Kubernetes/Helm templates
- Nginx proxy configuration

## 🔧 MCP Tools

The AI agent uses two MCP tools for real-time analytics:

1. **`get_product_popularity()`** - Returns trending products
2. **`get_product_ratings(sku)`** - Fetches ratings and reviews

These tools enhance the AI's decision-making with actual behavioral data.

## 📊 How It Works

1. User adds items to cart
2. Frontend calls `/api/recommendations/:cartId`
3. LangGraph agent:
   - Analyzes cart contents
   - Calls MCP tools for product data
   - Sends enhanced prompt to watsonx.ai
   - Generates intelligent recommendations
4. Frontend displays recommendations
5. User can add recommended items with one click

## 🎓 Learning Resources

This implementation demonstrates:
- **AI Integration** - Adding AI to existing applications
- **LangGraph** - Structured AI agent workflows
- **MCP Protocol** - Tool integration for AI agents
- **Microservices** - Adding new services to existing architecture
- **Kubernetes** - Deploying AI services at scale

## 📖 Documentation Structure

```
recommendations/
├── README.md                          # Service overview
├── QUICK_START_GUIDE.md              # 5-minute setup
├── DEPLOYMENT_GUIDE.md               # Complete deployment
├── AI_IMPLEMENTATION_SUMMARY.md      # What was built
├── AI_AGENT_IMPLEMENTATION_PLAN.md   # Technical spec
├── AI_AGENT_ARCHITECTURE.md          # Architecture diagrams
├── MCP_SERVER_README.md              # MCP tools docs
├── server.py                         # Main service
├── mcp_server.py                     # FastMCP server
├── requirements.txt                  # Dependencies
└── Dockerfile                        # Container config
```

## 🚢 Deployment Options

### Docker Compose (Local)
```bash
docker-compose up -d
```

### Kubernetes
```bash
kubectl create secret generic watsonx-credentials \
  --from-literal=api-key=YOUR_KEY \
  --from-literal=project-id=YOUR_PROJECT

helm install robot-shop K8s/helm
```

## 🔍 Monitoring

- **Health**: `http://localhost:8080/api/recommendations/health`
- **Metrics**: `http://localhost:8080/api/recommendations/metrics`
- **Logs**: `docker-compose logs -f recommendations`

## 🎯 Success Metrics

Track these to measure AI agent effectiveness:
- Recommendation acceptance rate (target: >25%)
- Average cart value increase
- User engagement with recommendations
- Response time (<500ms p95)

## 🤝 Contributing

This is a demo implementation. To extend it:
1. Add more MCP tools (user history, promotions, etc.)
2. Implement A/B testing for different strategies
3. Add caching for improved performance
4. Enhance personalization with user data

## 📝 License

Same as Robot Shop parent project.

## 🆘 Support

For issues or questions:
1. Check [DEPLOYMENT_GUIDE.md](recommendations/DEPLOYMENT_GUIDE.md) troubleshooting section
2. Review service logs
3. Test API endpoints directly
4. Verify watsonx.ai connectivity

## 🎉 What's Next?

After deployment:
1. Monitor recommendation quality
2. Gather user feedback
3. A/B test different strategies
4. Add personalization features
5. Optimize performance

---

**Ready to add AI to your applications?** Start with the [Quick Start Guide](recommendations/QUICK_START_GUIDE.md)!