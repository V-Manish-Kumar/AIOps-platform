"""
Root Cause Analysis (RCA) Module

Correlates anomalies across endpoints to identify root causes.
Uses trace_id to understand request flow and dependency chains.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Set
from collections import defaultdict

from telemetry.storage import TelemetryStorage


class RCAEngine:
    """
    Root Cause Analysis Engine.
    
    Key Capabilities:
    1. Trace correlation - link failures across multiple endpoints
    2. Temporal correlation - group anomalies that occurred together
    3. Dependency inference - identify which failure caused others
    4. Incident deduplication - one incident for related issues
    """
    
    def __init__(self):
        self.storage = TelemetryStorage()
        
        # Active incidents (in-memory for MVP, use Redis in production)
        self.incidents = {}
        self.incident_counter = 0
        
        # Configuration
        self.CORRELATION_WINDOW_MINUTES = 5  # Group anomalies within 5 min
        self.INCIDENT_TTL_MINUTES = 30  # Auto-close incidents after 30 min
    
    def correlate_anomalies(self, anomalies: List[Dict]) -> List[Dict]:
        """
        Correlate detected anomalies into incidents with root cause analysis.
        
        Process:
        1. Group anomalies by time window
        2. For each group, find common trace_ids
        3. For each trace, reconstruct request flow
        4. Identify earliest failure (root cause)
        5. Create incident with RCA
        
        Args:
            anomalies: List of anomalies from analyzer
            
        Returns:
            List of incidents with RCA
        """
        if not anomalies:
            return []
        
        # Step 1: Group anomalies by time proximity
        grouped = self._group_by_time(anomalies)
        
        incidents = []
        
        for group in grouped:
            # Step 2: Extract all trace_ids from this group
            all_trace_ids = set()
            for anomaly in group:
                if 'trace_ids' in anomaly:
                    all_trace_ids.update(anomaly['trace_ids'])
            
            if not all_trace_ids:
                # No trace correlation possible - create simple incident
                incidents.append(self._create_simple_incident(group))
                continue
            
            # Step 3: Perform trace-based RCA
            rca_result = self._analyze_traces(all_trace_ids, group)
            
            # Step 4: Create incident with RCA
            incident = self._create_incident_with_rca(group, rca_result)
            incidents.append(incident)
        
        # Store incidents
        self._store_incidents(incidents)
        
        return incidents
    
    def _group_by_time(self, anomalies: List[Dict]) -> List[List[Dict]]:
        """
        Group anomalies that occurred close in time.
        
        Why: Anomalies detected within a short window are likely related
        (e.g., payment failure causing checkout failure).
        """
        if not anomalies:
            return []
        
        # Sort by detection time
        sorted_anomalies = sorted(
            anomalies,
            key=lambda x: x.get('detected_at', datetime.utcnow().isoformat())
        )
        
        groups = []
        current_group = [sorted_anomalies[0]]
        group_start = datetime.fromisoformat(sorted_anomalies[0]['detected_at'])
        
        for anomaly in sorted_anomalies[1:]:
            anomaly_time = datetime.fromisoformat(anomaly['detected_at'])
            
            # If within correlation window, add to current group
            if (anomaly_time - group_start).total_seconds() < (self.CORRELATION_WINDOW_MINUTES * 60):
                current_group.append(anomaly)
            else:
                # Start new group
                groups.append(current_group)
                current_group = [anomaly]
                group_start = anomaly_time
        
        # Add last group
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _analyze_traces(self, trace_ids: Set[str], anomalies: List[Dict]) -> Dict:
        """
        Analyze request traces to identify root cause.
        
        Algorithm:
        1. For each trace_id, get all metrics (full request flow)
        2. Identify first failure in each trace
        3. Find most common root endpoint across traces
        4. Determine affected downstream endpoints
        
        Why: In a trace like: checkout -> payment -> inventory
        If payment fails, checkout will also fail.
        RCA identifies payment as root cause, not checkout.
        """
        root_causes = defaultdict(int)  # endpoint -> failure count
        affected_endpoints = set()
        trace_details = []
        
        for trace_id in trace_ids:
            # Get all requests in this trace
            trace_metrics = self.storage.get_metrics_by_trace(trace_id)
            
            if not trace_metrics:
                continue
            
            # Sort by timestamp to get chronological order
            trace_metrics.sort(key=lambda x: x['timestamp'])
            
            # Find first failure in trace
            first_failure = None
            for metric in trace_metrics:
                if metric['status_code'] >= 500 or metric['latency_ms'] > 5000:
                    first_failure = metric
                    break
            
            if first_failure:
                root_causes[first_failure['endpoint']] += 1
                
                # All endpoints in this trace are affected
                for metric in trace_metrics:
                    affected_endpoints.add(metric['endpoint'])
                
                trace_details.append({
                    'trace_id': trace_id,
                    'root_endpoint': first_failure['endpoint'],
                    'root_status': first_failure['status_code'],
                    'affected_chain': [m['endpoint'] for m in trace_metrics]
                })
        
        # Identify most common root cause
        if root_causes:
            root_endpoint = max(root_causes.items(), key=lambda x: x[1])[0]
        else:
            # Fallback: use first anomaly endpoint
            root_endpoint = anomalies[0]['endpoint'] if anomalies else 'unknown'
        
        return {
            'root_endpoint': root_endpoint,
            'root_cause_frequency': root_causes.get(root_endpoint, 0),
            'affected_endpoints': list(affected_endpoints),
            'trace_analysis': trace_details[:5],  # Limit to 5 sample traces
            'total_traces_analyzed': len(trace_ids)
        }
    
    def _create_incident_with_rca(self, anomalies: List[Dict], rca: Dict) -> Dict:
        """
        Create incident with root cause analysis.
        
        Includes:
        - Unique incident ID
        - Severity (based on anomaly types)
        - Root cause endpoint
        - Affected endpoints
        - Detailed RCA
        - Anomaly details
        """
        self.incident_counter += 1
        
        # Determine severity (highest from anomalies)
        severity_order = {'critical': 3, 'high': 2, 'medium': 1, 'low': 0}
        max_severity = max(
            (severity_order.get(a.get('severity', 'medium'), 1) for a in anomalies),
            default=1
        )
        severity = [k for k, v in severity_order.items() if v == max_severity][0]
        
        # Create human-readable title
        root_endpoint = rca['root_endpoint']
        anomaly_types = list(set(a['type'] for a in anomalies))
        
        if 'error_spike' in anomaly_types:
            issue_type = "Error spike"
        elif 'latency_anomaly' in anomaly_types:
            issue_type = "Latency spike"
        else:
            issue_type = "Service degradation"
        
        incident_id = f"INC-{int(datetime.utcnow().timestamp())}-{self.incident_counter}"
        
        return {
            'id': incident_id,
            'severity': severity,
            'status': 'active',
            'title': f"{issue_type} detected in {root_endpoint}",
            'root_cause': {
                'endpoint': root_endpoint,
                'confidence': round(rca['root_cause_frequency'] / max(rca['total_traces_analyzed'], 1), 2),
                'description': self._generate_rca_description(anomalies, rca)
            },
            'affected_endpoints': rca['affected_endpoints'],
            'anomalies': anomalies,
            'trace_correlation': {
                'total_traces': rca['total_traces_analyzed'],
                'sample_traces': rca['trace_analysis']
            },
            'first_detected': anomalies[0]['detected_at'],
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def _create_simple_incident(self, anomalies: List[Dict]) -> Dict:
        """
        Create incident when trace correlation is not possible.
        
        Used when:
        - No trace_ids available
        - Single endpoint issue
        """
        self.incident_counter += 1
        
        anomaly = anomalies[0]
        endpoint = anomaly['endpoint']
        
        incident_id = f"INC-{int(datetime.utcnow().timestamp())}-{self.incident_counter}"
        
        return {
            'id': incident_id,
            'severity': anomaly.get('severity', 'medium'),
            'status': 'active',
            'title': f"Anomaly detected in {endpoint}",
            'root_cause': {
                'endpoint': endpoint,
                'confidence': 1.0,
                'description': f"{anomaly['type']} detected"
            },
            'affected_endpoints': [endpoint],
            'anomalies': anomalies,
            'first_detected': anomaly['detected_at'],
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def _generate_rca_description(self, anomalies: List[Dict], rca: Dict) -> str:
        """
        Generate human-readable root cause description.
        """
        root = rca['root_endpoint']
        
        # Find anomaly for root endpoint
        root_anomaly = next((a for a in anomalies if a['endpoint'] == root), None)
        
        if not root_anomaly:
            return f"Issue detected in {root}"
        
        anomaly_type = root_anomaly['type']
        
        if anomaly_type == 'latency_anomaly':
            baseline = root_anomaly.get('baseline_ms', 0)
            current = root_anomaly.get('current_ms', 0)
            return f"Latency spike: {current:.0f}ms (baseline: {baseline:.0f}ms, {root_anomaly.get('deviation', 0):.1f}x slower)"
        
        elif anomaly_type == 'error_spike':
            error_rate = root_anomaly.get('error_rate', 0)
            error_count = root_anomaly.get('error_count', 0)
            return f"Error spike: {error_rate*100:.0f}% error rate ({error_count} failures)"
        
        elif anomaly_type == 'timeout_issue':
            return f"Endpoint stopped responding"
        
        return f"{anomaly_type} detected"
    
    def _store_incidents(self, incidents: List[Dict]):
        """
        Store incidents in memory.
        
        In production:
        - Use Redis for distributed storage
        - Persist to database for historical analysis
        - Implement incident lifecycle (open -> ack -> resolved)
        """
        for incident in incidents:
            self.incidents[incident['id']] = incident
    
    def get_active_incidents(self) -> List[Dict]:
        """
        Get all active incidents.
        
        Filters out old incidents (auto-resolve after TTL).
        """
        cutoff = datetime.utcnow() - timedelta(minutes=self.INCIDENT_TTL_MINUTES)
        
        active = []
        for incident in self.incidents.values():
            last_updated = datetime.fromisoformat(incident['last_updated'])
            if last_updated > cutoff and incident['status'] == 'active':
                active.append(incident)
        
        # Sort by severity and time
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        active.sort(key=lambda x: (
            severity_order.get(x['severity'], 999),
            x['first_detected']
        ))
        
        return active
    
    def get_incident_by_id(self, incident_id: str) -> Dict:
        """Get specific incident by ID."""
        return self.incidents.get(incident_id)
    
    def resolve_incident(self, incident_id: str):
        """
        Manually resolve an incident.
        
        In production, implement:
        - Acknowledgment workflow
        - Resolution notes
        - Post-mortem links
        """
        if incident_id in self.incidents:
            self.incidents[incident_id]['status'] = 'resolved'
            self.incidents[incident_id]['resolved_at'] = datetime.utcnow().isoformat()
