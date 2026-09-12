# AI Agent Architecture Diagram

## System Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        Browser[Browser - AngularJS]
        CartHTML[cart.html]
        Controller[controller.js]
    end

    subgraph "Web Layer"
        Nginx[Nginx Web Server]
    end

    subgraph "Microservices Layer"
        Cart[Cart Service<br/>Node.js]
        Catalogue[Catalogue Service<br/>Node.js]
        Recommendations[Recommendations Service<br/>Python + LangGraph]
    end

    subgraph "AI Layer"
        WatsonX[watsonx.ai<br/>mistral-medium]
    end

    subgraph "Data Layer"
        Redis[(Redis<br/>Cart Data)]
        MongoDB[(MongoDB<br/>Product Catalog)]
    end

    Browser --> Nginx
    Nginx --> Cart
    Nginx --> Recommendations
    Cart --> Redis
    Cart --> Recommendations
    Recommendations --> Catalogue
    Recommendations --> WatsonX
    Catalogue --> MongoDB

    style Recommendations fill:#e1f5ff,stroke:#01579b,stroke-width:3px
    style WatsonX fill:#fff3e0,stroke:#e65100,stroke-width:2px
```

## LangGraph Agent Workflow

```mermaid
graph TD
    Start([API Request<br/>/recommendations/:cartId]) --> FetchCart[Fetch Cart Data<br/>from Cart Service]
    FetchCart --> AnalyzeCart[Analyze Cart Node<br/>Extract categories, prices]
    AnalyzeCart --> DetermineStrategy[Determine Strategy Node<br/>complementary/similar/mixed]
    DetermineStrategy --> FetchProducts[Fetch Products Node<br/>Get available products]
    FetchProducts --> LLMRecommend[LLM Recommend Node<br/>watsonx.ai reasoning]
    LLMRecommend --> RankFilter[Rank & Filter Node<br/>Apply business rules]
    RankFilter --> FormatOutput[Format Output<br/>Structure response]
    FormatOutput --> End([Return JSON Response])

    style LLMRecommend fill:#fff3e0,stroke:#e65100,stroke-width:3px
    style Start fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style End fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
```

## Agent State Flow

```mermaid
stateDiagram-v2
    [*] --> AnalyzeCart
    AnalyzeCart --> DetermineStrategy: cart_items, categories
    DetermineStrategy --> FetchProducts: intent determined
    FetchProducts --> LLMRecommend: available_products loaded
    LLMRecommend --> RankFilter: raw recommendations + reasoning
    RankFilter --> [*]: final recommendations

    note right of LLMRecommend
        Uses watsonx.ai mistral-medium
        Considers:
        - Cart context
        - Product relationships
        - Business rules
    end note
```

## Data Flow Sequence

```mermaid
sequenceDiagram
    participant U as User Browser
    participant N as Nginx
    participant C as Cart Service
    participant R as Recommendations
    participant Cat as Catalogue
    participant W as watsonx.ai
    participant DB as MongoDB

    U->>N: View Cart Page
    N->>C: GET /cart/:id
    C-->>N: Cart Data
    N-->>U: Display Cart
    
    U->>N: Load Recommendations
    N->>R: GET /recommendations/:cartId
    R->>C: GET /cart/:cartId
    C-->>R: Cart Items
    
    R->>Cat: GET /products
    Cat->>DB: Query Products
    DB-->>Cat: Product List
    Cat-->>R: Available Products
    
    R->>R: Analyze Cart<br/>Determine Strategy
    R->>W: Generate Recommendations<br/>(LLM Prompt)
    W-->>R: AI Recommendations
    R->>R: Rank & Filter
    R-->>N: Recommendations JSON
    N-->>U: Display Recommendations
    
    U->>N: Add Recommended Item
    N->>C: GET /add/:id/:sku/:qty
    C-->>N: Updated Cart
    N-->>U: Cart Updated
```

## Recommendation Strategies

```mermaid
graph LR
    subgraph "Cart Analysis"
        Cart[Cart Items]
    end

    subgraph "Strategy Selection"
        Cart --> HasAI{Contains AI<br/>Products?}
        Cart --> HasRobots{Contains<br/>Robots?}
        Cart --> IsEmpty{Cart<br/>Empty?}
    end

    subgraph "Recommendation Types"
        HasAI -->|Yes| Complementary[Complementary Strategy<br/>Suggest physical robots]
        HasRobots -->|Yes| Similar[Similar Strategy<br/>Same category robots]
        IsEmpty -->|Yes| Popular[Popular Strategy<br/>Best sellers]
        HasAI -->|Mixed| Smart[Smart Mix Strategy<br/>LLM decides best approach]
    end

    subgraph "LLM Processing"
        Complementary --> LLM[watsonx.ai<br/>mistral-medium]
        Similar --> LLM
        Popular --> LLM
        Smart --> LLM
    end

    subgraph "Output"
        LLM --> Ranked[Ranked Recommendations<br/>with reasoning]
    end

    style LLM fill:#fff3e0,stroke:#e65100,stroke-width:3px
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Docker Compose / Kubernetes"
        subgraph "Pod: Web"
            WebContainer[Nginx Container]
        end
        
        subgraph "Pod: Cart"
            CartContainer[Node.js Container]
        end
        
        subgraph "Pod: Recommendations"
            RecContainer[Python Container<br/>Flask + LangGraph]
        end
        
        subgraph "Pod: Catalogue"
            CatContainer[Node.js Container]
        end
        
        subgraph "StatefulSet: Data"
            RedisContainer[(Redis)]
            MongoContainer[(MongoDB)]
        end
    end

    subgraph "External Services"
        WatsonXCloud[watsonx.ai Cloud<br/>IBM Cloud]
        Instana[Instana Observability]
    end

    WebContainer --> CartContainer
    WebContainer --> RecContainer
    CartContainer --> RedisContainer
    RecContainer --> CatContainer
    RecContainer --> WatsonXCloud
    CatContainer --> MongoContainer
    
    RecContainer -.->|Traces| Instana
    CartContainer -.->|Traces| Instana
    CatContainer -.->|Traces| Instana

    style RecContainer fill:#e1f5ff,stroke:#01579b,stroke-width:3px
    style WatsonXCloud fill:#fff3e0,stroke:#e65100,stroke-width:2px
