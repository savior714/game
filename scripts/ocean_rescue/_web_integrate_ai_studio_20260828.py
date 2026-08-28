from __future__ import annotations

import os
from pathlib import Path

BASE = "f984670efa538aa679f65bea729f03dafec5fa66"
AI_HEAD = "9edd0cee4260ad6e79042809835611561c176704"
ROOT = Path(__file__).resolve().parents[2]
AI_ROOT = Path(os.environ["AI_ROOT"]).resolve()

source_base = (AI_ROOT / ".source-base").read_text(encoding="utf-8").strip()
if source_base != BASE:
    raise SystemExit(f"AI Studio source base mismatch: {source_base} != {BASE}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


controller_path = ROOT / "domains/ocean-rescue/src/controllers/launch-travel.ts"
controller = controller_path.read_text(encoding="utf-8")

readiness_block = r'''

// Canonicalized from the AI Studio Sea Turtle Travel Slice authored from
// game@f984670e and recovered at ocean-rescue-ai-studio@9edd0cee.  Keep the
// numeric readiness internal: the child-facing UI only exposes prepared gear.
interface SeaTurtleReadinessSnapshot {
  readonly active: boolean;
  readonly searchlightReady: boolean;
  readonly thrusterReady: boolean;
  readonly cutterReady: boolean;
}

class SeaTurtleReadiness {
  private active = false;
  private value = 0;
  private committedFloor = 0;
  private searchlightReady = false;
  private thrusterReady = false;
  private cutterReady = false;

  start(): void {
    this.active = true;
    this.value = 0;
    this.committedFloor = 0;
    this.searchlightReady = false;
    this.thrusterReady = false;
    this.cutterReady = false;
  }

  stop(): void {
    this.active = false;
  }

  step(deltaMs: number, meaningfulInput: boolean, inCurrent: boolean): void {
    if (!this.active || !finiteNumber(deltaMs) || deltaMs <= 0) {
      return;
    }
    const seconds = Math.min(deltaMs, 50) / 1000;
    if (meaningfulInput) {
      this.add(0.04 * seconds);
    }
    if (inCurrent) {
      this.add(0.08 * seconds);
    }
  }

  onBoost(): void {
    this.add(0.18);
  }

  onPrecisionClear(): void {
    this.add(0.12);
  }

  onScan(): void {
    this.add(0.15);
  }

  onCollision(): void {
    if (!this.active) {
      return;
    }
    this.value = Math.max(this.committedFloor, this.value - 0.12);
    this.commitMilestones();
  }

  getSnapshot(): SeaTurtleReadinessSnapshot {
    return Object.freeze({
      active: this.active,
      searchlightReady: this.searchlightReady,
      thrusterReady: this.thrusterReady,
      cutterReady: this.cutterReady,
    });
  }

  private add(amount: number): void {
    if (!this.active || !finiteNumber(amount) || amount <= 0) {
      return;
    }
    this.value = Math.min(1, Math.max(this.committedFloor, this.value + amount));
    this.commitMilestones();
  }

  private commitMilestones(): void {
    if (!this.searchlightReady && this.value >= 0.33) {
      this.searchlightReady = true;
      this.committedFloor = Math.max(this.committedFloor, 0.33);
    }
    if (!this.thrusterReady && this.value >= 0.66) {
      this.thrusterReady = true;
      this.committedFloor = Math.max(this.committedFloor, 0.66);
    }
    if (!this.cutterReady && this.value >= 0.9) {
      this.cutterReady = true;
      this.committedFloor = Math.max(this.committedFloor, 0.9);
    }
  }
}

const SEA_TURTLE_CURRENT = Object.freeze({
  startDistance: 1500,
  endDistance: 3000,
  minY: 240,
  maxY: 440,
  pilotingMultiplier: 0.72,
  currentMultiplier: 0.88,
  boostMultiplier: 1,
  boostDurationMs: 2400,
  inputGraceMs: 900,
  collisionScreenX: 320,
  startX: 260,
  minX: 140,
  maxX: 1140,
});
'''

anchor = '''function finiteNumber(value: unknown): value is number {
  return typeof value === "number" && isFinite(value);
}
'''
controller = replace_once(controller, anchor, anchor + readiness_block, "readiness anchor")

state_block = r'''

  const seaTurtleReadiness = new SeaTurtleReadiness();
  let seaTurtleTravelX = SEA_TURTLE_CURRENT.startX;
  let seaTurtleInputGraceMs = 0;
  let seaTurtleCurrentActive = false;
  let seaTurtleBoostRemainingMs = 0;
  let seaTurtleBoostConsumed = false;
  let seaTurtlePrecisionAwarded = false;
  let seaTurtleScanComplete = false;
  let seaTurtleScanAwaiting = false;
  let seaTurtleLastCollisionCount = 0;
  let seaTurtleCurrentEntryCollisionCount = 0;
  let seaTurtleGearOverlay: HTMLElement | null = null;
  let seaTurtleBoostButton: HTMLButtonElement | null = null;
  let seaTurtleScanButton: HTMLButtonElement | null = null;
  const seaTurtleGearNodes: HTMLElement[] = [];

  function isSeaTurtleTravel(): boolean {
    return Missions.getSnapshot().selectedMissionId === "sea-turtle";
  }

  function clampSeaTurtleX(value: number): number {
    return Math.max(SEA_TURTLE_CURRENT.minX, Math.min(SEA_TURTLE_CURRENT.maxX, value));
  }

  function ensureSeaTurtleTravelUi(): void {
    if (seaTurtleGearOverlay && seaTurtleBoostButton && seaTurtleScanButton) {
      return;
    }
    const stage = document.getElementById("ocean-rescue-stage");
    if (!stage) {
      return;
    }

    const overlay = document.createElement("div");
    overlay.id = "ocean-rescue-readiness-gear";
    overlay.setAttribute("aria-label", "Rescue gear preparation");
    overlay.style.cssText = [
      "position:absolute",
      "left:18px",
      "bottom:18px",
      "z-index:12",
      "display:flex",
      "gap:8px",
      "padding:8px 10px",
      "border-radius:14px",
      "background:rgba(5,26,46,.82)",
      "border:1px solid rgba(61,218,215,.45)",
      "font:700 13px/1.2 system-ui,sans-serif",
      "pointer-events:none",
    ].join(";");
    const gear = [
      ["searchlight", "🔦 Searchlight"],
      ["thruster", "⚡ Thruster"],
      ["cutter", "✂ Cutter"],
    ] as const;
    for (const [id, label] of gear) {
      const node = document.createElement("span");
      node.setAttribute("data-readiness-gear", id);
      node.textContent = label;
      node.style.opacity = "0.34";
      overlay.appendChild(node);
      seaTurtleGearNodes.push(node);
    }

    const boost = document.createElement("button");
    boost.id = "ocean-rescue-current-boost";
    boost.type = "button";
    boost.textContent = "BOOST";
    boost.hidden = true;
    boost.style.cssText = [
      "position:absolute",
      "right:24px",
      "bottom:92px",
      "z-index:14",
      "padding:14px 22px",
      "border:0",
      "border-radius:999px",
      "background:#ffd166",
      "color:#05243a",
      "font:900 18px/1 system-ui,sans-serif",
      "box-shadow:0 0 24px rgba(255,209,102,.5)",
    ].join(";");
    boost.addEventListener("click", () => {
      if (!isSeaTurtleTravel() || !seaTurtleCurrentActive || seaTurtleBoostConsumed) {
        return;
      }
      seaTurtleBoostConsumed = true;
      seaTurtleBoostRemainingMs = SEA_TURTLE_CURRENT.boostDurationMs;
      seaTurtleReadiness.onBoost();
      syncSeaTurtleTravelUi();
    });

    const scan = document.createElement("button");
    scan.id = "ocean-rescue-scan-arrival";
    scan.type = "button";
    scan.textContent = "SCAN";
    scan.hidden = true;
    scan.style.cssText = [
      "position:absolute",
      "left:50%",
      "top:50%",
      "transform:translate(-50%,-50%)",
      "z-index:16",
      "padding:18px 34px",
      "border:2px solid #9ff7f3",
      "border-radius:999px",
      "background:rgba(4,45,67,.94)",
      "color:#eaffff",
      "font:900 22px/1 system-ui,sans-serif",
      "box-shadow:0 0 30px rgba(61,218,215,.55)",
    ].join(";");
    scan.addEventListener("click", () => {
      if (!seaTurtleScanAwaiting || seaTurtleScanComplete) {
        return;
      }
      seaTurtleReadiness.onScan();
      seaTurtleScanComplete = true;
      seaTurtleScanAwaiting = false;
      scan.hidden = true;
      syncSeaTurtleTravelUi();
    });

    stage.appendChild(overlay);
    stage.appendChild(boost);
    stage.appendChild(scan);
    seaTurtleGearOverlay = overlay;
    seaTurtleBoostButton = boost;
    seaTurtleScanButton = scan;
  }

  function syncSeaTurtleTravelUi(): void {
    ensureSeaTurtleTravelUi();
    const visible = isSeaTurtleTravel() && Travel.getSnapshot().active;
    if (seaTurtleGearOverlay) {
      seaTurtleGearOverlay.hidden = !visible;
    }
    const ready = seaTurtleReadiness.getSnapshot();
    const readiness = [ready.searchlightReady, ready.thrusterReady, ready.cutterReady];
    for (let index = 0; index < seaTurtleGearNodes.length; index += 1) {
      seaTurtleGearNodes[index].style.opacity = readiness[index] ? "1" : "0.34";
      seaTurtleGearNodes[index].setAttribute(
        "data-ready",
        readiness[index] ? "true" : "false",
      );
    }
    if (seaTurtleBoostButton) {
      seaTurtleBoostButton.hidden = !(
        visible && seaTurtleCurrentActive && !seaTurtleBoostConsumed
      );
    }
    if (seaTurtleScanButton) {
      seaTurtleScanButton.hidden = !(visible && seaTurtleScanAwaiting && !seaTurtleScanComplete);
    }
    const root = document.getElementById("ocean-rescue-root");
    if (root && visible) {
      root.setAttribute("data-travel-current", seaTurtleCurrentActive ? "active" : "inactive");
      root.setAttribute(
        "data-travel-boost",
        seaTurtleBoostRemainingMs > 0
          ? "active"
          : seaTurtleBoostConsumed
            ? "used"
            : "available",
      );
      root.setAttribute(
        "data-travel-scan",
        seaTurtleScanComplete ? "complete" : seaTurtleScanAwaiting ? "ready" : "pending",
      );
      root.setAttribute("data-travel-x", String(Math.round(seaTurtleTravelX)));
      root.setAttribute(
        "data-readiness-searchlight",
        ready.searchlightReady ? "ready" : "preparing",
      );
      root.setAttribute(
        "data-readiness-thruster",
        ready.thrusterReady ? "ready" : "preparing",
      );
      root.setAttribute(
        "data-readiness-cutter",
        ready.cutterReady ? "ready" : "preparing",
      );
    }
  }

  function resetSeaTurtleTravelSlice(): void {
    seaTurtleTravelX = SEA_TURTLE_CURRENT.startX;
    seaTurtleInputGraceMs = 0;
    seaTurtleCurrentActive = false;
    seaTurtleBoostRemainingMs = 0;
    seaTurtleBoostConsumed = false;
    seaTurtlePrecisionAwarded = false;
    seaTurtleScanComplete = false;
    seaTurtleScanAwaiting = false;
    seaTurtleLastCollisionCount = Terrain?.getSnapshot().collisionCount ?? 0;
    seaTurtleCurrentEntryCollisionCount = seaTurtleLastCollisionCount;
    if (isSeaTurtleTravel()) {
      seaTurtleReadiness.start();
    } else {
      seaTurtleReadiness.stop();
    }
    syncSeaTurtleTravelUi();
  }

  function hideSeaTurtleTravelUi(): void {
    seaTurtleReadiness.stop();
    if (seaTurtleGearOverlay) {
      seaTurtleGearOverlay.hidden = true;
    }
    if (seaTurtleBoostButton) {
      seaTurtleBoostButton.hidden = true;
    }
    if (seaTurtleScanButton) {
      seaTurtleScanButton.hidden = true;
    }
  }

  function mapClientXToStage(event: PointerEvent): number | null {
    if (!travelCanvas) {
      return null;
    }
    const rect = travelCanvas.getBoundingClientRect();
    if (!finiteNumber(rect.left) || !finiteNumber(rect.width) || rect.width <= 0) {
      return null;
    }
    const stageX = (event.clientX - rect.left) * (travelCanvas.width / rect.width);
    return finiteNumber(stageX) ? clampSeaTurtleX(stageX) : null;
  }

  function registerSeaTurtlePointerX(event: PointerEvent): void {
    if (!isSeaTurtleTravel()) {
      return;
    }
    const stageX = mapClientXToStage(event);
    if (stageX === null) {
      return;
    }
    seaTurtleTravelX = stageX;
    seaTurtleInputGraceMs = SEA_TURTLE_CURRENT.inputGraceMs;
    syncSeaTurtleTravelUi();
  }

  function seaTurtleSceneSnapshot(): unknown {
    const snapshot = Travel.getSnapshot();
    if (!isSeaTurtleTravel()) {
      return snapshot;
    }
    return { ...snapshot, x: seaTurtleTravelX };
  }

  function runSeaTurtleTravelStep(deltaMs: number): void {
    if (!isSeaTurtleTravel()) {
      if (Terrain?.getSnapshot().active) {
        Terrain.step(deltaMs, Travel.getSnapshot());
        Travel.step(deltaMs, Terrain.getSnapshot().forwardSpeedMultiplier);
      } else {
        Travel.step(deltaMs);
      }
      return;
    }
    if (seaTurtleScanAwaiting) {
      syncSeaTurtleTravelUi();
      return;
    }

    const before = Travel.getSnapshot();
    if (Terrain?.getSnapshot().active) {
      Terrain.step(deltaMs, {
        ...before,
        distance:
          before.distance +
          (seaTurtleTravelX - SEA_TURTLE_CURRENT.collisionScreenX),
      });
    }
    const terrain = Terrain?.getSnapshot() ?? null;
    const collisionCount = terrain?.collisionCount ?? 0;
    if (collisionCount > seaTurtleLastCollisionCount) {
      seaTurtleReadiness.onCollision();
      seaTurtleLastCollisionCount = collisionCount;
    }

    const wasInCurrent = seaTurtleCurrentActive;
    seaTurtleCurrentActive =
      before.distance >= SEA_TURTLE_CURRENT.startDistance &&
      before.distance <= SEA_TURTLE_CURRENT.endDistance &&
      before.y >= SEA_TURTLE_CURRENT.minY &&
      before.y <= SEA_TURTLE_CURRENT.maxY;
    if (!wasInCurrent && seaTurtleCurrentActive) {
      seaTurtleCurrentEntryCollisionCount = collisionCount;
    } else if (
      wasInCurrent &&
      !seaTurtleCurrentActive &&
      !seaTurtlePrecisionAwarded &&
      collisionCount === seaTurtleCurrentEntryCollisionCount
    ) {
      seaTurtlePrecisionAwarded = true;
      seaTurtleReadiness.onPrecisionClear();
    }

    const meaningfulInput =
      pointerActive ||
      pointerDragging ||
      seaTurtleInputGraceMs > 0 ||
      before.tapTargetY !== null;
    seaTurtleReadiness.step(deltaMs, meaningfulInput, seaTurtleCurrentActive);

    const applied = Math.min(Math.max(deltaMs, 0), 50);
    seaTurtleInputGraceMs = Math.max(0, seaTurtleInputGraceMs - applied);
    seaTurtleBoostRemainingMs = Math.max(0, seaTurtleBoostRemainingMs - applied);

    let intendedMultiplier = 0;
    if (seaTurtleBoostRemainingMs > 0) {
      intendedMultiplier = SEA_TURTLE_CURRENT.boostMultiplier;
    } else if (seaTurtleCurrentActive) {
      intendedMultiplier = SEA_TURTLE_CURRENT.currentMultiplier;
    } else if (meaningfulInput) {
      intendedMultiplier = SEA_TURTLE_CURRENT.pilotingMultiplier;
    }
    const collisionMultiplier = terrain?.forwardSpeedMultiplier ?? 1;
    Travel.step(deltaMs, Math.max(0, Math.min(1, intendedMultiplier * collisionMultiplier)));
    syncSeaTurtleTravelUi();
  }

  function holdForSeaTurtleScan(): boolean {
    if (!isSeaTurtleTravel() || seaTurtleScanComplete) {
      return false;
    }
    const travel = Travel.getSnapshot();
    if (travel.distance < Rescue.ArrivalDistance) {
      return false;
    }
    seaTurtleScanAwaiting = true;
    syncSeaTurtleTravelUi();
    return true;
  }
'''

state_anchor = '''  const boundTravelCanvases = new WeakSet<HTMLCanvasElement>();
'''
controller = replace_once(controller, state_anchor, state_anchor + state_block, "travel state anchor")

controller = replace_once(
    controller,
    '''    pointerActive = true;
    pointerId = event.pointerId;
''',
    '''    registerSeaTurtlePointerX(event);
    pointerActive = true;
    pointerId = event.pointerId;
''',
    "pointer down x",
)
controller = replace_once(
    controller,
    '''    const stageY = mapClientYToStage(event);
    if (stageY === null) {
      return;
    }
    if (!pointerDragging) {
''',
    '''    const stageY = mapClientYToStage(event);
    if (stageY === null) {
      return;
    }
    registerSeaTurtlePointerX(event);
    if (!pointerDragging) {
''',
    "pointer move x",
)
controller = replace_once(
    controller,
    '''    const stageY = mapClientYToStage(event);
    if (pointerDragging) {
''',
    '''    const stageY = mapClientYToStage(event);
    registerSeaTurtlePointerX(event);
    if (pointerDragging) {
''',
    "pointer up x",
)

old_frame = '''    if (travelLastTimestamp !== null) {
      const deltaMs = timestamp - travelLastTimestamp;
      if (deltaMs > 0) {
        if (Terrain?.getSnapshot().active) {
          Terrain.step(deltaMs, Travel.getSnapshot());
          Travel.step(deltaMs, Terrain.getSnapshot().forwardSpeedMultiplier);
        } else {
          Travel.step(deltaMs);
        }
      }
    }
    travelLastTimestamp = timestamp;
    syncTravelProgress(Travel.getSnapshot());
    if (host.handoffTravelArrival()) {
      return;
    }
    if (TravelScene?.isMounted()) {
      TravelScene.sync(Travel.getSnapshot(), Terrain?.getSnapshot() ?? null);
    }
    scheduleTravelFrame(runId);
'''
new_frame = '''    if (travelLastTimestamp !== null) {
      const deltaMs = timestamp - travelLastTimestamp;
      if (deltaMs > 0) {
        runSeaTurtleTravelStep(deltaMs);
      }
    }
    travelLastTimestamp = timestamp;
    syncTravelProgress(Travel.getSnapshot());
    if (holdForSeaTurtleScan()) {
      if (TravelScene?.isMounted()) {
        TravelScene.sync(seaTurtleSceneSnapshot(), Terrain?.getSnapshot() ?? null);
      }
      scheduleTravelFrame(runId);
      return;
    }
    if (host.handoffTravelArrival()) {
      return;
    }
    if (TravelScene?.isMounted()) {
      TravelScene.sync(seaTurtleSceneSnapshot(), Terrain?.getSnapshot() ?? null);
    }
    scheduleTravelFrame(runId);
'''
controller = replace_once(controller, old_frame, new_frame, "travel frame")

controller = replace_once(
    controller,
    '''    Travel.start();
    startTerrainRuntime();
    hideTravelProgress();
''',
    '''    Travel.start();
    startTerrainRuntime();
    resetSeaTurtleTravelSlice();
    hideTravelProgress();
''',
    "travel start reset",
)
controller = replace_once(
    controller,
    '''    hideTravelProgress();
    const root = document.getElementById("ocean-rescue-root");
''',
    '''    hideTravelProgress();
    hideSeaTurtleTravelUi();
    const root = document.getElementById("ocean-rescue-root");
''',
    "travel stop ui",
)
controller_path.write_text(controller, encoding="utf-8")

# AI Studio's latest compatible Pixi scene adds X-aware submarine placement and
# the current visual refinements without importing its alternate Vite/Tailwind
# application shell.
ai_scene = AI_ROOT / "workspace/src/travel-scene.js"
canonical_scene = ROOT / "domains/ocean-rescue/src/travel-scene.js"
canonical_scene.write_bytes(ai_scene.read_bytes())

# Update the existing browser acceptance to make SCAN a real arrival checkpoint.
wp33b = ROOT / "tests/test_ocean_rescue_wp33b_launch_travel_controller.py"
text = wp33b.read_text(encoding="utf-8")
old = '''            page.wait_for_function(
                "OceanRescue.State.getSnapshot().phase === 'RESCUE_SITE_TRANSITION'",
                timeout=5000,
            )
            arrival = page.evaluate(
'''
new = '''            page.wait_for_function(
                "document.getElementById('ocean-rescue-scan-arrival') && "
                "document.getElementById('ocean-rescue-scan-arrival').hidden === false",
                timeout=5000,
            )
            assert page.evaluate("OceanRescue.State.getSnapshot().phase") == "TRAVEL"
            assert page.locator("#ocean-rescue-root").get_attribute("data-travel-scan") == "ready"
            page.click("#ocean-rescue-scan-arrival")
            page.wait_for_function(
                "OceanRescue.State.getSnapshot().phase === 'RESCUE_SITE_TRANSITION'",
                timeout=5000,
            )
            arrival = page.evaluate(
'''
if text.count(old) != 1:
    raise SystemExit("WP33B arrival patch anchor mismatch")
text = text.replace(old, new, 1)
wp33b.write_text(text, encoding="utf-8")

contract_test = ROOT / "tests/test_ocean_rescue_ai_studio_travel_slice.py"
contract_test.write_text(
    '''"""Canonicalization checks for the 2026-08-28 AI Studio Sea Turtle slice."""\n\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\nSRC = ROOT / "domains" / "ocean-rescue" / "src"\n\n\ndef test_ai_studio_slice_is_inside_existing_canonical_owner() -> None:\n    text = (SRC / "controllers" / "launch-travel.ts").read_text(encoding="utf-8")\n    assert "ocean-rescue-ai-studio@9edd0cee" in text\n    assert "pilotingMultiplier: 0.72" in text\n    assert "currentMultiplier: 0.88" in text\n    assert "boostMultiplier: 1" in text\n    assert "boostDurationMs: 2400" in text\n    assert "id = \\\"ocean-rescue-current-boost\\\"" in text\n    assert "id = \\\"ocean-rescue-scan-arrival\\\"" in text\n    assert "host.handoffTravelArrival()" in text\n\n\ndef test_readiness_is_hidden_and_committed_gear_is_not_removed() -> None:\n    text = (SRC / "controllers" / "launch-travel.ts").read_text(encoding="utf-8")\n    assert "this.committedFloor" in text\n    assert "Math.max(this.committedFloor, this.value - 0.12)" in text\n    for gear in ("Searchlight", "Thruster", "Cutter"):\n        assert gear in text\n    assert "readiness-percent" not in text\n    assert "readiness-score" not in text\n\n\ndef test_ai_studio_deployment_and_progression_scaffold_was_not_imported() -> None:\n    template = (SRC / "index.template.html").read_text(encoding="utf-8")\n    controller = (SRC / "controllers" / "launch-travel.ts").read_text(encoding="utf-8")\n    assert "cdn.tailwindcss.com" not in template\n    assert "fonts.googleapis.com" not in template\n    for forbidden in ("별빛 크리스탈", "ocean_rescue_restoration_v4", "GUP GARAGE", "ecology quiz"):\n        assert forbidden not in controller\n\ndef test_latest_ai_studio_scene_supports_direct_x_snapshot() -> None:\n    scene = (SRC / "travel-scene.js").read_text(encoding="utf-8")\n    assert "snapshot.x" in scene\n    assert "travel-submarine" in scene\n''',
    encoding="utf-8",
)

print(f"canonicalized AI Studio {AI_HEAD} onto game base {BASE}")
