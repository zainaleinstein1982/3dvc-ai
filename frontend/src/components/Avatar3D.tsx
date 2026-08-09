import { forwardRef, useImperativeHandle, useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
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

  // Ambil elemen video lokal dari DOM
  const videoElement = typeof document !== 'undefined' ? (document.querySelector('video') as HTMLVideoElement) : null;
  const videoTexture = useMemo(() => videoElement ? new VideoTexture(videoElement) : null, [videoElement]);

  const geometry = useMemo(() => new PlaneGeometry(3, 3), []);
  
  // Menggunakan MeshBasicMaterial agar video tampil terang natural tanpa butuh pencahayaan lampu 3D
  const material = useMemo(() => new MeshBasicMaterial({ 
    map: videoTexture || undefined, 
    color: videoTexture ? 0xffffff : props.color,
    side: DoubleSide 
  }), [videoTexture, props.color]);

  useImperativeHandle(ref, () => ({
    updateTracking: (data: any) => { trackingDataRef.current = data; }
  }));

  useFrame(() => {
    if (!groupRef.current) return;
    if (trackingDataRef.current) {
      const targetPitch = (trackingDataRef.current.pitch || 0) * (Math.PI / 180) * 0.3;
      const targetYaw = (trackingDataRef.current.yaw || 0) * (Math.PI / 180) * 0.3;
      groupRef.current.rotation.x += (targetPitch - groupRef.current.rotation.x) * 0.1;
      groupRef.current.rotation.y += (targetYaw - groupRef.current.rotation.y) * 0.1;
    }
  });

  return (
    <group ref={groupRef} position={props.position}>
      <mesh geometry={geometry} material={material} />
    </group>
  );
});

Avatar3D.displayName = 'Avatar3D';
export default Avatar3D;