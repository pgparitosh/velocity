import asyncio

from velocity.core.circuit_breaker import CircuitBreaker


def test_circuit_breaker_initial_state():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout_s=0.1)
    assert cb.allow_request() is True

def test_circuit_breaker_open_on_failure():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout_s=1.0)
    cb.record_failure()
    assert cb.allow_request() is True
    cb.record_failure()
    assert cb.allow_request() is False

async def test_circuit_breaker_recovery():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout_s=0.2)
    cb.record_failure()
    assert cb.allow_request() is False
    
    await asyncio.sleep(0.3)
    # Should be Half-Open now
    assert cb.allow_request() is True
    
    # Success should Reset
    cb.record_success()
    assert cb.allow_request() is True
    
    # Failure in Half-Open should immediately Open
    cb.record_failure()
    assert cb.allow_request() is False
    
    await asyncio.sleep(0.3)
    assert cb.allow_request() is True
    cb.record_failure()
    assert cb.allow_request() is False
