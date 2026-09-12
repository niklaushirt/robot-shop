# Load Generator Deployment Guide

This guide explains how to deploy and use the in-cluster load generator with admin UI controls for the Robot Shop application.

## Overview

The load generator system consists of:

1. **Load Generator Controller** - REST API service that manages Kubernetes Jobs
2. **Load Generator Job** - Locust-based load testing that runs as a Kubernetes Job
3. **Admin UI** - Web interface to start/stop the load generator and view metrics

## Architecture

```
┌─────────────────┐
│   Admin UI      │ (web/static/admin.html)
│  (Browser)      │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│   Web Service   │ (nginx proxy)
│   Port 8080     │
└────────┬────────┘
         │ Proxy /api/loadgen/*
         ▼
┌─────────────────┐
│ Load Gen        │
│ Controller      │ (Python Flask + Kubernetes API)
│ Port 8080       │
└────────┬────────┘
         │ Creates/Deletes
         ▼
┌─────────────────┐
│ Load Generator  │
│ Job (Locust)    │ ──────► Invokes APIs ──────► Robot Shop Services
└─────────────────┘                               (triggers memory leak)
```

## Prerequisites

1. Kubernetes cluster with RBAC enabled
2. Helm 3.x installed
3. Docker images built and pushed:
   - `robotshop/rs-load:latest` (existing)
   - `robotshop/rs-load-gen-controller:latest` (new)
   - `robotshop/rs-web:latest` (updated)

## Building Docker Images

### 1. Build Load Generator Controller

```bash
cd load-gen-controller
docker build -t robotshop/rs-load-gen-controller:latest .
docker push robotshop/rs-load-gen-controller:latest
```

### 2. Rebuild Web Service (with updated UI)

```bash
cd web
docker build -t robotshop/rs-web:latest .
docker push robotshop/rs-web:latest
```

### 3. Verify Load Generator Image Exists

```bash
cd load-gen
docker build -t robotshop/rs-load:latest .
docker push robotshop/rs-load:latest
```

## Deployment

### Option 1: Helm Deployment (Recommended)

```bash
# Navigate to helm directory
cd K8s/helm

# Install or upgrade the release
helm upgrade --install robot-shop . \
  --set image.repo=robotshop \
  --set image.version=latest \
  --set image.pullPolicy=Always \
  --set psp.enabled=true \
  --namespace robot-shop \
  --create-namespace
```

### Option 2: Manual Kubernetes Deployment

```bash
# Create namespace
kubectl create namespace robot-shop

# Apply RBAC
kubectl apply -f K8s/helm/templates/serviceaccount.yaml
kubectl apply -f K8s/helm/templates/clusterrole.yaml
kubectl apply -f K8s/helm/templates/clusterrolebinding.yaml

# Deploy load-gen-controller
kubectl apply -f K8s/helm/templates/load-gen-controller-deployment.yaml
kubectl apply -f K8s/helm/templates/load-gen-controller-service.yaml

# Deploy web service (updated)
kubectl apply -f K8s/helm/templates/web-deployment.yaml
kubectl apply -f K8s/helm/templates/web-service.yaml

# Deploy other services...
```

## Verification

### 1. Check Pod Status

```bash
kubectl get pods -n robot-shop

# Expected output should include:
# load-gen-controller-xxxxx   1/1     Running
# web-xxxxx                    1/1     Running
```

### 2. Check Services

```bash
kubectl get svc -n robot-shop

# Expected output should include:
# load-gen-controller   ClusterIP   10.x.x.x   <none>   8080/TCP
# web                   NodePort    10.x.x.x   <none>   8080:30080/TCP
```

### 3. Test Load Gen Controller API

```bash
# Port-forward to test directly
kubectl port-forward -n robot-shop svc/load-gen-controller 8081:8080

# In another terminal
curl http://localhost:8081/health
# Expected: {"status": "healthy", "service": "load-gen-controller"}

curl http://localhost:8081/api/loadgen/status
# Expected: {"job_status": "stopped", ...}
```

## Using the Admin UI

### 1. Access the Admin Panel

Navigate to: `http://<your-robot-shop-url>/admin`

Or if using port-forward:
```bash
kubectl port-forward -n robot-shop svc/web 8080:8080
```
Then open: `http://localhost:8080/admin`

### 2. Start Load Generator

1. Set the number of clients (default: 10)
2. Click "▶️ Start Load Generator"
3. Wait for status to change to "RUNNING"
4. Metrics will auto-refresh every 5 seconds

### 3. Monitor Memory Leak

The load generator will invoke all APIs including the checkout-recommendations service, which has an intentional memory leak.

