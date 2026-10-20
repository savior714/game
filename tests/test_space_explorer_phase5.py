"""태양계 3D 탐험대 — 순수 궤도/자전 계산 계약 (Node 실행)."""

from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPACE_DIR = ROOT / "experiments" / "space-explorer"


def run_node(source: str) -> dict:
    completed = subprocess.run(
        ["node", "--input-type=module", "--eval", textwrap.dedent(source)],
        check=True,
        capture_output=True,
        text=True,
        cwd=SPACE_DIR,
    )
    return json.loads(completed.stdout.strip())


def test_kepler_solver_converges_for_every_planet() -> None:
    payload = run_node(
        """
        import { PLANETS } from "./data.js";
        import { solveKepler, normalizeAngle } from "./simulation.js";

        const results = PLANETS.map((planet) => {
          const m = 1.234;
          const E = solveKepler(m, planet.orbit.e);
          const residual = Math.abs(E - planet.orbit.e * Math.sin(E) - m);
          return { id: planet.id, residual };
        });

        console.log(JSON.stringify({ results, wrapped: normalizeAngle(-Math.PI / 2) }));
        """
    )

    for result in payload["results"]:
        assert result["residual"] < 1e-8, f"{result['id']} Kepler residual too large"
    assert 0 <= payload["wrapped"] < 6.2832


def test_planet_positions_follow_orbital_periods() -> None:
    payload = run_node(
        """
        import { PLANETS } from "./data.js";
        import { visualOrbitPosition, orbitRadiusForDistance } from "./simulation.js";

        const rows = PLANETS.map((planet) => {
          const start = visualOrbitPosition(planet.orbit, 0);
          const half = visualOrbitPosition(planet.orbit, planet.orbit.periodDays / 2);
          const full = visualOrbitPosition(planet.orbit, planet.orbit.periodDays);
          const distance = (p) => Math.hypot(p.x, p.y, p.z);
          return {
            id: planet.id,
            halfDistance: Math.hypot(start.x - half.x, start.y - half.y, start.z - half.z),
            fullDistance: Math.hypot(start.x - full.x, start.y - full.y, start.z - full.z),
            startRadius: distance(start),
            expectedRadius: orbitRadiusForDistance(planet.orbit.a),
            period: planet.orbit.periodDays,
          };
        });

        console.log(JSON.stringify(rows));
        """
    )

    for row in payload:
        # 반 주기 뒤에는 반대편에 있어야 하고, 한 주기 뒤에는 제자리로 돌아와야 한다.
        assert row["halfDistance"] > row["startRadius"] * 1.2, row["id"]
        assert row["fullDistance"] < row["startRadius"] * 0.02, row["id"]
        assert (
            abs(row["startRadius"] - row["expectedRadius"])
            < row["expectedRadius"] * 0.22
        )

    periods = {row["id"]: row["period"] for row in payload}
    assert (
        periods["mercury"] < periods["earth"] < periods["jupiter"] < periods["neptune"]
    )


def test_orbit_view_is_compressed_but_order_preserving() -> None:
    payload = run_node(
        """
        import { PLANETS } from "./data.js";
        import { orbitRadiusForDistance } from "./simulation.js";

        console.log(JSON.stringify(PLANETS.map((planet) => ({
          id: planet.id,
          au: planet.orbit.a,
          display: orbitRadiusForDistance(planet.orbit.a),
        }))));
        """
    )

    for previous, current in zip(payload, payload[1:]):
        assert current["au"] > previous["au"]
        assert current["display"] > previous["display"]
        assert current["display"] - previous["display"] < 55

    assert payload[-1]["display"] < 200, "outermost orbit must fit the overview camera"


def test_rotation_periods_and_retrograde_planets() -> None:
    payload = run_node(
        """
        import { PLANETS, MOONS } from "./data.js";
        import { spinAngleRad } from "./simulation.js";

        console.log(JSON.stringify({
          venusRetrograde: spinAngleRad(PLANETS.find(p => p.id === "venus").rotationHours, 1) < 0,
          uranusRetrograde: spinAngleRad(PLANETS.find(p => p.id === "uranus").rotationHours, 1) < 0,
          earthOneDay: spinAngleRad(PLANETS.find(p => p.id === "earth").rotationHours, 1),
          tritonRetrograde: MOONS.find(m => m.id === "triton").periodDays < 0,
          moonPeriod: MOONS.find(m => m.id === "moon").periodDays,
        }));
        """
    )

    assert payload["venusRetrograde"] is True
    assert payload["uranusRetrograde"] is True
    assert payload["tritonRetrograde"] is True
    assert abs(payload["earthOneDay"] - 6.2831853 * 24 / 23.9345) < 0.3
    assert 27.3 < payload["moonPeriod"] < 27.4


def test_simulation_dates_are_utc_and_reversible() -> None:
    payload = run_node(
        """
        import { daysSinceJ2000, dateFromSimulationDays, formatSimDate } from "./simulation.js";

        const days = daysSinceJ2000("2026-08-28T00:00:00Z");
        console.log(JSON.stringify({
          days,
          iso: dateFromSimulationDays(days).toISOString(),
          label: formatSimDate(days),
        }));
        """
    )

    assert payload["iso"].startswith("2026-08-28T00:00:00")
    assert payload["label"] == "2026년 08월 28일"
    assert payload["days"] > 9000
