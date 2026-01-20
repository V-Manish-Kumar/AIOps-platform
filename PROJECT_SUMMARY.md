# 🚀 AIOps MVP - Project Summary

## Project Structure

```
AIops/
├── app.py                          # Main Flask application (300+ lines)
├── requirements.txt                # Python dependencies
├── setup.bat                       # Windows setup script
├── test_aiops.py                   # Automated test suite
├── README.md                       # User documentation
├── ARCHITECTURE.md                 # Technical deep-dive
│
├── telemetry/                      # Telemetry Collection Module
│   ├── __init__.py
│   ├── collector.py                # Middleware & instrumentation
│   └── storage.py                  # SQLite persistence
│
├── aiops/                          # AIOps Analysis Module
│   ├── __init__.py
│   ├── analyzer.py                 # Anomaly detection engine
│   └── rca.py                      # Root cause analysis
│
└── simulation/                     # Failure Injection Module
    ├── __init__.py
    └── failure_injector.py         # Chaos engineering tools
```

## What Makes This AIOps (Not Just Monitoring)

### ❌ Traditional Monitoring
- Manual threshold configuration
- Alert fatigue (noise)
- No correlation between events
- Reactive - alerts after failure
- Requires domain expertise to configure

### ✅ AIOps MVP
- **Self-Learning**: Learns baselines automatically from data
- **Intelligent Correlation**: Links failures across endpoints using trace_id
- **Root Cause Analysis**: Identifies which failure caused others
- **Auto-Discovery**: No need to declare endpoints or dependencies
- **Alert Deduplication**: One incident for related issues
- **Continuous Adaptation**: Baselines adjust to changing patterns

## Key Capabilities Demonstrated

### 1. Automatic Baseline Learning
```python
# No manual configuration needed!
# System learns: "/payment normally takes 180ms"
# Automatically detects when it takes 600ms
```

**How it works**:
- Collects historical latency data
- Calculates exponential weighted moving average
- Adapts to gradual changes (e.g., increased traffic)
- Alerts on sudden deviations (>3x baseline)

### 2. Trace-Based Root Cause Analysis
```python
# Scenario: Checkout fails due to payment error
# 
# Trace ID: abc-123
#   1. /checkout → calls /payment (with same trace_id)
#   2. /payment → FAILS (500 error)
#   3. /checkout → FAILS (cascading failure)
#
# RCA Logic:
# - Both failures share trace_id
# - Payment failed FIRST (timestamp)
# - Conclusion: Payment is root cause
# - Affected: Payment + Checkout
```

### 3. Multi-Dimensional Anomaly Detection

**Latency Anomalies**:
- Compares current vs. baseline
- Accounts for variance
- Severity based on deviation

**Error Spikes**:
- Tracks 5xx error rate
- Percentage-based (not absolute counts)
- Includes sample error messages

**Timeout Detection**:
- Identifies endpoints that stopped responding
- Distinguishes from low-traffic endpoints
- Critical for detecting hanging services

### 4. Intelligent Incident Management

**Correlation Window**:
- Groups anomalies within 5-minute window
- Assumes temporal proximity = related issues

**Deduplication**:
- Multiple anomalies → Single incident
- Prevents alert storm

**Severity Calculation**:
- Based on anomaly types
- Critical: Error rate >50%
- High: Error rate >20% or latency >5x
- Medium: Other anomalies

## Technical Highlights

### Telemetry Collection
- **Zero-code instrumentation**: Flask middleware automatically captures all requests
- **Trace propagation**: trace_id flows through entire request chain
- **Exception handling**: Full stack traces captured automatically
- **Thread-safe**: SQLite with locking for concurrent requests

### Storage Design
- **Indexed queries**: Fast lookups by endpoint, time, trace_id
- **Time-range queries**: Efficient recent data retrieval
- **Schema design**: Optimized for time-series analysis
- **Minimal dependencies**: Just Python stdlib + Flask

### Analysis Engine
- **EWMA algorithm**: Exponential weighted moving average for baseline
- **Statistical detection**: 3-sigma-style deviation detection
- **Configurable sensitivity**: Tune false positive vs. false negative rate
- **Background processing**: Non-blocking analysis in separate thread

