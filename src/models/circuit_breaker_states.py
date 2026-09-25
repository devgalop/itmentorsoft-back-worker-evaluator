from enum import Enum


class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerEvent:
    def __init__(self, state: str, failure_count: int = 0, failed_at: float = 0):
        self.state = state
        self.failure_count = failure_count
        self.failed_at = failed_at

    def to_dict(self):
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failed_at": self.failed_at,
        }
