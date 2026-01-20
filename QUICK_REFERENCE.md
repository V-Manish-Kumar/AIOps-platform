# AIOps MVP - Quick Reference Card

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0.0-000000?logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Planned-316192?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-Planned-DC382D?logo=redis&logoColor=white)

## Installation (30 seconds)

### Windows
```bash
cd AIops
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### Linux/Mac
```bash
cd AIops
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Using setup.bat (Windows Only)
```bash
setup.bat
```

## Technology Stack at a Glance

### Current Stack
- **Backend**: Flask 3.0.0 + Python 3.8+
- **Storage**: SQLite 3 (embedded database)
- **HTTP**: Requests 2.31.0

### Planned Stack
- **Databases**: PostgreSQL 16 + TimescaleDB 2.13 + Redis 7.2
- **Queue**: RabbitMQ 3.12 + Celery 5.3
- **Monitoring**: Prometheus + Grafana + Jaeger + OpenTelemetry
- **ML**: scikit-learn + TensorFlow + NumPy + Pandas
- **Container**: Docker 24 + Kubernetes 1.28
- **API Docs**: OpenAPI 3.1 + Swagger

## Core Concepts

### What is AIOps?
**Traditional Monitoring**: Manual thresholds, alert storms, no correlation, reactive  
**AIOps**: Self-learning, intelligent correlation, root cause analysis, proactive

### Key Features
- Auto-learns baselines - No manual configuration required
- Detects anomalies - Latency spikes, error storms, timeouts
- Finds root causes - Trace-based correlation across services
- Groups alerts - One incident instead of 50+ alerts
- Adapts continuously - Baselines adjust to traffic patterns

## API Quick Reference

### Monitor Endpoints (Auto-instrumented)
```bash
GET  /health          # Health check
GET  /inventory       # Check inventory
POST /payment         # Process payment
POST /checkout        # Complete order (calls payment + inventory)
```

### AIOps Endpoints
```bash
GET  /aiops/metrics              # View all endpoint metrics
GET  /aiops/incidents            # View active incidents
GET  /aiops/incidents/<id>       # Get incident details
POST /aiops/incidents/<id>/resolve  # Resolve incident
POST /aiops/analyze              # Trigger immediate analysis
```

### Simulation Endpoints
```bash
# Add 2-second delay to payment
POST /simulate/delay?endpoint=/payment&duration=2000

# Make inventory fail 80% of time
POST /simulate/error?endpoint=/inventory&rate=0.8

# Clear all simulations
POST /simulate/clear

# View active simulations
GET /simulate/status
```

## Test Scenarios

### Scenario 1: Latency Spike (30 seconds)
```bash
# Simulate
curl -X POST "http://localhost:5000/simulate/delay?endpoint=/payment&duration=3000"

# Generate traffic
for i in {1..10}; do curl -X POST http://localhost:5000/checkout; sleep 1; done

# View incident (wait 30s for analysis)
curl http://localhost:5000/aiops/incidents | jq
```

### Scenario 2: Error Storm (30 seconds)
```bash
# Simulate
curl -X POST "http://localhost:5000/simulate/error?endpoint=/inventory&rate=0.8"

# Generate traffic
for i in {1..20}; do curl http://localhost:5000/inventory; sleep 0.5; done

# View incident
curl http://localhost:5000/aiops/incidents | jq
```

### Scenario 3: Cascading Failure (RCA Demo)
```bash
# Break payment
curl -X POST "http://localhost:5000/simulate/error?endpoint=/payment&rate=1.0"

# Trigger checkout (depends on payment)
for i in {1..10}; do curl -X POST http://localhost:5000/checkout; sleep 1; done

# View RCA (should identify /payment as root cause)
curl http://localhost:5000/aiops/incidents | jq '.active_incidents[0].root_cause'
```

## Automated Testing
```bash
# Full demo (2 minutes)
python test_aiops.py

# Quick test (no waiting)
python test_aiops.py quick
```

## Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `app.py` | Main Flask app | 300+ |
| `telemetry/collector.py` | Request instrumentation | 150+ |
| `telemetry/storage.py` | SQLite persistence | 250+ |
| `aiops/analyzer.py` | Anomaly detection | 300+ |
| `aiops/rca.py` | Root cause analysis | 300+ |
| `simulation/failure_injector.py` | Chaos testing | 150+ |

## How It Works (Simple)

### 1. Data Collection
Every request → Captured automatically → Stored in DB with trace_id

### 2. Baseline Learning (every 30s)
Analyze last hour → Calculate average → Update baseline

### 3. Anomaly Detection (every 30s)
Current metrics → Compare to baseline → Alert if deviation

### 4. Root Cause Analysis
Group related anomalies → Use trace_id → Find first failure → Create incident

## Configuration Tuning

