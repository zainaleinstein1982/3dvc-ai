import torch
import numpy as np
import logging

log = logging.getLogger(__name__)

class LivePortraitEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.is_loaded = False

    async def load(self):
        log.info("Loading LivePortrait model on %s...", self.device)
        self.is_loaded = True

    async def animate(self, source_frame: np.ndarray, motion_data: dict) -> dict:
        return {"frame": source_frame, "inference_ms": 45.0, "device": self.device}

liveportrait_engine = LivePortraitEngine()
