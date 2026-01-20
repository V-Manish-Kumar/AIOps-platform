# AIOps MVP - Automatic Incident Detection & Root Cause Analysis

## Overview
This is a Flask-based AIOps prototype that **automatically** detects API failures, latency anomalies, and error spikes using telemetry data. It performs root cause analysis by correlating issues across endpoints.

## Key Features

### 🤖 Automatic Detection (No Manual Configuration)
- **Baseline Learning**: Learns normal latency per endpoint using moving averages
- **Anomaly Detection**: Detects latency spikes >3x baseline
- **Error Spike Detection**: Identifies unusual 5xx error rates
- **Timeout Detection**: Flags endpoints with no responses

### 🔍 Root Cause Analysis (RCA)
- **Trace Correlation**: Links requests across endpoints using `trace_id`
- **Dependency Analysis**: Identifies which endpoint failure caused downstream issues
- **Incident Deduplication**: Groups related anomalies into single incidents

### 📊 Telemetry Collection
- Automatic request instrumentation (middleware)
- Captures: latency, status codes, errors, stack traces
- SQLite storage with structured schema

## Project Structure

```
AIops/
├── app.py                          # Main Flask application
├── telemetry/
│   ├── collector.py                # Middleware & request instrumentation
│   └── storage.py                  # SQLite telemetry storage
├── aiops/
│   ├── analyzer.py                 # Anomaly detection engine
│   └── rca.py                      # Root cause analysis logic
├── simulation/
│   └── failure_injector.py         # Simulate failures for testing
├── requirements.txt
└── README.md
```

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

The server starts on `http://localhost:5000`

## API Endpoints

### Monitored Service Endpoints
- `GET /health` - Health check endpoint
- `POST /checkout` - Checkout process (calls payment & inventory)
- `POST /payment` - Payment processing
- `GET /inventory` - Inventory check

### AIOps Endpoints
- `GET /aiops/incidents` - View current detected incidents
- `GET /aiops/metrics` - View latency & error statistics per endpoint

### Simulation Controls
- `POST /simulate/delay?endpoint=payment&duration=2000` - Add artificial delay (ms)
- `POST /simulate/error?endpoint=inventory&rate=0.5` - Inject errors (rate: 0-1)
- `POST /simulate/clear` - Clear all simulations

## How It Works

### 1. Telemetry Collection
Every request is automatically instrumented via Flask middleware:
- Generates unique `trace_id` for request correlation
- Measures request duration
- Captures exceptions and stack traces
- Stores all data in SQLite

### 2. Baseline Learning
The analyzer continuously learns normal behavior:
- Calculates **moving average** latency per endpoint
- Updates baseline with each new request (exponential weighted average)
- No manual thresholds needed

### 3. Anomaly Detection
Runs every 30 seconds to detect:
- **Latency Anomalies**: Current latency > 3x baseline
- **Error Spikes**: 5xx error rate > 20% (with min 5 requests)
- **Timeout Issues**: Endpoints with no recent responses

### 4. Root Cause Analysis
When anomalies are detected:
- Groups anomalies within 5-minute windows
- Uses `trace_id` to correlate related failures
- Identifies the **root endpoint** (earliest failure in trace)
- Creates single incident with correlated anomalies
- Suppresses duplicate alerts

## Example Usage

### Test Normal Operations
```bash
# Call checkout (internally calls payment & inventory)
curl -X POST http://localhost:5000/checkout

# Check metrics
curl http://localhost:5000/aiops/metrics
```

### Simulate Failure Scenarios

#### Scenario 1: Payment Latency Issue
```bash
# Add 3-second delay to payment endpoint
curl -X POST "http://localhost:5000/simulate/delay?endpoint=payment&duration=3000"

# Trigger checkout (will detect payment latency anomaly)
curl -X POST http://localhost:5000/checkout

# Wait 30 seconds for analysis, then check incidents
curl http://localhost:5000/aiops/incidents
```

#### Scenario 2: Inventory Errors
```bash
# Make inventory fail 80% of the time
curl -X POST "http://localhost:5000/simulate/error?endpoint=inventory&rate=0.8"

# Trigger multiple checkouts
for i in {1..10}; do curl -X POST http://localhost:5000/checkout; done

# Check incidents (should show inventory error spike + RCA)
curl http://localhost:5000/aiops/incidents
```

#### Scenario 3: Cascading Failure
```bash
# Break payment (causes checkout to fail)
curl -X POST "http://localhost:5000/simulate/error?endpoint=payment&rate=1.0"

# Trigger checkout
curl -X POST http://localhost:5000/checkout

# AIOps will identify payment as root cause
curl http://localhost:5000/aiops/incidents
```

## Expected Output

### Metrics Response
```json
{
  "metrics": {
    "checkout": {
      "avg_latency_ms": 245.3,
      "baseline_latency_ms": 230.5,
      "error_rate": 0.02,
      "request_count": 150,
      "status_distribution": {
        "200": 147,
        "500": 3
      }
    }
  }
}
```

### Incidents Response
```json
{
  "active_incidents": [
    {
      "id": "INC-1737404800-1",
      "severity": "high",
      "title": "Multiple anomalies detected",
      "root_cause": {
        "endpoint": "payment",
        "issue": "Latency spike: 1250ms (baseline: 180ms)"
      },
      "affected_endpoints": ["payment", "checkout"],
      "first_detected": "2026-01-20T10:30:15",
      "trace_correlation": {
        "trace_id": "abc-123-def",
        "correlated_failures": ["payment_latency", "checkout_timeout"]
      }
    }
  ]
}
```

## AIOps Logic Explained

### Why This is AIOps (Not Just Monitoring)

1. **Self-Learning**: No manual threshold configuration
2. **Automatic Correlation**: Links failures across services
3. **Root Cause Inference**: Identifies which failure caused others
4. **Context-Aware**: Uses trace_id to understand request flow
5. **Alert Suppression**: One incident for related issues

### Detection Algorithms

**Latency Anomaly**:
```
if current_latency > (baseline * 3):
    anomaly = True
```

**Error Spike**:
```
if (5xx_count / total_requests) > 0.2 AND total_requests >= 5:
    anomaly = True
```

**Baseline Update** (Exponential Weighted Average):
```
new_baseline = (0.9 * old_baseline) + (0.1 * current_latency)
```

### RCA Process
1. Collect all anomalies in time window (5 min)
2. Group by `trace_id`
3. Find earliest failure in each trace (root cause)
4. Aggregate into single incident
5. Identify affected downstream endpoints

## Production Considerations

This is an MVP. For production:
- Replace SQLite with proper time-series DB (Prometheus, InfluxDB)
- Add distributed tracing (OpenTelemetry, Jaeger)
- Implement more sophisticated ML models
- Add alerting integrations (PagerDuty, Slack)
- Use background workers for analysis (Celery)
- Add authentication & authorization
- Implement incident acknowledgment & resolution workflow

## License
MIT
