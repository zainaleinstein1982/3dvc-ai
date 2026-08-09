/// <reference lib="webworker" />
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
