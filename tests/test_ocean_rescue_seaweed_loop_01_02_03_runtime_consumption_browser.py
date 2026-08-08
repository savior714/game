"""Browser acceptance test verifying sea-turtle runtime consumes authored seaweed loops .01, .02, .03."""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
from test_ocean_rescue_wp11_dev_server import ViteServerFixture  # noqa: E402


def _instrument(page: Page, base_url: str):
    page_errors: list[str] = []
    console_errors: list[str] = []
    request_failures: list[dict[str, object]] = []
    external_requests: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on(
        "console",
        lambda message: (
            console_errors.append(message.text) if message.type == "error" else None
        ),
    )
    page.on(
        "requestfailed",
        lambda request: request_failures.append(
            {"url": request.url, "failure": request.failure}
        ),
    )
    page.on(
        "request",
        lambda request: (
            external_requests.append(request.url)
            if not request.url.startswith(base_url)
            else None
        ),
    )
    return page_errors, console_errors, request_failures, external_requests


def _assert_quality_gates(errors) -> None:
    page_errors, console_errors, request_failures, external_requests = errors
    assert page_errors == [], f"page errors: {page_errors}"
    assert console_errors == [], f"console errors: {console_errors}"
    assert request_failures == [], f"request failures: {request_failures}"
    assert [
        url
        for url in external_requests
        if not url.startswith("data:")
        and "localhost" not in url
        and "127.0.0.1" not in url
    ] == [], f"external requests: {external_requests}"


def test_seaweed_loops_01_02_03_distinct_texture_consumption_browser() -> None:
    with ViteServerFixture() as server:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            context.add_init_script("localStorage.clear(); sessionStorage.clear();")
            page = context.new_page()
            errors = _instrument(page, server.base_url)
            page.goto(f"{server.base_url}/index.dev.html")

            page.wait_for_selector(
                "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=20000
            )

            # Assert each of the 3 loop textures are registered in RenderRuntime
            loop_textures = page.evaluate(
                """() => {
                  const RenderRuntime = window.OceanRescue.RenderRuntime;
                  const aliases = ['scene.seaweed-loop.01', 'scene.seaweed-loop.02', 'scene.seaweed-loop.03'];
                  return aliases.map(alias => RenderRuntime.hasTexture(alias));
                }"""
            )
            assert loop_textures == [True, True, True], (
                f"All 3 seaweed loop textures must be loaded: {loop_textures}"
            )

            # Start sea-turtle session via public API flow
            start_result = page.evaluate(
                """() => {
                  OceanRescue.State.forcePhase(OceanRescue.State.Phases.RESCUE_ACTIVE);
                  const content = OceanRescue.Rescue.getMissionContent('sea-turtle');
                  const seq = {
                    sequenceId: 101,
                    missionId: 'sea-turtle',
                    gupId: 'gup-c',
                    missionContent: content,
                    tutorialComplete: true,
                    tutorialSkipped: true,
                  };
                  OceanRescue.App.setActiveRescueSequence(seq);
                  return OceanRescue.App.startSeaTurtleSession(seq);
                }"""
            )
            assert start_result is True, "startSeaTurtleSession must return true"

            # Execute 3 rope releases using pointer gestures and finishFeedback
            release_result = page.evaluate(
                """() => {
                  const SeaTurtle = window.OceanRescue.SeaTurtle;
                  const Ropes = SeaTurtle.Ropes;
                  
                  // Release Rope 1
                  SeaTurtle.pointerDown(1, Ropes[0].start.x, Ropes[0].start.y);
                  SeaTurtle.pointerMove(1, Ropes[0].end.x, Ropes[0].end.y);
                  SeaTurtle.pointerUp(1, Ropes[0].end.x, Ropes[0].end.y);
                  const s1 = SeaTurtle.getSnapshot();
                  SeaTurtle.finishFeedback();

                  // Release Rope 2
                  SeaTurtle.pointerDown(2, Ropes[1].start.x, Ropes[1].start.y);
                  SeaTurtle.pointerMove(2, Ropes[1].end.x, Ropes[1].end.y);
                  SeaTurtle.pointerUp(2, Ropes[1].end.x, Ropes[1].end.y);
                  const s2 = SeaTurtle.getSnapshot();
                  SeaTurtle.finishFeedback();

                  // Release Rope 3
                  SeaTurtle.pointerDown(3, Ropes[2].start.x, Ropes[2].start.y);
                  SeaTurtle.pointerMove(3, Ropes[2].end.x, Ropes[2].end.y);
                  SeaTurtle.pointerUp(3, Ropes[2].end.x, Ropes[2].end.y);
                  SeaTurtle.finishFeedback();
                  const s3 = SeaTurtle.getSnapshot();

                  return { s1, s2, s3 };
                }"""
            )

            assert release_result["s1"]["completedRopeIds"] == ["rope-1"]
            assert release_result["s2"]["completedRopeIds"] == ["rope-1", "rope-2"]
            assert release_result["s3"]["completedRopeIds"] == [
                "rope-1",
                "rope-2",
                "rope-3",
            ]
            assert release_result["s3"]["complete"] is True, (
                "Session must be complete after releasing 3 ropes"
            )

            _assert_quality_gates(errors)
            context.close()
            browser.close()
