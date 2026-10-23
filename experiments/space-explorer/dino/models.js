import * as THREE from "../vendor/three/build/three.module.min.js";
import { clamp, damp, lerp } from "./util.js";

/* ------------------------------------------------------------------ */
/* Tiny geometry helpers                                               */
/* ------------------------------------------------------------------ */

const GEO = {
  sphere: new THREE.SphereGeometry(1, 18, 14),
  sphereLow: new THREE.SphereGeometry(1, 10, 8),
  box: new THREE.BoxGeometry(1, 1, 1),
  cylinder: new THREE.CylinderGeometry(1, 1, 1, 12),
  cone: new THREE.ConeGeometry(1, 1, 8),
  torus: new THREE.TorusGeometry(1, 0.09, 8, 24),
  octa: new THREE.OctahedronGeometry(1, 0),
  ico: new THREE.IcosahedronGeometry(1, 0),
  dodeca: new THREE.DodecahedronGeometry(1, 0),
};

function mesh(geometry, material, position = [0, 0, 0], rotation = [0, 0, 0], scale = [1, 1, 1]) {
  const item = new THREE.Mesh(geometry, material);
  item.position.set(position[0], position[1], position[2]);
  item.rotation.set(rotation[0], rotation[1], rotation[2]);
  item.scale.set(scale[0], scale[1], scale[2]);
  item.castShadow = true;
  item.receiveShadow = true;
  return item;
}

function group(parent, position = [0, 0, 0], name = "") {
  const item = new THREE.Group();
  item.position.set(position[0], position[1], position[2]);
  if (name) {
    item.name = name;
  }
  parent.add(item);
  return item;
}

function limbGeometry(topRadius, bottomRadius, length, segments = 10) {
  const geometry = new THREE.CylinderGeometry(topRadius, bottomRadius, length, segments);
  geometry.translate(0, -length / 2, 0);
  return geometry;
}

function tapered(length, topRadius, bottomRadius, segments = 10) {
  return new THREE.CylinderGeometry(topRadius, bottomRadius, length, segments);
}

function lambert(color, options = {}) {
  return new THREE.MeshStandardMaterial({
    color,
    roughness: options.roughness ?? 0.88,
    metalness: options.metalness ?? 0,
    flatShading: options.flatShading ?? false,
    emissive: options.emissive ?? 0x000000,
    emissiveIntensity: options.emissiveIntensity ?? 1,
    transparent: options.transparent ?? false,
    opacity: options.opacity ?? 1,
    side: options.side ?? THREE.FrontSide,
    depthWrite: options.depthWrite ?? true,
  });
}

function markNoShadow(root) {
  root.traverse((child) => {
    if (child.isMesh) {
      child.castShadow = false;
      child.receiveShadow = false;
    }
  });
  return root;
}

/* ------------------------------------------------------------------ */
/* Vertex-coloured merged geometry (used for scenery + bone props)     */
/* ------------------------------------------------------------------ */

const scratchMatrix = new THREE.Matrix4();
const scratchQuat = new THREE.Quaternion();
const scratchEuler = new THREE.Euler();
const scratchScale = new THREE.Vector3();

/**
 * Merges several primitive parts into one BufferGeometry with baked vertex
 * colours. Keeps draw calls low for instanced scenery and bone arches.
 * @param {Array<{geometry: THREE.BufferGeometry, color: number, position?: number[], rotation?: number[], scale?: number[]}>} parts
 */
export function buildMergedGeometry(parts) {
  const positions = [];
  const normals = [];
  const colors = [];
  const color = new THREE.Color();

  for (const part of parts) {
    const geometry = part.geometry.index ? part.geometry.toNonIndexed() : part.geometry.clone();
    scratchEuler.set(part.rotation?.[0] ?? 0, part.rotation?.[1] ?? 0, part.rotation?.[2] ?? 0);
    scratchQuat.setFromEuler(scratchEuler);
    scratchScale.set(part.scale?.[0] ?? 1, part.scale?.[1] ?? 1, part.scale?.[2] ?? 1);
    scratchMatrix.compose(
      new THREE.Vector3(part.position?.[0] ?? 0, part.position?.[1] ?? 0, part.position?.[2] ?? 0),
      scratchQuat,
      scratchScale,
    );
    geometry.applyMatrix4(scratchMatrix);

    const positionAttribute = geometry.getAttribute("position");
    const normalAttribute = geometry.getAttribute("normal");
    color.set(part.color ?? 0xffffff);
    for (let i = 0; i < positionAttribute.count; i += 1) {
      positions.push(positionAttribute.getX(i), positionAttribute.getY(i), positionAttribute.getZ(i));
      normals.push(normalAttribute.getX(i), normalAttribute.getY(i), normalAttribute.getZ(i));
      colors.push(color.r, color.g, color.b);
    }
    geometry.dispose();
  }

  const merged = new THREE.BufferGeometry();
  merged.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  merged.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
  merged.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  merged.computeBoundingSphere();
  return merged;
}

export const vertexMaterial = new THREE.MeshStandardMaterial({
  vertexColors: true,
  roughness: 0.9,
  metalness: 0.02,
  flatShading: true,
});

/* ------------------------------------------------------------------ */
/* Explorer (player)                                                   */
/* ------------------------------------------------------------------ */

