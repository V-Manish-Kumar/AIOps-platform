"""
Telemetry Collector Module

Provides middleware and decorators for automatic request instrumentation.
Captures latency, status codes, errors, and trace information.
"""

import time
import uuid
import traceback
from functools import wraps
from datetime import datetime
from flask import request, g
from typing import Callable

from telemetry.storage import TelemetryStorage


class TelemetryCollector:
    """
    Automatic telemetry collection for Flask applications.
    
    Why middleware: Intercepts all requests transparently, no manual instrumentation needed.
    Why trace_id: Enables correlation across multiple endpoint calls (essential for RCA).
    """
    
    def __init__(self, service_name: str = "api-service"):
        self.service_name = service_name
        self.storage = TelemetryStorage()
    
    def init_app(self, app):
        """
        Register Flask middleware hooks.
        
        before_request: Generate trace_id and start timer
        after_request: Capture metrics and store
        """
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        
        # Handle uncaught exceptions
        app.register_error_handler(Exception, self._handle_exception)
    
    def _before_request(self):
        """
        Called before each request.
        
        Sets up trace context:
        - Propagate trace_id from header (for distributed tracing)
        - Or generate new trace_id
        - Start latency timer
        """
        # Check if trace_id exists in headers (from upstream service)
        trace_id = request.headers.get('X-Trace-ID')
        if not trace_id:
            trace_id = str(uuid.uuid4())
        
        # Store in Flask's request-local context
        g.trace_id = trace_id
        g.start_time = time.time()
    
    def _after_request(self, response):
        """
        Called after each request completes successfully.
        
        Captures:
        - Final status code
        - Request duration
        - No error (error_message = None)
        """
        # Skip telemetry endpoints to avoid infinite recursion
        if request.path.startswith('/aiops/'):
            return response
        
        latency_ms = (time.time() - g.start_time) * 1000
        
        metric = {
            'service_name': self.service_name,
            'endpoint': request.path,
            'method': request.method,
            'status_code': response.status_code,
            'latency_ms': round(latency_ms, 2),
            'error_message': None,
            'trace_id': g.trace_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Store asynchronously in production (use queue + worker)
        self.storage.store_metric(metric)
        
        # Add trace_id to response headers (for debugging & distributed tracing)
        response.headers['X-Trace-ID'] = g.trace_id
        
        return response
    
    def _handle_exception(self, error):
        """
        Called when unhandled exception occurs.
        
        Captures:
        - 500 status code
        - Error message and stack trace
        - Latency up to failure point
        
        Why: Critical for detecting error spikes and diagnosing root causes.
        """
        from werkzeug.exceptions import HTTPException
        
        # Don't track 404s and other HTTP exceptions - only real errors
        if isinstance(error, HTTPException) and error.code < 500:
            raise error
        
        latency_ms = (time.time() - g.start_time) * 1000
        
        # Get full stack trace
        error_details = ''.join(traceback.format_exception(
            type(error), error, error.__traceback__
        ))
        
        metric = {
            'service_name': self.service_name,
            'endpoint': request.path,
            'method': request.method,
            'status_code': 500,
            'latency_ms': round(latency_ms, 2),
            'error_message': f"{type(error).__name__}: {str(error)}\n{error_details}",
            'trace_id': g.trace_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.storage.store_metric(metric)
        
        # Re-raise so Flask can handle it
        raise error


def traced_call(func: Callable) -> Callable:
    """
    Decorator for internal function calls that should use same trace_id.
    
    Why: When endpoint A calls endpoint B internally, they should share trace_id
    for proper correlation in RCA.
    
    Usage:
        @traced_call
        def call_payment_api():
            # This will inherit trace_id from current request
            return requests.post('/payment', headers={'X-Trace-ID': g.trace_id})
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Ensure trace_id is available in context
        if not hasattr(g, 'trace_id'):
            g.trace_id = str(uuid.uuid4())
        return func(*args, **kwargs)
    return wrapper
