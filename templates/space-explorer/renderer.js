import { BASE_ORBIT, ORBIT_STEP, TWO_PI } from "./state.js";

export function createRenderer(canvas, ctx, state, planets) {
  function resizeCanvas() {
    if (!canvas) return;
    const parent = canvas.parentElement;
    if (!parent) return;
    const rect = parent.getBoundingClientRect();
    const width = Math.max(640, Math.floor(rect.width - 2));
    const height = Math.max(420, Math.floor(width * 0.56));
    canvas.width = width;
    canvas.height = height;
  }

  function drawOrbit(cx, cy, orbitRadius) {
    if (state.quality === "low" && orbitRadius > BASE_ORBIT + ORBIT_STEP * 5) {
      return;
    }
    ctx.beginPath();
    ctx.arc(cx, cy, orbitRadius, 0, TWO_PI);
    ctx.strokeStyle = "rgba(255,255,255,0.12)";
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  function drawBody(x, y, radius, color) {
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, TWO_PI);
    ctx.fillStyle = color;
    ctx.fill();
  }

  function render() {
    if (!canvas || !ctx) return;
    const { width, height } = canvas;
    const cx = width / 2;
    const cy = height / 2;

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#050918";
    ctx.fillRect(0, 0, width, height);

    if (state.quality === "high") {
      for (let i = 0; i < 36; i += 1) {
        const sx = (i * 97) % width;
        const sy = (i * 53) % height;
        ctx.fillStyle = "rgba(255,255,255,0.35)";
        ctx.fillRect(sx, sy, 1.2, 1.2);
      }
    }

    drawBody(cx, cy, 14, "#ffd166");

    for (const planet of planets) {
      const orbitRadius = BASE_ORBIT + planet.orbitIndex * ORBIT_STEP;
      drawOrbit(cx, cy, orbitRadius);
      const px = cx + Math.cos(planet.angle) * orbitRadius;
      const py = cy + Math.sin(planet.angle) * orbitRadius;
      drawBody(px, py, planet.radius, planet.color);

      if (state.showLabels) {
        ctx.fillStyle = "#d8e0ff";
        ctx.font = state.quality === "high" ? "12px sans-serif" : "10px sans-serif";
        ctx.fillText(planet.name, px + planet.radius + 4, py - planet.radius - 2);
      }
    }
  }

  return { resizeCanvas, render };
}
