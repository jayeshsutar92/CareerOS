import time
import logging
from dataclasses import dataclass, field
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@dataclass
class DiscoveryMetrics:
    total_execution_time_ms: float = 0
    cache_hits: int = 0
    cache_misses: int = 0
    http_requests_made: int = 0
    http_requests_failed: int = 0
    ai_invocations: int = 0
    stage_times_ms: dict[str, float] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)

    def record_cache_hit(self):
        self.cache_hits += 1

    def record_cache_miss(self):
        self.cache_misses += 1

    def record_http_request(self, success: bool = True):
        self.http_requests_made += 1
        if not success:
            self.http_requests_failed += 1

    def record_ai_invocation(self):
        self.ai_invocations += 1

    @contextmanager
    def measure_stage(self, stage_name: str):
        start = time.time()
        try:
            yield
        finally:
            elapsed_ms = (time.time() - start) * 1000
            self.stage_times_ms[stage_name] = self.stage_times_ms.get(stage_name, 0) + elapsed_ms

    def finalize(self):
        self.total_execution_time_ms = (time.time() - self.start_time) * 1000

    def emit_summary(self):
        self.finalize()
        logger.info(
            "Discovery Workflow Metrics Summary",
            extra={
                "action": "discovery_metrics_summary",
                "total_time_ms": round(self.total_execution_time_ms, 2),
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "http_requests_made": self.http_requests_made,
                "http_requests_failed": self.http_requests_failed,
                "ai_invocations": self.ai_invocations,
                "stage_times_ms": {k: round(v, 2) for k, v in self.stage_times_ms.items()}
            }
        )
