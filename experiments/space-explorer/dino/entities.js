/**
 * Pooled 3D entities for the chase: hazards, pickups, instanced amber and the
 * thrown bait projectile. The game owns the simulation descriptors; this layer
 * only maps them onto meshes.
 */

import * as THREE from "../vendor/three/three.module.min.js";
import { HAZARD, REX_LAYER } from "./constants.js";
import { clamp, randRange } from "./util.js";
import {
  amberAssets,
  createHazardModel,
  createMeatPickup,
  createShieldPickup,
} from "./models.js";

const CAPS = Object.freeze({
  rock: 12,
  log: 12,
  ribs: 4,
  ptero: 10,
  geyser: 6,
  shield: 4,
  bait: 4,
  projectile: 3,
});

const AMBER_MAX = 96;

function enableRexLayer(root) {
  root.traverse((object) => {
    object.layers.enable(REX_LAYER);
  });
}

export function createEntityLayer(scene) {
  const pools = new Map();
  const entries = new Map();
  const dummy = new THREE.Object3D();
  const amberList = [];
  const projectiles = [];

  // Instanced amber field: one draw call for the crystals, one for the halos.
  const amberMesh = new THREE.InstancedMesh(amberAssets.geometry, amberAssets.material, AMBER_MAX);
  amberMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  amberMesh.frustumCulled = false;
  amberMesh.castShadow = false;
  amberMesh.receiveShadow = false;
  amberMesh.layers.enable(REX_LAYER);
  amberMesh.count = 0;
  scene.add(amberMesh);

  const haloMesh = new THREE.InstancedMesh(amberAssets.haloGeometry, amberAssets.haloMaterial, AMBER_MAX);
  haloMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  haloMesh.frustumCulled = false;
  haloMesh.renderOrder = 4;
  haloMesh.layers.enable(REX_LAYER);
  haloMesh.count = 0;
  scene.add(haloMesh);

  function getPool(type) {
    let pool = pools.get(type);
    if (!pool) {
      pool = { list: [], cursor: 0, cap: CAPS[type] ?? 6 };
      pools.set(type, pool);
    }
    return pool;
  }

  function acquire(type) {
    const pool = getPool(type);
    for (const item of pool.list) {
      if (!item.busy) {
        item.busy = true;
        return item;
      }
    }
    if (pool.list.length >= pool.cap) {
      return null;
    }
    let built;
    if (type === "bait" || type === "projectile") {
      built = createMeatPickup();
    } else if (type === "shield") {
      built = createShieldPickup();
    } else {
      built = createHazardModel(type);
    }
    built.root.visible = false;
    enableRexLayer(built.root);
    scene.add(built.root);
    const item = { ...built, busy: true, type };
    pool.list.push(item);
    return item;
  }

  function add(descriptor) {
    if (descriptor.kind === "amber") {
      amberList.push(descriptor);
      entries.set(descriptor, { amber: true });
      return;
    }
    const type = descriptor.kind === "hazard" ? descriptor.type : descriptor.kind;
    const view = acquire(type);
    if (!view) {
      descriptor.dead = true;
      return;
    }
    view.root.visible = true;
    view.root.position.set(descriptor.x, 0, descriptor.z);
    entries.set(descriptor, { view, type });
  }

  function remove(descriptor) {
    const entry = entries.get(descriptor);
    if (!entry) {
      return;
    }
    entries.delete(descriptor);
    if (entry.amber) {
      const index = amberList.indexOf(descriptor);
      if (index >= 0) {
        amberList.splice(index, 1);
      }
      return;
    }
    if (entry.view) {
      entry.view.busy = false;
      entry.view.root.visible = false;
    }
  }

  function clear() {
    for (const descriptor of [...entries.keys()]) {
      remove(descriptor);
    }
    amberList.length = 0;
    projectiles.length = 0;
    for (const pool of pools.values()) {
      for (const item of pool.list) {
        item.busy = false;
        item.root.visible = false;
      }
    }
    amberMesh.count = 0;
    haloMesh.count = 0;
  }

  function update(dt, time, playerZ) {
    // Hazards + pickups.
    for (const [descriptor, entry] of entries) {
      if (entry.amber || !entry.view) {
        continue;
      }
      const view = entry.view;
      const behind = playerZ - HAZARD.despawnBehind;
      if (descriptor.z < behind) {
        view.root.visible = false;
        descriptor.dead = true;
        continue;
      }
      view.root.position.set(descriptor.x, 0, descriptor.z);
      if (descriptor.kind !== "hazard") {
        view.update(dt, time);
        view.root.position.y = Math.sin(time * 2.2 + descriptor.z * 0.3) * 0.12;
        continue;
      }
      if (descriptor.type === "ptero") {
        view.update(dt, time, { speed: 12 + Math.sin(time * 0.7) * 3 });
        view.root.position.y = Math.sin(time * 2.1 + descriptor.phase * 5) * 0.08;
      } else if (descriptor.type === "geyser") {
        view.update(dt, time, { warning: descriptor.warning, erupting: descriptor.erupting });
      } else if (descriptor.type === "ribs") {
        view.root.position.y = 0;
      }
      view.root.visible = true;
    }

    // Amber instances.
    let amberCount = 0;
    let haloCount = 0;
    for (const amber of amberList) {
      if (amber.collected) {
        continue;
      }
      const bob = Math.sin(time * 2.4 + amber.z * 0.22) * 0.11;
      const spin = time * 1.35 + amber.z * 0.12;
      dummy.position.set(amber.x, amber.y + bob, amber.z);
      dummy.rotation.set(0.18, spin, 0.12);
      dummy.scale.setScalar(1);
      dummy.updateMatrix();
      amberMesh.setMatrixAt(amberCount, dummy.matrix);
      amberCount += 1;

      const pulse = 1 + Math.sin(time * 3.1 + amber.z * 0.4) * 0.12;
      dummy.rotation.set(0.4, -spin * 0.6, 0);
      dummy.scale.setScalar(pulse);
      dummy.updateMatrix();
      haloMesh.setMatrixAt(haloCount, dummy.matrix);
      haloCount += 1;
    }
    amberMesh.count = amberCount;
    haloMesh.count = haloCount;
    amberMesh.instanceMatrix.needsUpdate = true;
    haloMesh.instanceMatrix.needsUpdate = true;

    // Thrown bait arc.
    for (let i = projectiles.length - 1; i >= 0; i -= 1) {
      const shot = projectiles[i];
      shot.t += dt / shot.duration;
      const t = clamp(shot.t, 0, 1);
      shot.mesh.position.set(
        shot.from.x + (shot.to.x - shot.from.x) * t,
        shot.from.y + (shot.to.y - shot.from.y) * t + Math.sin(t * Math.PI) * shot.arc,
        shot.from.z + (shot.to.z - shot.from.z) * t,
      );
      shot.mesh.rotation.x += dt * 7;
      shot.mesh.rotation.z += dt * 5;
      if (t >= 1) {
        shot.mesh.visible = false;
        shot.mesh.position.y = -999;
        shot.item.busy = false;
        projectiles.splice(i, 1);
        if (shot.onLand) {
          shot.onLand();
        }
      }
    }
  }

  function throwBait(from, to, onLand) {
    const pool = getPool("projectile");
    let item = pool.list.find((candidate) => !candidate.busy);
    if (!item && pool.list.length < pool.cap) {
      item = acquire("bait");
    }
    if (!item) {
      item = pool.list[0] ?? null;
      if (!item) {
        return;
      }
    }
    item.busy = true;
    item.root.visible = true;
    item.root.position.copy(from);
    projectiles.push({
      mesh: item.root,
      item,
      from: from.clone(),
      to: to.clone(),
      t: 0,
      duration: clamp(from.distanceTo(to) / 26, 0.45, 1.1),
      arc: randRange(1.2, 2.4),
      onLand,
    });
  }

  function dispose() {
    scene.remove(amberMesh);
    scene.remove(haloMesh);
    for (const pool of pools.values()) {
      for (const item of pool.list) {
        scene.remove(item.root);
        item.root.traverse((object) => {
          if (object.isMesh) {
            object.geometry?.dispose?.();
            if (Array.isArray(object.material)) {
              object.material.forEach((material) => material.dispose?.());
            } else {
              object.material?.dispose?.();
            }
          }
        });
      }
    }
    pools.clear();
    entries.clear();
    amberList.length = 0;
    projectiles.length = 0;
  }

  return {
    add,
    remove,
    clear,
    update,
    throwBait,
    dispose,
    amberMesh,
    haloMesh,
  };
}