export function createExplorer() {
  const root = new THREE.Group();
  root.name = "explorer";

  const rig = group(root, [0, 0, 0], "rig");

  const MAT = {
    jacket: lambert(0x18b9a8, { roughness: 0.72 }),
    jacketDark: lambert(0x0d867f, { roughness: 0.78 }),
    sleeve: lambert(0x159c90, { roughness: 0.8 }),
    skin: lambert(0xeec39b, { roughness: 0.9 }),
    skinDark: lambert(0xd8a077, { roughness: 0.9 }),
    shorts: lambert(0x243247, { roughness: 0.85 }),
    cap: lambert(0xff6f3f, { roughness: 0.7 }),
    capDark: lambert(0xd94e29, { roughness: 0.75 }),
    pack: lambert(0xd6a34c, { roughness: 0.85 }),
    packDark: lambert(0x9a7130, { roughness: 0.9 }),
    boot: lambert(0x2a2f3a, { roughness: 0.8 }),
    bootSole: lambert(0xd7ff00, { roughness: 0.55, emissive: 0x465200, emissiveIntensity: 0.4 }),
    eye: lambert(0x1a1c22, { roughness: 0.45 }),
    scarf: lambert(0xffc247, { roughness: 0.7 }),
    metal: lambert(0xbfd2cf, { roughness: 0.4, metalness: 0.6 }),
    glow: new THREE.MeshBasicMaterial({ color: 0x7df9ff }),
  };

  const hips = group(rig, [0, 0.9, 0], "hips");

  const torso = mesh(GEO.sphere, MAT.jacket, [0, 0.31, 0], [0, 0, 0], [0.29, 0.36, 0.24]);
  hips.add(torso);
  const chest = mesh(GEO.sphere, MAT.jacket, [0, 0.47, 0.005], [0, 0, 0], [0.3, 0.22, 0.24]);
  hips.add(chest);
  const belt = mesh(GEO.cylinder, MAT.packDark, [0, 0.05, 0], [0, 0, 0], [0.25, 0.07, 0.22]);
  hips.add(belt);
  const beltBuckle = mesh(GEO.box, MAT.metal, [0, 0.05, 0.215], [0, 0, 0], [0.08, 0.07, 0.03]);
  hips.add(beltBuckle);

  // Cargo backpack + little glowing gadget.
  const pack = mesh(GEO.box, MAT.pack, [0, 0.36, -0.28], [0, 0, 0], [0.38, 0.42, 0.2]);
  hips.add(pack);
  const packTop = mesh(GEO.cylinder, MAT.packDark, [0, 0.6, -0.28], [0, 0, Math.PI / 2], [0.1, 0.42, 0.1]);
  hips.add(packTop);
  const packFlap = mesh(GEO.box, MAT.packDark, [0, 0.36, -0.39], [0, 0, 0], [0.3, 0.16, 0.05]);
  hips.add(packFlap);
  const gadget = mesh(GEO.box, MAT.glow, [0.23, 0.38, -0.24], [0, 0.2, 0], [0.035, 0.11, 0.05]);
  hips.add(gadget);
  const strapL = mesh(GEO.box, MAT.packDark, [-0.16, 0.42, 0.01], [0, 0, 0.15], [0.07, 0.5, 0.05]);
  hips.add(strapL);
  const strapR = mesh(GEO.box, MAT.packDark, [0.16, 0.42, 0.01], [0, 0, -0.15], [0.07, 0.5, 0.05]);
  hips.add(strapR);

  // Scarf ring + two flowing tails.
  const scarfRing = mesh(GEO.torus, MAT.scarf, [0, 0.63, 0.01], [Math.PI / 2, 0, 0], [0.17, 0.17, 0.17]);
  hips.add(scarfRing);
  const scarfPivot = group(hips, [0, 0.63, -0.06], "scarf");
  const scarfTailA = mesh(GEO.box, MAT.scarf, [0, -0.1, -0.13], [0.15, 0, 0.2], [0.1, 0.5, 0.025]);
  const scarfTailB = mesh(GEO.box, MAT.scarf, [0.08, -0.06, -0.2], [0.3, 0.2, -0.2], [0.08, 0.4, 0.02]);
  scarfPivot.add(scarfTailA, scarfTailB);

  // Head.
  const headPivot = group(hips, [0, 0.68, 0.02], "head");
  const head = mesh(GEO.sphere, MAT.skin, [0, 0.06, 0], [0, 0, 0], [0.205, 0.22, 0.2]);
  headPivot.add(head);
  const earL = mesh(GEO.sphereLow, MAT.skinDark, [-0.2, 0.06, 0], [0, 0, 0], [0.045, 0.06, 0.04]);
  const earR = mesh(GEO.sphereLow, MAT.skinDark, [0.2, 0.06, 0], [0, 0, 0], [0.045, 0.06, 0.04]);
  headPivot.add(earL, earR);
  const eyeL = mesh(GEO.sphereLow, MAT.eye, [-0.075, 0.09, 0.175], [0, 0, 0], [0.028, 0.036, 0.02]);
  const eyeR = mesh(GEO.sphereLow, MAT.eye, [0.075, 0.09, 0.175], [0, 0, 0], [0.028, 0.036, 0.02]);
  headPivot.add(eyeL, eyeR);
  const smile = mesh(GEO.torus, MAT.eye, [0, 0.005, 0.185], [0, 0, Math.PI], [0.05, 0.05, 0.05]);
  smile.scale.z = 0.3;
  headPivot.add(smile);
  const cap = mesh(GEO.sphere, MAT.cap, [0, 0.2, -0.01], [0, 0, 0], [0.218, 0.12, 0.21]);
  headPivot.add(cap);
  const capBrim = mesh(GEO.box, MAT.capDark, [0, 0.16, 0.19], [-0.2, 0, 0], [0.24, 0.035, 0.17]);
  headPivot.add(capBrim);
  const capButton = mesh(GEO.sphereLow, MAT.capDark, [0, 0.29, -0.01], [0, 0, 0], [0.025, 0.02, 0.025]);
  headPivot.add(capButton);

  // Arms.
  function makeArm(side) {
    const shoulder = group(hips, [side * 0.31, 0.51, 0], side < 0 ? "armL" : "armR");
    const upper = new THREE.Mesh(limbGeometry(0.068, 0.058, 0.31), MAT.sleeve);
    upper.castShadow = true;
    shoulder.add(upper);
    const elbow = group(shoulder, [0, -0.31, 0]);
    const forearm = new THREE.Mesh(limbGeometry(0.055, 0.048, 0.28), MAT.skin);
    forearm.castShadow = true;
    elbow.add(forearm);
    const hand = mesh(GEO.sphereLow, MAT.skinDark, [0, -0.3, 0.015], [0, 0, 0], [0.062, 0.075, 0.062]);
    elbow.add(hand);
    return { shoulder, elbow };
  }
  const armL = makeArm(-1);
  const armR = makeArm(1);

  // Legs.
  function makeLeg(side) {
    const hip = group(rig, [side * 0.15, 0.9, 0], side < 0 ? "legL" : "legR");
    const thigh = new THREE.Mesh(limbGeometry(0.095, 0.075, 0.43), MAT.shorts);
    thigh.castShadow = true;
    hip.add(thigh);
    const knee = group(hip, [0, -0.43, 0]);
    const shin = new THREE.Mesh(limbGeometry(0.07, 0.055, 0.39), MAT.skin);
    shin.castShadow = true;
    knee.add(shin);
    const ankle = group(knee, [0, -0.39, 0]);
    const boot = mesh(GEO.box, MAT.boot, [0, -0.045, 0.055], [0, 0, 0], [0.16, 0.12, 0.29]);
    ankle.add(boot);
    const sole = mesh(GEO.box, MAT.bootSole, [0, -0.105, 0.06], [0, 0, 0], [0.165, 0.025, 0.295]);
    ankle.add(sole);
    const toe = mesh(GEO.sphereLow, MAT.boot, [0, -0.045, 0.21], [0, 0, 0], [0.08, 0.06, 0.07]);
    ankle.add(toe);
    return { hip, knee, ankle, boot };
  }
  const legL = makeLeg(-1);
  const legR = makeLeg(1);

  // Soft contact shadow (also readable when real shadows are disabled).
  const contact = new THREE.Mesh(
    new THREE.CircleGeometry(0.62, 24),
    new THREE.MeshBasicMaterial({
      color: 0x000000,
      transparent: true,
      opacity: 0.16,
      depthWrite: false,
    }),
  );
  contact.rotation.x = -Math.PI / 2;
  contact.position.y = 0.015;
  contact.renderOrder = 1;
  root.add(contact);
  markNoShadow(contact);

  const state = {
    phase: 0,
    slide: 0,
    lean: 0,
    land: 0,
    stumble: 0,
    blink: 0,
    look: 0,
    wave: 0,
    lastMode: "menu",
  };

  /**
   * @param {number} dt
   * @param {{mode: string, speed: number, grounded: boolean, sliding: number, sprinting: boolean, stumble: number, landImpact: number, tilt: number}} view
   */
  function update(dt, view) {
    state.phase += dt * (3.4 + view.speed * 0.66);
    state.slide = damp(state.slide, clamp(view.sliding ?? 0, 0, 1), 13, dt);
    state.lean = damp(state.lean, clamp(view.tilt ?? 0, -1, 1), 7, dt);
    state.land = Math.max(0, state.land - dt * 5.5);
    if (view.landImpact > 0) {
      state.land = 1;
    }
    state.stumble = Math.max(0, (view.stumble ?? 0) - dt);
    state.look = damp(state.look, Math.sin(state.phase * 0.27) * 0.22, 2.2, dt);

    const intro = view.mode === "intro";
    const running = view.mode === "running";
    const t = view.time ?? 0;
    const speedRatio = clamp((view.speed - 13) / 12, 0, 1);
    const stride = running || intro ? 1 : 0;
    const swing = Math.sin(state.phase);
    const swingB = Math.sin(state.phase + Math.PI);
    const slide = state.slide;
    const stumble = state.stumble;

    // Whole rig: bob, forward lean, slide lean-back, stumble wobble.
    const bob = running ? Math.abs(Math.cos(state.phase * 2)) * 0.045 * (1 - slide) : Math.sin(t * 1.7) * 0.012;
    rig.position.y = bob + slide * 0.27;
    rig.rotation.x = running ? -0.07 - speedRatio * 0.09 - slide * 1.0 : Math.sin(t * 0.8) * 0.006;
    rig.rotation.z =
      state.lean * 0.09 * (view.grounded ? 1 : 0.4) + Math.sin(state.stumble * 28) * 0.12 * (stumble > 0 ? 1 : 0);
    rig.scale.y = 1 - state.land * 0.055;
    rig.scale.x = 1 + state.land * 0.03;

    // Legs.
    const legSwing = (0.6 + speedRatio * 0.32) * stride;
    const legLTarget = view.grounded && !slide ? swing * legSwing : lerp(0.55, 1.1, clamp(view.vy ?? 0, -1, 1));
    const legRTarget = view.grounded && !slide ? swingB * legSwing : lerp(0.35, 1.2, clamp(-(view.vy ?? 0), -1, 1));
    legL.hip.rotation.x = damp(legL.hip.rotation.x, legLTarget - slide * 0.28, 22, dt);
    legR.hip.rotation.x = damp(legR.hip.rotation.x, legRTarget - slide * 0.12, 22, dt);
    legL.knee.rotation.x = damp(
      legL.knee.rotation.x,
      view.grounded ? Math.max(0.08, -swing) * 1.25 * stride - slide * 0.15 : 1.35,
      20,
      dt,
    );
    legR.knee.rotation.x = damp(
      legR.knee.rotation.x,
      view.grounded ? Math.max(0.08, -swingB) * 1.25 * stride - slide * 0.35 : 1.5,
      20,
      dt,
    );
    legL.ankle.rotation.x = damp(legL.ankle.rotation.x, view.grounded ? swing * -0.18 : 0.35, 18, dt);
    legR.ankle.rotation.x = damp(legR.ankle.rotation.x, view.grounded ? swingB * -0.18 : 0.35, 18, dt);

    // Arms opposite legs. Intro: friendly wave on the right arm.
    const wave = intro ? 1 : 0;
    state.wave = damp(state.wave, wave, 4, dt);
    const armSwing = 0.7 + speedRatio * 0.45;
    armL.shoulder.rotation.x = damp(armL.shoulder.rotation.x, slide * 0.5 + swing * armSwing * stride, 18, dt);
    armR.shoulder.rotation.x = damp(armR.shoulder.rotation.x, slide * 0.35 + swingB * armSwing * stride, 18, dt);
    armL.shoulder.rotation.z = damp(armL.shoulder.rotation.z, 0.12 + state.wave * 0.1, 10, dt);
    armR.shoulder.rotation.z = damp(
      armR.shoulder.rotation.z,
      -0.12 - state.wave * 2.2 + Math.sin(t * 7) * 0.28 * state.wave,
      10,
      dt,
    );
    armL.elbow.rotation.x = damp(armL.elbow.rotation.x, -0.55 - speedRatio * 0.55 - slide * 0.3, 16, dt);
    armR.elbow.rotation.x = damp(armR.elbow.rotation.x, -0.55 - speedRatio * 0.55 - state.wave * 0.5, 16, dt);

    // Torso/head counter motion.
    hips.rotation.y = Math.sin(state.phase) * 0.09 * stride * (1 - slide);
    hips.rotation.z = -state.lean * 0.04;
    headPivot.rotation.x = (running ? -0.06 : 0.04) + Math.sin(state.phase * 2 + 0.6) * 0.03 * stride;
    headPivot.rotation.y = intro ? Math.sin(t * 0.6) * 0.34 : -state.lean * 0.08;
    headPivot.rotation.z = stumble > 0 ? Math.sin(stumble * 30) * 0.15 : 0;

    // Scarf flutter.
    scarfPivot.rotation.x = 0.32 + Math.sin(t * 7.5) * 0.12 + speedRatio * 0.32;
    scarfPivot.rotation.z = Math.sin(t * 5.6) * 0.13;
    scarfTailA.rotation.x = 0.15 + Math.sin(t * 9) * 0.16;
    scarfTailB.rotation.x = 0.25 + Math.sin(t * 8 + 1.2) * 0.2;

    // Blink (head tip in the intro).
    state.blink = Math.max(0, state.blink - dt);
    if (intro && Math.random() < dt * 0.25) {
      state.blink = 0.12;
    }
    const eyeScale = state.blink > 0 ? 0.15 : 1;
    eyeL.scale.y = 0.036 * eyeScale;
    eyeR.scale.y = 0.036 * eyeScale;
    const jumpHeight = clamp(view.y ?? 0, 0, 4);
    contact.material.opacity = 0.06 + (1 - clamp(jumpHeight / 2.2, 0, 1)) * 0.12;
    contact.position.y = 0.015 - jumpHeight;
    contact.scale.setScalar(1 + jumpHeight * 0.3);
  }

  return { root, update };
}

