# AIOps Architecture & Implementation Guide

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Flask Application                        │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   /health    │  │  /checkout   │  │  /payment    │          │
│  │  /inventory  │  │              │  │              │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                   │
│         └──────────────────┴──────────────────┘                  │
│                            │                                      │
│                    ┌───────▼────────┐                           │
│                    │   Telemetry    │                           │
│                    │   Middleware   │                           │
│                    └───────┬────────┘                           │
└────────────────────────────┼──────────────────────────────────┘
                             │
                    ┌────────▼─────────┐
                    │  SQLite Storage  │
                    │  (telemetry.db)  │
                    └────────┬─────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                   │
    ┌─────▼─────┐    ┌──────▼──────┐    ┌──────▼──────┐
    │  Baseline │    │   Anomaly   │    │     RCA     │
    │  Learning │    │  Detection  │    │   Engine    │
    └───────────┘    └──────┬──────┘    └──────┬──────┘
                            │                   │
                            └─────────┬─────────┘
                                      │
                              ┌───────▼────────┐
                              │   Incidents    │
                              │  (In-Memory)   │
                              └────────────────┘
```

## Component Details

### 1. Telemetry Collection Layer

**File**: `telemetry/collector.py`

**Responsibilities**:
- Automatic request instrumentation via Flask middleware
- Generate and propagate `trace_id` for request correlation
- Measure latency with microsecond precision
- Capture exceptions and full stack traces
- Zero-code-change instrumentation

**Key Design Decisions**:
- **Why middleware?** Transparent instrumentation - no need to modify business logic
- **Why trace_id?** Essential for RCA - tracks request flow across services
- **Why before/after hooks?** Captures both successful and failed requests

**Data Flow**:
```
Request arrives → Generate trace_id → Start timer →
Execute handler → Capture result → Calculate latency →
Store in DB → Return response (with trace_id in header)
```

### 2. Storage Layer

**File**: `telemetry/storage.py`

**Responsibilities**:
- Persist telemetry to SQLite
- Indexed queries for time-range and trace-based lookups
- Thread-safe operations
- Aggregate statistics calculation

**Schema**:
```sql
CREATE TABLE telemetry (
    id INTEGER PRIMARY KEY,
    service_name TEXT,
    endpoint TEXT,           -- e.g., '/payment'
    method TEXT,            -- GET, POST, etc.
    status_code INTEGER,    -- HTTP status
    latency_ms REAL,        -- Request duration
    error_message TEXT,     -- Stack trace if failed
    trace_id TEXT,          -- Correlation ID
    timestamp TEXT          -- ISO format
)

INDEX idx_endpoint_time ON (endpoint, timestamp)  -- Fast time-range queries
INDEX idx_trace_id ON (trace_id)                  -- Fast trace lookups
```

**Why SQLite?** Simple, embedded, no dependencies. In production, replace with:
- InfluxDB / TimescaleDB for time-series data
- Elasticsearch for full-text search on errors
- S3 / Data Lake for long-term storage

### 3. AIOps Analysis Engine

**File**: `aiops/analyzer.py`

**Responsibilities**:
- Learn baseline latency automatically (no manual thresholds)
- Detect latency anomalies
- Detect error spikes
- Detect timeouts/silence
- Continuous adaptation to changing patterns

**Algorithms**:

#### Baseline Learning (EWMA)
```python
# Exponential Weighted Moving Average
new_baseline = (0.9 * old_baseline) + (0.1 * current_value)
```

**Why EWMA?**
- Adapts to gradual changes (e.g., increased traffic)
- Gives more weight to recent data
- Resistant to outliers
- No need to store historical data

#### Latency Anomaly Detection
```python
if current_latency > (baseline * 3):
    alert("Latency anomaly")
```

**Why 3x multiplier?**
- 2x could be normal variance
- 3x indicates clear degradation
- Configurable per SLA requirements

#### Error Spike Detection
```python
error_rate = 5xx_count / total_requests
if error_rate > 0.2 and total_requests >= 5:
    alert("Error spike")
