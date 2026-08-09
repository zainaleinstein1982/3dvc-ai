export class SpatialAudioEngine {
  private audioContext: AudioContext | null = null;
  private sources: Map<string, any> = new Map();
  public isInitialized = false;

  public async initialize() {
    if (this.isInitialized) return;
    this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    if (this.audioContext.state === 'suspended') await this.audioContext.resume();
    this.isInitialized = true;
  }

  public connectRemoteStream(stream: MediaStream, participantId: string = 'remote') {
    if (!this.audioContext) return;
    const sourceNode = this.audioContext.createMediaStreamSource(stream);
    const gainNode = this.audioContext.createGain();
    const pannerNode = this.audioContext.createPanner();
    pannerNode.panningModel = 'HRTF';
    pannerNode.distanceModel = 'inverse';
    pannerNode.refDistance = 1;
    pannerNode.maxDistance = 50;
    pannerNode.rolloffFactor = 1.5;
    sourceNode.connect(gainNode);
    gainNode.connect(pannerNode);
    pannerNode.connect(this.audioContext.destination);
    this.sources.set(participantId, { sourceNode, gainNode, pannerNode, currentPosition: { x: 0, y: 0, z: 2 }, targetPosition: { x: 0, y: 0, z: 2 } });
  }

  public setSourcePosition(participantId: string, x: number, y: number, z: number) {
    const source = this.sources.get(participantId);
    if (source) source.targetPosition = { x, y, z };
  }

  public setListenerPosition(x: number, y: number, z: number) {
    if (!this.audioContext) return;
    const listener = this.audioContext.listener;
    if (listener.positionX) { listener.positionX.value = x; listener.positionY.value = y; listener.positionZ.value = z; }
  }

  public update() {
    if (!this.audioContext) return;
    this.sources.forEach((source) => {
      source.currentPosition.x += (source.targetPosition.x - source.currentPosition.x) * 0.1;
      source.currentPosition.y += (source.targetPosition.y - source.currentPosition.y) * 0.1;
      source.currentPosition.z += (source.targetPosition.z - source.currentPosition.z) * 0.1;
      source.pannerNode.positionX.value = source.currentPosition.x;
      source.pannerNode.positionY.value = source.currentPosition.y;
      source.pannerNode.positionZ.value = source.currentPosition.z;
    });
  }

  public disconnectSource(participantId: string) {
    const source = this.sources.get(participantId);
    if (source) { source.sourceNode.disconnect(); source.gainNode.disconnect(); source.pannerNode.disconnect(); this.sources.delete(participantId); }
  }

  public dispose() {
    this.sources.forEach((_, id) => this.disconnectSource(id));
    if (this.audioContext) { this.audioContext.close(); this.audioContext = null; }
    this.isInitialized = false;
  }
}
