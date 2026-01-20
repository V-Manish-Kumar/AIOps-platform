"""
Telemetry Storage Module

Handles persistence of telemetry data to SQLite database.
Provides methods for storing and querying request metrics.
"""

import sqlite3
import threading
from datetime import datetime
from typing import List, Dict, Optional


class TelemetryStorage:
    """
    Thread-safe SQLite storage for telemetry data.
    
    Why SQLite: Simple, embedded, no external dependencies.
    In production, replace with time-series DB like InfluxDB or Prometheus.
    """
    
    def __init__(self, db_path: str = "telemetry.db"):
        self.db_path = db_path
        self.lock = threading.Lock()  # Thread-safe operations
        self._init_db()
    
    def _init_db(self):
        """
        Initialize database schema.
        Creates telemetry table with all required fields for AIOps analysis.
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    status_code INTEGER NOT NULL,
                    latency_ms REAL NOT NULL,
                    error_message TEXT,
                    trace_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            
            # Index for fast queries by endpoint and time (critical for AIOps)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_endpoint_time 
                ON telemetry(endpoint, timestamp)
            """)
            
            # Index for trace correlation
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trace_id 
                ON telemetry(trace_id)
            """)
            
            conn.commit()
            conn.close()
    
    def store_metric(self, metric: Dict):
        """
        Store a single telemetry metric.
        
        Args:
            metric: Dictionary containing all telemetry fields
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO telemetry 
                (service_name, endpoint, method, status_code, latency_ms, 
                 error_message, trace_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metric['service_name'],
                metric['endpoint'],
                metric['method'],
                metric['status_code'],
                metric['latency_ms'],
                metric.get('error_message'),
                metric['trace_id'],
                metric['timestamp']
            ))
            
            conn.commit()
            conn.close()
    
    def get_recent_metrics(self, endpoint: Optional[str] = None, 
                          minutes: int = 60) -> List[Dict]:
        """
        Retrieve recent metrics for analysis.
        
        Args:
            endpoint: Filter by specific endpoint (None = all endpoints)
            minutes: How far back to look
            
        Returns:
            List of metric dictionaries
            
        Why: AIOps needs recent data for baseline calculation and anomaly detection.
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return dict-like objects
            cursor = conn.cursor()
            
            # Calculate time threshold
            from datetime import datetime, timedelta
            time_threshold = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
            
            if endpoint:
                cursor.execute("""
                    SELECT * FROM telemetry 
                    WHERE endpoint = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                """, (endpoint, time_threshold))
            else:
                cursor.execute("""
                    SELECT * FROM telemetry 
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                """, (time_threshold,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
    
    def get_metrics_by_trace(self, trace_id: str) -> List[Dict]:
        """
        Get all metrics for a specific trace.
        
        Why: Essential for RCA - we need to see the entire request flow
        across multiple endpoints to identify root cause.
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM telemetry 
                WHERE trace_id = ?
                ORDER BY timestamp ASC
            """, (trace_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
    
    def get_endpoint_stats(self, endpoint: str, minutes: int = 60) -> Dict:
        """
        Calculate aggregate statistics for an endpoint.
        
        Returns:
            Dictionary with avg_latency, error_rate, request_count, status distribution
            
        Why: Used by AIOps to compare current behavior against historical patterns.
        """
        metrics = self.get_recent_metrics(endpoint, minutes)
        
        if not metrics:
            return {
                'endpoint': endpoint,
                'request_count': 0,
                'avg_latency_ms': 0,
                'error_rate': 0,
                'status_distribution': {}
            }
        
        total_requests = len(metrics)
        total_latency = sum(m['latency_ms'] for m in metrics)
        error_count = sum(1 for m in metrics if m['status_code'] >= 500)
        
        # Status code distribution
        status_dist = {}
        for m in metrics:
            status = m['status_code']
            status_dist[status] = status_dist.get(status, 0) + 1
        
        return {
            'endpoint': endpoint,
            'request_count': total_requests,
            'avg_latency_ms': round(total_latency / total_requests, 2),
            'error_rate': round(error_count / total_requests, 2),
            'status_distribution': status_dist
        }
    
    def get_all_endpoints(self) -> List[str]:
        """
        Auto-discover all monitored endpoints.
        
        Why: AIOps should automatically monitor all endpoints without manual config.
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT DISTINCT endpoint FROM telemetry
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            return [row[0] for row in rows]
