"""Contract and Node-VM runtime tests for Ocean Rescue short-play study admission."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE_BIN = shutil.which("node") or ""
if not NODE_BIN:
    raise RuntimeError("Node executable not found on PATH")

ADMISSION_JS = ROOT / "shared/ui/study-game-admission.js"
HUB_HTML = ROOT / "index.html"
OCEAN_HTML = ROOT / "ocean-rescue/index.html"
OCEAN_TEMPLATE = ROOT / "domains/ocean-rescue/src/index.template.html"
OCEAN_STYLE = ROOT / "domains/ocean-rescue/src/style.css"
OCEAN_APP_JS = ROOT / "domains/ocean-rescue/src/app.js"


def _run_node(script: str) -> dict:
    completed = subprocess.run(
        [NODE_BIN, "-e", script],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, (
        f"Node harness failed (code={completed.returncode}):\n"
        f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    assert lines, f"Expected JSON output from Node harness, stderr={completed.stderr}"
    return json.loads(lines[-1])


def test_shared_admission_registers_ocean_rescue_five_answers_five_minutes() -> None:
    content = ADMISSION_JS.read_text(encoding="utf-8")

    assert "const REQUIRED = 5;" in content
    assert "const DURATION = 5 * 60 * 1000;" in content
    assert "'ocean-rescue': ['ocean-rescue/index.html', '🌊 바다 구조대']" in content


def test_hub_ocean_rescue_card_uses_short_play_admission_without_daily_math_lock() -> (
    None
):
    html = HUB_HTML.read_text(encoding="utf-8")

    assert html.count("./ocean-rescue/index.html") == 1
    assert 'id="ocean-rescue-card"' in html
    assert 'id="ocean-rescue-card-title"' in html
    assert 'aria-labelledby="ocean-rescue-card-title"' in html
    assert "Ocean Rescue" in html
    assert "잠수정을 타고 바다 생물을 구조해요" in html
    assert "정답 5개" in html
    assert "5분" in html

    for removed_legacy_token in (
        "hasCompletedTodayMathGoal",
        "updateOceanRescueCardState",
        "aiden_math_daily_goal_v1",
        "ocean-rescue-lock-badge",
        "오늘의 수학 목표(20문제)",
    ):
        assert removed_legacy_token not in html, (
            f"index.html still contains legacy daily-math lock token: {removed_legacy_token}"
        )


def test_ocean_rescue_template_and_artifact_remove_legacy_twenty_problem_gate() -> None:
    template = OCEAN_TEMPLATE.read_text(encoding="utf-8")
    artifact = OCEAN_HTML.read_text(encoding="utf-8")
    style = OCEAN_STYLE.read_text(encoding="utf-8")

    for text in (template, artifact):
        assert "ocean-rescue-admission-gate" not in text
        assert "수학 문제 20개" not in text
        assert 'id="ocean-rescue-pause-home"' in text
        assert 'id="ocean-rescue-mission-complete-home"' in text

    assert ".study-game-choice" in style
    assert ".study-game-clock" in style
    assert "html[data-study-game-locked]" in style


def test_shared_admission_hub_to_subject_to_ocean_rescue_flow_in_node_vm() -> None:
    script = textwrap.dedent(
        """\
        const fs = require("fs");
        const vm = require("vm");
        const assert = require("assert");

        const CODE = fs.readFileSync("shared/ui/study-game-admission.js", "utf8");
        const KEY = "aiden_study_game_admission_v1";

        function createHarness(pathname, sessionSeed, nowRef) {
          const store = Object.assign({}, sessionSeed || {});
          const navigations = [];
          const alerts = [];
          const docListeners = {};
          const winListeners = {};

          function makeEl(tag) {
            const el = {
              tagName: tag.toUpperCase(),
              className: "",
              id: "",
              textContent: "",
              open: false,
              attributes: {},
              dataset: {},
              children: [],
              listeners: {},
              append(...nodes) {
                for (const node of nodes) {
                  if (typeof node === "string") {
                    const textNode = makeEl("#text");
                    textNode.textContent = node;
                    this.children.push(textNode);
                  } else if (node) {
                    node.parentElement = this;
                    this.children.push(node);
                  }
                }
              },
              prepend(...nodes) {
                const items = nodes.map((node) => {
                  if (typeof node === "string") {
                    const textNode = makeEl("#text");
                    textNode.textContent = node;
                    return textNode;
                  }
                  node.parentElement = this;
                  return node;
                });
                this.children.unshift(...items);
              },
              replaceChildren(...nodes) {
                this.children = [];
                this.append(...nodes);
              },
              remove() {
                if (this.parentElement) {
                  this.parentElement.children = this.parentElement.children.filter((c) => c !== this);
                }
              },
              setAttribute(k, v) {
                this.attributes[k] = String(v);
              },
              getAttribute(k) {
                return Object.prototype.hasOwnProperty.call(this.attributes, k) ? this.attributes[k] : null;
              },
              addEventListener(type, fn) {
                (this.listeners[type] = this.listeners[type] || []).push(fn);
              },
              click() {
                for (const fn of this.listeners.click || []) {
                  fn({ preventDefault() {} });
                }
              },
              showModal() {
                this.open = true;
              },
              close() {
                this.open = false;
              },
              closest(selector) {
                if (selector === "a[href]" && this.tagName === "A" && this.href) {
                  return this;
                }
                return null;
              },
            };
            return el;
          }

          const head = makeEl("head");
          const body = makeEl("body");
          const documentElement = makeEl("html");
          const currentScript = { src: "http://127.0.0.1:8000/shared/ui/study-game-admission.js" };
          const location = {
            href: "http://127.0.0.1:8000" + pathname,
            origin: "http://127.0.0.1:8000",
            pathname,
            assign(url) { navigations.push({ type: "assign", url: String(url) }); },
            replace(url) { navigations.push({ type: "replace", url: String(url) }); },
          };
          const sessionStorage = {
            getItem(k) { return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
            setItem(k, v) { store[k] = String(v); },
            removeItem(k) { delete store[k]; },
          };
          const document = {
            readyState: "complete",
            currentScript,
            head,
            body,
            documentElement,
            createElement: makeEl,
            addEventListener(type, fn) {
              (docListeners[type] = docListeners[type] || []).push(fn);
            },
          };
          const RealDate = Date;
          function FakeDate(...args) {
            if (args.length === 0) return new RealDate(nowRef.now);
            return new RealDate(...args);
          }
          FakeDate.now = () => nowRef.now;

          const windowObj = {
            location,
            sessionStorage,
            document,
            URL,
            Date: FakeDate,
            Math,
            Number,
            Object,
            String,
            JSON,
            alert(msg) { alerts.push(String(msg)); },
            setInterval() { return 1; },
            clearInterval() {},
            addEventListener(type, fn) {
              (winListeners[type] = winListeners[type] || []).push(fn);
            },
          };
          windowObj.window = windowObj;
          const sandbox = {
            window: windowObj,
            document,
            location,
            sessionStorage,
            URL,
            Date: FakeDate,
            alert: windowObj.alert,
            setInterval: windowObj.setInterval,
            clearInterval: windowObj.clearInterval,
          };
          vm.createContext(sandbox);
          vm.runInContext(CODE, sandbox, { filename: "study-game-admission.js" });
          return { window: windowObj, document, body, docListeners, store, navigations, alerts, makeEl };
        }

        const nowRef = { now: 1700000000000 };
        const hub = createHarness("/index.html", {}, nowRef);
        const oceanLink = hub.makeEl("a");
        oceanLink.href = "http://127.0.0.1:8000/ocean-rescue/index.html";
        let defaultPrevented = false;
        for (const fn of hub.docListeners.click || []) {
          fn({
            target: oceanLink,
            preventDefault() { defaultPrevented = true; },
          });
        }
        assert.strictEqual(defaultPrevented, true);
        const dialog = hub.body.children.find((el) => el.className === "study-game-choice");
        assert.ok(dialog && dialog.open, "clicking ocean-rescue link on hub must open subject dialog");
        const intro = dialog.children.find((el) => el.tagName === "P");
        assert.ok(intro.textContent.includes("🌊 바다 구조대"));
        const subjectWrap = dialog.children.find((el) => el.className === "study-game-subjects");
        assert.strictEqual(subjectWrap.children.length, 4);

        // Pick science (4th button)
        subjectWrap.children[3].click();
        const learningState = JSON.parse(hub.store[KEY]);
        assert.deepStrictEqual(learningState, {
          version: 1,
          phase: "learning",
          game: "ocean-rescue",
          subject: "science",
          correct: 0,
        });
        assert.strictEqual(hub.navigations[0].url, "http://127.0.0.1:8000/domains/science/index.html");

        // On science study page: wrong answers & other subjects do not count; 5 correct unlocks 5-minute play
        const study = createHarness("/domains/science/index.html", hub.store, nowRef);
        study.window.StudyGameAdmission.recordAnswer("math", true);
        study.window.StudyGameAdmission.recordAnswer("science", false);
        assert.strictEqual(JSON.parse(study.store[KEY]).correct, 0);

        for (let i = 0; i < 6; i += 1) {
          study.window.StudyGameAdmission.recordAnswer("science", true);
        }
        assert.strictEqual(JSON.parse(study.store[KEY]).correct, 5);
        const banner = study.body.children.find((el) => el.className === "study-game-progress");
        const enterBtn = banner.children.find((el) => el.tagName === "BUTTON" && el.textContent.includes("게임 입장하기"));
        assert.ok(enterBtn, "5 correct answers must render game entry button");

        enterBtn.click();
        const playingState = JSON.parse(study.store[KEY]);
        assert.strictEqual(playingState.phase, "playing");
        assert.strictEqual(playingState.game, "ocean-rescue");
        assert.strictEqual(playingState.correct, 5);
        assert.strictEqual(playingState.startedAt, nowRef.now);
        assert.strictEqual(playingState.deadline, nowRef.now + 300000);
        assert.strictEqual(study.navigations[0].url, "http://127.0.0.1:8000/ocean-rescue/index.html");

        // Returning to hub consumes the playing session immediately
        const hubReturn = createHarness("/index.html", study.store, nowRef);
        assert.strictEqual(hubReturn.store[KEY], undefined);

        console.log(JSON.stringify({ ok: true }));
        """
    )
    result = _run_node(script)
    assert result["ok"] is True


def test_standalone_ocean_rescue_enforces_study_admission_and_five_minute_deadline() -> (
    None
):
    html = OCEAN_HTML.read_text(encoding="utf-8")
    scripts = re.findall(r"<script>([\s\S]*?)</script>", html)
    assert len(scripts) == 2, (
        "Production ocean-rescue/index.html must keep 2 inline scripts"
    )

    node_script = textwrap.dedent(
        """\
        const fs = require("fs");
        const vm = require("vm");
        const assert = require("assert");

        const html = fs.readFileSync("ocean-rescue/index.html", "utf8");
        const matches = [...html.matchAll(/<script>([\\s\\S]*?)<\\/script>/g)];
        assert.strictEqual(matches.length, 2);
        const appBundle = matches[1][1];
        const KEY = "aiden_study_game_admission_v1";

        function runOceanBundle(options) {
          const opts = options || {};
          const store = Object.assign({}, opts.sessionSeed || {});
          const localStore = Object.assign({}, opts.localSeed || {});
          const navigations = [];
          const alerts = [];
          const intervals = [];
          const docListeners = {};
          const winListeners = {};
          let now = opts.now || 1700000000000;
          let renderBootCalls = 0;

          function makeEl(tag) {
            const el = {
              tagName: String(tag).toUpperCase(),
              className: "",
              id: "",
              type: "",
              hidden: false,
              disabled: false,
              open: false,
              textContent: "",
              style: {},
              dataset: {},
              attributes: {},
              children: [],
              listeners: {},
              append(...nodes) {
                for (const node of nodes) {
                  if (typeof node === "string") {
                    const t = makeEl("#text");
                    t.textContent = node;
                    this.children.push(t);
                  } else if (node) {
                    node.parentElement = this;
                    this.children.push(node);
                  }
                }
              },
              appendChild(child) {
                if (child) {
                  child.parentElement = this;
                  this.children.push(child);
                }
                return child;
              },
              replaceChildren(...nodes) {
                this.children = [];
                this.append(...nodes);
              },
              remove() {
                if (this.parentElement) {
                  this.parentElement.children = this.parentElement.children.filter((c) => c !== this);
                }
              },
              setAttribute(name, value) {
                const str = String(value);
                this.attributes[name] = str;
                if (name === "data-study-game-locked") {
                  this.dataset.studyGameLocked = str;
                }
              },
              getAttribute(name) {
                if (name === "data-study-game-locked" && Object.prototype.hasOwnProperty.call(this.dataset, "studyGameLocked")) {
                  return this.dataset.studyGameLocked;
                }
                return Object.prototype.hasOwnProperty.call(this.attributes, name)
                  ? this.attributes[name]
                  : null;
              },
              removeAttribute(name) {
                delete this.attributes[name];
                if (name === "data-study-game-locked") {
                  delete this.dataset.studyGameLocked;
                }
              },
              addEventListener(type, fn) {
                (this.listeners[type] = this.listeners[type] || []).push(fn);
              },
              dispatchEvent(event) {
                for (const fn of this.listeners[event.type] || []) {
                  fn(event);
                }
              },
              click() {
                for (const fn of this.listeners.click || []) {
                  fn({ preventDefault() {} });
                }
              },
              showModal() {
                this.open = true;
              },
              close() {
                this.open = false;
              },
              querySelectorAll(sel) {
                if (sel === "button") {
                  return this.children.filter((c) => c.tagName === "BUTTON");
                }
                return [];
              },
            };
            Object.defineProperty(el, "innerHTML", {
              enumerable: false,
              get() { return this._innerHTML || ""; },
              set(v) { this._innerHTML = String(v); this.children = []; },
            });
            return el;
          }

          const documentElement = makeEl("html");
          const head = makeEl("head");
          const body = makeEl("body");
          const rootEl = makeEl("main");
          rootEl.setAttribute("data-ocean-rescue-ready", "false");
          const statusEl = makeEl("p");
          const profileSection = makeEl("section");
          const profileName = makeEl("p");
          const profileList = makeEl("div");
          const profileContinue = makeEl("button");
          const missionSection = makeEl("section");
          const missionList = makeEl("div");
          const gupSection = makeEl("section");
          gupSection.hidden = true;
          const gupMission = makeEl("p");
          const gupList = makeEl("div");
          const gupActions = makeEl("div");
          const gupBack = makeEl("button");
          const gupLaunch = makeEl("button");

          const elements = {
            "ocean-rescue-root": rootEl,
            "ocean-rescue-status": statusEl,
            "ocean-rescue-profile-choice": profileSection,
            "ocean-rescue-profile-player-name": profileName,
            "ocean-rescue-profile-animal-list": profileList,
            "ocean-rescue-profile-continue": profileContinue,
            "ocean-rescue-mission-select": missionSection,
            "ocean-rescue-mission-list": missionList,
            "ocean-rescue-gup-select": gupSection,
            "ocean-rescue-gup-mission": gupMission,
            "ocean-rescue-gup-list": gupList,
            "ocean-rescue-gup-actions": gupActions,
            "ocean-rescue-gup-back": gupBack,
            "ocean-rescue-gup-launch": gupLaunch,
          };

          const document = {
            readyState: "loading",
            documentElement,
            head,
            body,
            createElement: makeEl,
            getElementById(id) {
              return Object.prototype.hasOwnProperty.call(elements, id) ? elements[id] : null;
            },
            addEventListener(type, fn) {
              (docListeners[type] = docListeners[type] || []).push(fn);
            },
          };

          const location = {
            href: "http://127.0.0.1:8000/ocean-rescue/index.html",
            origin: "http://127.0.0.1:8000",
            pathname: "/ocean-rescue/index.html",
            assign(url) { navigations.push({ type: "assign", url: String(url) }); },
            replace(url) { navigations.push({ type: "replace", url: String(url) }); },
          };

          const sessionStorage = {
            getItem(k) { return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
            setItem(k, v) {
              if (opts.failStorageWrite) throw new Error("quota");
              store[k] = String(v);
            },
            removeItem(k) { delete store[k]; },
          };
          const localStorage = {
            getItem(k) { return Object.prototype.hasOwnProperty.call(localStore, k) ? localStore[k] : null; },
            setItem(k, v) { localStore[k] = String(v); },
            removeItem(k) { delete localStore[k]; },
          };

          const RealDate = Date;
          function FakeDate(...args) {
            if (args.length === 0) return new RealDate(now);
            return new RealDate(...args);
          }
          FakeDate.now = () => now;

              const windowObj = {
                PIXI: {},
                location,
                sessionStorage,
                localStorage,
                document,
                URL,
                Date: FakeDate,
                alert(msg) { alerts.push(String(msg)); },
                setTimeout(fn, ms) {
                  const id = intervals.length + 1;
                  intervals.push({ id, fn, ms, cleared: false });
                  return id;
                },
                clearTimeout(id) {
                  const found = intervals.find((item) => item.id === id);
                  if (found) found.cleared = true;
                },
                addEventListener(type, fn) {
                  (winListeners[type] = winListeners[type] || []).push(fn);
                },
              };
              windowObj.window = windowObj;

              const sandbox = {
                window: windowObj,
                document,
                location,
                sessionStorage,
                localStorage,
                URL,
                Date: FakeDate,
                Math,
                Number,
                String,
                Boolean,
                Array,
                Object,
                JSON,
                Error,
                TypeError,
                Promise,
                Set,
                Map,
                WeakMap,
                Symbol,
                Uint8Array,
                Float32Array,
                Int32Array,
                parseInt,
                parseFloat,
                isNaN,
                isFinite,
                setTimeout: windowObj.setTimeout,
                clearTimeout: windowObj.clearTimeout,
                alert: windowObj.alert,
                console,
              };
          sandbox.globalThis = windowObj;
          vm.createContext(sandbox);
          vm.runInContext(appBundle, sandbox, { filename: "ocean-rescue-app.js" });

          if (windowObj.OceanRescue && windowObj.OceanRescue.RenderRuntime) {
            windowObj.OceanRescue.RenderRuntime.boot = function () {
              renderBootCalls += 1;
              return Promise.resolve();
            };
          }

          return {
            window: windowObj,
            document,
            documentElement,
            body,
            rootEl,
            store,
            navigations,
            alerts,
            intervals,
            fireDomReady() {
              document.readyState = "complete";
              for (const fn of docListeners.DOMContentLoaded || []) fn();
            },
            setNow(nextNow) { now = nextNow; },
            getRenderBootCalls() { return renderBootCalls; },
          };
        }

        (async () => {
          // 1. Direct navigation without session (even with old math daily goal completed) locks Ocean Rescue
          const unentitled = runOceanBundle({
            localSeed: {
              aiden_math_daily_goal_v1: JSON.stringify({
                date: "2026-10-23",
                completed: true,
                solvedCount: 20,
              }),
            },
            sessionSeed: { [KEY]: "{" },
          });
          assert.strictEqual(unentitled.documentElement.dataset.studyGameLocked, "true");
          unentitled.fireDomReady();
          await Promise.resolve();
          assert.strictEqual(unentitled.getRenderBootCalls(), 0, "unentitled visit must not boot Pixi runtime");
          assert.strictEqual(unentitled.rootEl.getAttribute("data-ocean-rescue-ready"), "false");
          assert.strictEqual(unentitled.window.StudyGameAdmission.isPlaying("ocean-rescue"), false);
          assert.strictEqual(unentitled.window.OceanRescue.App.boot(), false, "manual App.boot() must also reject when unentitled");

          const dialog = unentitled.body.children.find((c) => c.className === "study-game-choice");
          assert.ok(dialog && dialog.open, "direct unentitled visit must open subject picker dialog");
          const subjectGrid = dialog.children.find((c) => c.className === "study-game-subjects");
          assert.strictEqual(subjectGrid.children.length, 4);

          // Selecting Korean starts learning session for ocean-rescue and redirects to ../domains/korean/index.html
          subjectGrid.children[2].click();
          assert.deepStrictEqual(JSON.parse(unentitled.store[KEY]), {
            version: 1,
            phase: "learning",
            game: "ocean-rescue",
            subject: "korean",
            correct: 0,
          });
          assert.strictEqual(unentitled.navigations[0].url, "http://127.0.0.1:8000/domains/korean/index.html");

          // 2. Escape on direct gate redirects home instead of unlocking Ocean Rescue
          const escCase = runOceanBundle({});
          escCase.fireDomReady();
          const escDialog = escCase.body.children.find((c) => c.className === "study-game-choice");
          let cancelPrevented = false;
          escDialog.dispatchEvent({
            type: "cancel",
            preventDefault() { cancelPrevented = true; },
          });
          assert.strictEqual(cancelPrevented, true);
          assert.strictEqual(escCase.navigations[0].type, "replace");
          assert.strictEqual(escCase.navigations[0].url, "http://127.0.0.1:8000/index.html");

          // 3. Storage write failure alerts and stays locked without navigating
          const storageFail = runOceanBundle({ failStorageWrite: true });
          storageFail.fireDomReady();
          const failDialog = storageFail.body.children.find((c) => c.className === "study-game-choice");
          failDialog.children.find((c) => c.className === "study-game-subjects").children[0].click();
          assert.strictEqual(storageFail.alerts.length, 1);
          assert.strictEqual(storageFail.navigations.length, 0);
          assert.strictEqual(storageFail.documentElement.dataset.studyGameLocked, "true");

          // 4. Valid 5-minute playing session unlocks Ocean Rescue, shows countdown clock, and expires to home
          const startNow = 1700000000000;
          const entitled = runOceanBundle({
            now: startNow,
            sessionSeed: {
              [KEY]: JSON.stringify({
                version: 1,
                phase: "playing",
                game: "ocean-rescue",
                subject: "math",
                correct: 5,
                startedAt: startNow,
                deadline: startNow + 300000,
              }),
            },
          });
          entitled.fireDomReady();
          await Promise.resolve();
          assert.strictEqual(entitled.documentElement.dataset.studyGameLocked, undefined);
          assert.strictEqual(entitled.window.StudyGameAdmission.isPlaying("ocean-rescue"), true);
          assert.strictEqual(entitled.rootEl.getAttribute("data-ocean-rescue-ready"), "true");
          const clock = entitled.body.children.find((c) => c.className === "study-game-clock");
          assert.ok(clock && clock.textContent.includes("5:00 남음"));

          // Advance past 5 minutes and fire interval tick -> clears session and redirects home
          entitled.setNow(startNow + 300001);
          assert.ok(entitled.intervals.length >= 1);
          entitled.intervals[0].fn();
          assert.strictEqual(entitled.store[KEY], undefined);
          assert.strictEqual(entitled.navigations[0].type, "replace");
          assert.strictEqual(entitled.navigations[0].url, "http://127.0.0.1:8000/index.html");

          console.log(JSON.stringify({ ok: true }));
        })().catch((err) => {
          console.error(err);
          process.exit(1);
        });
        """
    )
    result = _run_node(node_script)
    assert result["ok"] is True