```

**Why percentage?**
- Absolute counts are meaningless without context
- 5 errors in 10 requests = critical
- 5 errors in 10,000 requests = normal

**Why minimum sample size?**
- Avoid false positives on low traffic
- 1 error in 1 request = 100% but not significant

### 4. Root Cause Analysis Engine

**File**: `aiops/rca.py`

**Responsibilities**:
- Correlate anomalies using trace_id
- Identify root cause in request chains
- Deduplicate related alerts
- Create unified incidents

**RCA Algorithm**:

```
Step 1: Group anomalies by time window (5 min)
  - Anomalies detected close together are likely related

Step 2: Extract all trace_ids from anomalies
  - Get trace_ids from each anomaly's affected requests

Step 3: For each trace, reconstruct request flow
  - Query DB for all requests with same trace_id
  - Sort chronologically

Step 4: Identify first failure in each trace
  - Find earliest request that failed/degraded
  - This is the root cause candidate

Step 5: Aggregate across traces
  - Count which endpoint failed first most often
  - Endpoint with highest frequency = root cause

Step 6: Create incident
  - Root cause: Identified endpoint
  - Affected: All endpoints in traces
  - Confidence: Frequency / Total traces
```

**Example**:
```
Trace ABC-123:
  1. [10:00:00] /checkout → 200 OK
  2. [10:00:01] /payment → 500 Error  ← FIRST FAILURE
  3. [10:00:02] /inventory → 200 OK
  4. [10:00:03] /checkout → 500 Error (due to payment)

Trace DEF-456:
  1. [10:00:05] /checkout → 200 OK
  2. [10:00:06] /payment → 500 Error  ← FIRST FAILURE
  3. [10:00:07] /checkout → 500 Error

Root Cause: /payment (failed first in 2/2 traces)
Affected: /payment, /checkout
Confidence: 100%
```

### 5. Failure Injection (Testing)

**File**: `simulation/failure_injector.py`

**Responsibilities**:
- Inject artificial delays
- Inject random errors
- Enable/disable per endpoint
- Chaos engineering testing

**Why needed?**
- Validate AIOps detection works
- Test RCA correlation logic
- Demonstrate without breaking real services

## Data Flow Examples

### Normal Request Flow

```
1. Request: POST /checkout
2. Middleware: Generate trace_id = "abc-123"
3. Handler calls: POST /payment (with trace_id = "abc-123")
4. Payment succeeds (latency = 150ms)
5. Handler calls: GET /inventory (with trace_id = "abc-123")
6. Inventory succeeds (latency = 50ms)
7. Checkout completes (total latency = 250ms)
8. Telemetry stored:
   - /payment: trace_id=abc-123, latency=150ms, status=200
   - /inventory: trace_id=abc-123, latency=50ms, status=200
   - /checkout: trace_id=abc-123, latency=250ms, status=200
```

### Failure Detection Flow

```
1. Background worker wakes up (every 30s)
2. Analyzer: Learn baselines
   - /payment baseline = 180ms (from last hour of data)
3. Analyzer: Check recent requests (last 5 min)
   - /payment average = 1250ms
4. Anomaly detected: 1250ms > (180ms * 3)
5. RCA: Find trace_ids in anomaly window
6. RCA: Reconstruct traces, identify /payment as root
7. Incident created:
   - ID: INC-123456-1
   - Root: /payment
   - Affected: /payment, /checkout
   - Severity: high
```

## Configuration Tuning

### Sensitivity Adjustments

**For stricter detection** (fewer false positives):
```python
# In aiops/analyzer.py
self.LATENCY_MULTIPLIER = 5.0  # Only alert if 5x slower
self.ERROR_RATE_THRESHOLD = 0.3  # Only alert if >30% errors
self.MIN_SAMPLES_FOR_BASELINE = 20  # Need more data
```

**For faster detection** (catch smaller issues):
```python
self.LATENCY_MULTIPLIER = 2.0  # Alert if 2x slower
self.ERROR_RATE_THRESHOLD = 0.1  # Alert if >10% errors
self.MIN_SAMPLES_FOR_BASELINE = 5  # Need less data
```

### Timing Adjustments

```python
# In aiops/analyzer.py
self.ANALYSIS_WINDOW_MINUTES = 10  # Look back 10 min (catch gradual issues)
self.BASELINE_WINDOW_MINUTES = 120  # Learn from 2 hours (more stable)

