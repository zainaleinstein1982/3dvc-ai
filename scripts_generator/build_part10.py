import os

FILES = {
    "3dvc/frontend/src/workers/TrackingWorker.ts": """/// <reference lib="webworker" />
import { FaceLandmarker, FilesetResolver } from '@mediapipe/tasks-vision';

let landmarker: FaceLandmarker | null = null;
let isInitialized = false;

self.onmessage = async (e: MessageEvent) => {
  const { type, payload } = e.data;

  if (type === 'init') {
    try {
      const vision = await FilesetResolver.forVisionTasks('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm');
      landmarker = await FaceLandmarker.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath: 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
          delegate: 'GPU'
        },
        outputFaceBlendshapes: true,
        outputFacialTransformationMatrixes: true,
        numFaces: 1
      });
      isInitialized = true;
      self.postMessage({ type: 'ready' });
    } catch (err) {
      self.postMessage({ type: 'error', error: (err as Error).message });
    }
  } else if (type === 'process') {
    if (!isInitialized || !landmarker) return;
    const { imageData, sequence, timestamp } = payload;
    const results = landmarker.detect(imageData);
    let result = null;
    if (results.faceLandmarks && results.faceLandmarks.length > 0) {
      const landmarks = results.faceLandmarks[0];
      const blendshapes = results.faceBlendshapes?.[0]?.categories || [];
      const matrix = results.facialTransformationMatrixes?.[0]?.data;
      const leftIris = landmarks[468];
      const leftEyeCorner1 = landmarks[33];
      const leftEyeCorner2 = landmarks[133];
      const eyeWidth = leftEyeCorner2.x - leftEyeCorner1.x;
      const eyeHeight = (leftEyeCorner1.y + leftEyeCorner2.y) / 2;
      const eyeX = ((leftIris.x - leftEyeCorner1.x) / eyeWidth - 0.5) * 2.0;
      const eyeY = -((leftIris.y - eyeHeight) / eyeWidth) * 2.0;
      result = {
        yaw: matrix ? matrix[8] * 90 : 0,
        pitch: matrix ? matrix[9] * 90 : 0,
        roll: matrix ? matrix[0] * 90 : 0,
        blinkLeft: blendshapes.find(b => b.categoryName === 'eyeBlinkLeft')?.score || 0,
        eyeX: eyeX * 0.5,
        eyeY: eyeY * 0.5,
        blink: blendshapes.find(b => b.categoryName === 'eyeBlinkLeft')?.score || 0,
        confidence: 0.95,
        sequence,
        timestamp
      };
    }
    self.postMessage({ type: 'result', payload: result, buffer: imageData.data.buffer }, [imageData.data.buffer]);
  }
};
""",
    "3dvc/frontend/src/lib/rendering/RenderQualityConfig.ts": """export const RenderQualityConfig = {
  distance: { lod0: 3.0, lod1: 7.0 },
  hysteresisMs: 1000,
};
""",
    "3dvc/frontend/src/lib/rendering/ActiveSpeakerManager.ts": """import { RenderQualityConfig } from './RenderQualityConfig';

export class ActiveSpeakerManager {
  private activeSpeakerId: string | null = null;
  private lastSpokenTimestamps: Map<string, number> = new Map();
  private onActiveSpeakerChange: (id: string | null) => void;

  constructor(onChange: (id: string | null) => void) {
    this.onActiveSpeakerChange = onChange;
    this.startEvaluationLoop();
  }

  reportSpeaking(participantId: string, audioLevel: number) {
    if (audioLevel > 0.1) {
      this.lastSpokenTimestamps.set(participantId, Date.now());
    }
  }

  private startEvaluationLoop() {
    setInterval(() => {
      const now = Date.now();
      let currentLoudest: string | null = null;
      let currentLoudestTime = 0;

      this.lastSpokenTimestamps.forEach((timestamp, id) => {
        if (now - timestamp < 2000) {
          if (timestamp > currentLoudestTime) {
            currentLoudestTime = timestamp;
            currentLoudest = id;
          }
        }
      });

      if (currentLoudest && currentLoudest !== this.activeSpeakerId) {
        if (this.activeSpeakerId === null || 
            (now - (this.lastSpokenTimestamps.get(this.activeSpeakerId) || 0)) > RenderQualityConfig.hysteresisMs) {
          this.activeSpeakerId = currentLoudest;
          this.onActiveSpeakerChange(this.activeSpeakerId);
        }
      } else if (!currentLoudest && this.activeSpeakerId) {
        this.activeSpeakerId = null;
        this.onActiveSpeakerChange(null);
      }
    }, 100);
  }
}
""",
    "3dvc/frontend/src/lib/tracking/TrackingScheduler.ts": """export class TrackingScheduler {
  private targetFPS = 30;
  private interval = 1000 / this.targetFPS;
  private lastTime = 0;
  private rafId: number | null = null;
  private callback: () => void;

  constructor(callback: () => void) {
    this.callback = callback;
  }

  public setActive(isActive: boolean) {
    this.targetFPS = isActive ? 30 : 10;
    this.interval = 1000 / this.targetFPS;
  }

  public start() {
    const loop = (time: number) => {
      this.rafId = requestAnimationFrame(loop);
      const delta = time - this.lastTime;
      if (delta < this.interval) return;
      this.lastTime = time - (delta % this.interval);
      this.callback();
    };
    this.rafId = requestAnimationFrame(loop);
  }

  public stop() {
    if (this.rafId) cancelAnimationFrame(this.rafId);
  }
}
""",
    "3dvc/backend/scripts/gpu_worker.py": """import sys, os, time, json, uuid, base64, cv2, asyncio
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
"""
}

def create_files():
    for filepath, content in FILES.items():
        full_path = os.path.join(os.getcwd(), filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        print(f"Created: {filepath}")

if __name__ == "__main__":
    create_files()
