import os

FILES = {
    "3dvc/frontend/src/components/Avatar3D.tsx": """import { forwardRef, useImperativeHandle, useRef, useMemo } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { Group, Mesh, SphereGeometry, MeshStandardMaterial } from 'three';
import { RenderQualityConfig } from '@/lib/rendering/RenderQualityConfig';

export interface Avatar3DHandle {
  updateTracking: (data: any) => void;
}

interface Avatar3DProps {
  isActiveSpeaker: boolean;
  position: [number, number, number];
  color: string;
}

const Avatar3D = forwardRef<Avatar3DHandle, Avatar3DProps>((props, ref) => {
  const groupRef = useRef<Group>(null);
  const meshRef = useRef<Mesh>(null);
  const trackingDataRef = useRef<any>(null);
  const { camera } = useThree();

  const geometries = useMemo(() => ({
    lod0: new SphereGeometry(0.5, 64, 64),
    lod1: new SphereGeometry(0.5, 16, 16),
    lod2: new SphereGeometry(0.5, 4, 4),
  }), []);

  const material = useMemo(() => new MeshStandardMaterial({ color: props.color, wireframe: !props.isActiveSpeaker }), [props.color, props.isActiveSpeaker]);

  useImperativeHandle(ref, () => ({
    updateTracking: (data: any) => { trackingDataRef.current = data; }
  }));

  useFrame(() => {
    if (!groupRef.current || !meshRef.current) return;
    const dist = camera.position.distanceTo(groupRef.current.position);
    let lod = 2;
    if (props.isActiveSpeaker) lod = 0;
    else if (dist < RenderQualityConfig.distance.lod0) lod = 0;
    else if (dist < RenderQualityConfig.distance.lod1) lod = 1;

    const targetGeo = lod === 0 ? geometries.lod0 : lod === 1 ? geometries.lod1 : geometries.lod2;
    if (meshRef.current.geometry !== targetGeo) meshRef.current.geometry = targetGeo;

    if (trackingDataRef.current) {
      groupRef.current.rotation.x = trackingDataRef.current.pitch * (Math.PI / 180);
      groupRef.current.rotation.y = trackingDataRef.current.yaw * (Math.PI / 180);
    }
  });

  return (
    <group ref={groupRef} position={props.position}>
      <mesh ref={meshRef} material={material} castShadow />
    </group>
  );
});
Avatar3D.displayName = 'Avatar3D';
export default Avatar3D;
""",
    "3dvc/frontend/src/components/ProductionDiagnosticsPanel.tsx": """'use client';
import { useState, useEffect } from 'react';

export default function ProductionDiagnosticsPanel({ token }: { token: string }) {
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch('http://localhost:8000/api/health/admin-diagnostics', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) setHealth(await res.json());
        else setHealth({ status: 'unauthorized' });
      } catch (e) { setHealth({ status: 'backend_offline' }); }
    }, 2000);
    return () => clearInterval(interval);
  }, [token]);

  return (
    <div className="absolute top-4 right-4 bg-black/90 p-4 rounded-xl border border-white/10 w-80 text-xs font-mono z-50">
      <div className="text-sm font-bold mb-2 text-emerald-400">SYSTEM HEALTH</div>
      {health ? (
        <div className="space-y-1">
          <div>Status: <span className="text-emerald-400">{health.status}</span></div>
          {health.dependencies && (
            <>
              <div>Redis: <span className="text-emerald-400">{health.dependencies.redis}</span></div>
              <div>MinIO: <span className="text-emerald-400">{health.dependencies.minio}</span></div>
              <div>GPU Workers: <span className="text-cyan-400">{health.dependencies.gpu_workers}</span></div>
            </>
          )}
        </div>
      ) : <div className="text-white/50">Checking...</div>}
    </div>
  );
}
""",
    "3dvc/frontend/src/lib/api.ts": """let accessToken: string | null = null;
export const setAccessToken = (token: string | null) => { accessToken = token; };

export async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const headers = { ...options.headers, 'Authorization': `Bearer ${accessToken}`, 'Content-Type': 'application/json' };
  let res = await fetch(url, { ...options, headers, credentials: 'include' });

  if (res.status === 401) {
    const refreshRes = await fetch('http://localhost:8000/api/auth/refresh', { method: 'POST', credentials: 'include' });
    if (refreshRes.ok) {
      const data = await refreshRes.json();
      setAccessToken(data.access_token);
      headers['Authorization'] = `Bearer ${data.access_token}`;
      res = await fetch(url, { ...options, headers, credentials: 'include' });
    } else {
      window.location.reload();
      throw new Error('Session expired');
    }
  }
  return res;
}
""",
    "3dvc/frontend/src/lib/webrtc/SFUTransport.ts": """import { Room, RoomEvent, Track, RemoteParticipant } from 'livekit-client';

export class SFUTransport {
  private room: Room;
  public localId: string = '';
  public onRemoteStream: (id: string, stream: MediaStream) => void = () => {};
  public onRemoteTrackingData: (id: string, data: any) => void = () => {};
  public onParticipantJoined: (id: string) => void = () => {};
  public onParticipantLeft: (id: string) => void = () => {};

  constructor() {
    this.room = new Room();
    this.setupEvents();
  }

  private setupEvents() {
    this.room.on(RoomEvent.ParticipantConnected, (p: RemoteParticipant) => this.onParticipantJoined(p.identity));
    this.room.on(RoomEvent.ParticipantDisconnected, (p: RemoteParticipant) => this.onParticipantLeft(p.identity));
    this.room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
      if (track.kind === Track.Kind.Audio) {
        const stream = new MediaStream([track.mediaStreamTrack]);
        this.onRemoteStream(participant.identity, stream);
      }
    });
    this.room.on(RoomEvent.DataReceived, (payload, participant) => {
      this.onRemoteTrackingData(participant.identity, JSON.parse(new TextDecoder().decode(payload)));
    });
  }

  async connect(roomId: string, userId: string) {
    const res = await fetch(`http://localhost:8000/api/sfu/token?room=${roomId}`, {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } // Simplified for script
    });
    const { token, url } = await res.json();
    await this.room.connect(url, token);
    this.localId = this.room.localParticipant.identity;
    this.room.remoteParticipants.forEach(p => this.onParticipantJoined(p.identity));
  }

  async publishTrack(track: MediaStreamTrack) {
    await this.room.localParticipant.publishTrack(track);
  }

  sendData(data: any) {
    this.room.localParticipant.publishData(new TextEncoder().encode(JSON.stringify(data)), { reliable: true });
  }

  disconnect() { this.room.disconnect(); }
}
""",
    "3dvc/frontend/src/lib/audio/SpatialAudioEngine.ts": """export class SpatialAudioEngine {
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
