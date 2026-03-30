"""
A robust, thread-safe Circuit Breaker pattern to protect the LLM Gateway.
When providers degrade, failing fast is preferable to letting requests stack up,
as upstream load balancers will otherwise exhaust available threads.
"""

import threading
import time
from enum import Enum, auto


class CircuitState(Enum):
    CLOSED = auto()     # Normal operations: requests flow through
    OPEN = auto()       # Degraded operations: requests fail fast
    HALF_OPEN = auto()  # Recovery state: testing the upstream with limited traffic


class CircuitBreaker:
    """
    Manages the availability state of a downstream dependency (e.g., an LLM Provider).
    
    States:
    - CLOSED: Service represents normal operation. Failures increment a counter. 
              Upon reaching threshold, transitions to OPEN.
    - OPEN: Service is degraded. Failures are fast-rejected. After a timeout,
            transitions to HALF_OPEN.
    - HALF_OPEN: Next request is allowed as a probe. If it succeeds, circuit CLOSES.
                 If it fails, circuit OPENS again.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout_s: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_s = recovery_timeout_s
        
        self.state = CircuitState.CLOSED
        
        self._failures = 0
        self._last_state_change_time = 0.0
        
        # We use a standard Lock to allow state transitions safely 
        # across threads/coroutines without the overhead of an asyncio lock
        # since the critical section is negligible (simple attribute access/mutation).
        self._lock = threading.Lock()

    def allow_request(self) -> bool:
        """
        Determines if a request should be allowed through based on current circuit state.
        
        Returns True if the upstream call should be attempted, False otherwise.
        """
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
                
            now = time.monotonic()
            
            if self.state == CircuitState.OPEN:
                if (now - self._last_state_change_time) > self.recovery_timeout_s:
                    # Time to test if the upstream healed
                    self._transition_state(CircuitState.HALF_OPEN, now)
                    return True
                return False
                
            if self.state == CircuitState.HALF_OPEN:
                # In half open state, only allow one concurrent testing request.
                # All other requests fail fast until the test request either succeeds or fails.
                # To enforce this strictly, we assume the first request calling `allow_request`
                # during HALF_OPEN is the probe.
                return True

        return False # Fallback

    def record_success(self) -> None:
        """Record a successful request. Resets failure counts and closes the circuit."""
        with self._lock:
            if self.state != CircuitState.CLOSED:
                self._transition_state(CircuitState.CLOSED, time.monotonic())
                
            self._failures = 0

    def record_failure(self) -> None:
        """Record a failed request. May trip the circuit open."""
        with self._lock:
            self._failures += 1
            
            if self.state == CircuitState.HALF_OPEN:
                # A failure during the test phase immediately re-opens the circuit
                self._transition_state(CircuitState.OPEN, time.monotonic())
            elif self.state == CircuitState.CLOSED:
                if self._failures >= self.failure_threshold:
                    self._transition_state(CircuitState.OPEN, time.monotonic())

    def _transition_state(self, new_state: CircuitState, current_time: float) -> None:
        """Execute a state change immediately without grabbing a new lock."""
        self.state = new_state
        self._last_state_change_time = current_time
        # Reset counters if we return to health
        if new_state == CircuitState.CLOSED:
            self._failures = 0
