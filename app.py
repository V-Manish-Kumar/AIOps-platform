"""
AIOps MVP - Main Flask Application

Provides:
1. Monitored service endpoints (/health, /checkout, /payment, /inventory)
2. AIOps analysis endpoints (/aiops/*)
3. Failure simulation controls (/simulate/*)

This demonstrates automatic failure detection with zero manual configuration.
"""

import threading
import time
from flask import Flask, request, jsonify, g

# Import our modules
from telemetry import TelemetryCollector
from aiops import AIOpsAnalyzer, RCAEngine
from simulation import get_injector, with_failure_injection

# Initialize Flask app
app = Flask(__name__)

# Initialize telemetry collection (automatic instrumentation)
telemetry = TelemetryCollector(service_name="api-service")
telemetry.init_app(app)

# Initialize AIOps components
analyzer = AIOpsAnalyzer()
rca_engine = RCAEngine()

# Failure injector for testing
injector = get_injector()


# ============================================================================
# MONITORED SERVICE ENDPOINTS
# These are the business endpoints that get automatically monitored
# ============================================================================

@app.route('/health', methods=['GET'])
@with_failure_injection
def health():
    """
    Simple health check endpoint.
    
    Automatically instrumented by telemetry middleware.
    No manual logging needed.
    """
    return jsonify({
        'status': 'healthy',
        'service': 'api-service',
        'trace_id': g.trace_id
    })


@app.route('/inventory', methods=['GET'])
@with_failure_injection
def inventory():
    """
    Inventory check endpoint.
    
    Simulates checking product availability.
    Can be made to fail via simulation API.
    """
    # Simulate some processing time
    time.sleep(0.05)
    
    return jsonify({
        'status': 'success',
        'available': True,
        'quantity': 42,
        'trace_id': g.trace_id
    })


@app.route('/payment', methods=['POST'])
@with_failure_injection
def payment():
    """
    Payment processing endpoint.
    
    Simulates payment gateway interaction.
    Note: Uses same trace_id as caller for correlation.
    """
    # Simulate payment processing
    time.sleep(0.1)
    
    return jsonify({
        'status': 'success',
        'transaction_id': 'txn-12345',
        'trace_id': g.trace_id
    })


@app.route('/checkout', methods=['POST'])
@with_failure_injection
def checkout():
    """
    Checkout endpoint - orchestrates payment and inventory.
    
    This demonstrates request flow for RCA:
    checkout -> payment (internal call)
    checkout -> inventory (internal call)
    
    If payment fails, checkout fails too.
    AIOps will identify payment as root cause.
    """
    import requests
    
    try:
        # Call payment endpoint (internal service call)
        # Pass trace_id for correlation
        payment_response = requests.post(
            'http://localhost:5000/payment',
            headers={'X-Trace-ID': g.trace_id},
            timeout=5
        )
        payment_response.raise_for_status()
        
        # Call inventory endpoint
        inventory_response = requests.get(
            'http://localhost:5000/inventory',
            headers={'X-Trace-ID': g.trace_id},
            timeout=5
        )
        inventory_response.raise_for_status()
        
        return jsonify({
            'status': 'success',
            'message': 'Checkout completed',
            'payment': payment_response.json(),
            'inventory': inventory_response.json(),
            'trace_id': g.trace_id
        })
    
    except requests.exceptions.RequestException as e:
        # Downstream failure
        raise Exception(f"Checkout failed due to downstream error: {str(e)}")


# ============================================================================
# AIOPS ENDPOINTS
# These expose the AIOps analysis and incident management
# ============================================================================

@app.route('/aiops/metrics', methods=['GET'])
def aiops_metrics():
    """
    Get current metrics and health status for all endpoints.
    
    Returns:
    - Per-endpoint statistics (latency, error rate, request count)
    - Baseline latency (learned automatically)
    - Health scores
    """
    endpoints = telemetry.storage.get_all_endpoints()
    
    # Filter out internal endpoints
    business_endpoints = [
        e for e in endpoints 
        if not e.startswith('/aiops/') and not e.startswith('/simulate/')
    ]
    
    metrics = {}
    for endpoint in business_endpoints:
        stats = telemetry.storage.get_endpoint_stats(endpoint, minutes=60)
        health = analyzer.get_endpoint_health(endpoint)
        
        metrics[endpoint] = {
            **stats,
            'baseline_latency_ms': analyzer.baseline_latency.get(endpoint),
            'health': health
        }
    
    return jsonify({
        'timestamp': time.time(),
        'metrics': metrics
    })


@app.route('/aiops/incidents', methods=['GET'])
def aiops_incidents():
    """
    Get active incidents detected by AIOps.
    
    Each incident includes:
    - Root cause analysis
    - Affected endpoints
    - Trace correlation
    - Severity and status
    """
    incidents = rca_engine.get_active_incidents()
    
    return jsonify({
        'timestamp': time.time(),
        'active_incidents': incidents,
        'incident_count': len(incidents)
    })


@app.route('/aiops/incidents/<incident_id>', methods=['GET'])
def aiops_incident_detail(incident_id):
    """Get detailed information about a specific incident."""
    incident = rca_engine.get_incident_by_id(incident_id)
    
    if not incident:
        return jsonify({'error': 'Incident not found'}), 404
    
    return jsonify(incident)


