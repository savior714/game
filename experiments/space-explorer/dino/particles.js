import * as THREE from "../vendor/three/three.module.min.js";

const VERTEX_SHADER = /* glsl */ `
  attribute float aSize;
  attribute float aAlpha;
  attribute vec3 aColor;
  uniform float uScale;
  varying vec3 vColor;
  varying float vAlpha;
  void main() {
    vColor = aColor;
    vAlpha = aAlpha;
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = clamp(aSize * uScale / max(1.0, -mv.z), 1.0, 96.0);
    gl_Position = projectionMatrix * mv;
  }
`;

const FRAGMENT_SHADER = /* glsl */ `
  varying vec3 vColor;
  varying float vAlpha;
  void main() {
    vec2 point = gl_PointCoord - vec2(0.5);
    float distanceToCenter = length(point);
    if (distanceToCenter > 0.5) discard;
    float mask = smoothstep(0.5, 0.08, distanceToCenter);
    if (vAlpha * mask < 0.003) discard;
    gl_FragColor = vec4(vColor, vAlpha * mask);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

/**
 * CPU-simulated point particles (dust, sparks, embers) sharing one draw call.
 * The pool is a ring buffer: when full, the oldest particle is recycled.
 * @param {THREE.Scene} scene
 * @param {{max?: number, additive?: boolean}} options
 */
export function createParticlePool(scene, options = {}) {
  const max = options.max ?? 200;
  const positions = new Float32Array(max * 3);
  const sizes = new Float32Array(max);
  const alphas = new Float32Array(max);
  const colors = new Float32Array(max * 3);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3).setUsage(THREE.DynamicDrawUsage));
  geometry.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1).setUsage(THREE.DynamicDrawUsage));
  geometry.setAttribute("aAlpha", new THREE.BufferAttribute(alphas, 1).setUsage(THREE.DynamicDrawUsage));
  geometry.setAttribute("aColor", new THREE.BufferAttribute(colors, 3).setUsage(THREE.DynamicDrawUsage));
  geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1000000);

  const material = new THREE.ShaderMaterial({
    uniforms: { uScale: { value: 500 } },
    vertexShader: VERTEX_SHADER,
    fragmentShader: FRAGMENT_SHADER,
    transparent: true,
    depthWrite: false,
    depthTest: true,
    blending: options.additive ? THREE.AdditiveBlending : THREE.NormalBlending,
  });

  const points = new THREE.Points(geometry, material);
  points.frustumCulled = false;
  points.renderOrder = options.additive ? 6 : 5;
  scene.add(points);

  const particles = new Array(max);
  for (let i = 0; i < max; i += 1) {
    particles[i] = {
      alive: false,
      x: 0,
      y: -999,
      z: 0,
      vx: 0,
      vy: 0,
      vz: 0,
      life: 0,
      maxLife: 1,
      size: 0,
      drag: 0,
      gravity: 0,
      floor: -1,
    };
    positions[i * 3 + 1] = -999;
  }

  let cursor = 0;
  let scale = 500;

  /**
   * @param {{x:number, y:number, z:number, vx?:number, vy?:number, vz?:number, life?:number, size?:number, color?:THREE.Color|number, drag?:number, gravity?:number, floor?:number}} spawn
   */
  function spawn(spawnOptions) {
    const index = cursor;
    cursor = (cursor + 1) % max;
    const particle = particles[index];
    particle.alive = true;
    particle.x = spawnOptions.x;
    particle.y = spawnOptions.y;
    particle.z = spawnOptions.z;
    particle.vx = spawnOptions.vx ?? 0;
    particle.vy = spawnOptions.vy ?? 0;
    particle.vz = spawnOptions.vz ?? 0;
    particle.maxLife = spawnOptions.life ?? 0.8;
    particle.life = particle.maxLife;
    particle.size = spawnOptions.size ?? 0.16;
    particle.drag = spawnOptions.drag ?? 0.7;
    particle.gravity = spawnOptions.gravity ?? 0;
    particle.floor = spawnOptions.floor ?? -1;
    const color = spawnOptions.color instanceof THREE.Color ? spawnOptions.color : new THREE.Color(spawnOptions.color ?? 0xd8c9a8);
    colors[index * 3] = color.r;
    colors[index * 3 + 1] = color.g;
    colors[index * 3 + 2] = color.b;
    sizes[index] = particle.size;
    alphas[index] = 1;
    positions[index * 3] = particle.x;
    positions[index * 3 + 1] = particle.y;
    positions[index * 3 + 2] = particle.z;
  }

  function update(dt) {
    if (!(dt > 0)) {
      return;
    }
    const step = Math.min(dt, 0.05);
    for (let i = 0; i < max; i += 1) {
      const particle = particles[i];
      if (!particle.alive) {
        continue;
      }
      particle.life -= step;
      if (particle.life <= 0) {
        particle.alive = false;
        alphas[i] = 0;
        sizes[i] = 0;
        continue;
      }
      const dragFactor = Math.max(0, 1 - particle.drag * step);
      particle.vx *= dragFactor;
      particle.vz *= dragFactor;
      particle.vy = particle.vy * dragFactor - particle.gravity * step;
      particle.x += particle.vx * step;
      particle.y += particle.vy * step;
      particle.z += particle.vz * step;
      if (particle.floor >= -0.5 && particle.y < particle.floor) {
        particle.y = particle.floor;
        particle.vy = Math.abs(particle.vy) * 0.18;
        particle.vx *= 0.7;
        particle.vz *= 0.7;
      }
      const ratio = particle.life / particle.maxLife;
      positions[i * 3] = particle.x;
      positions[i * 3 + 1] = particle.y;
      positions[i * 3 + 2] = particle.z;
      alphas[i] = Math.min(1, ratio * 2.2) * 0.9;
      sizes[i] = particle.size * (0.55 + ratio * 0.65);
    }
    geometry.attributes.position.needsUpdate = true;
    geometry.attributes.aSize.needsUpdate = true;
    geometry.attributes.aAlpha.needsUpdate = true;
    geometry.attributes.aColor.needsUpdate = true;
  }

  function setViewport(heightPx, pixelRatio) {
    scale = Math.max(120, heightPx * 0.5 * Math.min(pixelRatio, 2));
    material.uniforms.uScale.value = scale;
  }

  function dispose() {
    scene.remove(points);
    geometry.dispose();
    material.dispose();
  }

  return { spawn, update, setViewport, dispose, points, material };
}