/* ------------------------------------------------------------------ */
/* T-Rex                                                               */
/* ------------------------------------------------------------------ */

export function createTRex() {
  const root = new THREE.Group();
  root.name = "t-rex";

  const MAT = {
    body: lambert(0x4f6b3e, { roughness: 0.82 }),
    bodyDark: lambert(0x3c5533, { roughness: 0.86 }),
    belly: lambert(0xa8a06b, { roughness: 0.9 }),
    spine: lambert(0xc9652c, { roughness: 0.7 }),
    claw: lambert(0xeadfc2, { roughness: 0.5 }),
    tooth: lambert(0xf3ead2, { roughness: 0.42 }),
    mouth: lambert(0x541f22, { roughness: 0.75 }),
    eye: new THREE.MeshStandardMaterial({
      color: 0xffb21f,
      emissive: 0xff7a00,
      emissiveIntensity: 2.2,
      roughness: 0.3,
    }),
    eyePupil: new THREE.MeshBasicMaterial({ color: 0x140a04 }),
    nostril: lambert(0x2b1c1a, { roughness: 0.9 }),
    scar: lambert(0x2c3c26, { roughness: 0.9 }),
  };

  const rig = group(root, [0, 0, 0], "rex-rig");

  // Body.
  const body = mesh(GEO.sphere, MAT.body, [0, 2.62, -0.45], [0, 0, 0], [1.32, 1.45, 2.15]);
  rig.add(body);
  const chest = mesh(GEO.sphere, MAT.body, [0, 2.9, 1.0], [0, 0, 0], [1.1, 1.25, 1.2]);
  rig.add(chest);
  const belly = mesh(GEO.sphere, MAT.belly, [0, 2.25, 0.25], [0, 0, 0], [0.92, 0.7, 1.75]);
  rig.add(belly);
  const hipBone = mesh(GEO.sphere, MAT.bodyDark, [0, 2.9, -1.45], [0, 0, 0], [0.85, 0.9, 0.85]);
  rig.add(hipBone);

  // Neck + head pivot.
  const neck = group(rig, [0, 3.32, 1.5], "neck");
  const neckMesh = mesh(GEO.cylinder, MAT.body, [0, 0.33, 0.08], [0.42, 0, 0], [0.62, 0.95, 0.7]);
  neck.add(neckMesh);
  const neckPlate = mesh(GEO.cone, MAT.spine, [0, 0.44, -0.18], [-0.7, 0, 0], [0.22, 0.5, 0.18]);
  neck.add(neckPlate);

  const headPivot = group(neck, [0, 0.8, 0.42], "rex-head");
  const skull = mesh(GEO.box, MAT.body, [0, 0.1, 0.2], [0, 0, 0], [1.02, 0.82, 1.05]);
  headPivot.add(skull);
  const skullTop = mesh(GEO.sphere, MAT.body, [0, 0.35, 0.15], [0, 0, 0], [0.56, 0.34, 0.72]);
  headPivot.add(skullTop);
  const snout = mesh(GEO.box, MAT.body, [0, 0.0, 0.95], [0, 0, 0], [0.82, 0.52, 0.92]);
  headPivot.add(snout);
  const snoutTop = mesh(GEO.box, MAT.bodyDark, [0, 0.25, 0.7], [0.12, 0, 0], [0.72, 0.24, 0.62]);
  headPivot.add(snoutTop);
  const browL = mesh(GEO.box, MAT.bodyDark, [-0.4, 0.36, 0.42], [0.18, -0.08, 0.16], [0.34, 0.18, 0.5]);
  const browR = mesh(GEO.box, MAT.bodyDark, [0.4, 0.36, 0.42], [0.18, 0.08, -0.16], [0.34, 0.18, 0.5]);
  headPivot.add(browL, browR);
  const crestL = mesh(GEO.cone, MAT.spine, [-0.4, 0.52, -0.1], [-0.2, 0, 0.28], [0.14, 0.42, 0.14]);
  const crestR = mesh(GEO.cone, MAT.spine, [0.4, 0.52, -0.1], [-0.2, 0, -0.28], [0.14, 0.42, 0.14]);
  headPivot.add(crestL, crestR);

  const eyeL = mesh(GEO.sphereLow, MAT.eye, [-0.43, 0.19, 0.56], [0, 0, 0], [0.115, 0.09, 0.085]);
  const eyeR = mesh(GEO.sphereLow, MAT.eye, [0.43, 0.19, 0.56], [0, 0, 0], [0.115, 0.09, 0.085]);
  const pupilL = mesh(GEO.sphereLow, MAT.eyePupil, [-0.45, 0.19, 0.635], [0, 0, 0], [0.035, 0.065, 0.02]);
  const pupilR = mesh(GEO.sphereLow, MAT.eyePupil, [0.45, 0.19, 0.635], [0, 0, 0], [0.035, 0.065, 0.02]);
  eyeL.userData.noShadow = true;
  eyeR.userData.noShadow = true;
  markNoShadow(eyeL);
  markNoShadow(eyeR);
  headPivot.add(eyeL, eyeR, pupilL, pupilR);

  const nostrilL = mesh(GEO.sphereLow, MAT.nostril, [-0.23, 0.13, 1.38], [0, 0, 0], [0.05, 0.04, 0.03]);
  const nostrilR = mesh(GEO.sphereLow, MAT.nostril, [0.23, 0.13, 1.38], [0, 0, 0], [0.05, 0.04, 0.03]);
  headPivot.add(nostrilL, nostrilR);

  // Lower jaw.
  const jawPivot = group(headPivot, [0, -0.24, 0.15], "jaw");
  const jaw = mesh(GEO.box, MAT.bodyDark, [0, -0.12, 0.62], [0, 0, 0], [0.76, 0.25, 1.2]);
  jawPivot.add(jaw);
  const mouth = mesh(GEO.box, MAT.mouth, [0, 0.01, 0.6], [0, 0, 0], [0.62, 0.1, 1.07]);
  jawPivot.add(mouth);
  for (let i = 0; i < 6; i += 1) {
    const z = 0.15 + i * 0.17;
    const side = i % 2 === 0 ? -1 : 1;
    const tooth = mesh(GEO.cone, MAT.tooth, [side * 0.26, 0.07, z], [Math.PI, 0, 0], [0.055, 0.2, 0.055]);
    const toothLow = mesh(GEO.cone, MAT.tooth, [side * 0.22, -0.23, z + 0.06], [0, 0, 0], [0.045, 0.16, 0.045]);
    jawPivot.add(tooth, toothLow);
  }
  for (let i = 0; i < 3; i += 1) {
    const scar = mesh(GEO.box, MAT.scar, [-0.98, 2.94 + i * 0.2, 0.3 - i * 0.12], [0, 0, 0.5], [0.04, 0.32, 0.05]);
    rig.add(scar);
  }

  // Tiny arms.
  function makeArm(side) {
    const shoulder = group(rig, [side * 0.95, 3.08, 1.15], side < 0 ? "rex-armL" : "rex-armR");
    shoulder.rotation.z = side * 0.25;
    const upper = new THREE.Mesh(limbGeometry(0.13, 0.1, 0.52), MAT.bodyDark);
    upper.castShadow = true;
    shoulder.add(upper);
    shoulder.rotation.x = -0.55;
    const elbow = group(shoulder, [0, -0.52, 0]);
    elbow.rotation.x = 1.35;
    const forearm = new THREE.Mesh(limbGeometry(0.1, 0.08, 0.42), MAT.body);
    forearm.castShadow = true;
    elbow.add(forearm);
    const hand = mesh(GEO.sphereLow, MAT.bodyDark, [0, -0.4, 0], [0, 0, 0], [0.1, 0.09, 0.12]);
    elbow.add(hand);
    for (let c = 0; c < 2; c += 1) {
      const claw = mesh(GEO.cone, MAT.claw, [0, -0.46, 0.08 + c * 0.06], [0.8, 0, 0], [0.03, 0.17, 0.03]);
      elbow.add(claw);
    }
    return { shoulder, elbow };
  }
  const armL = makeArm(-1);
  const armR = makeArm(1);

  // Legs.
  function makeLeg(side) {
    const hip = group(rig, [side * 0.85, 2.5, -0.25], side < 0 ? "rex-legL" : "rex-legR");
    hip.rotation.z = side * 0.14;
    const thigh = new THREE.Mesh(limbGeometry(0.62, 0.4, 1.28), MAT.body);
    thigh.castShadow = true;
    hip.add(thigh);
    const knee = group(hip, [0, -1.3, 0]);
    const shin = new THREE.Mesh(limbGeometry(0.36, 0.24, 1.1), MAT.bodyDark);
    shin.castShadow = true;
    knee.add(shin);
    const ankle = group(knee, [0, -1.1, 0]);
    const foot = mesh(GEO.box, MAT.bodyDark, [0, -0.07, 0.43], [0, 0, 0], [0.56, 0.26, 1.05]);
    ankle.add(foot);
    for (let i = -1; i <= 1; i += 1) {
      const toe = mesh(GEO.box, MAT.bodyDark, [i * 0.17, -0.1, 0.92], [0, i * 0.1, 0], [0.15, 0.16, 0.38]);
      const claw = mesh(GEO.cone, MAT.claw, [i * 0.17, -0.1, 1.16], [Math.PI / 2, 0, 0], [0.065, 0.24, 0.065]);
      ankle.add(toe, claw);
    }
    return { hip, knee, ankle };
  }
  const legL = makeLeg(-1);
  const legR = makeLeg(1);

  // Tail: a chain of segments with a delayed swish.
  const tailPivots = [];
  const tailRoot = group(rig, [0, 2.55, -2.15], "tail");
  let parent = tailRoot;
  let tailRadius = 0.62;
  for (let i = 0; i < 7; i += 1) {
    const segment = group(parent, [0, 0, i === 0 ? 0 : -0.78]);
    const length = 0.92 - i * 0.04;
    const geo = tapered(length, tailRadius, tailRadius * 0.68, 8);
    geo.rotateX(Math.PI / 2);
    geo.translate(0, 0, -length / 2);
    const tailMesh = new THREE.Mesh(geo, i % 2 === 0 ? MAT.body : MAT.bodyDark);
    tailMesh.castShadow = true;
    segment.add(tailMesh);
    if (i < 5) {
      const spike = mesh(
        GEO.cone,
        MAT.spine,
        [0, tailRadius * 0.95, -length * 0.45],
        [-0.15, 0, 0],
        [0.11, 0.28 - i * 0.02, 0.1],
      );
      segment.add(spike);
    }
    tailPivots.push(segment);
    parent = segment;
    tailRadius *= 0.78;
  }

  // Dorsal plates.
  const plates = [];
  for (let i = 0; i < 7; i += 1) {
    const z = 1.3 - i * 0.6;
    const scale = 0.34 - Math.abs(i - 2) * 0.035;
    const plate = mesh(GEO.cone, MAT.spine, [0, 3.98 - i * 0.1, z], [-0.18, 0, 0], [0.17, scale, 0.12]);
    plate.castShadow = true;
    rig.add(plate);
    plates.push(plate);
  }

  const anim = {
    phase: 0,
    roar: 0,
    eat: 0,
    blink: 0,
    lunge: 0,
    jaw: 0,
    headLift: 0,
  };

  function roar() {
    anim.roar = 1;
  }

  function setLunge(value) {
    anim.lunge = clamp(value, 0, 1);
  }

  /**
   * @param {number} dt
   * @param {{mode: string, speed: number, gap: number, eating: boolean, caught: boolean, danger: number}} view
   */
  function update(dt, view) {
    anim.roar = Math.max(0, anim.roar - dt * 0.85);
    anim.eat = damp(anim.eat, view.eating ? 1 : 0, 5, dt);
    anim.lunge = damp(anim.lunge, view.caught ? 1 : 0, 9, dt);
    anim.phase += dt * (view.mode === "intro" ? 2.2 : 4 + view.speed * 0.3);
    anim.blink = Math.max(0, anim.blink - dt);
    if (Math.random() < dt * 0.18) {
      anim.blink = 0.11;
    }

    const t = view.time ?? 0;
    const roar = anim.roar;
    const eat = anim.eat;
    const lunge = anim.lunge;
    const speedRatio = clamp((view.speed - 13) / 11, 0, 1);
    const stride = Math.sin(anim.phase);
    const strideB = Math.sin(anim.phase + Math.PI);
    const running = view.mode === "running" || view.mode === "caught";

    const jawTarget = Math.max(
      eat > 0.1 ? 0.42 + Math.abs(Math.sin(t * 11)) * 0.45 : 0,
      roar * 1.05,
      view.danger > 0.55 ? 0.18 + Math.sin(t * 3.1) * 0.08 : 0.05,
      lunge * 0.9,
    );
    anim.jaw = damp(anim.jaw, jawTarget, 10, dt);
    jawPivot.rotation.x = 0.05 + anim.jaw * 0.62;

    // Body: heavy gallop, low predatory crouch as the gap closes.
    const crouch = clamp(view.danger, 0, 1) * 0.28 + lunge * 0.24 - eat * 0.15;
    const bob = running ? Math.abs(Math.cos(anim.phase * 2)) * 0.12 : Math.sin(t * 1.25) * 0.04;
    rig.position.y = bob - crouch * 0.45 + 0.2;
    rig.rotation.x = running ? -0.04 + speedRatio * 0.07 + crouch * 0.18 : Math.sin(t * 0.7) * 0.01;
    rig.rotation.z = Math.sin(anim.phase) * 0.035 * (running ? 1 : 0.2) + roar * Math.sin(t * 24) * 0.008;
    rig.rotation.y = Math.sin(anim.phase * 0.5) * 0.025;

    // Legs — slower, heavier stomps than the explorer.
    const legAmp = running ? 0.64 + speedRatio * 0.2 : 0.1;
    legL.hip.rotation.x = damp(legL.hip.rotation.x, stride * legAmp - eat * 0.45, 9, dt);
    legR.hip.rotation.x = damp(legR.hip.rotation.x, strideB * legAmp - eat * 0.45, 9, dt);
    legL.knee.rotation.x = damp(legL.knee.rotation.x, Math.max(0, -stride) * 1.05 + 0.12 + eat * 0.35, 9, dt);
    legR.knee.rotation.x = damp(legR.knee.rotation.x, Math.max(0, -strideB) * 1.05 + 0.12 + eat * 0.35, 9, dt);
    legL.ankle.rotation.x = damp(legL.ankle.rotation.x, stride * -0.25, 9, dt);
    legR.ankle.rotation.x = damp(legR.ankle.rotation.x, strideB * -0.25, 9, dt);

    // Arms tuck while running, wiggle during a roar.
    armL.shoulder.rotation.x = -0.55 + Math.sin(t * 5) * 0.06 * roar;
    armR.shoulder.rotation.x = -0.55 + Math.sin(t * 5 + 1) * 0.06 * roar;
    armL.elbow.rotation.x = 1.35 + Math.sin(t * 7) * 0.15 * roar;
    armR.elbow.rotation.x = 1.35 + Math.sin(t * 7 + 2) * 0.15 * roar;

    // Head: look at the runner, rear back for the roar, dive down to eat.
    const headLift = roar * 0.5 + lunge * 0.15;
    anim.headLift = damp(anim.headLift, headLift, 8, dt);
    headPivot.position.y = 0.8 + anim.headLift * 0.32 - eat * 0.62;
    headPivot.position.z = 0.42 + anim.headLift * 0.12 + eat * 0.3;
    headPivot.rotation.x = 0.06 + anim.headLift * -0.42 + eat * 0.95 + crouch * 0.15;
    headPivot.rotation.y = Math.sin(t * 0.8) * 0.08 * (1 - roar) + Math.sin(t * 18) * 0.02 * roar;
    headPivot.rotation.z = Math.sin(t * 0.6) * 0.03;

    // Tail wave with a phase delay down the chain.
    for (let i = 0; i < tailPivots.length; i += 1) {
      const delay = i * 0.42;
      tailPivots[i].rotation.y =
        Math.sin(anim.phase * 0.75 - delay) * (0.055 + i * 0.012) * (1 + speedRatio * 0.5) +
        (eat > 0.2 ? Math.sin(t * 9 - delay) * 0.12 * eat : 0);
      tailPivots[i].rotation.x = Math.sin(anim.phase * 0.5 - delay) * 0.02;
    }

    // Dorsal plates breathe/scintillate.
    for (let i = 0; i < plates.length; i += 1) {
      plates[i].rotation.z = Math.sin(t * 1.4 + i * 0.5) * 0.04;
    }

    // Eyes: blink + glow pulse when close.
    const eyeScale = anim.blink > 0 ? 0.2 : 1;
    eyeL.scale.y = 0.09 * eyeScale;
    eyeR.scale.y = 0.09 * eyeScale;
    MAT.eye.emissiveIntensity = 1.6 + clamp(view.danger, 0, 1) * 2.8 + roar * 2;

    // Neck / chest lean into the lunge.
    neck.rotation.x = -0.1 + lunge * 0.15;
  }

  return { root, update, roar, setLunge };
}

