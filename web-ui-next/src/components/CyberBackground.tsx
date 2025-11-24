"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

export function CyberBackground() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
    });
    renderer.setPixelRatio(window.devicePixelRatio || 1);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      55,
      window.innerWidth / window.innerHeight,
      0.1,
      1000,
    );
    camera.position.z = 40;

    const particleCount = 650;
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    const colorA = new THREE.Color(0x22d3ee);
    const colorB = new THREE.Color(0xa855f7);

    for (let i = 0; i < particleCount; i++) {
      const i3 = i * 3;
      positions[i3] = (Math.random() - 0.5) * 120;
      positions[i3 + 1] = (Math.random() - 0.5) * 70;
      positions[i3 + 2] = (Math.random() - 0.5) * 80;

      const t = Math.random();
      const c = colorA.clone().lerp(colorB, t);
      colors[i3] = c.r;
      colors[i3 + 1] = c.g;
      colors[i3 + 2] = c.b;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
      size: 0.7,
      vertexColors: true,
      transparent: true,
      opacity: 0.9,
    });

    const points = new THREE.Points(geometry, material);
    scene.add(points);

    const lineGeometry = new THREE.BufferGeometry();
    const linePositions = new Float32Array(particleCount * 3);
    lineGeometry.setAttribute(
      "position",
      new THREE.BufferAttribute(linePositions, 3),
    );
    const lineMaterial = new THREE.LineBasicMaterial({
      color: 0x22d3ee,
      transparent: true,
      opacity: 0.16,
    });
    const lines = new THREE.LineSegments(lineGeometry, lineMaterial);
    scene.add(lines);

    function resize() {
      const width = window.innerWidth;
      const height = window.innerHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    }

    resize();

    let frameId: number | null = null;

    const animate = () => {
      frameId = requestAnimationFrame(animate);

      const time = Date.now() * 0.00012;
      points.rotation.y = time;
      points.rotation.x = time * 0.25;

      const positionsArr = geometry.attributes.position.array as Float32Array;
      const linePositionsArr =
        lineGeometry.attributes.position.array as Float32Array;

      let idx = 0;
      for (let i = 0; i < particleCount; i += 3) {
        const i3 = i * 3;
        const j3 = ((i + 7) % particleCount) * 3;

        linePositionsArr[idx++] = positionsArr[i3];
        linePositionsArr[idx++] = positionsArr[i3 + 1];
        linePositionsArr[idx++] = positionsArr[i3 + 2];

        linePositionsArr[idx++] = positionsArr[j3];
        linePositionsArr[idx++] = positionsArr[j3 + 1];
        linePositionsArr[idx++] = positionsArr[j3 + 2];
      }

      lineGeometry.attributes.position.needsUpdate = true;
      renderer.render(scene, camera);
    };

    animate();
    window.addEventListener("resize", resize);

    return () => {
      if (frameId !== null) {
        cancelAnimationFrame(frameId);
      }
      window.removeEventListener("resize", resize);
      renderer.dispose();
      geometry.dispose();
      lineGeometry.dispose();
      material.dispose();
      lineMaterial.dispose();
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none fixed inset-0 -z-10 h-full w-full"
    />
  );
}