### More Sensitive (catch smaller issues)
```python
# In aiops/analyzer.py
self.LATENCY_MULTIPLIER = 2.0      # Alert at 2x baseline (default: 3.0)
self.ERROR_RATE_THRESHOLD = 0.1    # Alert at 10% errors (default: 0.2)
```

### Less Sensitive (fewer false positives)
```python
self.LATENCY_MULTIPLIER = 5.0      # Alert at 5x baseline
self.ERROR_RATE_THRESHOLD = 0.3    # Alert at 30% errors
self.MIN_SAMPLES_FOR_BASELINE = 20 # Need more data
```

### Faster Detection
```python
# In app.py
time.sleep(10)  # Run analysis every 10s (default: 30s)

# In aiops/analyzer.py
self.ANALYSIS_WINDOW_MINUTES = 2  # Check last 2 min (default: 5)
```

## Expected Output

### Healthy System
```json
{
  "metrics": {
    "/payment": {
      "avg_latency_ms": 180.5,
      "baseline_latency_ms": 175.2,
      "error_rate": 0.01,
      "health": {
        "status": "healthy",
        "health_score": 98.5
      }
    }
  }
}
```

### Incident Detected
```json
{
  "active_incidents": [{
    "id": "INC-1737404800-1",
    "severity": "high",
    "title": "Latency spike detected in /payment",
    "root_cause": {
      "endpoint": "/payment",
      "description": "Latency spike: 1250ms (baseline: 180ms, 6.9x slower)",
      "confidence": 1.0
    },
    "affected_endpoints": ["/payment", "/checkout"],
    "first_detected": "2026-01-20T10:30:15"
  }]
}
```

## Troubleshooting

### "No incidents detected"
- Wait 30 seconds for background analysis
- Or trigger manually: `POST /aiops/analyze`
- Check baseline learned: `GET /aiops/metrics`

### "Baseline is null"
- Need minimum 10 requests to learn baseline
- Generate traffic first: `for i in {1..20}; do curl http://localhost:5000/health; done`

### "Too many false positives"
- Increase `LATENCY_MULTIPLIER` to 4.0 or 5.0
- Increase `MIN_SAMPLES_FOR_BASELINE` to 20
- Increase `ANALYSIS_WINDOW_MINUTES` to 10

### "Missed a real issue"
- Decrease `LATENCY_MULTIPLIER` to 2.0
- Decrease `ERROR_RATE_THRESHOLD` to 0.1
- Decrease `ANALYSIS_WINDOW_MINUTES` to 2

## Architecture (Simplified)

```
Request → Middleware (telemetry) → Handler → Database
                                              ↓
                            Background Worker (every 30s)
                                              ↓
                              Analyzer (detect anomalies)
                                              ↓
                              RCA Engine (find root cause)
                                              ↓
                              Incidents (accessible via API)
```

## Project Structure
```
AIops/
├── app.py                    # Main application
├── telemetry/               # Data collection
│   ├── collector.py         # Middleware
│   └── storage.py           # Database
├── aiops/                   # Analysis engine
│   ├── analyzer.py          # Anomaly detection
│   └── rca.py              # Root cause analysis
└── simulation/             # Testing tools
    └── failure_injector.py # Chaos engineering
```

## Next Steps

1. ✅ **Run demo**: `python test_aiops.py`
2. ✅ **Experiment**: Try different simulations
3. ✅ **Read code**: Start with `app.py`
4. ✅ **Customize**: Adjust thresholds for your needs
5. ✅ **Extend**: Add new detectors or integrations

## Common Commands

```bash
# Start
python app.py

# Test
python test_aiops.py

# Metrics
curl http://localhost:5000/aiops/metrics | jq

# Incidents
curl http://localhost:5000/aiops/incidents | jq

# Simulate delay
curl -X POST "http://localhost:5000/simulate/delay?endpoint=/payment&duration=2000"

# Simulate errors
curl -X POST "http://localhost:5000/simulate/error?endpoint=/inventory&rate=0.8"

# Clear
curl -X POST http://localhost:5000/simulate/clear
```

## Documentation

- **README.md** - Getting started guide
- **ARCHITECTURE.md** - Technical deep-dive
- **PROJECT_SUMMARY.md** - Complete overview
- **VISUAL_GUIDE.md** - Visual explanations
- **Quick-Reference.md** - This file

## Support

**Issues?** Check:
1. Python 3.8+ installed?
2. Dependencies installed? (`pip install -r requirements.txt`)
3. Port 5000 available?
4. Firewall allowing connections?

**Questions?** Review:
- Comments in code (extensive)
- Architecture documentation
- Example outputs in README

---

**Status**: ✅ Production-ready MVP  
**License**: MIT  
**Author**: Senior Platform Engineer  
**Last Updated**: January 2026
