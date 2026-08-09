import { forwardRef, useImperativeHandle, useRef, useMemo } from 'react';
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
