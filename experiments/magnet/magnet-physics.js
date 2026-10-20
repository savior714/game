/*!
 * AIDEN MAGNET LAB — 자석 실험실 물리 엔진
 *
 * 화면(DOM/canvas)과 완전히 분리된 순수 계산 모듈이다.
 * Node에서 그대로 require해 자석 인력·척력, 철 물건의 끌림, 극 위치를 검증한다.
 */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.MagnetPhysics = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const DEFAULTS = Object.freeze({
    magnetLength: 158,
    magnetWidth: 52,
    magnetForce: 5.2e6,
    magnetSoftening: 225,
    magnetDamping: 3.1,
    magnetAngularDamping: 4.4,
    magnetMaxSpeed: 720,
    magnetMaxOmega: 8,
    itemForce: 2.8e7,
    itemSoftening: 900,
    itemReach: 280,
    itemFadeStart: 195,
    itemMaxAccel: 6400,
    itemMaxSpeed: 940,
    itemFriction: 1.7,
    capturePadding: 7,
    captureSidePadding: 5,
    boundaryPadding: 8,
    substeps: 2,
  });

  function clamp(value, min, max) {
    return value < min ? min : value > max ? max : value;
  }

  function createMagnet(options) {
    const opts = options || {};
    return {
      id: opts.id == null ? 0 : opts.id,
      x: opts.x || 0,
      y: opts.y || 0,
      angle: opts.angle || 0,
      power: opts.power == null ? 1 : opts.power,
      length: opts.length || DEFAULTS.magnetLength,
      width: opts.width || DEFAULTS.magnetWidth,
      vx: 0,
      vy: 0,
      omega: 0,
      dragged: false,
    };
  }

  function createItem(options) {
    const opts = options || {};
    return {
      id: opts.id == null ? 0 : opts.id,
      kind: opts.kind || "clip",
      x: opts.x || 0,
      y: opts.y || 0,
      angle: opts.angle || 0,
      radius: opts.radius == null ? 11 : opts.radius,
      magnetic: opts.magnetic === true,
      vx: 0,
      vy: 0,
      capturedBy: null,
      localX: 0,
      localY: 0,
      localAngle: 0,
      dragged: false,
    };
  }

  /** 막대자석의 두 극. sign +1 = N극(빨강), -1 = S극(파랑). */
  function poleList(magnet) {
    const cos = Math.cos(magnet.angle);
    const sin = Math.sin(magnet.angle);
    const half = magnet.length / 2;
    return [
      { sign: 1, x: magnet.x + cos * half, y: magnet.y + sin * half },
      { sign: -1, x: magnet.x - cos * half, y: magnet.y - sin * half },
    ];
  }

  function fieldAt(x, y, magnets, skipId) {
    let bx = 0;
    let by = 0;
    for (let i = 0; i < magnets.length; i += 1) {
      const magnet = magnets[i];
      if (skipId != null && magnet.id === skipId) continue;
      const half = magnet.length / 2;
      const cos = Math.cos(magnet.angle);
      const sin = Math.sin(magnet.angle);
      const q = magnet.power;

      let dx = x - (magnet.x + cos * half);
      let dy = y - (magnet.y + sin * half);
      let r2 = dx * dx + dy * dy + DEFAULTS.magnetSoftening;
      let inv = q / (r2 * Math.sqrt(r2));
      bx += dx * inv;
      by += dy * inv;

      dx = x - (magnet.x - cos * half);
      dy = y - (magnet.y - sin * half);
      r2 = dx * dx + dy * dy + DEFAULTS.magnetSoftening;
      inv = -q / (r2 * Math.sqrt(r2));
      bx += dx * inv;
      by += dy * inv;
    }
    return { x: bx, y: by, magnitude: Math.sqrt(bx * bx + by * by) };
  }

  function worldToLocal(magnet, x, y) {
    const cos = Math.cos(magnet.angle);
    const sin = Math.sin(magnet.angle);
    const dx = x - magnet.x;
    const dy = y - magnet.y;
    return { x: dx * cos + dy * sin, y: -dx * sin + dy * cos };
  }

  function localToWorld(magnet, x, y) {
    const cos = Math.cos(magnet.angle);
    const sin = Math.sin(magnet.angle);
    return {
      x: magnet.x + x * cos - y * sin,
      y: magnet.y + x * sin + y * cos,
    };
  }

  function findMagnet(magnets, id) {
    for (let i = 0; i < magnets.length; i += 1) {
      if (magnets[i].id === id) return magnets[i];
    }
    return null;
  }

  /** 가까운 극까지의 거리(자석 몸통 밖 기준). 놀이 안내에 사용한다. */
  function distanceToMagnet(magnet, x, y) {
    const local = worldToLocal(magnet, x, y);
    const dx = Math.max(Math.abs(local.x) - magnet.length / 2, 0);
    const dy = Math.max(Math.abs(local.y) - magnet.width / 2, 0);
    return Math.sqrt(dx * dx + dy * dy);
  }

  function integrateMagnet(magnet, fx, fy, torque, dt) {
    if (magnet.dragged) {
      magnet.vx = 0;
      magnet.vy = 0;
      magnet.omega = 0;
      return;
    }
    magnet.vx += fx * dt;
    magnet.vy += fy * dt;

    const damping = Math.exp(-DEFAULTS.magnetDamping * dt);
    magnet.vx *= damping;
    magnet.vy *= damping;

    const speed = Math.sqrt(magnet.vx * magnet.vx + magnet.vy * magnet.vy);
    if (speed > DEFAULTS.magnetMaxSpeed) {
      const scale = DEFAULTS.magnetMaxSpeed / speed;
      magnet.vx *= scale;
      magnet.vy *= scale;
    }

    const inertia = (magnet.length * magnet.length + magnet.width * magnet.width) / 12;
    magnet.omega += (torque / inertia) * dt;
    magnet.omega *= Math.exp(-DEFAULTS.magnetAngularDamping * dt);
    magnet.omega = clamp(magnet.omega, -DEFAULTS.magnetMaxOmega, DEFAULTS.magnetMaxOmega);

    magnet.x += magnet.vx * dt;
    magnet.y += magnet.vy * dt;
    magnet.angle += magnet.omega * dt;
  }

  function clampMagnetToBounds(magnet, bounds) {
    const cos = Math.cos(magnet.angle);
    const sin = Math.sin(magnet.angle);
    const halfW = (Math.abs(cos) * magnet.length + Math.abs(sin) * magnet.width) / 2;
    const halfH = (Math.abs(sin) * magnet.length + Math.abs(cos) * magnet.width) / 2;
    const pad = DEFAULTS.boundaryPadding;
    const minX = halfW + pad;
    const maxX = Math.max(minX, bounds.width - halfW - pad);
    const minY = halfH + pad;
    const maxY = Math.max(minY, bounds.height - halfH - pad);

    if (magnet.x < minX) {
      magnet.x = minX;
      magnet.vx = Math.abs(magnet.vx) * 0.18;
    } else if (magnet.x > maxX) {
      magnet.x = maxX;
      magnet.vx = -Math.abs(magnet.vx) * 0.18;
    }
    if (magnet.y < minY) {
      magnet.y = minY;
      magnet.vy = Math.abs(magnet.vy) * 0.18;
    } else if (magnet.y > maxY) {
      magnet.y = maxY;
      magnet.vy = -Math.abs(magnet.vy) * 0.18;
    }
  }

  function bodyCircles(magnet) {
    const cos = Math.cos(magnet.angle);
    const sin = Math.sin(magnet.angle);
    const offset = magnet.length * 0.33;
    const radius = magnet.width * 0.52;
    return [
      { x: magnet.x + cos * offset, y: magnet.y + sin * offset, r: radius },
      { x: magnet.x - cos * offset, y: magnet.y - sin * offset, r: radius },
    ];
  }

  function resolveMagnetCollisions(magnets) {
    for (let i = 0; i < magnets.length; i += 1) {
      for (let j = i + 1; j < magnets.length; j += 1) {
        const a = magnets[i];
        const b = magnets[j];
        const circlesA = bodyCircles(a);
        const circlesB = bodyCircles(b);

        for (let ca = 0; ca < circlesA.length; ca += 1) {
          for (let cb = 0; cb < circlesB.length; cb += 1) {
            const da = circlesA[ca];
            const db = circlesB[cb];
            let dx = db.x - da.x;
            let dy = db.y - da.y;
            let dist = Math.sqrt(dx * dx + dy * dy);
            const minDist = da.r + db.r;
            if (dist >= minDist) continue;
            if (dist < 0.001) {
              dx = 1;
              dy = 0;
              dist = 1;
            }
            const nx = dx / dist;
            const ny = dy / dist;
            const overlap = minDist - dist;
            const moveA = !a.dragged;
            const moveB = !b.dragged;

            if (moveA && moveB) {
              a.x -= nx * overlap * 0.5;
              a.y -= ny * overlap * 0.5;
              b.x += nx * overlap * 0.5;
              b.y += ny * overlap * 0.5;
            } else if (moveB) {
              b.x += nx * overlap;
              b.y += ny * overlap;
            } else if (moveA) {
              a.x -= nx * overlap;
              a.y -= ny * overlap;
            }

            const relative = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny;
            if (relative < 0) {
              if (moveA && moveB) {
                const impulse = -relative * 0.5;
                a.vx -= nx * impulse;
                a.vy -= ny * impulse;
                b.vx += nx * impulse;
                b.vy += ny * impulse;
              } else if (moveB) {
                b.vx += nx * -relative;
                b.vy += ny * -relative;
              } else if (moveA) {
                a.vx -= nx * -relative;
                a.vy -= ny * -relative;
              }
            }
          }
        }
      }
    }
  }

  /**
   * 자석끼리 미는 힘과 돌림힘을 계산해 한 프레임 진행한다.
   * 자석은 서로 다른 극이면 끌어당기고, 같은 극이면 밀어낸다.
   */
  function stepMagnets(magnets, dt, bounds, options) {
    const opts = options || {};
    const steps = opts.substeps || DEFAULTS.substeps;
    const h = dt / steps;

    for (let s = 0; s < steps; s += 1) {
      const forces = magnets.map(function () {
        return { fx: 0, fy: 0, torque: 0 };
      });

      for (let i = 0; i < magnets.length; i += 1) {
        for (let j = i + 1; j < magnets.length; j += 1) {
          const a = magnets[i];
          const b = magnets[j];
          const polesA = poleList(a);
          const polesB = poleList(b);
          let fax = 0;
          let fay = 0;
          let fbx = 0;
          let fby = 0;
          let ta = 0;
          let tb = 0;

          for (let pa = 0; pa < polesA.length; pa += 1) {
            for (let pb = 0; pb < polesB.length; pb += 1) {
              const poleA = polesA[pa];
              const poleB = polesB[pb];
              const dx = poleB.x - poleA.x;
              const dy = poleB.y - poleA.y;
              const d2 = dx * dx + dy * dy + DEFAULTS.magnetSoftening;
              const strength = DEFAULTS.magnetForce * a.power * b.power;
              const inv = (strength * poleA.sign * poleB.sign) / (d2 * Math.sqrt(d2));
              const fx = dx * inv;
              const fy = dy * inv;

              fbx += fx;
              fby += fy;
              tb += (poleB.x - b.x) * fy - (poleB.y - b.y) * fx;

              fax -= fx;
              fay -= fy;
              ta -= (poleA.x - a.x) * fy - (poleA.y - a.y) * fx;
            }
          }

          forces[i].fx += fax;
          forces[i].fy += fay;
          forces[i].torque += ta;
          forces[j].fx += fbx;
          forces[j].fy += fby;
          forces[j].torque += tb;
        }
      }

      for (let i = 0; i < magnets.length; i += 1) {
        const magnet = magnets[i];
        integrateMagnet(magnet, forces[i].fx, forces[i].fy, forces[i].torque, h);
        if (bounds) clampMagnetToBounds(magnet, bounds);
      }

      resolveMagnetCollisions(magnets);
    }
  }

  /** 철로 된 물체가 각 극에서 받는 인력. 극에 가까울수록 훨씬 세다. */
  function itemAcceleration(item, magnets) {
    let ax = 0;
    let ay = 0;
    for (let i = 0; i < magnets.length; i += 1) {
      const poles = poleList(magnets[i]);
      for (let p = 0; p < poles.length; p += 1) {
        const dx = poles[p].x - item.x;
        const dy = poles[p].y - item.y;
        const d2 = dx * dx + dy * dy + DEFAULTS.itemSoftening;
        const d = Math.sqrt(d2);
        if (d >= DEFAULTS.itemReach) continue;
        const fade =
          d <= DEFAULTS.itemFadeStart
            ? 1
            : 1 - (d - DEFAULTS.itemFadeStart) / (DEFAULTS.itemReach - DEFAULTS.itemFadeStart);
        const strength = (DEFAULTS.itemForce * magnets[i].power * fade * fade) / d2;
        ax += (dx / d) * strength;
        ay += (dy / d) * strength;
      }
    }
    const magnitude = Math.sqrt(ax * ax + ay * ay);
    if (magnitude > DEFAULTS.itemMaxAccel) {
      const scale = DEFAULTS.itemMaxAccel / magnitude;
      ax *= scale;
      ay *= scale;
    }
    return { x: ax, y: ay };
  }

  function captureItem(item, magnet) {
    if (!item.magnetic || item.capturedBy != null) return false;
    const local = worldToLocal(magnet, item.x, item.y);
    const halfLength = magnet.length / 2;
    const halfWidth = magnet.width / 2;
    const reachX = halfLength + item.radius * 0.7 + DEFAULTS.capturePadding;
    const reachY = halfWidth + item.radius * 0.55 + DEFAULTS.captureSidePadding;

    if (Math.abs(local.x) > reachX || Math.abs(local.y) > reachY) return false;

    const end = local.x >= 0 ? 1 : -1;
    if (Math.abs(local.x) > halfLength * 0.72) {
      item.localX = end * (halfLength + item.radius * 0.34);
      item.localY = clamp(local.y * 0.55, -halfWidth * 0.8, halfWidth * 0.8);
    } else {
      item.localX = clamp(local.x, -halfLength * 0.9, halfLength * 0.9);
      item.localY = (local.y >= 0 ? 1 : -1) * (halfWidth + item.radius * 0.45);
    }
    item.capturedBy = magnet.id;
    item.localAngle = item.angle - magnet.angle;
    item.vx = 0;
    item.vy = 0;
    return true;
  }

  function releaseItem(item) {
    item.capturedBy = null;
    item.vx = 0;
    item.vy = 0;
  }

  /** 같은 자석에 붙은 물건끼리 겹치지 않게 살짝 밀어 준다. */
  function separateCaptured(items, magnets) {
    for (let iter = 0; iter < 2; iter += 1) {
      for (let i = 0; i < items.length; i += 1) {
        const a = items[i];
        if (a.capturedBy == null) continue;
        const magnet = findMagnet(magnets, a.capturedBy);
        if (!magnet) continue;
        for (let j = i + 1; j < items.length; j += 1) {
          const b = items[j];
          if (b.capturedBy !== a.capturedBy) continue;
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const minDist = a.radius + b.radius + 1.5;
          if (dist >= minDist) continue;

          const cos = Math.cos(magnet.angle);
          const sin = Math.sin(magnet.angle);
          const along = dx * cos + dy * sin >= 0 ? 1 : -1;
          const push = (minDist - dist) * 0.5;
          const limit = magnet.length * 0.46;
          a.localX = clamp(a.localX - along * push, -limit, limit);
          b.localX = clamp(b.localX + along * push, -limit, limit);
          const worldA = localToWorld(magnet, a.localX, a.localY);
          const worldB = localToWorld(magnet, b.localX, b.localY);
          a.x = worldA.x;
          a.y = worldA.y;
          b.x = worldB.x;
          b.y = worldB.y;
        }
      }
    }
  }

  function syncCaptured(items, magnets) {
    for (let i = 0; i < items.length; i += 1) {
      const item = items[i];
      if (item.capturedBy == null) continue;
      const magnet = findMagnet(magnets, item.capturedBy);
      if (!magnet) {
        releaseItem(item);
        continue;
      }
      const world = localToWorld(magnet, item.localX, item.localY);
      item.x = world.x;
      item.y = world.y;
      item.angle = magnet.angle + item.localAngle;
      item.vx = 0;
      item.vy = 0;
    }
  }

  function clampItemToBounds(item, bounds) {
    const pad = item.radius + DEFAULTS.boundaryPadding;
    if (item.x < pad) {
      item.x = pad;
      item.vx = Math.abs(item.vx) * 0.28;
    } else if (item.x > bounds.width - pad) {
      item.x = bounds.width - pad;
      item.vx = -Math.abs(item.vx) * 0.28;
    }
    if (item.y < pad) {
      item.y = pad;
      item.vy = Math.abs(item.vy) * 0.28;
    } else if (item.y > bounds.height - pad) {
      item.y = bounds.height - pad;
      item.vy = -Math.abs(item.vy) * 0.28;
    }
  }

  function stepItems(items, magnets, dt, bounds, options) {
    const opts = options || {};
    const steps = opts.substeps || DEFAULTS.substeps;
    const h = dt / steps;

    for (let s = 0; s < steps; s += 1) {
      for (let i = 0; i < items.length; i += 1) {
        const item = items[i];
        if (item.capturedBy != null || item.dragged) continue;

        if (item.magnetic) {
          const accel = itemAcceleration(item, magnets);
          item.vx += accel.x * h;
          item.vy += accel.y * h;
          const damping = Math.exp(-DEFAULTS.itemFriction * h);
          item.vx *= damping;
          item.vy *= damping;
          const speed = Math.sqrt(item.vx * item.vx + item.vy * item.vy);
          if (speed > DEFAULTS.itemMaxSpeed) {
            const scale = DEFAULTS.itemMaxSpeed / speed;
            item.vx *= scale;
            item.vy *= scale;
          }
        } else {
          item.vx *= Math.exp(-6 * h);
          item.vy *= Math.exp(-6 * h);
        }

        item.x += item.vx * h;
        item.y += item.vy * h;
        if (bounds) clampItemToBounds(item, bounds);

        if (item.magnetic) {
          for (let m = 0; m < magnets.length; m += 1) {
            if (captureItem(item, magnets[m])) break;
          }
        }
      }
    }
    syncCaptured(items, magnets);
    separateCaptured(items, magnets);
  }

  function seedRandom(seed) {
    let state = seed >>> 0;
    return function random() {
      state = (state * 1664525 + 1013904223) >>> 0;
      return state / 4294967296;
    };
  }

  return {
    DEFAULTS,
    clamp,
    createMagnet,
    createItem,
    poleList,
    fieldAt,
    worldToLocal,
    localToWorld,
    distanceToMagnet,
    stepMagnets,
    itemAcceleration,
    captureItem,
    releaseItem,
    syncCaptured,
    separateCaptured,
    stepItems,
    seedRandom,
    findMagnet,
  };
});
