import { Suspense, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, MeshDistortMaterial } from "@react-three/drei";
import type { Group } from "three";
import { usePrefersReducedMotion } from "../hooks/usePrefersReducedMotion";
import { useIsSmallViewport } from "../hooks/useIsSmallViewport";

/** Rotates its children slightly toward the pointer — ambient parallax, no drag controls. */
function ParallaxRig({ children }: { children: React.ReactNode }) {
  const group = useRef<Group>(null);

  useFrame((state) => {
    if (!group.current) return;
    const targetX = state.pointer.y * 0.18;
    const targetY = state.pointer.x * 0.28;
    group.current.rotation.x += (targetX - group.current.rotation.x) * 0.03;
    group.current.rotation.y += (targetY - group.current.rotation.y) * 0.03;
  });

  return <group ref={group}>{children}</group>;
}

function DriftingBlob() {
  return (
    <Float speed={1.4} rotationIntensity={0.5} floatIntensity={1.1}>
      <mesh scale={1.45} position={[0.7, 0.15, -0.5]}>
        <icosahedronGeometry args={[1, 14]} />
        <MeshDistortMaterial
          color="#ff6b57"
          distort={0.32}
          speed={1.5}
          roughness={0.55}
          metalness={0}
          emissive="#3ddc97"
          emissiveIntensity={0.05}
          transparent
          opacity={0.9}
        />
      </mesh>
    </Float>
  );
}

/** A static gradient used on mobile / reduced-motion instead of the WebGL scene. */
function StaticFallback() {
  return (
    <div
      aria-hidden
      className="absolute inset-0 bg-[radial-gradient(circle_at_50%_38%,rgba(255,107,87,0.32),transparent_60%),radial-gradient(circle_at_62%_62%,rgba(61,220,151,0.22),transparent_55%)]"
    />
  );
}

export function Hero3D() {
  const reducedMotion = usePrefersReducedMotion();
  const isSmallViewport = useIsSmallViewport();

  if (reducedMotion || isSmallViewport) {
    return <StaticFallback />;
  }

  return (
    <div className="absolute inset-0" aria-hidden="true">
      <Canvas
        dpr={[1, 1.5]}
        frameloop="always"
        camera={{ position: [0, 0, 6], fov: 40 }}
        gl={{ antialias: true, powerPreference: "low-power" }}
      >
        <ambientLight intensity={0.55} />
        <directionalLight position={[3, 3, 4]} intensity={0.7} color="#ffe4d6" />
        <pointLight position={[-4, -2, -3]} intensity={0.4} color="#3ddc97" />
        <Suspense fallback={null}>
          <ParallaxRig>
            <DriftingBlob />
          </ParallaxRig>
        </Suspense>
      </Canvas>
    </div>
  );
}
