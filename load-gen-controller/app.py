from flask import Flask, jsonify, request
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import os
import logging
from datetime import datetime, timedelta
import json
import requests
import threading
import time

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Kubernetes config
try:
    config.load_incluster_config()
    logger.info("Loaded in-cluster Kubernetes config")
except:
    config.load_kube_config()
    logger.info("Loaded local Kubernetes config")

batch_v1 = client.BatchV1Api()
core_v1 = client.CoreV1Api()

NAMESPACE = os.environ.get('NAMESPACE', 'robot-shop')
JOB_NAME = 'load-generator'
LOAD_GEN_IMAGE = os.environ.get('LOAD_GEN_IMAGE', 'robotshop/rs-load:latest')

# In-memory metrics storage
metrics = {
    'job_status': 'stopped',
    'start_time': None,
    'requests_sent': 0,
    'last_update': None,
    'active_clients': 0,
    'target_host': 'http://web:8080',
    'apis_invoked': {
        'catalogue': 0,
        'user': 0,
        'cart': 0,
        'shipping': 0,
        'payment': 0,
        'ratings': 0,
        'recommendations': 0
    },
    'oom_trigger': {
        'active': False,
        'requests_sent': 0,
        'start_time': None,
        'target_requests': 0
    },
    'checkout_memory': {
        'current_mb': 0,
        'limit_mb': 0,
        'percentage': 0,
        'last_update': None
    }
}

# OOM trigger state
oom_trigger_active = False
oom_trigger_thread = None

def get_job_status():
    """Get the current status of the load generator job"""
    try:
        job = batch_v1.read_namespaced_job(name=JOB_NAME, namespace=NAMESPACE)
        if job.status.active and job.status.active > 0:
            return 'running'
        elif job.status.succeeded and job.status.succeeded > 0:
            return 'completed'
        elif job.status.failed and job.status.failed > 0:
            return 'failed'
        return 'unknown'
    except ApiException as e:
        if e.status == 404:
            return 'stopped'
        logger.error(f"Error getting job status: {e}")
        return 'error'

def get_pod_logs():
    """Get logs from the load generator pod to extract metrics"""
    try:
        pods = core_v1.list_namespaced_pod(
            namespace=NAMESPACE,
            label_selector=f'job-name={JOB_NAME}'
        )
        
        if pods.items:
            pod_name = pods.items[0].metadata.name
            logs = core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=NAMESPACE,
                tail_lines=200
            )
            
            # Parse Locust statistics table to extract metrics
            # Reset counters before parsing to avoid accumulation
            api_counts = {
                'catalogue': 0,
                'user': 0,
                'cart': 0,
                'shipping': 0,
                'payment': 0,
                'ratings': 0,
                'recommendations': 0
            }
            total_requests = 0
            
            lines = logs.split('\n')
            for line in lines:
                # Look for lines with API endpoints and request counts
                # Format: METHOD  //api/endpoint  # reqs  # fails | ...
                if '//api/' in line and '|' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            # Extract request count (3rd column after method and endpoint)
                            req_count = int(parts[2])
                            total_requests += req_count
                            
                            # Categorize by API endpoint
                            endpoint = line.lower()
                            if '/api/catalogue/' in endpoint:
                                api_counts['catalogue'] += req_count
                            elif '/api/user/' in endpoint:
                                api_counts['user'] += req_count
                            elif '/api/cart/' in endpoint:
                                api_counts['cart'] += req_count
                            elif '/api/shipping/' in endpoint:
                                api_counts['shipping'] += req_count
                            elif '/api/payment/' in endpoint:
                                api_counts['payment'] += req_count
                            elif '/api/ratings/' in endpoint:
                                api_counts['ratings'] += req_count
                            elif '/api/recommendations/' in endpoint or 'checkout' in endpoint:
                                api_counts['recommendations'] += req_count
                        except (ValueError, IndexError):
                            continue
            
            # Update metrics with parsed values
            metrics['apis_invoked'] = api_counts
            metrics['requests_sent'] = total_requests
            
            return logs
        return None
    except Exception as e:
        logger.error(f"Error getting pod logs: {e}")
        return None

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'load-gen-controller'}), 200

