# Technology Stack - Comprehensive Guide

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0.0-000000?style=for-the-badge&logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7.2-DC382D?style=for-the-badge&logo=redis&logoColor=white)

## Overview

This document provides a comprehensive overview of all technologies used and planned for the AIOps platform, including version numbers, purposes, and integration patterns.

---

## Current Technology Stack (MVP)

### Backend Framework

#### Flask 3.0.0
![Flask](https://img.shields.io/badge/Flask-3.0.0-000000?logo=flask&logoColor=white)

**Purpose**: Lightweight WSGI web application framework  
**Use Cases**:
- REST API endpoints for AIOps operations
- Middleware for automatic request instrumentation
- Service endpoint simulation (checkout, payment, inventory)

**Key Features Used**:
- Request/response hooks for telemetry collection
- Blueprint support for modular API design (planned)
- Built-in development server
- JSON serialization support

**Why Flask?**
- Lightweight and minimal - perfect for microservices
- Easy middleware implementation for instrumentation
- Extensive ecosystem and community support
- Simple deployment options

#### Python 3.8+
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)

**Purpose**: Core programming language  
**Version Requirement**: 3.8 or higher for:
- Assignment expressions (walrus operator `:=`)
- Positional-only parameters
- F-string debugging (`f"{var=}"`)
- `functools.cached_property`

**Key Libraries Used**:
- `threading` - Background analysis thread
- `datetime` - Timestamp handling and time calculations
- `json` - Data serialization
- `uuid` - Trace ID generation
- `sqlite3` - Database operations

