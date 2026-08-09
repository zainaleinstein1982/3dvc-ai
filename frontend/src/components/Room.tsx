'use client';
import { useEffect, useRef, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import Avatar3D from './Avatar3D';
import LoginScreen from './LoginScreen';
import ProductionDiagnosticsPanel from './ProductionDiagnosticsPanel';
import { SFUTransport } from '@/lib/webrtc/SFUTransport';
import { ActiveSpeakerManager } from '@/lib/rendering/ActiveSpeakerManager';
import { TrackingScheduler } from '@/lib/tracking/TrackingScheduler';

export default function Room() {
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [activeSpeakerId, setActiveSpeakerId] = useState<string | null>(null);
  const [participants, setParticipants] = useState<Map<string, any>>(new Map());
  const avatarRefs = useRef<Map<string, any>>(new Map());
  const transport = useRef<SFUTransport | null>(null);
  const activeSpeakerManager = useRef<ActiveSpeakerManager | null>(null);
  const trackingScheduler = useRef<TrackingScheduler | null>(null);
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const trackingWorker = useRef<Worker | null>(null);
  const sequenceNumber = useRef(0);

  useEffect(() => {
    if (!authToken) return;
    
    const init = async () => {
      // Setup WebRTC
      transport.current = new SFUTransport();
      await transport.current.connect('demo-room', currentUser.id);
      
      transport.current.onRemoteTrackingData = (id, data) => {
        const avatar = avatarRefs.current.get(id);
        if (avatar) avatar.updateTracking(data);
      };
      transport.current.onParticipantJoined = (id) => {
        setParticipants(prev => new Map(prev).set(id, { id, isActive: false }));
      };

      // Setup Active Speaker
      activeSpeakerManager.current = new ActiveSpeakerManager(setActiveSpeakerId);

      // Setup Tracking Worker
      if (typeof Worker !== 'undefined') {
        trackingWorker.current = new Worker(new URL('../workers/TrackingWorker.ts', import.meta.url));
        trackingWorker.current.onmessage = (e) => {
          if (e.data.type === 'ready') {
            trackingScheduler.current = new TrackingScheduler(async () => {
              if (!localVideoRef.current || !trackingWorker.current) return;
              const canvas = document.createElement('canvas');
              canvas.width = 256; canvas.height = 256;
              const ctx = canvas.getContext('2d')!;
              ctx.drawImage(localVideoRef.current, 0, 0, 256, 256);
              const imageData = ctx.getImageData(0, 0, 256, 256);
              trackingWorker.current.postMessage({ type: 'process', payload: { imageData, sequence: sequenceNumber.current++, timestamp: Date.now() } }, [imageData.data.buffer]);
            });
            trackingScheduler.current.start();
          } else if (e.data.type === 'result' && e.data.payload) {
            const localAvatar = avatarRefs.current.get(transport.current?.localId || 'local');
            localAvatar?.updateTracking(e.data.payload);
            transport.current?.sendData(e.data.payload);
          }
        };
        trackingWorker.current.postMessage({ type: 'init' });
      }

      // Get local media
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      if (localVideoRef.current) localVideoRef.current.srcObject = stream;
    };
    init();

    return () => {
      transport.current?.disconnect();
      trackingScheduler.current?.stop();
      trackingWorker.current?.terminate();
    };
  }, [authToken]);

  useEffect(() => {
    // Adaptive FPS based on active speaker
    const isActive = activeSpeakerId === currentUser?.id;
    trackingScheduler.current?.setActive(isActive);
  }, [activeSpeakerId, currentUser]);

  if (!authToken || !currentUser) return <LoginScreen onLogin={(token, user) => { setAuthToken(token); setCurrentUser(user); }} />;

  return (
    <div className="flex flex-col h-screen bg-black text-white">
      {currentUser.role === 'ADMIN' && <ProductionDiagnosticsPanel token={authToken} />}
      <div className="flex-1 relative">
        <video ref={localVideoRef} autoPlay playsInline muted className="hidden" />
        <Canvas camera={{ position: [0, 1, 6], fov: 50 }}>
          <ambientLight intensity={0.8} />
          <directionalLight position={[10, 10, 5]} intensity={1} />
          <Avatar3D ref={(node) => { if (node) avatarRefs.current.set(currentUser.id, node); }} isActiveSpeaker={true} position={[0, 0, 0]} color="blue" />
          {Array.from(participants.values()).map((p) => (
            <Avatar3D key={p.id} ref={(node) => { if (node) avatarRefs.current.set(p.id, node); else avatarRefs.current.delete(p.id); }} isActiveSpeaker={p.id === activeSpeakerId} position={[2, 0, 0]} color="red" />
          ))}
          <OrbitControls />
        </Canvas>
      </div>
    </div>
  );
}