```

## Component Interaction Matrix

| Component | Calls | Called By | Data Store | External API |
|-----------|-------|-----------|------------|--------------|
| **Browser** | Nginx | - | - | - |
| **Nginx** | Cart, Recommendations | Browser | - | - |
| **Cart Service** | Redis, Catalogue | Nginx, Recommendations | Redis | - |
| **Recommendations** | Catalogue, watsonx.ai | Nginx, Cart | - | watsonx.ai |
| **Catalogue** | MongoDB | Cart, Recommendations | MongoDB | - |

## Technology Stack Summary

```mermaid
mindmap
  root((AI Agent<br/>Tech Stack))
    Frontend
      AngularJS 1.x
      HTML5/CSS3
      JavaScript
    Backend Services
      Node.js
        Express
        Redis Client
      Python
        Flask
        LangGraph
        LangChain
    AI/ML
      watsonx.ai
        mistral-medium
      LangGraph
        State Management
        Workflow Orchestration
    Data Storage
      Redis
        Cart Data
      MongoDB
        Product Catalog
    Infrastructure
      Docker
      Kubernetes
      Helm
    Observability
      Instana
        Tracing
        Metrics
      Prometheus
        Custom Metrics
```

## Security & Configuration

```mermaid
graph LR
    subgraph "Environment Variables"
        ENV[.env file]
    end

    subgraph "Secrets"
        WX_KEY[WATSONX_API_KEY]
        WX_PROJECT[WATSONX_PROJECT_ID]
        WX_URL[WATSONX_URL]
        INSTANA_KEY[INSTANA_AGENT_KEY]
    end

    subgraph "Recommendations Service"
        Config[Configuration Manager]
        WXClient[watsonx.ai Client]
    end

    ENV --> WX_KEY
    ENV --> WX_PROJECT
    ENV --> WX_URL
    ENV --> INSTANA_KEY

    WX_KEY --> Config
    WX_PROJECT --> Config
    WX_URL --> Config
    Config --> WXClient

    style WX_KEY fill:#ffebee,stroke:#c62828,stroke-width:2px
    style WX_PROJECT fill:#ffebee,stroke:#c62828,stroke-width:2px
    style WX_URL fill:#ffebee,stroke:#c62828,stroke-width:2px
```

## Error Handling & Resilience

```mermaid
graph TD
    Request[Recommendation Request] --> CheckCache{Cache<br/>Available?}
    CheckCache -->|Yes| ReturnCache[Return Cached<br/>Recommendations]
    CheckCache -->|No| CallWatsonX[Call watsonx.ai]
    
    CallWatsonX --> WXSuccess{Success?}
    WXSuccess -->|Yes| CacheResult[Cache Result]
    CacheResult --> ReturnRecs[Return Recommendations]
    
    WXSuccess -->|No| Retry{Retry<br/>Count < 3?}
    Retry -->|Yes| CallWatsonX
    Retry -->|No| Fallback[Fallback Strategy]
    
    Fallback --> RuleBased[Rule-Based<br/>Recommendations]
    RuleBased --> ReturnRecs
    
    ReturnCache --> End([Response])
    ReturnRecs --> End

    style Fallback fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style RuleBased fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
```

## Monitoring Dashboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Recommendations Service - Instana Dashboard                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Request Rate │  │   Latency    │  │  Error Rate  │      │
│  │   125 req/s  │  │   245ms p95  │  │     0.2%     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ watsonx.ai API Calls                                 │    │
│  │ ▂▃▅▇█▇▅▃▂▃▅▇█▇▅▃▂ (Last 1 hour)                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Recommendation Acceptance Rate: 34%                  │    │
│  │ ████████████░░░░░░░░░░░░░░░░░░░░                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Top Strategies   │  │ Cache Hit Rate   │                │
│  │ • Mixed: 45%     │  │      78%         │                │
│  │ • Complementary  │  │ ████████░░       │                │
│  │   32%            │  └──────────────────┘                │
│  │ • Similar: 23%   │                                       │
│  └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

1. **Python for AI Service**: Better ecosystem for AI/ML libraries
2. **LangGraph**: Provides structured workflow for complex agent logic
3. **watsonx.ai**: Enterprise-grade LLM with IBM support
4. **Microservice Pattern**: Maintains Robot Shop's architecture
5. **Graceful Degradation**: Service failure doesn't break cart functionality
6. **Caching Strategy**: Reduces watsonx.ai API calls and improves performance
7. **Instana Integration**: Maintains observability across all services

## Performance Targets

- **Response Time**: < 500ms p95
- **Availability**: 99.5%
- **Cache Hit Rate**: > 70%
- **Recommendation Acceptance**: > 25%
- **watsonx.ai API Success**: > 99%
