export class TrackingScheduler {
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