# In aiops/rca.py
self.CORRELATION_WINDOW_MINUTES = 2  # Tighter correlation (less grouping)
self.INCIDENT_TTL_MINUTES = 60  # Keep incidents longer

# In app.py (background worker)
time.sleep(10)  # Run analysis every 10 seconds (faster detection)
```

## Production Deployment Considerations

### 1. Replace SQLite with Time-Series DB
```python
# Use InfluxDB
from influxdb_client import InfluxDBClient

# Or Prometheus
from prometheus_client import Histogram
latency = Histogram('request_latency', 'Request latency')
```

### 2. Use Distributed Tracing
```python
# OpenTelemetry
from opentelemetry import trace
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("payment"):
    # Automatic context propagation
```

### 3. Background Workers with Celery
```python
# celery_app.py
@celery.task
def run_aiops_analysis():
    analyzer.run_analysis()

# Beat schedule
beat_schedule = {
    'aiops-analysis': {
        'task': 'run_aiops_analysis',
        'schedule': 30.0  # Every 30 seconds
    }
}
```

### 4. Alert Integration
```python
# In rca.py, after creating incident
def send_alerts(incident):
    # PagerDuty
    pagerduty.trigger_incident(incident)
    
    # Slack
    slack.post_message(f"🚨 {incident['title']}")
    
    # Email
    send_email(to=on_call, incident=incident)
```

### 5. Distributed Storage
```python
# Use Redis for incidents (shared across replicas)
import redis
r = redis.Redis()

def store_incident(incident):
    r.setex(
        f"incident:{incident['id']}",
        ttl=3600,
        value=json.dumps(incident)
    )
```

## Testing Scenarios

### Scenario 1: Single Endpoint Latency
```bash
# Simulate
curl -X POST "http://localhost:5000/simulate/delay?endpoint=/payment&duration=3000"

# Generate traffic
for i in {1..10}; do curl -X POST http://localhost:5000/payment; done

# Expected: Latency anomaly on /payment
```

### Scenario 2: Cascading Failure
```bash
# Break root service
curl -X POST "http://localhost:5000/simulate/error?endpoint=/payment&rate=1.0"

# Call dependent service
curl -X POST http://localhost:5000/checkout

# Expected: 
# - Error spike on /payment
# - Error on /checkout
# - RCA identifies /payment as root cause
```

### Scenario 3: Gradual Degradation
```bash
# Add increasing delays
curl -X POST "http://localhost:5000/simulate/delay?endpoint=/inventory&duration=500"
# Generate traffic, then increase
curl -X POST "http://localhost:5000/simulate/delay?endpoint=/inventory&duration=1500"

# Expected: Baseline adjusts, then alerts when exceeds 3x
```

## Key Metrics to Monitor

1. **Baseline Accuracy**: How stable are learned baselines?
2. **False Positive Rate**: Alerts that aren't real issues
3. **False Negative Rate**: Missed issues
4. **Time to Detection**: How long to identify issue?
5. **RCA Accuracy**: Is root cause correct?

## Limitations & Future Enhancements

### Current Limitations
- In-memory incident storage (lost on restart)
- Single-instance only (no distributed coordination)
- Simple statistical detection (no ML models)
- No anomaly type learning (e.g., periodic patterns)

### Enhancements
1. **Machine Learning**: LSTM for time-series prediction
2. **Seasonality**: Detect daily/weekly patterns
3. **Dependency Mapping**: Auto-discover service dependencies
4. **Incident Prediction**: Predict failures before they occur
5. **Auto-Remediation**: Trigger healing actions automatically
6. **Multi-Service**: Monitor multiple services simultaneously
7. **Custom Metrics**: Support business metrics (conversion rate, etc.)

## License
MIT
