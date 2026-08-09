import { forwardRef, useImperativeHandle, useRef, useMemo, useEffect, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { Group, Mesh, PlaneGeometry, MeshStandardMaterial, VideoTexture, DoubleSide, DirectionalLight, AmbientLight } from 'three';

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

  // Menggunakan Plane dengan segmentasi tinggi agar bisa melengkung (memberikan efek volume 3D / curved display)
  const geometry = useMemo(() => new PlaneGeometry(3, 3, 32, 32), []);
  
  // Menggunakan MeshStandardMaterial agar merespons cahaya studio (menghasilkan efek kontras & kedalaman wajah seperti 3DVC)
  const material = useMemo(() => new MeshStandardMaterial({ 
    map: videoTexture || undefined, 
    color: videoTexture ? 0xffffff : props.color,
    roughness: 0.4,
    metalness: 0.1,
    side: DoubleSide 
  }), [videoTexture, props.color]);

  useImperativeHandle(ref, () => ({
    updateTracking: (data: any) => { trackingDataRef.current = data; }
  }));

  useFrame(() => {
    if (!groupRef.current) return;
    
    // Pergerakan sudut pandang dinamis (Parallax Head Tracking) ala sistem 3DVC
    if (trackingDataRef.current) {
      const targetPitch = (trackingDataRef.current.pitch || 0) * (Math.PI / 180) * 0.6;
      const targetYaw = (trackingDataRef.current.yaw || 0) * (Math.PI / 180) * 0.6;
      
      groupRef.current.rotation.x += (targetPitch - groupRef.current.rotation.x) * 0.15;
      groupRef.current.rotation.y += (targetYaw - groupRef.current.rotation.y) * 0.15;
    }
  });

  return (
    <group ref={groupRef} position={props.position}>
      {/* Pencahayaan Studio Virtual untuk memberikan efek kontras kedalaman wajah */}
      <ambientLight intensity={1.2} />
      <directionalLight position={[5, 5, 5]} intensity={2.0} color="#ffffff" />
      <directionalLight position={[-5, -2, 2]} intensity={0.8} color="#88bbff" />

      <mesh geometry={geometry} material={material} castShadow receiveShadow />
    </group>
  );
});

Avatar3D.displayName = 'Avatar3D';
export default Avatar3D;