/* ------------------------------------------------------------------ */
/* Hazards                                                             */
/* ------------------------------------------------------------------ */

const HAZARD_MAT = {
  rock: vertexMaterial,
  bone: vertexMaterial,
  log: vertexMaterial,
  ptero: lambert(0x5f3333, { roughness: 0.82, flatShading: true }),
  pteroWing: lambert(0x6c3a34, { roughness: 0.86, flatShading: true, side: THREE.DoubleSide }),
  pteroBeak: lambert(0xe3c785, { roughness: 0.5 }),
  pteroEye: new THREE.MeshBasicMaterial({ color: 0xffd05a }),
  lava: new THREE.MeshStandardMaterial({
    color: 0xff5e1f,
    emissive: 0xff4a00,
    emissiveIntensity: 2.4,
    roughness: 0.4,
  }),
  lavaColumn: new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uOpacity: { value: 0.0 },
      uColorHot: { value: new THREE.Color(0xffd27a) },
      uColorCool: { value: new THREE.Color(0xff5a1f) },
    },
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      varying vec3 vNormalW;
      void main() {
        vUv = uv;
        vNormalW = normalize(mat3(modelMatrix) * normal);
        gl_Position = projectionMatrix * viewMatrix * modelMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform float uTime;
      uniform float uOpacity;
      uniform vec3 uColorHot;
      uniform vec3 uColorCool;
      varying vec2 vUv;
      varying vec3 vNormalW;
      float hash(float n) { return fract(sin(n * 91.3458) * 47453.5453); }
      float noise(float x) { return mix(hash(floor(x)), hash(floor(x) + 1.0), smoothstep(0.0, 1.0, fract(x))); }
      void main() {
        // Vertical fade: hot at the vent, dissolving into mist at the top.
        float rise = clamp(vUv.y, 0.0, 1.0);
        float body = smoothstep(0.0, 0.22, rise) * pow(1.0 - rise, 0.85);
        // Animated streaks + billowing grain.
        float streak = noise(vUv.y * 7.0 - uTime * 3.4 + vUv.x * 4.0);
        float grain = noise(vUv.y * 21.0 - uTime * 6.2 + hash(vUv.x * 13.0) * 4.0);
        float fresnel = pow(1.0 - abs(normalize(vNormalW).z), 1.4);
        float alpha = body * (0.42 + streak * 0.42 + grain * 0.16 + fresnel * 0.25) * uOpacity;
        if (alpha < 0.004) discard;
        vec3 color = mix(uColorCool, uColorHot, smoothstep(0.0, 0.85, 1.0 - rise) * (0.55 + streak * 0.45));
        gl_FragColor = vec4(color, clamp(alpha, 0.0, 0.85));
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
  }),
  steam: new THREE.MeshBasicMaterial({
    color: 0xffb27a,
    transparent: true,
    opacity: 0.25,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  }),
};

