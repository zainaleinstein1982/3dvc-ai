import redis
import json
import time
import uuid
import os
import logging
from typing import Optional
from app.observability.circuit_breaker import CircuitBreaker

log = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class DistributedAIQueue:
    def __init__(self):
        self.redis = None
        self.cb = CircuitBreaker("redis_queue")
        try:
            self.redis = redis.from_url(REDIS_URL, decode_responses=True)
            self.redis.ping()
            log.info("Connected to Redis for distributed GPU queue.")
        except Exception as e:
            log.warning("Redis unavailable. Falling back to local queue. Error: %s", e)
            self.redis = None

    def is_available(self) -> bool:
        return self.redis is not None

    def submit_job(self, payload: dict, priority: int) -> str:
        if self.cb.is_open(): raise RuntimeError("Redis Circuit Breaker OPEN")
        try:
            job_id = str(uuid.uuid4())
            score = (priority * 10**13) - time.time() * 1000
            self.redis.zadd("ai_jobs", {json.dumps({"job_id": job_id, "payload": payload}): score})
            self.cb.record_success()
            return job_id
        except Exception as e:
            self.cb.record_failure()
            raise e

    def get_job(self) -> Optional[dict]:
        if not self.redis: return None
        result = self.redis.zpopmin("ai_jobs", count=1)
        if result:
            return json.loads(result[0][0])
        return None

    def register_worker(self, worker_id: str, capabilities: dict):
        self.redis.hset(f"workers:{worker_id}", mapping={"status": "idle", "capabilities": json.dumps(capabilities), "last_heartbeat": time.time()})
        self.redis.expire(f"workers:{worker_id}", 10)

    def heartbeat(self, worker_id: str, status: str = "idle"):
        self.redis.hset(f"workers:{worker_id}", "status", status)
        self.redis.hset(f"workers:{worker_id}", "last_heartbeat", time.time())
        self.redis.expire(f"workers:{worker_id}", 10)

    def get_worker_stats(self) -> dict:
        if not self.redis: return {}
        keys = self.redis.keys("workers:*")
        stats = {"total": 0, "idle": 0, "busy": 0}
        for key in keys:
            worker = self.redis.hgetall(key)
            stats["total"] += 1
            if worker.get("status") == "idle": stats["idle"] += 1
            else: stats["busy"] += 1
        return stats

distributed_queue = DistributedAIQueue()