### RCA Algorithm
- **Graph traversal**: Reconstructs request flow from traces
- **Temporal analysis**: Identifies first failure in sequence
- **Confidence scoring**: Frequency of root cause across traces
- **Incident lifecycle**: Active → Acknowledged → Resolved

## API Reference

### Business Endpoints (Monitored)
- `GET /health` - Health check
- `GET /inventory` - Inventory availability
- `POST /payment` - Payment processing
- `POST /checkout` - Order checkout (calls payment + inventory)

### AIOps Endpoints
- `GET /aiops/metrics` - Current metrics & health scores
- `GET /aiops/incidents` - Active incidents with RCA
- `GET /aiops/incidents/<id>` - Incident details
- `POST /aiops/incidents/<id>/resolve` - Resolve incident
- `POST /aiops/analyze` - Trigger manual analysis

### Simulation Endpoints
- `POST /simulate/delay?endpoint=X&duration=Y` - Add latency (ms)
- `POST /simulate/error?endpoint=X&rate=Y` - Inject errors (0-1)
- `POST /simulate/clear` - Clear all simulations
- `GET /simulate/status` - View active simulations

## Quick Start

### 1. Setup
```bash
# Windows
setup.bat

# Or manually
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run Server
```bash
python app.py
```

Output:
```
======================================================================
AIOps MVP - Automatic Failure Detection & Root Cause Analysis
======================================================================

📊 Starting AIOps background analysis...
✅ Background worker started

🌐 Starting Flask server...
Available endpoints:
  Business endpoints:
    GET  /health
    GET  /inventory
    POST /payment
    POST /checkout

  AIOps endpoints:
    GET  /aiops/metrics    - View endpoint metrics
    GET  /aiops/incidents  - View active incidents
    POST /aiops/analyze    - Trigger manual analysis

  Simulation endpoints:
    POST /simulate/delay   - Add latency
    POST /simulate/error   - Inject errors
    POST /simulate/clear   - Clear simulations
    GET  /simulate/status  - View config

======================================================================
🚀 Server running on http://localhost:5000
======================================================================
```

### 3. Run Tests
```bash
# Full demo (takes ~2 minutes)
python test_aiops.py

# Quick test (no waiting)
python test_aiops.py quick
```

### 4. Manual Testing
```bash
# Generate normal traffic
curl http://localhost:5000/health
curl http://localhost:5000/inventory
curl -X POST http://localhost:5000/payment

# Simulate payment slowdown
curl -X POST "http://localhost:5000/simulate/delay?endpoint=/payment&duration=2000"

# Trigger affected requests
curl -X POST http://localhost:5000/checkout

# Wait 30 seconds for analysis, then check incidents
curl http://localhost:5000/aiops/incidents
```

## Example Output

### Metrics Response
```json
{
  "timestamp": 1737404800,
  "metrics": {
    "/payment": {
      "request_count": 150,
      "avg_latency_ms": 245.3,
      "error_rate": 0.02,
      "baseline_latency_ms": 230.5,
      "status_distribution": {
        "200": 147,
        "500": 3
      },
      "health": {
        "health_score": 95.2,
        "status": "healthy"
      }
    }
  }
}
```

### Incident Response (With RCA)
```json
{
  "incident_count": 1,
  "active_incidents": [
    {
      "id": "INC-1737404800-1",
      "severity": "high",
      "status": "active",
      "title": "Latency spike detected in /payment",
      "root_cause": {
        "endpoint": "/payment",
        "confidence": 1.0,
        "description": "Latency spike: 1250ms (baseline: 180ms, 6.9x slower)"
      },
      "affected_endpoints": ["/payment", "/checkout"],
      "anomalies": [
        {
          "type": "latency_anomaly",
          "endpoint": "/payment",
          "severity": "high",
          "baseline_ms": 180.0,
          "current_ms": 1250.0,
          "deviation": 6.94
        }
      ],
      "trace_correlation": {
        "total_traces": 8,
        "sample_traces": [
          {
            "trace_id": "abc-123-def",
            "root_endpoint": "/payment",
            "root_status": 500,
            "affected_chain": ["/checkout", "/payment", "/inventory"]
          }
        ]
      },
      "first_detected": "2026-01-20T10:30:15.123456"
    }
  ]
}
```

## Test Scenarios

### Scenario 1: Latency Spike
```bash
# Add 3-second delay to payment
curl -X POST "http://localhost:5000/simulate/delay?endpoint=/payment&duration=3000"

