from datetime import datetime, timedelta, timezone
from threading import Lock


class SimpleCircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_seconds=30):
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self._failure_count = 0
        self._state = "CLOSED"
        self._opened_at = None
        self._lock = Lock()

    def allow_request(self):
        with self._lock:
            if self._state != "OPEN":
                return True
            if datetime.now(timezone.utc) - self._opened_at >= timedelta(seconds=self.recovery_seconds):
                self._state = "HALF_OPEN"
                return True
            return False

    def on_success(self):
        with self._lock:
            self._failure_count = 0
            self._state = "CLOSED"
            self._opened_at = None

    def on_failure(self):
        with self._lock:
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._state = "OPEN"
                self._opened_at = datetime.now(timezone.utc)

    @property
    def state(self):
        return self._state
