import asyncio
import time
import logging
from typing import Dict
from .distributed_queue import distributed_queue
import json, base64, cv2, numpy as np

log = logging.getLogger(__name__)

class GPUResourceManager:
    def __init__(self, max_workers: int = 2, max_queue_size: int = 50):
        self.local_queue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self.max_workers = max_workers
        self.workers = []
        self.is_running = False
        self.stats = {"processed": 0, "dropped_stale": 0, "dropped_full": 0, "queue_depth": 0}
        self.last_sequence: Dict[str, int] = {}
        self.redis = distributed_queue

    async def start(self):
        self.is_running = True
        if self.redis.is_available():
            log.info("GPUResourceManager running in DISTRIBUTED mode (Redis).")
        else:
            log.info("GPUResourceManager running in LOCAL mode (asyncio).")
            for i in range(self.max_workers):
                task = asyncio.create_task(self._local_worker(f"local-worker-{i}"))
                self.workers.append(task)

    async def submit_job(self, priority: int, payload: dict) -> dict:
        seq = payload.get("sequence", 0)
        pid = payload.get("participantId", "unknown")
        if pid in self.last_sequence and seq <= self.last_sequence[pid]:
            self.stats["dropped_stale"] += 1
            raise RuntimeError("Stale frame dropped")
        self.last_sequence[pid] = seq

        if self.redis.is_available():
            job_id = self.redis.submit_job(payload, priority)
            result_key = f"result_data:{job_id}"
            for _ in range(100):
                res = self.redis.redis.get(result_key)
                if res:
                    self.redis.redis.delete(result_key)
                    return json.loads(res)
                await asyncio.sleep(0.1)
            self.stats["dropped_full"] += 1
            raise RuntimeError("Distributed GPU Timeout")
        else:
            if self.local_queue.full():
                self.stats["dropped_full"] += 1
                raise RuntimeError("Local Queue Full")
            future = asyncio.get_event_loop().create_future()
            await self.local_queue.put((priority, time.time(), payload, future))
            self.stats["queue_depth"] = self.local_queue.qsize()
            return await future

    async def _local_worker(self, name: str):
        while self.is_running:
            try:
                priority, ts, payload, future = await asyncio.wait_for(self.local_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            try:
                # Mock inference for local fallback
                await asyncio.sleep(0.05)
                h, w = 256, 256
                depth_map = np.random.rand(h, w).astype(np.float32)
                frame = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
                _, depth_buf = cv2.imencode('.png', (depth_map * 255).astype(np.uint8))
                _, frame_buf = cv2.imencode('.jpg', frame)
                result = {"success": True, "inference_ms": 50.0, "sequence": payload["sequence"], "assets": {}, "depth_b64": base64.b64encode(depth_buf).decode('utf-8'), "frame_b64": base64.b64encode(frame_buf).decode('utf-8')}
                self.stats["processed"] += 1
                if not future.done(): future.set_result(result)
            except Exception as e:
                if not future.done(): future.set_exception(e)
            finally:
                self.local_queue.task_done()

gpu_manager = GPUResourceManager()