**Expected Timeline:**
- **10 clients**: OOM in ~30 minutes
- **20 clients**: OOM in ~15 minutes
- **30+ clients**: OOM in ~10 minutes

Monitor with:
```bash
# Watch pod memory usage
kubectl top pods -n robot-shop --watch

# Watch for OOM events
kubectl get events -n robot-shop --watch | grep OOM
```

### 4. View Metrics

The admin UI displays:
- **Status**: Running/Stopped/Error
- **Active Clients**: Number of concurrent users
- **API Invocations**: Counter for each service
- **Start Time**: When load generator started
- **Logs**: Recent output from load generator

### 5. Stop Load Generator

Click "⏹️ Stop Load Generator" to terminate the job.

## Troubleshooting

### Load Generator Won't Start

```bash
# Check controller logs
kubectl logs -n robot-shop -l service=load-gen-controller

# Check RBAC permissions
kubectl auth can-i create jobs --as=system:serviceaccount:robot-shop:robot-shop -n robot-shop
# Should return: yes
```

### Admin UI Not Loading

```bash
# Check web service logs
kubectl logs -n robot-shop -l service=web

# Verify nginx config includes load-gen-controller proxy
kubectl exec -n robot-shop -it <web-pod> -- cat /etc/nginx/conf.d/default.conf | grep loadgen
```

### Job Stays in Pending

```bash
# Check job status
kubectl get jobs -n robot-shop

# Check pod events
kubectl describe pod -n robot-shop -l job-name=load-generator

# Common issues:
# - Image pull errors
# - Resource constraints
# - Node selector mismatches
```

### Memory Leak Not Triggering

```bash
# Verify checkout-recommendations is running
kubectl get pods -n robot-shop -l service=checkout-recommendations

# Check if recommendations API is being called
kubectl logs -n robot-shop -l service=checkout-recommendations | grep "recommendations"

# Verify load generator is making requests
kubectl logs -n robot-shop -l job-name=load-generator
```

## Configuration

### Adjust Load Intensity

In the Admin UI, you can set the number of clients from 1-50. Higher numbers will:
- Generate more load
- Trigger OOM faster
- Consume more cluster resources

### Modify Load Generator Behavior

Edit `load-gen/robot-shop.py` to:
- Change wait times between requests
- Add/remove API endpoints
- Adjust error injection rate

### Change Memory Leak Timing

The OOM timing depends on:
1. Number of clients (set in Admin UI)
2. Cache growth rate (in checkout-recommendations)
3. Memory limits (in checkout-recommendations deployment)

To make OOM happen faster, reduce memory limits:
```yaml
# K8s/helm/templates/checkout-recommendations-deployment.yaml
resources:
  limits:
    memory: 256Mi  # Reduce from 512Mi
```

## Monitoring with APM Tools

### Instana

The load generator includes proper headers for distributed tracing:
- `x-forwarded-for`: Simulates different geographic locations
- User sessions are tracked
- All API calls are traced

View in Instana:
1. Navigate to Applications → robot-shop
2. Check Service Map for traffic flow
3. Monitor checkout-recommendations memory usage
4. Set alerts for OOM events

### Prometheus/Grafana

Monitor metrics:
```promql
# Memory usage
container_memory_usage_bytes{pod=~"checkout-recommendations.*"}

# Request rate
rate(http_requests_total{service="checkout-recommendations"}[5m])

# OOM kills
kube_pod_container_status_restarts_total{pod=~"checkout-recommendations.*"}
```

## Cleanup

### Stop Load Generator
Use the Admin UI or:
```bash
kubectl delete job load-generator -n robot-shop
```

### Remove All Components
```bash
helm uninstall robot-shop -n robot-shop
kubectl delete namespace robot-shop
```

## Security Considerations

1. **RBAC**: The load-gen-controller requires permissions to manage Jobs
2. **Network Policies**: Consider restricting load-gen-controller access
3. **Resource Limits**: Set appropriate limits to prevent cluster exhaustion
4. **Admin UI**: Consider adding authentication for production use

## Next Steps

1. Deploy the system
2. Access the Admin UI
3. Start the load generator with 10 clients
4. Monitor checkout-recommendations memory usage
5. Observe OOM event in ~30 minutes
6. Use this to demonstrate APM capabilities

## Support

For issues or questions:
- Check logs: `kubectl logs -n robot-shop -l service=load-gen-controller`
- Review events: `kubectl get events -n robot-shop`
- Verify RBAC: `kubectl auth can-i create jobs --as=system:serviceaccount:robot-shop:robot-shop`