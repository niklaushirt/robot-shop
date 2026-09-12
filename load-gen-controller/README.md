# Load Generator Controller

This service provides a REST API to control the Robot Shop load generator running as Kubernetes Jobs.

## Features

- Start/Stop load generator via API
- Real-time metrics and status
- Configurable number of concurrent clients
- Automatic memory leak triggering (targets checkout-recommendations service)

## API Endpoints

### GET /health
Health check endpoint

### GET /api/loadgen/status
Get current load generator status and metrics

Response:
```json
{
  "job_status": "running",
  "start_time": "2026-03-25T00:00:00Z",
  "active_clients": 10,
  "target_host": "http://web:8080",
  "apis_invoked": {
    "catalogue": 150,
    "user": 120,
    "cart": 100,
    "shipping": 80,
    "payment": 75,
    "ratings": 60,
    "recommendations": 50
  },
  "last_update": "2026-03-25T00:30:00Z"
}
```

### POST /api/loadgen/start
Start the load generator

Request body:
```json
{
  "num_clients": 10
}
```

### POST /api/loadgen/stop
Stop the load generator

### GET /api/loadgen/logs
Get recent logs from the load generator pod

## Building

```bash
docker build -t robotshop/rs-load-gen-controller:latest .
```

## Environment Variables

- `NAMESPACE`: Kubernetes namespace (default: robot-shop)
- `LOAD_GEN_IMAGE`: Load generator Docker image (default: robotshop/rs-load:latest)

## Kubernetes Deployment

The service requires RBAC permissions to manage Jobs and Pods:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: robot-shop
rules:
- apiGroups: ["batch"]
  resources: ["jobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["pods", "pods/log"]
  verbs: ["get", "list", "watch"]
```

## Memory Leak Demo

The load generator is configured to trigger the memory leak in the checkout-recommendations service:

- With 10+ clients, the service should OOM in ~30 minutes
- The leak is caused by unbounded caching in the AI agent
- Monitor memory usage in your APM tool or Kubernetes dashboard

## Admin UI

Access the admin panel at: `http://your-robot-shop/admin`

Features:
- Start/Stop controls
- Real-time metrics
- API invocation counters
- Status monitoring