@app.route('/api/loadgen/status', methods=['GET'])
def status():
    """Get current load generator status and metrics"""
    job_status = get_job_status()
    metrics['job_status'] = job_status
    metrics['status'] = job_status  # Add 'status' field for UI compatibility
    metrics['last_update'] = datetime.utcnow().isoformat()
    
    # Get pod logs to update metrics and retrieve active_clients from running pod
    if job_status == 'running':
        get_pod_logs()
        
        # Get active_clients and start_time from the running pod
        try:
            pods = core_v1.list_namespaced_pod(
                namespace=NAMESPACE,
                label_selector=f'job-name={JOB_NAME}'
            )
            
            if pods.items:
                pod = pods.items[0]
                # Get NUM_CLIENTS from pod env vars
                for container in pod.spec.containers:
                    if container.name == 'load-gen':
                        for env_var in container.env:
                            if env_var.name == 'NUM_CLIENTS':
                                metrics['active_clients'] = int(env_var.value)
                                break
                
                # Get start time from pod creation timestamp
                if pod.metadata.creation_timestamp and not metrics['start_time']:
                    metrics['start_time'] = pod.metadata.creation_timestamp.isoformat()
        except Exception as e:
            logger.error(f"Error getting pod details: {e}")
    
    return jsonify(metrics), 200