@app.route('/aiops/incidents/<incident_id>/resolve', methods=['POST'])
def aiops_resolve_incident(incident_id):
    """
    Manually resolve an incident.
    
    In production, would include:
    - Acknowledgment workflow
    - Resolution notes
    - Post-mortem documentation
    """
    rca_engine.resolve_incident(incident_id)
    return jsonify({'status': 'resolved', 'incident_id': incident_id})


@app.route('/aiops/analyze', methods=['POST'])
def aiops_trigger_analysis():
    """
    Manually trigger AIOps analysis.
    
    Normally runs automatically in background,
    but can be triggered on-demand for testing.
    """
    # Run anomaly detection
    analysis = analyzer.run_analysis()
    
    # Run RCA on detected anomalies
    incidents = rca_engine.correlate_anomalies(analysis['anomalies'])
    
    return jsonify({
        'analysis': analysis,
        'incidents_created': len(incidents)
    })


# ============================================================================
# SIMULATION ENDPOINTS
# Control failure injection for testing
# ============================================================================

@app.route('/simulate/delay', methods=['POST'])
def simulate_delay():
    """
    Add artificial delay to an endpoint.
    
    Query params:
    - endpoint: Target endpoint (e.g., '/payment')
    - duration: Delay in milliseconds
    
    Example: POST /simulate/delay?endpoint=/payment&duration=2000
    """
    endpoint = request.args.get('endpoint')
    duration_ms = int(request.args.get('duration', 0))
    
    if not endpoint:
        return jsonify({'error': 'endpoint parameter required'}), 400
    
    injector.set_delay(endpoint, duration_ms)
    
    return jsonify({
        'status': 'configured',
        'endpoint': endpoint,
        'delay_ms': duration_ms
    })


@app.route('/simulate/error', methods=['POST'])
def simulate_error():
    """
    Configure endpoint to fail randomly.
    
    Query params:
    - endpoint: Target endpoint
    - rate: Error rate (0.0 - 1.0)
    
    Example: POST /simulate/error?endpoint=/inventory&rate=0.5
    """
    endpoint = request.args.get('endpoint')
    rate = float(request.args.get('rate', 0))
    
    if not endpoint:
        return jsonify({'error': 'endpoint parameter required'}), 400
    
    injector.set_error_rate(endpoint, rate)
    
    return jsonify({
        'status': 'configured',
        'endpoint': endpoint,
        'error_rate': rate
    })


@app.route('/simulate/clear', methods=['POST'])
def simulate_clear():
    """
    Clear all failure simulations.
    
    Optional query param:
    - endpoint: Clear only specific endpoint (if omitted, clears all)
    """
    endpoint = request.args.get('endpoint')
    
    if endpoint:
        injector.clear_endpoint(endpoint)
        return jsonify({'status': 'cleared', 'endpoint': endpoint})
    else:
        injector.clear_all()
        return jsonify({'status': 'cleared', 'message': 'All simulations cleared'})


@app.route('/simulate/status', methods=['GET'])
def simulate_status():
    """Get current simulation configuration."""
    return jsonify({
        'simulations': injector.get_config()
    })


# ============================================================================
# BACKGROUND AIOPS ANALYSIS
# Runs continuously to detect anomalies
# ============================================================================

def aiops_background_worker():
    """
    Background thread that runs AIOps analysis periodically.
    
    In production, use:
    - Celery beat for distributed scheduling
    - Separate worker processes
    - Redis for coordination
    
    For MVP, simple thread is sufficient.
    """
    while True:
        try:
            # Wait 30 seconds between analyses
            time.sleep(30)
            
            # Run analysis
            analysis = analyzer.run_analysis()
            
            # If anomalies detected, run RCA
            if analysis['anomalies']:
                incidents = rca_engine.correlate_anomalies(analysis['anomalies'])
                if incidents:
                    print(f"[AIOps] Detected {len(incidents)} incident(s)")
                    for inc in incidents:
                        print(f"  - {inc['id']}: {inc['title']} (severity: {inc['severity']})")
            
        except Exception as e:
            print(f"[AIOps] Background worker error: {e}")


# ============================================================================
# APPLICATION STARTUP
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("AIOps MVP - Automatic Failure Detection & Root Cause Analysis")
    print("=" * 70)
    print("\n📊 Starting AIOps background analysis...")
    
    # Start background analysis thread
    worker_thread = threading.Thread(target=aiops_background_worker, daemon=True)
    worker_thread.start()
    
    print("✅ Background worker started")
    print("\n🌐 Starting Flask server...")
    print("\nAvailable endpoints:")
    print("  Business endpoints:")
    print("    GET  /health")
    print("    GET  /inventory")
    print("    POST /payment")
    print("    POST /checkout")
    print("\n  AIOps endpoints:")
    print("    GET  /aiops/metrics    - View endpoint metrics")
    print("    GET  /aiops/incidents  - View active incidents")
    print("    POST /aiops/analyze    - Trigger manual analysis")
    print("\n  Simulation endpoints:")
    print("    POST /simulate/delay   - Add latency")
    print("    POST /simulate/error   - Inject errors")
    print("    POST /simulate/clear   - Clear simulations")
    print("    GET  /simulate/status  - View config")
    print("\n" + "=" * 70)
    print("🚀 Server running on http://localhost:5000")
    print("=" * 70 + "\n")
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
