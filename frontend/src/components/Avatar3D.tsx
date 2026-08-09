import { forwardRef, useImperativeHandle, useRef, useMemo } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { Group, Mesh, BufferGeometry, BufferAttribute, MeshStandardMaterial, DoubleSide } from 'three';
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
  const geometryRef = useRef<BufferGeometry>(null);
  const trackingDataRef = useRef<any>(null);
  const { camera } = useThree();

  // Inisialisasi BufferGeometry dinamis untuk menangani custom face mesh
  const customGeometry = useMemo(() => new BufferGeometry(), []);

  const material = useMemo(() => new MeshStandardMaterial({ 
    color: props.color, 
    wireframe: true, // Menampilkan wireframe jaring wajah 3D ala NVIDIA 3DVC
    side: DoubleSide 
  }), [props.color]);

  useImperativeHandle(ref, () => ({
    updateTracking: (data: any) => { 
      trackingDataRef.current = data; 
      
      // Jika data membawa array faceLandmarks dari worker pelacakan
      if (data?.faceLandmarks && data.faceLandmarks.length > 0 && geometryRef.current) {
        const landmarks = data.faceLandmarks[0]; // 478 titik 3D MediaPipe
        const positions = new Float32Array(landmarks.length * 3);
        
        landmarks.forEach((pt: any, i: number) => {
          // Normalisasi koordinat agar proporsional di ruang 3D Three.js
          positions[i * 3] = (pt.x - 0.5) * 1.5;
          positions[i * 3 + 1] = -(pt.y - 0.5) * 1.5;
          positions[i * 3 + 2] = -pt.z * 1.5;
        });

        geometryRef.current.setAttribute('position', new BufferAttribute(positions, 3));
        geometryRef.current.computeVertexNormals();
        geometryRef.current.attributes.position.needsUpdate = true;
      }
    }
  }));

  useFrame(() => {
    if (!groupRef.current || !meshRef.current) return;
    const dist = camera.position.distanceTo(groupRef.current.position);

    // Terapkan data rotasi kepala (Rigid Head Pose) dari tracking
    if (trackingDataRef.current) {
      if (trackingDataRef.current.pitch !== undefined) {
        groupRef.current.rotation.x = trackingDataRef.current.pitch * (Math.PI / 180);
      }
      if (trackingDataRef.current.yaw !== undefined) {
        groupRef.current.rotation.y = trackingDataRef.current.yaw * (Math.PI / 180);
      }
      if (trackingDataRef.current.roll !== undefined) {
        groupRef.current.rotation.z = trackingDataRef.current.roll * (Math.PI / 180);
      }
    }
  });

  return (
    <group ref={groupRef} position={props.position}>
      <mesh ref={meshRef} geometry={customGeometry} material={material} castShadow />
    </group>
  );
});

Avatar3D.displayName = 'Avatar3D';
export default Avatar3D;