# Trigger requests
for i in {1..10}; do curl -X POST http://localhost:5000/checkout; sleep 1; done

# Check incidents (after 30s)
curl http://localhost:5000/aiops/incidents

# Expected: Latency anomaly on /payment
```

### Scenario 2: Error Spike
```bash
# Make inventory fail 80% of time
curl -X POST "http://localhost:5000/simulate/error?endpoint=/inventory&rate=0.8"

# Trigger requests
for i in {1..20}; do curl http://localhost:5000/inventory; sleep 0.5; done

# Expected: Error spike on /inventory with sample error messages
```

### Scenario 3: Cascading Failure (RCA Demo)
```bash
# Break payment completely
curl -X POST "http://localhost:5000/simulate/error?endpoint=/payment&rate=1.0"

# Call checkout (depends on payment)
for i in {1..10}; do curl -X POST http://localhost:5000/checkout; sleep 1; done

# Check incidents
curl http://localhost:5000/aiops/incidents

# Expected: 
# - Root cause: /payment
# - Affected: /payment, /checkout
# - RCA identifies payment as source
```

## Code Statistics

- **Total Files**: 13
- **Total Lines**: ~1,800
- **Python Modules**: 7
- **Core Logic**:
  - Telemetry: ~400 lines
  - AIOps Analysis: ~500 lines
  - RCA: ~400 lines
  - Main App: ~300 lines
  - Simulation: ~150 lines

## What This Demonstrates

### For AIOps
✅ Self-learning (baseline calculation)
✅ Anomaly detection (latency + errors)
✅ Root cause analysis (trace correlation)
✅ Incident correlation & deduplication
✅ Auto-discovery (no manual config)
✅ Continuous adaptation

### For Software Engineering
✅ Clean architecture (separation of concerns)
✅ Type hints for clarity
✅ Extensive comments explaining "why"
✅ Thread-safe operations
✅ Error handling
✅ Testing utilities
✅ Production-ready patterns

### For Operations
✅ Zero-config monitoring
✅ Automatic instrumentation
✅ Clear incident attribution
✅ Actionable alerts
✅ Chaos engineering tools
✅ Health scoring

## Next Steps / Production Readiness

### Immediate Improvements
1. **Persistent incident storage** (Redis/PostgreSQL)
2. **Alert integrations** (PagerDuty, Slack, Email)
3. **Authentication & authorization**
4. **Rate limiting on AIOps endpoints**
5. **Grafana dashboards** for visualization

### Scalability
1. **Replace SQLite** → InfluxDB/TimescaleDB
2. **Distributed tracing** → OpenTelemetry/Jaeger
3. **Background workers** → Celery with Redis
4. **Load balancer** → Multiple Flask instances
5. **Horizontal scaling** → Kubernetes deployment

### Advanced Features
1. **Machine learning models** (LSTM for time-series)
2. **Seasonality detection** (daily/weekly patterns)
3. **Dependency mapping** (service mesh integration)
4. **Predictive analytics** (predict failures before they occur)
5. **Auto-remediation** (trigger healing actions)
6. **Multi-service monitoring** (distributed systems)

## Why This Is MVP-Quality

### ✅ Production Patterns
- Middleware-based instrumentation
- Background worker architecture
- Indexed database queries
- Thread-safe operations
- Error handling & recovery

### ✅ Real AIOps Concepts
- Baseline learning (not static thresholds)
- Trace correlation (not just logs)
- Root cause inference (not just alerting)
- Incident management (not just detection)

### ✅ Extensible Design
- Modular architecture
- Clear interfaces between components
- Configurable parameters
- Easy to add new detectors
- Plugin-ready simulation

### ❌ Not Production (Yet)
- Single-instance only
- In-memory state
- No authentication
- Simple statistical models
- Limited scalability

**But**: Demonstrates all core AIOps concepts with production-quality code structure.

## License
MIT - Free to use, modify, extend

---

**Built with**: Python 3.8+, Flask 3.0, SQLite  
**Author**: Senior Platform Engineer  
**Purpose**: Educational MVP for AIOps concepts  
**Status**: ✅ Complete & Functional