@app.route('/api/loadgen/start', methods=['POST'])
def start():
    """Start the load generator job"""
    try:
        # Check if job already exists
        current_status = get_job_status()
        if current_status == 'running':
            return jsonify({'error': 'Load generator is already running'}), 400
        
        # Delete old job if it exists
        try:
            batch_v1.delete_namespaced_job(
                name=JOB_NAME,
                namespace=NAMESPACE,
                body=client.V1DeleteOptions(propagation_policy='Background')
            )
            logger.info(f"Deleted old job {JOB_NAME}")
        except ApiException as e:
            if e.status != 404:
                logger.warning(f"Error deleting old job: {e}")
        
        # Get parameters from request
        data = request.get_json() or {}
        num_clients = data.get('num_clients', 10)
        
        # Create job
        job = client.V1Job(
            api_version='batch/v1',
            kind='Job',
            metadata=client.V1ObjectMeta(name=JOB_NAME),
            spec=client.V1JobSpec(
                ttl_seconds_after_finished=300,
                backoff_limit=0,
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={'job-name': JOB_NAME}),
                    spec=client.V1PodSpec(
                        restart_policy='Never',
                        containers=[
                            client.V1Container(
                                name='load-gen',
                                image=LOAD_GEN_IMAGE,
                                env=[
                                    client.V1EnvVar(name='HOST', value='http://web:8080/'),
                                    client.V1EnvVar(name='NUM_CLIENTS', value=str(num_clients)),
                                    client.V1EnvVar(name='SILENT', value='0'),
                                    client.V1EnvVar(name='ERROR', value='1'),
                                    client.V1EnvVar(name='RUN_TIME', value='0')  # Run indefinitely
                                ],
                                resources=client.V1ResourceRequirements(
                                    limits={'cpu': '500m', 'memory': '512Mi'},
                                    requests={'cpu': '200m', 'memory': '256Mi'}
                                )
                            )
                        ]
                    )
                )
            )
        )
        
        batch_v1.create_namespaced_job(namespace=NAMESPACE, body=job)
        
        # Update metrics
        metrics['job_status'] = 'running'
        metrics['start_time'] = datetime.utcnow().isoformat()
        metrics['active_clients'] = num_clients
        metrics['requests_sent'] = 0
        metrics['apis_invoked'] = {k: 0 for k in metrics['apis_invoked']}
        
        logger.info(f"Started load generator job with {num_clients} clients")
        return jsonify({'message': 'Load generator started', 'clients': num_clients}), 200
        
    except Exception as e:
        logger.error(f"Error starting load generator: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/loadgen/stop', methods=['POST'])
def stop():
    """Stop the load generator job"""
    try:
        batch_v1.delete_namespaced_job(
            name=JOB_NAME,
            namespace=NAMESPACE,
            body=client.V1DeleteOptions(propagation_policy='Background')
        )
        
        # Update metrics
        metrics['job_status'] = 'stopped'
        metrics['active_clients'] = 0
        
        logger.info("Stopped load generator job")
        return jsonify({'message': 'Load generator stopped'}), 200
        
    except ApiException as e:
        if e.status == 404:
            return jsonify({'message': 'Load generator was not running'}), 200
        logger.error(f"Error stopping load generator: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/loadgen/logs', methods=['GET'])
def logs():
    """Get load generator logs"""
    try:
        log_output = get_pod_logs()
        if log_output:
            return jsonify({'logs': log_output}), 200
        return jsonify({'logs': 'No logs available'}), 200
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/checkout/memory', methods=['GET'])
def get_checkout_memory():
    """Get memory usage of checkout-recommendations pod"""
    try:
        pods = core_v1.list_namespaced_pod(
            namespace=NAMESPACE,
            label_selector='service=checkout-recommendations'
        )
        
        if not pods.items:
            return jsonify({'error': 'checkout-recommendations pod not found'}), 404
        
        pod = pods.items[0]
        pod_name = pod.metadata.name
        
        # Get memory limit from pod spec
        memory_limit_str = None
        for container in pod.spec.containers:
            if container.resources and container.resources.limits:
                memory_limit_str = container.resources.limits.get('memory')
                break
        
        # Parse memory limit (e.g., "512Mi" -> 512)
        memory_limit_mb = 512  # default
        if memory_limit_str:
            if memory_limit_str.endswith('Mi'):
                memory_limit_mb = int(memory_limit_str[:-2])
            elif memory_limit_str.endswith('Gi'):
                memory_limit_mb = int(memory_limit_str[:-2]) * 1024
        
        # Get current memory usage from metrics API
        try:
            from kubernetes import client as k8s_client
            metrics_api = k8s_client.CustomObjectsApi()
            pod_metrics = metrics_api.get_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace=NAMESPACE,
                plural="pods",
                name=pod_name
            )
            
            # Parse memory usage (e.g., "123456Ki" -> MB)
            memory_usage_str = pod_metrics['containers'][0]['usage']['memory']
            if memory_usage_str.endswith('Ki'):
                memory_usage_mb = int(memory_usage_str[:-2]) / 1024
            elif memory_usage_str.endswith('Mi'):
                memory_usage_mb = int(memory_usage_str[:-2])
            else:
                memory_usage_mb = int(memory_usage_str) / (1024 * 1024)
            
            percentage = (memory_usage_mb / memory_limit_mb) * 100
            
            # Update metrics
            metrics['checkout_memory'] = {
                'current_mb': round(memory_usage_mb, 2),
                'limit_mb': memory_limit_mb,
                'percentage': round(percentage, 2),
                'last_update': datetime.utcnow().isoformat()
            }
            
            return jsonify(metrics['checkout_memory']), 200
            
        except Exception as e:
            logger.warning(f"Could not get pod metrics: {e}")
            # Fallback: try to get from cache stats endpoint
            try:
                cache_response = requests.get(
                    f'http://checkout-recommendations:8080/cache/stats',
                    timeout=2
                )
                if cache_response.status_code == 200:
                    cache_data = cache_response.json()
                    # Estimate memory from cache size
                    estimated_mb = cache_data.get('cache_size_mb', 0) + 50  # base memory
                    percentage = (estimated_mb / memory_limit_mb) * 100
                    
                    metrics['checkout_memory'] = {
                        'current_mb': round(estimated_mb, 2),
                        'limit_mb': memory_limit_mb,
                        'percentage': round(percentage, 2),
                        'last_update': datetime.utcnow().isoformat(),
                        'estimated': True
                    }
                    return jsonify(metrics['checkout_memory']), 200
            except:
                pass
            
            return jsonify({'error': 'Could not retrieve memory metrics'}), 500
            
    except Exception as e:
        logger.error(f"Error getting checkout memory: {e}")
        return jsonify({'error': str(e)}), 500

def oom_trigger_worker(target_requests):
    """Background worker to trigger OOM by hammering recommendations endpoint with parallel requests"""
    global oom_trigger_active
    
    logger.info(f"🚨 AGGRESSIVE OOM trigger started - target: {target_requests} requests with 20 parallel workers")
    metrics['oom_trigger']['active'] = True
    metrics['oom_trigger']['requests_sent'] = 0
    metrics['oom_trigger']['start_time'] = datetime.utcnow().isoformat()
    metrics['oom_trigger']['target_requests'] = target_requests
    
    base_url = 'http://checkout-recommendations:8080'
    requests_sent = 0
    request_lock = threading.Lock()
    
    def send_request(request_num):
        """Send a single request with unique cart ID"""
        nonlocal requests_sent
        if not oom_trigger_active or requests_sent >= target_requests:
            return
        
        # 🚨 AGGRESSIVE: Use timestamp + random to ensure 100% unique cart IDs
        import random
        cart_id = f"oom-{int(time.time() * 1000000)}-{request_num}-{random.randint(1, 999999)}"
        
        try:
            response = requests.get(
                f'{base_url}/recommendations/{cart_id}',
                timeout=15
            )
            with request_lock:
                requests_sent += 1
                metrics['oom_trigger']['requests_sent'] = requests_sent
                
                if requests_sent % 50 == 0:
                    logger.info(f"💥 OOM trigger progress: {requests_sent}/{target_requests}")
                    
        except requests.exceptions.RequestException as e:
            # Don't log every error, just count them
            with request_lock:
                requests_sent += 1
                metrics['oom_trigger']['requests_sent'] = requests_sent
    
    try:
        # 🚨 AGGRESSIVE: Use 20 parallel workers for maximum throughput
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            for i in range(target_requests):
                if not oom_trigger_active:
                    break
                future = executor.submit(send_request, i)
                futures.append(future)
                
                # 🚨 AGGRESSIVE: Submit in larger batches for faster execution
                if len(futures) >= 100:
                    # Wait for some to complete
                    for f in as_completed(futures[:50]):
                        pass
                    futures = futures[50:]
            
            # Wait for remaining requests
            for f in as_completed(futures):
                pass
                
    except Exception as e:
        logger.error(f"OOM trigger error: {e}")
    finally:
        oom_trigger_active = False
        metrics['oom_trigger']['active'] = False
        logger.info(f"🎯 OOM trigger completed - sent {requests_sent} requests")

@app.route('/api/oom/trigger', methods=['POST'])
def trigger_oom():
    """Start aggressive OOM trigger - designed to trigger OOM within 30 seconds"""
    global oom_trigger_active, oom_trigger_thread
    
    if oom_trigger_active:
        return jsonify({'error': 'OOM trigger already active'}), 400
    
    data = request.get_json() or {}
    # 🚨 AGGRESSIVE DEFAULT: 500 requests with 1MB padding each = ~500MB in 30 seconds
    # With 20 parallel workers, this should complete in ~25-30 seconds
    target_requests = data.get('target_requests', 500)
    
    oom_trigger_active = True
    oom_trigger_thread = threading.Thread(
        target=oom_trigger_worker,
        args=(target_requests,),
        daemon=True
    )
    oom_trigger_thread.start()
    
    logger.info(f"🚨 OOM trigger initiated with {target_requests} requests - expect OOM in ~30 seconds")
    
    return jsonify({
        'message': 'OOM trigger started - expect OOM within 30 seconds',
        'target_requests': target_requests,
        'estimated_memory_mb': target_requests * 1,  # ~1MB per request
        'parallel_workers': 20
    }), 200

@app.route('/api/oom/stop', methods=['POST'])
def stop_oom_trigger():
    """Stop OOM trigger"""
    global oom_trigger_active
    
    if not oom_trigger_active:
        return jsonify({'message': 'OOM trigger was not active'}), 200
    
    oom_trigger_active = False
    logger.info("OOM trigger stopped by user")
    
    return jsonify({'message': 'OOM trigger stopped'}), 200

@app.route('/api/oom/status', methods=['GET'])
def oom_status():
    """Get OOM trigger status"""
    return jsonify(metrics['oom_trigger']), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)

# Made with Bob