let rockGeometry;
let logGeometry;
let geyserColumnGeometry;
let ribGeometry;
let ventGeometry;

/**
 * WebGPU 경계에서만 호출한다. GLSL lavaColumn ShaderMaterial을 동등한 TSL
 * 머티리얼로 교체한다. 지오서 모델 생성 전에 한 번만 적용하면 된다.
 * @param {{backend:string, three:object, tsl:object}} gfx
 */
export async function upgradeHazardMaterialsForWebGPU(gfx) {
  const { createWebGpuLavaColumn } = await import("./webgpu-materials.js");
  HAZARD_MAT.lavaColumn = createWebGpuLavaColumn(gfx.three, gfx.tsl);
}

function getRockGeometry() {
  if (!rockGeometry) {
    rockGeometry = buildMergedGeometry([
      { geometry: GEO.ico, color: 0x707868, position: [0, 0.62, 0], rotation: [0.4, 0.2, 0.1], scale: [1.05, 0.95, 0.85] },
      { geometry: GEO.ico, color: 0x5d665a, position: [-0.7, 0.45, 0.35], rotation: [0.1, 0.8, 0.2], scale: [0.62, 0.68, 0.6] },
      { geometry: GEO.ico, color: 0x7e8774, position: [0.62, 0.4, -0.3], rotation: [0.8, 0.1, 0.3], scale: [0.55, 0.5, 0.6] },
      { geometry: GEO.ico, color: 0x4c5a4a, position: [0.1, 0.3, 0.7], rotation: [0.2, 0.5, 0.6], scale: [0.38, 0.34, 0.4] },
      { geometry: GEO.ico, color: 0x6d8a4a, position: [0.2, 1.15, 0.05], rotation: [0.6, 0.3, 0.1], scale: [0.36, 0.14, 0.34] },
    ]);
  }
  return rockGeometry;
}

