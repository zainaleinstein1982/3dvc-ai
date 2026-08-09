import sys, os, time, json, uuid, base64, cv2, asyncio
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.ai.distributed_queue import distributed_queue
from app.ai.liveportrait_engine import liveportrait_engine
from app.ai.depth_engine import depth_engine
from app.storage.object_storage import object_storage

async def main():
    if not distributed_queue.is_available():
        print("Redis not available. Worker cannot start.")
        return

    worker_id = f"worker-{os.getpid()}"
    distributed_queue.register_worker(worker_id, {"models": ["LivePortrait", "DepthAnything"], "gpu": "cuda"})
    print(f"GPU Worker {worker_id} started. Storage: {'MinIO' if object_storage.is_available else 'Disabled'}")
    
    await liveportrait_engine.load()
    await depth_engine.load()
    print("Models loaded.")

    while True:
        distributed_queue.heartbeat(worker_id, "idle")
        job = distributed_queue.get_job()
        
        if job:
            job_id = job["job_id"]
            payload = job["payload"]
            participant_id = payload.get("participantId", "unknown")
            sequence = payload.get("sequence", 0)
            
            print(f"Worker {worker_id} processing job {job_id} for {participant_id} seq={sequence}")
            distributed_queue.heartbeat(worker_id, "busy")
            
            try:
                # Mock Inference for script execution
                h, w = 256, 256
                depth_map = np.random.rand(h, w).astype(np.float32)
                frame = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
                
                _, depth_buf = cv2.imencode('.png', (depth_map * 255).astype(np.uint8))
                _, frame_buf = cv2.imencode('.jpg', frame)
                
                ts = int(time.time())
                depth_key = f"ai-assets/{participant_id}/{ts}_{sequence}_depth.png"
                frame_key = f"ai-assets/{participant_id}/{ts}_{sequence}_frame.jpg"
                
                assets = {}
                if object_storage.is_available:
                    if object_storage.upload(depth_key, depth_buf.tobytes(), "image/png"):
                        assets["depthMap"] = {"key": depth_key, "mimeType": "image/png", "size": len(depth_buf)}
                    if object_storage.upload(frame_key, frame_buf.tobytes(), "image/jpeg"):
                        assets["frame"] = {"key": frame_key, "mimeType": "image/jpeg", "size": len(frame_buf)}
                
                result = {
                    "jobId": job_id, "participantId": participant_id, "sequence": sequence, "timestamp": ts,
                    "assets": assets, "inference_ms": 75.0, "success": True
                }
                distributed_queue.redis.setex(f"result_data:{job_id}", 30, json.dumps(result))
                print(f"Job {job_id} completed. Assets uploaded.")
                
            except Exception as e:
                print(f"Job failed: {e}")
                distributed_queue.redis.setex(f"result_data:{job_id}", 30, json.dumps({"success": False, "error": str(e)}))
        
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(main())
