import time
import random
from enum import Enum

# Define the possible states of the Circuit Breaker
class CircuitBreakerState(Enum):
    CLOSED = 1
    OPEN = 2
    HALF_OPEN = 3

# Custom exception for when the circuit is open
class CircuitBreakerOpenException(Exception):
    """Custom exception raised when the circuit breaker is open."""
    pass

class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=5, half_open_test_attempts=1):
        self.state = CircuitBreakerState.CLOSED
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_test_attempts = half_open_test_attempts

        self.current_failures = 0
        self.last_failure_time = None
        self.successful_half_open_attempts = 0

    def __call__(self, func):
        """Makes the CircuitBreaker instance a decorator."""
        def wrapper(*args, **kwargs):
            if self.state == CircuitBreakerState.OPEN:
                # If OPEN, check if recovery timeout has passed
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    # Time elapsed, attempt to transition to HALF_OPEN
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.successful_half_open_attempts = 0 # Reset for half-open tests
                    print(f"[{time.time():.2f}] Circuit Breaker: Transitioned to HALF_OPEN.")
                else:
                    # Still within recovery timeout, fail fast without calling the service
                    print(f"[{time.time():.2f}] Circuit Breaker: OPEN. Failing fast without calling service.")
                    raise CircuitBreakerOpenException("Circuit Breaker is OPEN.")

            if self.state == CircuitBreakerState.HALF_OPEN:
                try:
                    # In HALF_OPEN, allow a test call to the service
                    result = func(*args, **kwargs)
                    self.successful_half_open_attempts += 1
                    print(f"[{time.time():.2f}] Circuit Breaker: HALF_OPEN. Test call successful ({self.successful_half_open_attempts}/{self.half_open_test_attempts}).")
                    if self.successful_half_open_attempts >= self.half_open_test_attempts:
                        # Enough successful test calls, transition back to CLOSED
                        self.state = CircuitBreakerState.CLOSED
                        self.current_failures = 0 # Reset failures on successful recovery
                        print(f"[{time.time():.2f}] Circuit Breaker: Transitioned to CLOSED.")
                    return result
                except Exception as e:
                    # Test call failed, transition back to OPEN immediately
                    self.current_failures = 0 # Reset for next half-open cycle
                    self.state = CircuitBreakerState.OPEN
                    self.last_failure_time = time.time()
                    print(f"[{time.time():.2f}] Circuit Breaker: HALF_OPEN. Test call failed. Transitioned back to OPEN.")
                    raise CircuitBreakerOpenException(f"Circuit Breaker is OPEN due to half-open failure: {e}")

            # State is CLOSED (or just transitioned from HALF_OPEN to CLOSED)
            try:
                # In CLOSED state, call the service normally
                result = func(*args, **kwargs)
                self.current_failures = 0 # Reset failures on success
                return result
            except Exception as e:
                # Service call failed, increment failure count
                self.current_failures += 1
                print(f"[{time.time():.2f}] Circuit Breaker: CLOSED. Service call failed. Current failures: {self.current_failures}/{self.failure_threshold}")
                if self.current_failures >= self.failure_threshold:
                    # Failure threshold reached, transition to OPEN
                    self.state = CircuitBreakerState.OPEN
                    self.last_failure_time = time.time()
                    print(f"[{time.time():.2f}] Circuit Breaker: Transitioned to OPEN.")
                raise e # Re-raise the original exception to the caller

        return wrapper

# --- Simulated Unreliable Service ---
def unreliable_service(request_id):
    """Simulates a service that sometimes fails or takes time."""
    if random.random() < 0.6: # 60% chance of failure
        print(f"[{time.time():.2f}] Service call {request_id}: FAILED.")
        raise ConnectionError("Simulated service connection error.")
    else:
        time.sleep(0.1) # Simulate some work
        print(f"[{time.time():.2f}] Service call {request_id}: SUCCESS.")
        return f"Data for {request_id}"

# --- Main execution --- 
if __name__ == "__main__":
    # Initialize the circuit breaker with custom parameters:
    # It will open after 3 failures, stay open for 5 seconds,
    # and require 1 successful call in HALF_OPEN state to close.
    my_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=5, half_open_test_attempts=1)

    # Apply the circuit breaker to the unreliable service using the decorator pattern
    @my_circuit_breaker
    def protected_service(request_id):
        return unreliable_service(request_id)

    print("--- Starting Circuit Breaker Demonstration ---")
    print("Initial state: CLOSED")

    for i in range(20):
        print(f"\n--- Attempt {i+1} ---")
        try:
            result = protected_service(f"req-{i+1}")
            # print(f"Received: {result}") # Uncomment to see successful results
        except CircuitBreakerOpenException as e:
            print(f"Caught CircuitBreakerOpenException: {e}")
        except Exception as e:
            print(f"Caught other exception: {e}")
        time.sleep(0.5) # Simulate some delay between requests

    print("\n--- Demonstration Finished ---")