function getLogGeometry() {
  if (!logGeometry) {
    logGeometry = buildMergedGeometry([
      { geometry: GEO.cylinder, color: 0x5b422d, position: [0, 0.42, 0], rotation: [0, 0, Math.PI / 2], scale: [0.36, 2.8, 0.36] },
      { geometry: GEO.cylinder, color: 0x7a5a3a, position: [0, 0.42, 0], rotation: [0, 0, Math.PI / 2], scale: [0.37, 0.08, 0.37] },
      { geometry: GEO.cylinder, color: 0x4b3624, position: [-0.9, 0.65, 0.25], rotation: [0.2, 0, 1.1], scale: [0.12, 0.65, 0.12] },
      { geometry: GEO.cylinder, color: 0x4b3624, position: [0.85, 0.6, -0.3], rotation: [-0.3, 0, 1.9], scale: [0.1, 0.55, 0.1] },
      { geometry: GEO.ico, color: 0x587c3e, position: [0.55, 0.68, 0.02], rotation: [0, 0.4, 0], scale: [0.55, 0.1, 0.3] },
      { geometry: GEO.ico, color: 0x4a7038, position: [-0.8, 0.58, -0.1], rotation: [0.3, 0, 0.2], scale: [0.4, 0.09, 0.25] },
    ]);
  }
  return logGeometry;
}

function ribCurveGeometry() {
  if (!ribGeometry) {
    const parts = [
      { geometry: GEO.cylinder, color: 0xd8cfb2, position: [-4.25, 1.7, 0], rotation: [0, 0, 0], scale: [0.25, 3.4, 0.25] },
      { geometry: GEO.cylinder, color: 0xcfc5a7, position: [4.25, 1.7, 0], rotation: [0, 0, 0], scale: [0.25, 3.4, 0.25] },
      { geometry: GEO.cylinder, color: 0xe1d8bb, position: [0, 3.35, 0], rotation: [0, 0, Math.PI / 2], scale: [0.28, 8.5, 0.28] },
      { geometry: GEO.sphereLow, color: 0xe8e0c4, position: [-4.25, 3.35, 0], scale: [0.36, 0.36, 0.36] },
      { geometry: GEO.sphereLow, color: 0xe8e0c4, position: [4.25, 3.35, 0], scale: [0.36, 0.36, 0.36] },
    ];
    const ribXs = [-3.1, -1.55, 0, 1.55, 3.1];
    for (let i = 0; i < ribXs.length; i += 1) {
      const x = ribXs[i];
      const curve = new THREE.CatmullRomCurve3([
        new THREE.Vector3(x, 3.3, -0.1),
        new THREE.Vector3(x * 0.94, 2.55, 0.15),
        new THREE.Vector3(x * 0.82, 1.85, 0.05),
        new THREE.Vector3(x * 0.7, 1.5, -0.2),
      ]);
      const tube = new THREE.TubeGeometry(curve, 8, 0.13 - Math.abs(x) * 0.012, 6, false);
      parts.push({ geometry: tube, color: i % 2 === 0 ? 0xd9d0b3 : 0xcec4a5 });
      parts.push({
        geometry: GEO.cone,
        color: 0xe8e0c4,
        position: [x * 0.7, 1.42, -0.2],
        rotation: [Math.PI, 0, 0],
        scale: [0.16, 0.32, 0.16],
      });
      parts.push({
        geometry: GEO.sphereLow,
        color: 0xbab08f,
        position: [x, 3.3, -0.1],
        scale: [0.22, 0.22, 0.22],
      });
    }
    // Small hanging moss / ancient rune stones.
    parts.push({ geometry: GEO.ico, color: 0x6b8a4a, position: [-2.4, 2.55, -0.1], scale: [0.2, 0.1, 0.2] });
    parts.push({ geometry: GEO.ico, color: 0x6b8a4a, position: [2.2, 2.2, -0.05], scale: [0.18, 0.08, 0.18] });
    ribGeometry = buildMergedGeometry(parts);
  }
  return ribGeometry;
}

