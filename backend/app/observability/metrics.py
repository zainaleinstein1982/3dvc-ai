import time
from collections import defaultdict
import threading

class MetricsAggregator:
    def __init__(self):
        self.lock = threading.Lock()
        self.counters = defaultdict(int)
        self.latencies = defaultdict(list)
        
    def increment(self, name: str, value: int = 1):
        with self.lock:
            self.counters[name] += value
            
    def record_latency(self, name: str, ms: float):
        with self.lock:
            self.latencies[name].append(ms)
            if len(self.latencies[name]) > 1000:
                self.latencies[name] = self.latencies[name][-500:]
                
    def get_percentile(self, name: str, p: float) -> float:
        with self.lock:
            data = sorted(self.latencies.get(name, []))
            if not data: return 0
            idx = int(len(data) * p)
            return data[min(idx, len(data)-1)]
            
    def snapshot(self) -> dict:
        with self.lock:
            return {
                "counters": dict(self.counters),
                "latencies_ms": {
                    "ai_pipeline": {
                        "p50": self.get_percentile("ai_pipeline", 0.5),
                        "p95": self.get_percentile("ai_pipeline", 0.95),
                        "p99": self.get_percentile("ai_pipeline", 0.99)
                    }
                }
            }

metrics = MetricsAggregator()
