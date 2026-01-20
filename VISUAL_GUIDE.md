# 📊 AIOps MVP - Visual Overview

## 🎯 What Problem Does This Solve?

### Traditional Monitoring Problems:
```
❌ Static thresholds break when traffic changes
❌ Alert fatigue - 100s of alerts for one root issue
❌ Manual correlation - "Which failure caused what?"
❌ Reactive - Only know after users complain
❌ Configuration hell - Each service needs manual setup
```

### AIOps Solution:
```
✅ Self-learning baselines - Adapts automatically
✅ One incident - All related anomalies grouped
✅ Root cause identified - "Payment caused checkout to fail"
✅ Proactive - Detects before major impact
✅ Zero configuration - Auto-discovers everything
```

## 🔄 How It Works (Visual Flow)

### Step 1: Data Collection (Automatic)
```
┌──────────────────────────────────────────────────────────┐
│                    Incoming Request                       │
│                  POST /checkout                           │
└─────────────────────┬────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Telemetry Middleware                        │
│  • Generate trace_id = "abc-123"                        │
│  • Start timer                                          │
│  • Execute request handler                              │
│  • Measure latency = 245ms                             │
│  • Capture status = 200                                │
│  • Store to database                                   │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                    SQLite Database                       │
│  ┌────────────────────────────────────────────────┐   │
│  │ trace_id │ endpoint  │ latency │ status │ time │   │
│  ├──────────┼───────────┼─────────┼────────┼──────┤   │
│  │ abc-123  │ /checkout │ 245ms   │ 200    │ 10:00│   │
│  │ abc-123  │ /payment  │ 180ms   │ 200    │ 10:00│   │
│  │ abc-123  │ /inventory│ 50ms    │ 200    │ 10:00│   │
│  └────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### Step 2: Baseline Learning (Every 30 seconds)
```
┌─────────────────────────────────────────────────────────┐
│              Baseline Learning Algorithm                 │
│                                                          │
│  For each endpoint:                                     │
│    1. Get last hour of successful requests (200-299)   │
│    2. Calculate average latency                        │
│    3. Update baseline with EWMA:                       │
│                                                          │
│       new_baseline = (0.9 × old) + (0.1 × new)        │
│                                                          │
│  Example:                                               │
│    /payment:  180ms (learned from 150 requests)        │
│    /checkout: 250ms (learned from 150 requests)        │
│    /inventory: 50ms (learned from 150 requests)        │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
            ┌──────────────────┐
            │ Baseline Storage │
            ├──────────────────┤
            │ /payment: 180ms  │
            │ /checkout: 250ms │
            │ /inventory: 50ms │
            └──────────────────┘
```

### Step 3: Anomaly Detection
```
┌─────────────────────────────────────────────────────────┐
│             Anomaly Detection Engine                     │
│                                                          │
│  Latency Check:                                         │
│    Current /payment avg (last 5 min) = 1200ms          │
│    Baseline /payment = 180ms                            │
│    1200ms > (180ms × 3) ? → YES! 🚨 ANOMALY            │
│                                                          │
│  Error Check:                                           │
│    /inventory errors = 12 out of 15 requests            │
│    Error rate = 80%                                     │
│    80% > 20% threshold? → YES! 🚨 ANOMALY              │
│                                                          │
│  Output:                                                │
│    [                                                    │
│      {                                                  │
│        type: "latency_anomaly",                        │
│        endpoint: "/payment",                           │
│        current: 1200ms,                                │
│        baseline: 180ms,                                │
│        trace_ids: ["abc-123", "def-456", ...]         │
│      },                                                │
│      {                                                  │
│        type: "error_spike",                            │
│        endpoint: "/inventory",                         │
│        error_rate: 0.8,                                │
│        trace_ids: ["ghi-789", ...]                    │
│      }                                                 │
│    ]                                                   │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
                  Anomalies Found!
```

### Step 4: Root Cause Analysis
```
┌─────────────────────────────────────────────────────────┐
│              Root Cause Analysis Engine                  │
│                                                          │
│  Step 1: Get trace_ids from anomalies                   │
│    → ["abc-123", "def-456", "ghi-789"]                 │
│                                                          │
│  Step 2: Reconstruct each trace chronologically         │
│                                                          │
│    Trace abc-123:                                       │
│      10:00:00.100 - /checkout starts                   │
│      10:00:00.150 - /payment called → 500 ERROR ❌     │
│      10:00:00.200 - /inventory called → 200 OK         │
│      10:00:00.250 - /checkout fails → 500 ERROR        │
│                                                          │
│    Trace def-456:                                       │
│      10:00:05.100 - /checkout starts                   │
│      10:00:05.150 - /payment called → 500 ERROR ❌     │
│      10:00:05.200 - /checkout fails → 500 ERROR        │
│                                                          │
│  Step 3: Find first failure in each trace              │
│    Trace abc-123: /payment failed first                │
│    Trace def-456: /payment failed first                │
│                                                          │
│  Step 4: Aggregate results                             │
│    /payment failed first in 2 out of 2 traces          │
│    Confidence = 100%                                    │
│                                                          │
│  Conclusion:                                            │
│    Root Cause: /payment                                │
│    Affected: /payment, /checkout                       │
│    Impact: Cascading failure                           │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   Incident Created                       │
│                                                          │
│  ID: INC-1737404800-1                                   │
│  Severity: HIGH                                         │
│  Title: "Error spike detected in /payment"             │
│                                                          │
│  Root Cause:                                            │
│    Endpoint: /payment                                   │
│    Issue: 80% error rate (12 failures)                 │
│    Confidence: 100%                                     │
│                                                          │
│  Affected Services:                                     │
│    • /payment (direct)                                  │
│    • /checkout (cascading)                             │
│                                                          │
│  Trace Correlation:                                     │
│    2 traces analyzed                                    │
│    All traces show /payment as first failure           │
└─────────────────────────────────────────────────────────┘
```

## 🔍 Key Algorithms Explained

### EWMA Baseline Learning
```
Problem: Traffic patterns change (morning vs evening, weekdays vs weekends)
Solution: Exponential Weighted Moving Average