function getVentGeometry() {
  if (!ventGeometry) {
    ventGeometry = buildMergedGeometry([
      { geometry: GEO.cylinder, color: 0x2d2524, position: [0, 0.11, 0], scale: [1.15, 0.22, 1.15] },
      { geometry: GEO.ico, color: 0x3b2f2c, position: [-0.8, 0.25, 0.15], rotation: [0.3, 0, 0.2], scale: [0.5, 0.42, 0.55] },
      { geometry: GEO.ico, color: 0x352a28, position: [0.75, 0.24, -0.2], rotation: [0.6, 0.4, 0], scale: [0.46, 0.38, 0.5] },
      { geometry: GEO.ico, color: 0x4a372f, position: [0.1, 0.28, 0.72], rotation: [0.2, 0.8, 0], scale: [0.35, 0.28, 0.34] },
      { geometry: GEO.cylinder, color: 0xff5d1e, position: [0, 0.17, 0], scale: [0.72, 0.1, 0.72] },
    ]);
  }
  return ventGeometry;
}

function createRibs() {
  const root = new THREE.Group();
  const bones = new THREE.Mesh(ribCurveGeometry(), HAZARD_MAT.bone);
  bones.castShadow = true;
  bones.receiveShadow = true;
  root.add(bones);
  const dust = new THREE.Mesh(
    new THREE.PlaneGeometry(8.5, 2.2),
    new THREE.MeshBasicMaterial({ color: 0x0b0f12, transparent: true, opacity: 0.16, depthWrite: false }),
  );
  dust.rotation.x = -Math.PI / 2;
  dust.position.y = 0.02;
  root.add(dust);
  markNoShadow(dust);
  return root;
}

function createPtero() {
  const root = new THREE.Group();
  const body = mesh(GEO.cone, HAZARD_MAT.ptero, [0, 2.1, 0], [Math.PI / 2, 0, 0], [0.36, 1.5, 0.3]);
  root.add(body);
  const neck = mesh(GEO.cylinder, HAZARD_MAT.ptero, [0, 2.17, 0.85], [0.55, 0, 0], [0.16, 0.62, 0.16]);
  root.add(neck);
  const head = mesh(GEO.box, HAZARD_MAT.ptero, [0, 2.35, 1.23], [0, 0, 0], [0.3, 0.3, 0.5]);
  root.add(head);
  const beak = mesh(GEO.cone, HAZARD_MAT.pteroBeak, [0, 2.31, 1.63], [Math.PI / 2, 0, 0], [0.1, 0.55, 0.1]);
  root.add(beak);
  const crest = mesh(GEO.cone, HAZARD_MAT.ptero, [0, 2.55, 1.15], [-0.5, 0, 0], [0.08, 0.35, 0.2]);
  root.add(crest);
  const eyeL = mesh(GEO.sphereLow, HAZARD_MAT.pteroEye, [-0.12, 2.42, 1.4], [0, 0, 0], [0.03, 0.03, 0.02]);
  const eyeR = mesh(GEO.sphereLow, HAZARD_MAT.pteroEye, [0.12, 2.42, 1.4], [0, 0, 0], [0.03, 0.03, 0.02]);
  root.add(eyeL, eyeR);
  markNoShadow(eyeL);
  markNoShadow(eyeR);

  const wingShape = new THREE.Shape();
  wingShape.moveTo(0, 0);
  wingShape.lineTo(1.8, 0.22);
  wingShape.lineTo(1.45, -0.15);
  wingShape.lineTo(0.55, -0.22);
  wingShape.lineTo(0, -0.07);
  wingShape.closePath();
  const wingGeometry = new THREE.ExtrudeGeometry(wingShape, {
    depth: 0.05,
    bevelEnabled: false,
    steps: 1,
  });
  wingGeometry.translate(0, 0, -0.025);

  const wingL = new THREE.Group();
  wingL.position.set(-0.18, 2.24, 0.15);
  const wl = new THREE.Mesh(wingGeometry, HAZARD_MAT.pteroWing);
  wl.castShadow = true;
  wingL.add(wl);
  wingL.rotation.y = Math.PI;
  const wingR = new THREE.Group();
  wingR.position.set(0.18, 2.24, 0.15);
  const wr = new THREE.Mesh(wingGeometry, HAZARD_MAT.pteroWing);
  wr.castShadow = true;
  wingR.add(wr);
  root.add(wingL, wingR);
  const anim = { phase: Math.random() * Math.PI * 2 };
  function update(dt, time, info) {
    anim.phase += dt * (5.2 + (info?.speed ?? 15) * 0.08);
    const flap = Math.sin(anim.phase);
    wingL.rotation.z = -0.22 + flap * 0.55;
    wingR.rotation.z = 0.22 - flap * 0.55;
    wingL.rotation.x = 0.1 + Math.cos(anim.phase) * 0.08;
    wingR.rotation.x = 0.1 + Math.cos(anim.phase) * 0.08;
    root.position.y = Math.sin(anim.phase * 0.45) * 0.16;
    body.rotation.z = Math.sin(anim.phase * 0.5) * 0.04;
  }
  return { root, update };
}

function createGeyser() {
  const root = new THREE.Group();
  const vent = new THREE.Mesh(getVentGeometry(), HAZARD_MAT.bone);
  vent.castShadow = true;
  vent.receiveShadow = true;
  root.add(vent);
  const core = new THREE.Mesh(GEO.sphereLow, HAZARD_MAT.lava);
  core.scale.set(0.62, 0.16, 0.62);
  core.position.y = 0.24;
  root.add(core);
  // Open-ended tube: caps would read as a solid drum in the middle of the jet.
  if (!geyserColumnGeometry) {
    geyserColumnGeometry = new THREE.CylinderGeometry(0.5, 0.34, 1, 14, 6, true);
  }
  const column = new THREE.Mesh(geyserColumnGeometry, HAZARD_MAT.lavaColumn);
  column.scale.set(0.62, 1, 0.62);
  column.position.y = 2.4;
  column.visible = false;
  root.add(column);
  const steam = new THREE.Mesh(GEO.sphere, HAZARD_MAT.steam);
  steam.scale.set(1.3, 0.5, 1.3);
  steam.position.y = 0.55;
  steam.visible = false;
  root.add(steam);
  markNoShadow(column);
  markNoShadow(steam);

  let burst = 0;
  function update(dt, time, info) {
    const warning = Boolean(info?.warning);
    const erupting = Boolean(info?.erupting);
    burst = damp(burst, erupting ? 1 : 0, erupting ? 16 : 5, dt);
    column.visible = burst > 0.04;
    steam.visible = warning || burst > 0.04;
    const height = 0.4 + burst * 4.6;
    column.scale.set(1.05 + burst * 0.55, height, 1.05 + burst * 0.55);
    column.position.y = height * 0.5 + 0.2;
    column.rotation.y += dt * 1.2;
    column.material.uniforms.uTime.value = time;
    column.material.uniforms.uOpacity.value = 0.16 + burst * 0.62;
    steam.scale.set(1 + burst * 0.8, 0.5 + burst * 0.4, 1 + burst * 0.8);
    steam.position.y = 0.4 + burst * 0.8;
    steam.material.opacity = warning ? 0.12 + Math.sin(time * 12) * 0.04 + burst * 0.2 : 0.05;
    core.material.emissiveIntensity = 1.2 + (warning ? 1.8 : 0) + burst * 2.5;
    const coreScale = 0.55 + Math.sin(time * 8) * 0.04 + burst * 0.1;
    core.scale.set(coreScale, 0.16, coreScale);
  }
  return { root, update };
}

