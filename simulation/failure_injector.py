"""
Failure Injection Module

Simulates various failure scenarios for testing AIOps detection.
Allows controlled testing of:
- Latency spikes
- Error rates
- Cascading failures
"""

import time
import random
from typing import Dict, Optional
from functools import wraps


class FailureInjector:
    """
    Chaos engineering tool for testing AIOps.
    
    Why: Need to validate that AIOps correctly detects and correlates failures.
    Simulates real production issues in controlled manner.
    """
    
    def __init__(self):
        # Configuration per endpoint
        # Structure: {endpoint: {'delay_ms': int, 'error_rate': float}}
        self.config = {}
    
    def set_delay(self, endpoint: str, delay_ms: int):
        """
        Add artificial latency to an endpoint.
        
        Args:
            endpoint: Target endpoint (e.g., '/payment')
            delay_ms: Delay in milliseconds
            
        Use case: Test latency anomaly detection
        """
        if endpoint not in self.config:
            self.config[endpoint] = {}
        self.config[endpoint]['delay_ms'] = delay_ms
    
    def set_error_rate(self, endpoint: str, error_rate: float):
        """
        Make endpoint fail randomly.
        
        Args:
            endpoint: Target endpoint
            error_rate: Probability of failure (0.0 - 1.0)
            
        Use case: Test error spike detection
        """
        if endpoint not in self.config:
            self.config[endpoint] = {}
        self.config[endpoint]['error_rate'] = max(0.0, min(1.0, error_rate))
    
    def clear_endpoint(self, endpoint: str):
        """Remove all simulations for an endpoint."""
        if endpoint in self.config:
            del self.config[endpoint]
    
    def clear_all(self):
        """Remove all simulations."""
        self.config = {}
    
    def inject(self, endpoint: str):
        """
        Apply configured failures to a request.
        
        Should be called at the start of endpoint handler.
        
        Raises:
            SimulatedFailure: If error injection triggers
        """
        if endpoint not in self.config:
            return
        
        config = self.config[endpoint]
        
        # Inject delay
        if 'delay_ms' in config:
            delay_seconds = config['delay_ms'] / 1000.0
            time.sleep(delay_seconds)
        
        # Inject error
        if 'error_rate' in config:
            if random.random() < config['error_rate']:
                # Simulate various error types
                error_types = [
                    "Database connection timeout",
                    "Downstream service unavailable",
                    "Out of memory error",
                    "Circuit breaker open",
                    "Rate limit exceeded"
                ]
                error_msg = random.choice(error_types)
                raise SimulatedFailure(f"Simulated failure: {error_msg}")
    
    def get_config(self) -> Dict:
        """Get current simulation configuration."""
        return self.config.copy()


class SimulatedFailure(Exception):
    """
    Exception raised by failure injection.
    
    Distinguishes simulated failures from real bugs.
    """
    pass


# Global injector instance (singleton for MVP)
_injector = FailureInjector()


def get_injector() -> FailureInjector:
    """Get global failure injector instance."""
    return _injector


def with_failure_injection(func):
    """
    Decorator to enable failure injection on endpoint.
    
    Usage:
        @app.route('/payment', methods=['POST'])
        @with_failure_injection
        def payment():
            # Will automatically inject failures if configured
            return {'status': 'success'}
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get endpoint from Flask request context
        from flask import request
        endpoint = request.path
        
        # Inject failures
        _injector.inject(endpoint)
        
        # Call original function
        return func(*args, **kwargs)
    
    return wrapper