Algorithm:
┌─────────────────────────────────────────────────┐
│ new_baseline = (α × old_baseline) + (β × new)  │
│ where α = 0.9, β = 0.1                         │
└─────────────────────────────────────────────────┘

Example:
  Day 1: /payment avg = 180ms → baseline = 180ms
  Day 2: /payment avg = 200ms → baseline = 182ms  (0.9×180 + 0.1×200)
  Day 3: /payment avg = 190ms → baseline = 183ms  (0.9×182 + 0.1×190)
  
  Gradual increase = baseline adapts ✅
  Sudden spike to 1000ms = anomaly detected 🚨
```

### Latency Anomaly Detection
```
Rule: current_latency > (baseline × multiplier)

Examples:
  Baseline = 180ms, Multiplier = 3

  ✅ 200ms → Normal (1.1x baseline)
  ✅ 350ms → Acceptable (1.9x baseline)
  ⚠️ 600ms → ANOMALY (3.3x baseline) 🚨
  🚨 1200ms → CRITICAL (6.7x baseline) 🚨🚨
```

### Error Rate Detection
```
Rule: (5xx_count / total_requests) > threshold

Examples:
  Threshold = 20%, Min samples = 5

  ✅ 1 error in 100 requests = 1% → Normal
  ✅ 2 errors in 15 requests = 13% → Acceptable
  🚨 5 errors in 15 requests = 33% → ANOMALY 🚨
  🚨 10 errors in 12 requests = 83% → CRITICAL 🚨🚨
  
  ❌ 1 error in 2 requests = 50% but sample too small → Ignored
```

### RCA Trace Correlation
```
Given: Multiple anomalies detected

Step 1: Group by time
  All anomalies within 5-minute window are related

Step 2: Extract trace_ids
  Get all traces that experienced these anomalies

Step 3: Reconstruct request flow
  Trace abc-123:
    1. [10:00:00] /checkout
    2. [10:00:01] /payment → FAIL ❌
    3. [10:00:02] /inventory
    4. [10:00:03] /checkout → FAIL

Step 4: Find first failure
  /payment failed at 10:00:01 (earliest in trace)

Step 5: Aggregate
  Count first failures across all traces:
    /payment: 15 times
    /inventory: 2 times
  
  Root cause = /payment (highest frequency)
```

## 📈 Real-World Scenario

### Scenario: Payment Gateway Timeout

```
Timeline:
─────────────────────────────────────────────────────────

10:00:00 │ System normal, all endpoints healthy
         │ /payment baseline = 180ms

10:15:30 │ Payment gateway starts timing out (external issue)
         │

10:15:45 │ 🔴 Requests start failing:
         │   • /payment: 3000ms latency (15x slower!)
         │   • /checkout: Also slow (waiting for payment)
         │   • Error rate: 40%
         │

10:16:00 │ 🤖 AIOps Analysis Runs:
         │   ✓ Detects latency anomaly on /payment
         │   ✓ Detects error spike on /payment
         │   ✓ Detects /checkout also affected
         │

10:16:05 │ 🧠 RCA Analysis:
         │   ✓ Traces show /payment fails first
         │   ✓ /checkout failures are cascading
         │   ✓ Root cause: /payment (confidence: 95%)
         │

10:16:10 │ 🚨 INCIDENT CREATED:
         │   ID: INC-123
         │   Title: "Payment gateway timeout"
         │   Severity: CRITICAL
         │   Root: /payment
         │   Affected: /payment, /checkout
         │   
         │   → Alert sent to on-call engineer
         │   → One incident (not 50 separate alerts)
         │

10:20:00 │ Engineer fixes payment gateway
         │

10:30:00 │ ✅ System returns to normal
         │ New baseline learned: 185ms
         │ Incident auto-resolved
```

## 🎨 Data Visualization

### Latency Over Time
```
Latency (ms)
  1200 │                    ╱╲ ← Anomaly detected
       │                   ╱  ╲
  1000 │                  ╱    ╲
       │                 ╱      ╲
   800 │                ╱        ╲
       │               ╱          ╲___
   600 │              ╱               ╲
       │             ╱                 ╲
   400 │────────────╱                   ╲────────
       │ ← Baseline (180ms × 3 = 540ms threshold)
   200 │▓▓▓▓▓▓▓▓▓▓▓                      ▓▓▓▓▓▓▓
       │ ← Normal operations
     0 └───────────────────────────────────────→ Time
       10:00    10:15    10:16    10:20    10:30