export function createHazardModel(type) {
  let item;
  if (type === "rock") {
    const root = new THREE.Group();
    const rock = new THREE.Mesh(getRockGeometry(), HAZARD_MAT.rock);
    rock.castShadow = true;
    rock.receiveShadow = true;
    root.add(rock);
    item = { root, update: () => {} };
  } else if (type === "log") {
    const root = new THREE.Group();
    const log = new THREE.Mesh(getLogGeometry(), HAZARD_MAT.log);
    log.castShadow = true;
    log.receiveShadow = true;
    root.add(log);
    item = { root, update: () => {} };
  } else if (type === "ribs") {
    item = { root: createRibs(), update: () => {} };
  } else if (type === "ptero") {
    item = createPtero();
  } else if (type === "geyser") {
    item = createGeyser();
  } else {
    throw new Error(`Unknown hazard type: ${type}`);
  }
  item.type = type;
  return item;
}

/* ------------------------------------------------------------------ */
/* Pickups                                                             */
/* ------------------------------------------------------------------ */

const AMBER_COLOR = 0xffb52e;
export const amberGeometry = new THREE.OctahedronGeometry(0.3, 0);
export const amberHaloGeometry = new THREE.OctahedronGeometry(0.52, 0);
export const amberMaterial = new THREE.MeshStandardMaterial({
  color: AMBER_COLOR,
  emissive: 0xff8a00,
  emissiveIntensity: 1.8,
  roughness: 0.22,
  metalness: 0.25,
  flatShading: true,
});
export const amberHaloMaterial = new THREE.MeshBasicMaterial({
  color: AMBER_COLOR,
  transparent: true,
  opacity: 0.18,
  blending: THREE.AdditiveBlending,
  depthWrite: false,
  side: THREE.DoubleSide,
});

const PICKUP_MAT = {
  meat: lambert(0xb8512f, { roughness: 0.78 }),
  meatDark: lambert(0x8c3520, { roughness: 0.82 }),
  bone: lambert(0xf0e6cb, { roughness: 0.55 }),
  ring: new THREE.MeshBasicMaterial({
    color: 0xffb52e,
    transparent: true,
    opacity: 0.42,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    side: THREE.DoubleSide,
  }),
  shield: new THREE.MeshStandardMaterial({
    color: 0x4fe8ff,
    emissive: 0x0a9fbf,
    emissiveIntensity: 1.7,
    roughness: 0.24,
    metalness: 0.2,
    flatShading: true,
  }),
  shieldRing: new THREE.MeshBasicMaterial({
    color: 0x76f3ff,
    transparent: true,
    opacity: 0.55,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    side: THREE.DoubleSide,
  }),
};

export function createMeatPickup() {
  const root = new THREE.Group();
  const meat = mesh(GEO.sphere, PICKUP_MAT.meat, [0, 0, 0], [0, 0, 0.25], [0.33, 0.4, 0.33]);
  root.add(meat);
  const meatTop = mesh(GEO.sphere, PICKUP_MAT.meatDark, [0, 0.22, -0.02], [0, 0, 0], [0.2, 0.16, 0.2]);
  root.add(meatTop);
  const bone = mesh(GEO.cylinder, PICKUP_MAT.bone, [0, -0.3, 0], [0.25, 0, 0], [0.06, 0.34, 0.06]);
  root.add(bone);
  const knobA = mesh(GEO.sphereLow, PICKUP_MAT.bone, [-0.07, -0.46, -0.04], [0, 0, 0], [0.08, 0.08, 0.08]);
  const knobB = mesh(GEO.sphereLow, PICKUP_MAT.bone, [0.07, -0.44, 0.03], [0, 0, 0], [0.08, 0.07, 0.08]);
  root.add(knobA, knobB);
  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.55, 0.015, 6, 32), PICKUP_MAT.ring);
  ring.rotation.x = Math.PI / 2;
  root.add(ring);
  markNoShadow(ring);
  const anim = { phase: Math.random() * Math.PI * 2 };
  function update(dt, time) {
    anim.phase += dt;
    ring.rotation.z += dt * 0.8;
    ring.scale.setScalar(1 + Math.sin(time * 3 + anim.phase) * 0.06);
    root.rotation.y = Math.sin(time * 1.4 + anim.phase) * 0.4;
  }
  return { root, update, kind: "meat" };
}

export function createShieldPickup() {
  const root = new THREE.Group();
  const crystal = mesh(GEO.octa, PICKUP_MAT.shield, [0, 0, 0], [0, 0, 0], [0.3, 0.42, 0.3]);
  root.add(crystal);
  const inner = mesh(GEO.octa, PICKUP_MAT.shieldRing, [0, 0, 0], [0, 0, 0], [0.42, 0.42, 0.42]);
  markNoShadow(inner);
  root.add(inner);
  const ringA = new THREE.Mesh(new THREE.TorusGeometry(0.62, 0.018, 6, 32), PICKUP_MAT.shieldRing);
  ringA.rotation.x = Math.PI / 2;
  root.add(ringA);
  const ringB = new THREE.Mesh(new THREE.TorusGeometry(0.5, 0.015, 6, 32), PICKUP_MAT.shieldRing);
  ringB.rotation.set(Math.PI / 2, 0, 0.8);
  root.add(ringB);
  markNoShadow(ringA);
  markNoShadow(ringB);
  const anim = { phase: Math.random() * Math.PI * 2 };
  function update(dt, time) {
    anim.phase += dt;
    crystal.rotation.y += dt * 1.3;
    inner.rotation.y -= dt * 0.8;
    ringA.rotation.z += dt * 1.5;
    ringB.rotation.z -= dt * 1.1;
    ringA.scale.setScalar(1 + Math.sin(time * 2.4 + anim.phase) * 0.05);
    root.rotation.y = Math.sin(time * 0.9 + anim.phase) * 0.2;
  }
  return { root, update, kind: "shield" };
}

/* Shield bubble that surrounds the explorer while the power-up is charged. */
export function createShieldBubble() {
  const root = new THREE.Group();
  const bubble = new THREE.Mesh(
    new THREE.SphereGeometry(1.15, 24, 16),
    new THREE.MeshBasicMaterial({
      color: 0x6ff4ff,
      transparent: true,
      opacity: 0.11,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
    }),
  );
  bubble.position.y = 0.92;
  root.add(bubble);
  const rim = new THREE.Mesh(
    new THREE.TorusGeometry(1.06, 0.012, 6, 48),
    new THREE.MeshBasicMaterial({
      color: 0x9ffcff,
      transparent: true,
      opacity: 0.45,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    }),
  );
  rim.position.y = 0.92;
  rim.rotation.x = Math.PI / 2;
  root.add(rim);
  markNoShadow(root);
  root.visible = false;
  let flash = 0;
  function update(dt, time, active) {
    root.visible = active || flash > 0.02;
    if (active) {
      bubble.material.opacity = 0.075 + Math.sin(time * 3.6) * 0.02;
      rim.rotation.z += dt * 0.7;
      rim.position.y = 0.92 + Math.sin(time * 1.6) * 0.12;
      rim.scale.setScalar(1 + Math.sin(time * 2.2) * 0.03);
    }
    if (flash > 0) {
      flash = Math.max(0, flash - dt * 2.4);
      bubble.material.opacity = flash * 0.55;
      bubble.scale.setScalar(1 + (1 - flash) * 1.4);
    }
  }
  function shatter() {
    flash = 1;
    bubble.scale.setScalar(1);
  }
  return { root, update, shatter };
}

/* Exported for the game's instanced amber field. */
export const amberAssets = {
  geometry: amberGeometry,
  haloGeometry: amberHaloGeometry,
  material: amberMaterial,
  haloMaterial: amberHaloMaterial,
};
