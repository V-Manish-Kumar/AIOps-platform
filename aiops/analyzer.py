"""
AIOps Analyzer Module

Implements automatic anomaly detection:
- Baseline learning (moving average)
- Latency anomaly detection
- Error spike detection
- Timeout detection

No manual thresholds - system learns normal behavior automatically.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict

from telemetry.storage import TelemetryStorage


class AIOpsAnalyzer:
    """
    Self-learning anomaly detection engine.
    
    Key Principles:
    1. Learn baselines automatically from historical data
    2. Detect deviations from normal patterns
    3. No manual threshold configuration
    4. Continuous adaptation to changing patterns
    """
    
    def __init__(self):
        self.storage = TelemetryStorage()
        
        # Store learned baselines per endpoint
        # baseline_latency[endpoint] = moving_average_latency
        self.baseline_latency = {}
        
        # Configuration (can be tuned based on SLA requirements)
        self.LATENCY_MULTIPLIER = 3.0  # Alert if 3x slower than baseline
        self.ERROR_RATE_THRESHOLD = 0.2  # Alert if >20% errors
        self.MIN_SAMPLES_FOR_BASELINE = 10  # Need min data before detecting anomalies
        self.ANALYSIS_WINDOW_MINUTES = 5  # Look at last 5 minutes for anomalies
        self.BASELINE_WINDOW_MINUTES = 60  # Learn baseline from last hour
    
    def learn_baselines(self):
        """
        Learn normal latency patterns for all endpoints.
        
        Uses exponential weighted moving average (EWMA):
        - Recent data has more weight
        - Adapts to gradual changes in traffic patterns
        - Stable against outliers
        
        Why: In production systems, "normal" changes over time (traffic patterns,
        seasonal effects). Static thresholds break. Self-learning adapts.
        """
        endpoints = self.storage.get_all_endpoints()
        
        for endpoint in endpoints:
            # Skip AIOps internal endpoints
            if endpoint.startswith('/aiops/') or endpoint.startswith('/simulate/'):
                continue
            
            # Get recent successful requests (exclude errors for baseline)
            metrics = self.storage.get_recent_metrics(
                endpoint, 
                minutes=self.BASELINE_WINDOW_MINUTES
            )
            
            # Filter to successful requests only (200-299)
            successful = [m for m in metrics if 200 <= m['status_code'] < 300]
            
            if len(successful) >= self.MIN_SAMPLES_FOR_BASELINE:
                # Calculate average latency
                avg_latency = sum(m['latency_ms'] for m in successful) / len(successful)
                
                # Update baseline with exponential smoothing
                if endpoint in self.baseline_latency:
                    # EWMA: 90% old baseline, 10% new measurement
                    old_baseline = self.baseline_latency[endpoint]
                    self.baseline_latency[endpoint] = (0.9 * old_baseline) + (0.1 * avg_latency)
                else:
                    # First time - use calculated average
                    self.baseline_latency[endpoint] = avg_latency
    
    def detect_latency_anomalies(self) -> List[Dict]:
        """
        Detect endpoints with unusual latency.
        
        Algorithm:
        1. Get recent requests (last 5 minutes)
        2. Calculate current average latency
        3. Compare to learned baseline
        4. Alert if current > baseline * multiplier
        
        Returns:
            List of anomaly dictionaries with details
        """
        anomalies = []
        endpoints = self.storage.get_all_endpoints()
        
        for endpoint in endpoints:
            if endpoint.startswith('/aiops/') or endpoint.startswith('/simulate/'):
                continue
            
            # Need baseline to compare against
            if endpoint not in self.baseline_latency:
                continue
            
            baseline = self.baseline_latency[endpoint]
            
            # Get recent metrics
            recent = self.storage.get_recent_metrics(
                endpoint,
                minutes=self.ANALYSIS_WINDOW_MINUTES
            )
            
            if not recent:
                continue
            
            # Calculate current average
            current_avg = sum(m['latency_ms'] for m in recent) / len(recent)
            
            # Detect anomaly
            if current_avg > (baseline * self.LATENCY_MULTIPLIER):
                anomalies.append({
                    'type': 'latency_anomaly',
                    'endpoint': endpoint,
                    'severity': 'high' if current_avg > (baseline * 5) else 'medium',
                    'baseline_ms': round(baseline, 2),
                    'current_ms': round(current_avg, 2),
                    'deviation': round((current_avg / baseline), 2),
                    'sample_size': len(recent),
                    'detected_at': datetime.utcnow().isoformat(),
                    # Include trace_ids for RCA
                    'trace_ids': list(set(m['trace_id'] for m in recent))
                })
        
        return anomalies
    
    def detect_error_spikes(self) -> List[Dict]:
        """
        Detect unusual error rates.
        
        Algorithm:
        1. Calculate 5xx error rate in recent window
        2. Alert if rate exceeds threshold
        3. Include sample error messages for debugging
        
        Why percentage: Absolute error count is meaningless without context.
        5 errors in 10 requests is critical. 5 errors in 10,000 is normal.
        """
        anomalies = []
        endpoints = self.storage.get_all_endpoints()
        
        for endpoint in endpoints:
            if endpoint.startswith('/aiops/') or endpoint.startswith('/simulate/'):
                continue
            
            recent = self.storage.get_recent_metrics(
                endpoint,
                minutes=self.ANALYSIS_WINDOW_MINUTES
            )
            
            if len(recent) < 5:  # Need minimum sample size
                continue
            
            # Count 5xx errors
            error_count = sum(1 for m in recent if m['status_code'] >= 500)
            error_rate = error_count / len(recent)
            
            if error_rate > self.ERROR_RATE_THRESHOLD:
                # Get sample error messages
                errors = [m for m in recent if m['status_code'] >= 500 and m['error_message']]
                sample_errors = [e['error_message'][:200] for e in errors[:3]]  # First 3 errors
                
                anomalies.append({
                    'type': 'error_spike',
                    'endpoint': endpoint,
                    'severity': 'critical' if error_rate > 0.5 else 'high',
                    'error_rate': round(error_rate, 2),
                    'error_count': error_count,
                    'total_requests': len(recent),
                    'sample_errors': sample_errors,
                    'detected_at': datetime.utcnow().isoformat(),
                    'trace_ids': list(set(m['trace_id'] for m in recent if m['status_code'] >= 500))
                })
        
        return anomalies
    
    def detect_timeout_issues(self) -> List[Dict]:
        """
        Detect endpoints that stopped responding.
        
        Algorithm:
        1. Check if endpoint received requests recently
        2. Check if it was active before
        3. Alert if suddenly silent
        
        Why: Timeouts often don't generate errors - the request just hangs.
        Need to detect absence of responses, not just bad responses.
        """
        anomalies = []
        endpoints = self.storage.get_all_endpoints()
        
        for endpoint in endpoints:
            if endpoint.startswith('/aiops/') or endpoint.startswith('/simulate/'):
                continue
            
            # Check if we had requests recently
            very_recent = self.storage.get_recent_metrics(endpoint, minutes=5)
            
            # Check if we had requests before (to avoid false positives on new endpoints)
            historical = self.storage.get_recent_metrics(endpoint, minutes=60)
            
            # If no recent requests but had historical activity
            if len(very_recent) == 0 and len(historical) > 10:
                anomalies.append({
                    'type': 'timeout_issue',
                    'endpoint': endpoint,
                    'severity': 'medium',
                    'message': 'Endpoint stopped responding (no requests in last 5 minutes)',
                    'last_seen': historical[0]['timestamp'] if historical else None,
                    'detected_at': datetime.utcnow().isoformat()
                })
        
        return anomalies
    
    def run_analysis(self) -> Dict:
        """
        Run complete anomaly detection cycle.
        
        Returns:
            Dictionary containing all detected anomalies and current baselines
        
        This should be called periodically (e.g., every 30 seconds)
        by a background scheduler in production.
        """
        # Step 1: Update baselines
        self.learn_baselines()
        
        # Step 2: Run all detectors
        latency_anomalies = self.detect_latency_anomalies()
        error_anomalies = self.detect_error_spikes()
        timeout_anomalies = self.detect_timeout_issues()
        
        # Combine results
        all_anomalies = latency_anomalies + error_anomalies + timeout_anomalies
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'anomalies_detected': len(all_anomalies),
            'anomalies': all_anomalies,
            'baselines': {
                endpoint: round(latency, 2) 
                for endpoint, latency in self.baseline_latency.items()
            }
        }
    
    def get_endpoint_health(self, endpoint: str) -> Dict:
        """
        Get current health status of an endpoint.
        
        Returns:
            Health score, current metrics, comparison to baseline
        """
        stats = self.storage.get_endpoint_stats(endpoint, minutes=60)
        baseline = self.baseline_latency.get(endpoint)
        
        # Calculate health score (0-100)
        health_score = 100
        
        if stats['error_rate'] > 0:
            health_score -= (stats['error_rate'] * 50)  # Errors reduce score
        
        if baseline and stats['avg_latency_ms'] > 0:
            latency_ratio = stats['avg_latency_ms'] / baseline
            if latency_ratio > 2:
                health_score -= 30
        
        health_score = max(0, health_score)
        
        return {
            'endpoint': endpoint,
            'health_score': round(health_score, 1),
            'status': 'healthy' if health_score > 80 else 'degraded' if health_score > 50 else 'critical',
            'current_metrics': stats,
            'baseline_latency_ms': round(baseline, 2) if baseline else None
        }
