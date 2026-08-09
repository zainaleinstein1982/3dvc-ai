import { forwardRef, useImperativeHandle, useRef, useMemo } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { Group, Mesh, PlaneGeometry, MeshBasicMaterial, VideoTexture, DoubleSide } from 'three';

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
  const trackingDataRef = useRef<any>(null);
  const { camera } = useThree();

  const videoElement = typeof document !== 'undefined' ? (document.querySelector('video') as HTMLVideoElement) : null;
  const videoTexture = useMemo(() => videoElement ? new VideoTexture(videoElement) : null, [videoElement]);

  // Membuat geometri bidang untuk efek berlapis (depth layers ala 3DVC)
  const geometry = useMemo(() => new PlaneGeometry(2.4, 2.4, 32, 32), []);
  
  // Material transparan untuk memberikan kesan volume/kedalaman neural rendering
  const materialFront = useMemo(() => new MeshBasicMaterial({ 
    map: videoTexture || undefined, 
    side: DoubleSide,
    transparent: true,
    opacity: 0.95
  }), [videoTexture]);

  const materialBack = useMemo(() => new MeshBasicMaterial({ 
    map: videoTexture || undefined, 
    color: 0x88bbff, // Efek glow depth ala sistem neural 
    side: DoubleSide,
    transparent: true,
    opacity: 0.4
  }), [videoTexture]);

  useImperativeHandle(ref, () => ({
    updateTracking: (data: any) => { trackingDataRef.current = data; }
  }));

  useFrame(() => {
    if (!groupRef.current) return;
    
    // Menggerakkan rotasi grup secara interaktif berdasarkan posisi kepala pengguna (Head Tracking Parallax)
    if (trackingDataRef.current) {
      const targetPitch = (trackingDataRef.current.pitch || 0) * (Math.PI / 180) * 0.4;
      const targetYaw = (trackingDataRef.current.yaw || 0) * (Math.PI / 180) * 0.4;
      
      groupRef.current.rotation.x += (targetPitch - groupRef.current.rotation.x) * 0.1;
      groupRef.current.rotation.y += (targetYaw - groupRef.current.rotation.y) * 0.1;
    } else {
      // Efek melayang halus (idle floating) jika tracking belum aktif penuh
      groupRef.current.rotation.y = Math.sin(Date.now() * 0.001) * 0.05;
    }
  });

  return (
    <group ref={groupRef} position={props.position}>
      {/* Layer Belakang (Depth Backplate untuk memberikan efek volume 3D) */}
      <mesh geometry={geometry} material={materialBack} position={[0, 0, -0.15]} scale={[1.05, 1.05, 1]} />
      
      <div></div>

      {/* Layer Utama (Video Wajah Partisipan) */}
      <mesh geometry={geometry} material={materialFront} position={[0, 0, 0]} />
    </group>
  );
});

Avatar3D.displayName = 'Avatar3D';
export default Avatar3D;