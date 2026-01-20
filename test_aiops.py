"""
Quick Test Script for AIOps MVP

Demonstrates the complete AIOps workflow:
1. Generate normal traffic
2. Simulate failures
3. View detected incidents and RCA
"""

import requests
import time
import json


BASE_URL = "http://localhost:5000"


def print_section(title):
    """Print formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def make_request(method, endpoint, **kwargs):
    """Make HTTP request and handle errors."""
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.request(method, url, **kwargs)
        return response
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None


def test_normal_traffic():
    """Generate some normal traffic to establish baselines."""
    print_section("1. Generating Normal Traffic (Baseline Learning)")
    print("Making 20 requests to establish normal behavior...")
    
    for i in range(20):
        make_request("GET", "/health")
        make_request("GET", "/inventory")
        make_request("POST", "/payment")
        time.sleep(0.1)
    
    print("✅ Baseline traffic generated")
    time.sleep(2)


def view_metrics():
    """View current endpoint metrics."""
    print_section("2. Viewing Current Metrics")
    
    response = make_request("GET", "/aiops/metrics")
    if response and response.status_code == 200:
        data = response.json()
        print("\nEndpoint Metrics:")
        for endpoint, metrics in data['metrics'].items():
            print(f"\n  {endpoint}:")
            print(f"    Requests: {metrics['request_count']}")
            print(f"    Avg Latency: {metrics['avg_latency_ms']:.2f}ms")
            print(f"    Baseline: {metrics['baseline_latency_ms']:.2f}ms" if metrics['baseline_latency_ms'] else "    Baseline: Learning...")
            print(f"    Error Rate: {metrics['error_rate']*100:.1f}%")
            print(f"    Health: {metrics['health']['status']} (score: {metrics['health']['health_score']})")


def simulate_latency_spike():
    """Test latency anomaly detection."""
    print_section("3. Simulating Latency Spike on /payment")
    
    # Add 2-second delay to payment
    response = make_request("POST", "/simulate/delay?endpoint=/payment&duration=2000")
    if response and response.status_code == 200:
        print("✅ Configured 2-second delay on /payment")
    
    # Trigger some requests
    print("\nTriggering affected requests...")
    for i in range(10):
        make_request("POST", "/checkout")  # Will be slow due to payment delay
        time.sleep(0.5)
    
    print("✅ Requests completed")


def simulate_error_spike():
    """Test error spike detection."""
    print_section("4. Simulating Error Spike on /inventory")
    
    # Make inventory fail 80% of the time
    response = make_request("POST", "/simulate/error?endpoint=/inventory&rate=0.8")
    if response and response.status_code == 200:
        print("✅ Configured 80% error rate on /inventory")
    
    # Trigger some requests
    print("\nTriggering requests (expect failures)...")
    for i in range(15):
        make_request("GET", "/inventory")
        time.sleep(0.3)
    
    print("✅ Test requests completed")


def wait_for_analysis():
    """Wait for background AIOps analysis to run."""
    print_section("5. Waiting for AIOps Analysis")
    print("Background analysis runs every 30 seconds...")
    print("Waiting 35 seconds for detection...")
    
    for i in range(35, 0, -5):
        print(f"  {i} seconds remaining...")
        time.sleep(5)
    
    print("✅ Analysis should have completed")


def view_incidents():
    """View detected incidents with RCA."""
    print_section("6. Viewing Detected Incidents (RCA)")
    
    response = make_request("GET", "/aiops/incidents")
    if response and response.status_code == 200:
        data = response.json()
        
        if data['incident_count'] == 0:
            print("\n⚠️  No incidents detected yet.")
            print("   Try running the analysis manually:")
            print("   POST http://localhost:5000/aiops/analyze")
            return
        
        print(f"\n🚨 Found {data['incident_count']} active incident(s):\n")
        
        for incident in data['active_incidents']:
            print(f"  Incident ID: {incident['id']}")
            print(f"  Severity: {incident['severity'].upper()}")
            print(f"  Title: {incident['title']}")
            print(f"  Status: {incident['status']}")
            print(f"\n  Root Cause:")
            print(f"    Endpoint: {incident['root_cause']['endpoint']}")
            print(f"    Description: {incident['root_cause']['description']}")
            print(f"    Confidence: {incident['root_cause']['confidence']*100:.0f}%")
            print(f"\n  Affected Endpoints: {', '.join(incident['affected_endpoints'])}")
            print(f"  Anomalies Detected: {len(incident['anomalies'])}")
            
            if incident.get('trace_correlation'):
                print(f"  Traces Analyzed: {incident['trace_correlation']['total_traces']}")
            
            print(f"  First Detected: {incident['first_detected']}")
            print("\n" + "-" * 70 + "\n")


def clear_simulations():
    """Clear all failure simulations."""
    print_section("7. Cleaning Up")
    
    response = make_request("POST", "/simulate/clear")
    if response and response.status_code == 200:
        print("✅ All simulations cleared")


def manual_analysis():
    """Trigger manual analysis (useful for quick testing)."""
    print_section("Manual Analysis (Quick Test)")
    print("Triggering immediate analysis...")
    
    response = make_request("POST", "/aiops/analyze")
    if response and response.status_code == 200:
        data = response.json()
        print(f"\n✅ Analysis completed:")
        print(f"   Anomalies detected: {data['analysis']['anomalies_detected']}")
        print(f"   Incidents created: {data['incidents_created']}")


def run_full_demo():
    """Run complete demonstration."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 20 + "AIOPS MVP DEMONSTRATION" + " " * 25 + "║")
    print("╚" + "=" * 68 + "╝")
    
    try:
        # Check if server is running
        response = make_request("GET", "/health")
        if not response:
            print("\n❌ Server not responding. Please start the server first:")
            print("   python app.py")
            return
        
        # Run demo sequence
        test_normal_traffic()
        view_metrics()
        simulate_latency_spike()
        simulate_error_spike()
        wait_for_analysis()
        view_incidents()
        clear_simulations()
        
        print_section("Demo Complete!")
        print("\n💡 Next Steps:")
        print("  1. View metrics: GET http://localhost:5000/aiops/metrics")
        print("  2. View incidents: GET http://localhost:5000/aiops/incidents")
        print("  3. Try more simulations:")
        print("     POST http://localhost:5000/simulate/delay?endpoint=/payment&duration=3000")
        print("     POST http://localhost:5000/simulate/error?endpoint=/checkout&rate=0.9")
        print("\n")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        clear_simulations()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "quick":
            # Quick test without waiting
            print("\n🚀 Quick Test Mode\n")
            test_normal_traffic()
            simulate_latency_spike()
            simulate_error_spike()
            manual_analysis()
            view_incidents()
            clear_simulations()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python test_aiops.py [quick]")
    else:
        # Full demo with proper timing
        run_full_demo()
