import { RenderQualityConfig } from './RenderQualityConfig';

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