```

### Error Rate Over Time
```
Error %
   100 │                 ██
       │                 ██
    80 │              ██████ ← Spike detected
       │              ██████
    60 │           ████████
       │           ████████
    40 │        ████████████
       │     ████████████████
    20 │──── ──────────────────── ← Threshold
       │ ▓
     0 └───────────────────────────────────────→ Time
```

## 🧪 Testing Matrix

| Test Case | Simulation | Expected Detection | RCA Result |
|-----------|------------|-------------------|------------|
| **Latency Spike** | `/payment` +2000ms | ✅ Latency anomaly | Root: `/payment` |
| **Error Storm** | `/inventory` 80% fail | ✅ Error spike | Root: `/inventory` |
| **Cascading Failure** | `/payment` 100% fail | ✅ 2 anomalies | Root: `/payment` Affected: `/checkout` |
| **Gradual Degradation** | `/payment` +500ms incremental | ⚠️ No alert (baseline adapts) | - |
| **Timeout** | `/payment` no response | ✅ Timeout detection | Root: `/payment` |
| **Multiple Services** | All endpoints +1000ms | ✅ Multiple anomalies | Separate incidents |

## 📊 Metrics Dashboard (Conceptual)

```
╔════════════════════════════════════════════════════════════╗
║                    AIOps Dashboard                          ║
╠════════════════════════════════════════════════════════════╣
║                                                             ║
║  Active Incidents: 2                          🔴 CRITICAL  ║
║                                                             ║
║  ┌─────────────────────────────────────────────────────┐  ║
║  │ INC-001: Payment Error Spike                        │  ║
║  │ Severity: HIGH | Root: /payment                     │  ║
║  │ Detected: 2 min ago | Affected: 2 endpoints         │  ║
║  └─────────────────────────────────────────────────────┘  ║
║                                                             ║
║  ┌─────────────────────────────────────────────────────┐  ║
║  │ INC-002: Inventory Latency Spike                    │  ║
║  │ Severity: MEDIUM | Root: /inventory                 │  ║
║  │ Detected: 5 min ago | Affected: 1 endpoint          │  ║
║  └─────────────────────────────────────────────────────┘  ║
║                                                             ║
╠════════════════════════════════════════════════════════════╣
║                    Endpoint Health                          ║
╠════════════════════════════════════════════════════════════╣
║                                                             ║
║  /payment      [████████░░] 80%  ⚠️  245ms (baseline 180) ║
║  /checkout     [██████████] 95%  ✅  260ms (baseline 250) ║
║  /inventory    [████░░░░░░] 40%  🔴  850ms (baseline 50)  ║
║  /health       [██████████] 100% ✅  15ms  (baseline 12)  ║
║                                                             ║
╚════════════════════════════════════════════════════════════╝
```

## 🚀 Quick Command Reference

```bash
# Start server
python app.py

# Generate normal traffic
curl http://localhost:5000/health

# Simulate latency issue
curl -X POST "http://localhost:5000/simulate/delay?endpoint=/payment&duration=2000"

# Simulate error spike
curl -X POST "http://localhost:5000/simulate/error?endpoint=/inventory&rate=0.8"

# View metrics
curl http://localhost:5000/aiops/metrics | jq

# View incidents
curl http://localhost:5000/aiops/incidents | jq

# Trigger manual analysis
curl -X POST http://localhost:5000/aiops/analyze | jq

# Clear simulations
curl -X POST http://localhost:5000/simulate/clear

# Run automated tests
python test_aiops.py
```

## 🎓 Learning Path

1. **Start Here**: Read [README.md](README.md) for quick start
2. **Run Demo**: Execute `python test_aiops.py` to see it in action
3. **Understand Code**: Review [app.py](app.py) main application flow
4. **Deep Dive**: Study [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
5. **Explore Modules**:
   - `telemetry/collector.py` - How requests are captured
   - `aiops/analyzer.py` - How anomalies are detected
   - `aiops/rca.py` - How root causes are identified
6. **Experiment**: Try different simulation scenarios

## ✅ Checklist for Production

- [ ] Replace SQLite with InfluxDB/Prometheus
- [ ] Add authentication (OAuth2/JWT)
- [ ] Implement alert integrations (PagerDuty, Slack)
- [ ] Use Celery for background processing
- [ ] Add Grafana dashboards
- [ ] Implement incident acknowledgment workflow
- [ ] Add ML models for prediction
- [ ] Set up distributed tracing (Jaeger)
- [ ] Configure load balancing
- [ ] Add rate limiting
- [ ] Implement audit logging
- [ ] Set up monitoring for the monitor (meta-monitoring)

---

**Status**: ✅ MVP Complete & Fully Functional  
**Lines of Code**: ~1,800  
**Test Coverage**: Integration tests included  
**Documentation**: Complete  
**License**: MIT
