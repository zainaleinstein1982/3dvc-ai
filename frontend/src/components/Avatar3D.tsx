import { forwardRef, useImperativeHandle, useRef, useMemo, useEffect, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { Group, Mesh, PlaneGeometry, MeshBasicMaterial, VideoTexture, DoubleSide, Color } from 'three';

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
  const [videoTexture, setVideoTexture] = useState<VideoTexture | null>(null);

  useEffect(() => {
    const videoElement = document.querySelector('video') as HTMLVideoElement;
    if (videoElement) {
      const texture = new VideoTexture(videoElement);
      setVideoTexture(texture);
    }
  }, []);

  const geometry = useMemo(() => new PlaneGeometry(3, 3, 32, 32), []);
  
  // Memberikan efek warna kebiruan ala Hologram Studio Vercel
  const material = useMemo(() => new MeshBasicMaterial({ 
    map: videoTexture || undefined, 
    color: new Color('#00d2ff'), // Efek neon hologram biru
    wireframe: false,
    transparent: true,
    opacity: 0.9,
    side: DoubleSide 
  }), [videoTexture]);

  useImperativeHandle(ref, () => ({
    updateTracking: (data: any) => { trackingDataRef.current = data; }
  }));

  useFrame(() => {
    if (!groupRef.current) return;
    if (trackingDataRef.current) {
      const targetPitch = (trackingDataRef.current.pitch || 0) * (Math.PI / 180) * 0.5;
      const targetYaw = (trackingDataRef.current.yaw || 0) * (Math.PI / 180) * 0.5;
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