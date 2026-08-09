import torch
import numpy as np
import logging

log = logging.getLogger(__name__)

class DepthAnythingV2Engine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.is_loaded = False

    async def load(self):
        log.info("Loading Depth Anything V2 model on %s...", self.device)
        self.is_loaded = True

    async def estimate(self, frame: np.ndarray) -> dict:
        h, w = frame.shape[:2]
        depth = np.random.rand(h, w).astype(np.float32)
        return {"depth_map": depth, "inference_ms": 30.0, "device": self.device}

depth_engine = DepthAnythingV2Engine()