#### Werkzeug 3.0.1
![Werkzeug](https://img.shields.io/badge/Werkzeug-3.0.1-000000?logo=python&logoColor=white)

**Purpose**: WSGI utility library  
**Use Cases**:
- Development server (Flask's built-in server)
- URL routing and request parsing
- HTTP header handling
- Exception handling and debugging

### Data Storage

#### SQLite 3
![SQLite](https://img.shields.io/badge/SQLite-3.0-003B57?logo=sqlite&logoColor=white)

**Purpose**: Embedded relational database  
**Use Cases**:
- Telemetry data storage (requests, latency, errors)
- Time-series data for historical analysis
- Indexed queries by endpoint and trace ID

**Schema**:
```sql
CREATE TABLE telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    latency_ms REAL NOT NULL,
    error_message TEXT,
    trace_id TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE INDEX idx_endpoint_time ON telemetry(endpoint, timestamp);
CREATE INDEX idx_trace_id ON telemetry(trace_id);
```

**Why SQLite?**
- Zero configuration - no separate database server needed
- Embedded - runs in same process as application
- Perfect for MVP and development
- Easy migration path to PostgreSQL

**Limitations (Addressed in Production)**:
- Single writer - no concurrent writes
- Not suitable for distributed systems
- Limited scalability
- No advanced time-series features

#### In-Memory Storage

**Purpose**: Incident and baseline storage  
**Implementation**: Python dictionaries  
**Limitations**:
- Data lost on restart
- No persistence
- No scalability
- To be replaced with Redis + PostgreSQL

### HTTP Client

#### Requests 2.31.0
![Requests](https://img.shields.io/badge/Requests-2.31.0-3776AB?logo=python&logoColor=white)

**Purpose**: HTTP library for Python  
**Use Cases**:
- Internal service-to-service communication
- Simulating checkout → payment calls
- Trace ID propagation via headers

**Why Requests?**
- Simple, intuitive API
- Automatic connection pooling
- Session management
- Industry standard

---

## Planned Production Stack

### Database Layer

#### PostgreSQL 16
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192?logo=postgresql&logoColor=white)

**Purpose**: Primary production database  
**Release**: September 2023  
**Use Cases**:
- Incidents and incident history
- User accounts and authentication
- Configuration and settings
- Service metadata and relationships

**Key Features**:
- **ACID Compliance**: Reliable transactions
- **Advanced Indexing**: GiST, GIN, BRIN indexes
- **JSON Support**: Native JSONB type for flexible schemas
- **Full-Text Search**: Built-in FTS with multiple languages
- **Partitioning**: Native table partitioning for scalability
- **Replication**: Streaming replication for high availability

**Configuration**:
```yaml
# postgresql.conf
max_connections = 200
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1  # For SSD
effective_io_concurrency = 200
work_mem = 20MB
min_wal_size = 2GB
max_wal_size = 8GB
```

**Extensions**:
- `pg_stat_statements` - Query performance monitoring
- `pg_trgm` - Fuzzy string matching for search
- `uuid-ossp` - UUID generation
- `btree_gin`, `btree_gist` - Additional index types

#### TimescaleDB 2.13
![TimescaleDB](https://img.shields.io/badge/TimescaleDB-2.13-FDB515?logo=timescale&logoColor=white)

**Purpose**: PostgreSQL extension for time-series data  
**Release**: November 2023  
**Use Cases**:
- High-volume telemetry data storage
- Metrics time-series (latency, throughput, errors)
- Historical trend analysis
- Automatic data retention and compression

**Key Features**:
- **Hypertables**: Automatic partitioning by time
- **Compression**: 90%+ storage reduction for old data
- **Continuous Aggregates**: Pre-computed rollups (materialized views)
- **Data Retention**: Automatic old data deletion
- **Time-Bucket Functions**: Efficient time-window queries

**Example Schema**:
```sql
CREATE TABLE telemetry (
    time TIMESTAMPTZ NOT NULL,
    service_name TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    latency_ms REAL NOT NULL,
    status_code INTEGER NOT NULL,
    trace_id TEXT,
    error_message TEXT
);

-- Convert to hypertable (time-series optimized)
SELECT create_hypertable('telemetry', 'time');

-- Create continuous aggregate (5-minute rollups)
CREATE MATERIALIZED VIEW telemetry_5min
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('5 minutes', time) AS bucket,
    service_name,
    endpoint,
    AVG(latency_ms) as avg_latency,
    MAX(latency_ms) as max_latency,
    COUNT(*) as request_count,
    SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) as error_count
FROM telemetry
GROUP BY bucket, service_name, endpoint;

-- Add compression policy (compress data older than 7 days)
SELECT add_compression_policy('telemetry', INTERVAL '7 days');

-- Add retention policy (delete data older than 90 days)
SELECT add_retention_policy('telemetry', INTERVAL '90 days');
```

**Performance Benefits**:
- 10-100x faster queries compared to vanilla PostgreSQL
- 90%+ compression ratio for historical data
- Automatic data lifecycle management
- Optimized for time-range queries

#### Redis 7.2
![Redis](https://img.shields.io/badge/Redis-7.2-DC382D?logo=redis&logoColor=white)

**Purpose**: In-memory data store  
**Release**: October 2023  
**Use Cases**:
1. **Caching**: Frequently accessed baselines and metrics
2. **Session Management**: User sessions and API tokens
3. **Pub/Sub**: Real-time incident notifications
4. **Rate Limiting**: API throttling using token bucket algorithm
5. **Leaderboards**: Top failing endpoints, error rankings
6. **Real-Time Metrics**: Current incident count, active alerts

**Key Features**:
- **Multiple Data Structures**: Strings, hashes, lists, sets, sorted sets
- **Persistence**: RDB snapshots + AOF (Append-Only File)
- **Pub/Sub**: Real-time messaging between services
- **Lua Scripting**: Atomic complex operations
- **Redis Cluster**: Horizontal scalability
- **Redis Sentinel**: Automatic failover

**Data Structure Usage**:
```python
# Baseline caching
redis.hset("baselines", "/payment", 180.5)  # Hash
baseline = redis.hget("baselines", "/payment")

# Incident counter
redis.incr("incidents:count:today")  # Counter

# Real-time metrics (sorted set - leaderboard)
redis.zadd("endpoints:errors", {"/payment": 42, "/checkout": 15})
top_failing = redis.zrevrange("endpoints:errors", 0, 9)  # Top 10

# Pub/Sub notifications
redis.publish("incidents:new", json.dumps(incident_data))

# Rate limiting (token bucket)
redis.incr(f"ratelimit:{user_id}:{window}")
redis.expire(f"ratelimit:{user_id}:{window}", 60)  # 60 second window
```

**Configuration**:
```conf
# redis.conf
maxmemory 4gb
maxmemory-policy allkeys-lru  # Evict least recently used keys
appendonly yes  # Enable AOF persistence
appendfsync everysec  # AOF sync every second
save 900 1  # RDB snapshot after 900 sec if 1 key changed
save 300 10
save 60 10000
```

### Message Queue & Processing

#### RabbitMQ 3.12
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-3.12-FF6600?logo=rabbitmq&logoColor=white)

**Purpose**: Message broker for asynchronous processing  
**Release**: June 2023  
**Protocol**: AMQP 0.9.1  

**Use Cases**:
- Decoupling telemetry collection from storage
- Buffering traffic spikes
- Distributing work across Celery workers
- Ensuring message delivery with acknowledgments

**Queue Architecture**:
```
Exchanges:
├── telemetry.exchange (topic)
│   ├── telemetry.high_priority → Queue: telemetry_high_priority
│   ├── telemetry.normal → Queue: telemetry_normal
│   └── telemetry.low → Queue: telemetry_low
│
├── analysis.exchange (direct)
│   └── analysis.job → Queue: analysis_jobs
│
└── dlx.exchange (dead letter exchange)
    └── failed.* → Queue: dlq_failed_messages

Queues:
├── telemetry_high_priority (Priority: 10, Max: 10000 msgs)
├── telemetry_normal (Priority: 5, Lazy mode)
├── analysis_jobs (Durable, TTL: 1 hour)
└── dlq_failed_messages (No expiry, manual processing)
```

**Features Used**:
- **Priority Queues**: Critical telemetry processed first
- **Lazy Queues**: Store messages on disk for high throughput
- **Dead Letter Queues**: Handle failed messages
- **Message TTL**: Expire old unprocessed messages
- **Quorum Queues**: Replicated queues for durability

#### Celery 5.3
![Celery](https://img.shields.io/badge/Celery-5.3-37814A?logo=celery&logoColor=white)

**Purpose**: Distributed task queue  
**Release**: September 2023  
**Broker**: RabbitMQ  
**Backend**: Redis  

**Worker Pools**:
```python
# Ingestion workers (high throughput)
celery -A aiops.celery worker \
    --queues=telemetry_high_priority,telemetry_normal \
    --concurrency=10 \
    --prefetch-multiplier=4

# Analysis workers (CPU intensive)
celery -A aiops.celery worker \
    --queues=analysis_jobs \
    --concurrency=4 \
    --pool=threads

# Notification workers (I/O bound)
celery -A aiops.celery worker \
    --queues=notifications \
    --concurrency=20 \
    --pool=gevent
```

**Task Examples**:
```python
@celery.task(bind=True, max_retries=3)
def process_telemetry(self, telemetry_data):
    """Process and store telemetry data"""
    try:
        storage.insert_telemetry(telemetry_data)
    except Exception as exc:
        self.retry(exc=exc, countdown=60)  # Retry after 60s

@celery.task
def run_anomaly_detection():
    """Scheduled task - runs every 30 seconds"""
    anomalies = analyzer.detect_anomalies()
    if anomalies:
        create_incident.delay(anomalies)

@celery.task(rate_limit='100/m')  # Max 100 per minute
def send_notification(incident_id, channel):
    """Send incident notification"""
    incident = get_incident(incident_id)
    notifier.send(channel, incident)
```

**Monitoring**: Flower (Celery monitoring tool)
- Web UI: http://localhost:5555
- Real-time task monitoring
- Worker statistics
- Task history and retries

### Observability Stack

#### Prometheus 2.48
![Prometheus](https://img.shields.io/badge/Prometheus-2.48-E6522C?logo=prometheus&logoColor=white)

**Purpose**: Metrics collection and time-series database  
**Release**: November 2023  
**Architecture**: Pull-based scraping  

**Metrics Collected**:
```yaml
# Application metrics
- http_requests_total{endpoint="/payment", status="200"}
- http_request_duration_seconds{endpoint="/payment", quantile="0.95"}
- aiops_incidents_active{severity="high"}
- aiops_anomalies_detected_total{type="latency"}

# System metrics
- node_cpu_seconds_total
- node_memory_bytes
- node_disk_io_time_seconds_total

# Database metrics
- postgresql_connections{state="active"}
- postgresql_queries_total{query_type="select"}
- redis_memory_used_bytes
```

**Configuration**:
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'aiops-api'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'

  - job_name: 'postgresql'
    static_configs:
      - targets: ['localhost:9187']  # postgres_exporter

  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']  # redis_exporter
```

#### Grafana 10.2
![Grafana](https://img.shields.io/badge/Grafana-10.2-F46800?logo=grafana&logoColor=white)

**Purpose**: Visualization and dashboarding  
**Release**: October 2023  

**Dashboard Examples**:

**1. AIOps Overview Dashboard**
- Active incidents count (stat panel)
- Incidents over time (time series)
- Incident severity distribution (pie chart)
- Top failing endpoints (bar chart)
- MTTD and MTTR trends (time series)

**2. Service Health Dashboard**
- Request rate per endpoint (time series)
- Error rate per endpoint (time series)
- P50, P95, P99 latency (time series)
- Status code distribution (bar chart)
- Endpoint uptime (stat panels)

**3. System Resources Dashboard**
- CPU usage per pod (time series)
- Memory usage per pod (time series)
- Database connection pool (gauge)
- Queue depth (time series)
- Disk I/O (time series)

**Alerting Rules**:
```yaml
# grafana_alerts.yml
- name: AIOps Alerts
  rules:
    - alert: HighIncidentRate
      expr: increase(aiops_incidents_active[5m]) > 10
      for: 5m
      annotations:
        summary: "High incident creation rate detected"
        
    - alert: APILatencyHigh
      expr: http_request_duration_seconds{quantile="0.95"} > 2
      for: 10m
      annotations:
        summary: "API P95 latency above 2 seconds"
```

#### Jaeger 1.52
![Jaeger](https://img.shields.io/badge/Jaeger-1.52-66CFE3?logo=jaeger&logoColor=white)

**Purpose**: Distributed tracing  
**Release**: December 2023  
**Architecture**: OpenTelemetry compatible  

**Components**:
- **Jaeger Agent**: Collects traces from services
- **Jaeger Collector**: Processes and stores traces
- **Jaeger Query**: API and UI for trace visualization
- **Storage**: Cassandra or Elasticsearch backend

**Trace Visualization**:
```
Request: POST /checkout [trace_id: abc-123-def]
├── Span: checkout_handler (200ms)
│   ├── Span: call_payment (150ms)
│   │   ├── Span: payment_validation (50ms)
│   │   └── Span: payment_processing (100ms) [ERROR: timeout]
│   └── Span: call_inventory (40ms)
│       └── Span: inventory_check (35ms)
└── Span: response_serialization (10ms)
```

**Integration**:
```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

tracer = trace.get_tracer(__name__)

@app.route('/payment', methods=['POST'])
def payment():
    with tracer.start_as_current_span("payment_handler") as span:
        span.set_attribute("payment.amount", amount)
        result = process_payment()
        span.set_attribute("payment.success", result.success)
        return result
```

#### OpenTelemetry 1.21
![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-1.21-000000?logo=opentelemetry&logoColor=white)

**Purpose**: Unified observability framework  
**Release**: November 2023  
**Standard**: CNCF project (graduated)  

**Signals**:
1. **Traces**: Distributed request tracking
2. **Metrics**: Performance measurements
3. **Logs**: Application and system logs

**Advantages**:
- Vendor-neutral standard
- Single SDK for all observability
- Automatic instrumentation for Flask
- Supports multiple exporters (Jaeger, Prometheus, etc.)

**Implementation**:
```python
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Automatic Flask instrumentation
FlaskInstrumentor().instrument_app(app)

# Automatic requests library instrumentation
RequestsInstrumentor().instrument()
```

### Machine Learning Stack

#### scikit-learn 1.3
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3-F7931E?logo=scikit-learn&logoColor=white)

**Purpose**: Machine learning algorithms  
**Release**: June 2023  

**Algorithms Used**:

**1. Isolation Forest** (Anomaly Detection)
```python
from sklearn.ensemble import IsolationForest

# Train on normal behavior
model = IsolationForest(contamination=0.05, random_state=42)
model.fit(normal_data)  # latency, error_rate, request_count

# Detect anomalies
predictions = model.predict(current_data)
# -1 = anomaly, 1 = normal
```

**2. DBSCAN** (Clustering)
```python
from sklearn.cluster import DBSCAN

# Cluster related incidents
clustering = DBSCAN(eps=0.5, min_samples=5)
clusters = clustering.fit_predict(incident_features)
```

**3. Random Forest** (Severity Classification)
```python
from sklearn.ensemble import RandomForestClassifier

# Predict incident severity
model = RandomForestClassifier()
model.fit(X_train, y_train)  # Features: latency, error_rate, impact
severity = model.predict(incident_features)  # Low, Medium, High, Critical
```

#### TensorFlow 2.15
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.15-FF6F00?logo=tensorflow&logoColor=white)

**Purpose**: Deep learning framework  
**Release**: November 2023  

**Use Cases**:

**1. LSTM Networks** (Time-Series Forecasting)
```python
import tensorflow as tf

model = tf.keras.Sequential([
    tf.keras.layers.LSTM(128, return_sequences=True, input_shape=(window_size, features)),
    tf.keras.layers.LSTM(64),
    tf.keras.layers.Dense(32, activation='relu'),
    tf.keras.layers.Dense(1)  # Predict future latency
])

# Predict next hour's latency
future_latency = model.predict(recent_telemetry)
```

**2. Autoencoders** (Anomaly Detection)
```python
# Encoder-Decoder architecture
encoder = tf.keras.Sequential([...])
decoder = tf.keras.Sequential([...])

# Train on normal data
autoencoder.fit(normal_telemetry)

# Detect anomalies by reconstruction error
reconstruction = autoencoder.predict(current_telemetry)
error = np.mean(np.abs(current_telemetry - reconstruction))
is_anomaly = error > threshold
```

#### NumPy 1.26 & Pandas 2.1
![NumPy](https://img.shields.io/badge/NumPy-1.26-013243?logo=numpy&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.1-150458?logo=pandas&logoColor=white)

**Purpose**: Numerical computing and data analysis  

**NumPy**: Fast array operations
```python
import numpy as np

# Statistical analysis
latencies = np.array([180, 185, 190, 500, 195])
mean = np.mean(latencies)
std = np.std(latencies)
z_scores = (latencies - mean) / std
anomalies = np.abs(z_scores) > 3  # 3 standard deviations
```

**Pandas**: Time-series manipulation
```python
import pandas as pd

# Load telemetry into DataFrame
df = pd.DataFrame(telemetry_data)
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Resample to 5-minute windows
df_5min = df.set_index('timestamp').resample('5T').agg({
    'latency_ms': ['mean', 'max', 'std'],
    'status_code': 'count'
})

# Rolling window statistics
df['rolling_avg'] = df['latency_ms'].rolling(window=20).mean()
```

### Containerization & Orchestration

#### Docker 24.0
![Docker](https://img.shields.io/badge/Docker-24.0-2496ED?logo=docker&logoColor=white)

**Purpose**: Application containerization  
**Release**: May 2023  

**Dockerfiles**:

**API Container**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

**Docker Compose**:
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "5000:5000"
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/aiops
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  postgres:
    image: timescale/timescaledb:2.13-pg16
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: aiops
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass

  redis:
    image: redis:7.2-alpine
    command: redis-server --appendonly yes
    volumes:
      - redisdata:/data

  celery-worker:
    build: .
    command: celery -A aiops.celery worker -l info
    depends_on:
      - postgres
      - redis
      - rabbitmq

  rabbitmq:
    image: rabbitmq:3.12-management-alpine
    ports:
      - "15672:15672"  # Management UI

volumes:
  pgdata:
  redisdata:
```

#### Kubernetes 1.28
![Kubernetes](https://img.shields.io/badge/Kubernetes-1.28-326CE5?logo=kubernetes&logoColor=white)

**Purpose**: Container orchestration  
**Release**: August 2023  

**Deployment Examples**:

**API Deployment**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aiops-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: aiops-api
  template:
    metadata:
      labels:
        app: aiops-api
    spec:
      containers:
      - name: api
        image: aiops-api:latest
        ports:
        - containerPort: 5000
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 2Gi
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: aiops-secrets
              key: database-url
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5
```

**Horizontal Pod Autoscaler**:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: aiops-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: aiops-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### API & Documentation

#### OpenAPI 3.1 / Swagger
![Swagger](https://img.shields.io/badge/Swagger-5.0-85EA2D?logo=swagger&logoColor=black)
![OpenAPI](https://img.shields.io/badge/OpenAPI-3.1-6BA539?logo=openapi-initiative&logoColor=white)

**Purpose**: API documentation and specification  

**Specification Example**:
```yaml
openapi: 3.1.0
info:
  title: AIOps Platform API
  version: 1.0.0
  description: Intelligent incident detection and root cause analysis

servers:
  - url: https://api.aiops.example.com/v1

paths:
  /aiops/incidents:
    get:
      summary: List all incidents
      parameters:
        - name: severity
          in: query
          schema:
            type: string
            enum: [low, medium, high, critical]
      responses:
        '200':
          description: List of incidents
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Incident'

components:
  schemas:
    Incident:
      type: object
      properties:
        id:
          type: string
        severity:
          type: string
        title:
          type: string
        root_cause:
          type: object
```

**UI**: Swagger UI at `/api/docs`

### Testing & Quality

#### pytest 7.4
![pytest](https://img.shields.io/badge/pytest-7.4-0A9EDC?logo=pytest&logoColor=white)

**Purpose**: Testing framework  
**Release**: June 2023  

**Test Structure**:
```python
# test_anomaly_detection.py
import pytest
from aiops.analyzer import AnomalyDetector

@pytest.fixture
def detector():
    return AnomalyDetector()

def test_latency_anomaly_detection(detector):
    baseline = 180
    current = 600
    assert detector.is_latency_anomaly(current, baseline) == True

def test_error_spike_detection(detector):
    errors = 15
    total = 20
    assert detector.is_error_spike(errors, total) == True

@pytest.mark.integration
def test_end_to_end_detection(client):
    # Inject failure
    client.post('/simulate/error?endpoint=/payment&rate=1.0')
    
    # Generate traffic
    for _ in range(10):
        client.post('/checkout')
    
    # Wait for analysis
    time.sleep(35)
    
    # Verify incident created
    response = client.get('/aiops/incidents')
    assert len(response.json['active_incidents']) > 0
```

**Coverage**: pytest-cov for code coverage analysis

### CI/CD

#### GitHub Actions
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?logo=github-actions&logoColor=white)

**Purpose**: Continuous integration and deployment  

**Workflow Example**:
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests
        run: pytest --cov=aiops tests/
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Build Docker image
        run: docker build -t aiops-api:${{ github.sha }} .
      
      - name: Push to registry
        run: docker push aiops-api:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to Kubernetes
        run: kubectl apply -f k8s/
```

---

## Technology Comparison Matrix

### Database Selection

| Feature | SQLite (Current) | PostgreSQL | TimescaleDB | Redis |
|---------|------------------|------------|-------------|-------|
| **Use Case** | Development | Relational data | Time-series | Cache/Pub-Sub |
| **Performance** | Low | High | Very High (TS) | Extremely High |
| **Scalability** | Single node | Vertical | Horizontal | Horizontal |
| **Persistence** | File | ACID | ACID | Optional |
| **Query Language** | SQL | SQL | SQL | Key-Value |
| **Best For** | MVP | Incidents | Telemetry | Real-time |

### Message Queue Comparison

| Feature | RabbitMQ | Apache Kafka | Redis Pub/Sub |
|---------|----------|--------------|---------------|
| **Protocol** | AMQP | Custom | RESP |
| **Ordering** | Per-queue | Per-partition | No guarantee |
| **Persistence** | Optional | Always | Optional |
| **Performance** | 20K msg/s | 1M+ msg/s | 1M+ msg/s |
| **Use Case** | Task queue | Event streaming | Notifications |
| **Why RabbitMQ?** | Task delivery guarantees, priority queues, mature Celery integration |

---

## Version Management

### Dependency Pinning Strategy

**requirements.txt** (Exact versions for reproducibility):
```
Flask==3.0.0
Werkzeug==3.0.1
requests==2.31.0
```

**requirements-prod.txt** (Production additions):
```
-r requirements.txt
psycopg2-binary==2.9.9  # PostgreSQL adapter
redis==5.0.1
celery==5.3.4
prometheus-client==0.19.0
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
```

**requirements-dev.txt** (Development tools):
```
-r requirements.txt
pytest==7.4.3
pytest-cov==4.1.0
black==23.12.0  # Code formatter
pylint==3.0.3  # Linter
mypy==1.7.1  # Type checker
```

### Upgrade Strategy

1. **Monitor releases**: GitHub watch, mailing lists
2. **Test in staging**: Full test suite on new versions
3. **Gradual rollout**: Canary deployment (10% → 50% → 100%)
4. **Rollback plan**: Keep previous version ready
5. **Document changes**: Update CHANGELOG.md

---

## License Compliance

| Technology | License | Commercial Use | Attribution Required |
|------------|---------|----------------|---------------------|
| Flask | BSD-3-Clause | Yes | No |
| Python | PSF License | Yes | No |
| PostgreSQL | PostgreSQL License | Yes | No |
| Redis | BSD-3-Clause | Yes | No |
| RabbitMQ | MPL 2.0 | Yes | No |
| Celery | BSD-3-Clause | Yes | No |
| scikit-learn | BSD-3-Clause | Yes | No |
| TensorFlow | Apache 2.0 | Yes | No |
| Docker | Apache 2.0 | Yes | No |
| Kubernetes | Apache 2.0 | Yes | No |

**Conclusion**: All technologies use permissive licenses allowing commercial use without restrictions.

---

## Contact & Support

For questions about technology choices or implementation:
- Architecture discussions: architecture@example.com
- Technical support: support@example.com
- Security concerns: security@example.com
