# 3DVC AI Demo Script

## Pre-requisites

* Docker Desktop running.
* `.env` configured with `OPENAI_API_KEY` and `LIVEKIT_API_SECRET`.

## Demo Flow (5 Minutes)

1. Introduction (30s)
   * "This is 3DVC AI, a spatial video conferencing platform that uses AI to reconstruct your face into a 3D avatar in real-time."
2. Authentication & Room Creation (1m)
   * Navigate to `http://localhost`.
   * Log in as `admin@3dvc.ai` / `admin123`.
   * Click "Create Room" and enter the room.
3. Edge Tracking & 3D Avatar (1m)
   * Allow camera/mic permissions.
   * Talking Point: "Notice the 3D avatar mirrors my head movement. This tracking is happening entirely in a Web Worker using WebAssembly, so the main thread stays at 60 FPS."
   * Open the `ProductionDiagnosticsPanel` to show `EDGE AI: WORKER` and 30 FPS tracking.
4. AI Mediation & Spatial Audio (1m 30s)
   * Say: "AI, can you nod your head?"
   * Talking Point: "The AI avatar heard me via ASR, processed the intent via LLM, executed a structured action, and responded via TTS. The TTS audio is spatialized in the 3D room."
   * Orbit the camera to hear the AI voice pan left/right.
5. Multi-User & LOD (1m)
   * Open a second browser tab (Chrome Incognito). Log in as `carol@3dvc.ai`.
   * Talking Point: "Notice the second avatar appears. Because I am the active speaker, my avatar is LOD 0 (full geometry). Carol's avatar is LOD 2 (low poly) to save draw calls."
   * Switch tabs. Carol becomes active. Observe the LOD swap seamlessly.
