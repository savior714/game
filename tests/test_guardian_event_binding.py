from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "domains/reward/guardian/guardian-events.js"

HARNESS = r"""
const fs = require('fs');
const vm = require('vm');
const listeners = { input: [], click: [] };
const calls = {
  originalSetSubject: 0,
  slider: 0,
  save: 0,
  weekly: 0,
  custom: 0,
  growth: 0,
  deleteWeekly: [],
};

const document = {
  addEventListener(type, listener) {
    if (!listeners[type]) listeners[type] = [];
    listeners[type].push(listener);
  },
};

const window = {
  document,
  location: { href: '' },
  onSliderChange() { calls.slider += 1; },
  saveSettings() { calls.save += 1; },
  addWeeklyWord() { calls.weekly += 1; },
  addCustomReward() { calls.custom += 1; },
  showGrowthTab() { calls.growth += 1; },
  deleteWeeklyWord(index) { calls.deleteWeekly.push(index); },
};

window.setSubject = function setSubject(subject) {
  calls.originalSetSubject += 1;
  document.addEventListener('input', (e) => {
    if (e.target.id === 'level-slider' && window.onSliderChange) {
      window.onSliderChange(e.target.value);
    }
  });
  document.addEventListener('click', (e) => {
    const target = e.target.closest('[data-action]');
    if (!target) return;
    switch (target.dataset.action) {
      case 'save-settings':
        if (window.saveSettings) window.saveSettings();
        break;
    }
  });
  return subject;
};

const context = vm.createContext({ window, document, Function, Number });
const source = fs.readFileSync(process.argv[2], 'utf8');
vm.runInContext(source, context);
vm.runInContext(source, context);

window.setSubject('math');
window.setSubject('english');

function target(action, extra = {}) {
  return {
    id: extra.id,
    value: extra.value,
    dataset: { action, ...extra.dataset },
    closest(selector) { return selector === '[data-action]' ? this : null; },
  };
}

listeners.input[0]({ target: target('', { id: 'level-slider', value: '4' }) });
listeners.click[0]({ target: target('save-settings'), stopPropagation() {} });
listeners.click[0]({ target: target('add-weekly-word'), stopPropagation() {} });
listeners.click[0]({ target: target('add-custom-reward'), stopPropagation() {} });
listeners.click[0]({ target: target('show-growth'), stopPropagation() {} });
listeners.click[0]({ target: target('delete-weekly-word', { dataset: { idx: '3' } }), stopPropagation() {} });
listeners.click[0]({ target: target('go-home'), stopPropagation() {} });

console.log(JSON.stringify({ listeners, calls, href: window.location.href }));
"""


def _node() -> str:
    node = shutil.which("node")
    assert node, "node is required"
    return node


def test_guardian_delegated_handlers_bind_once_and_dispatch_once(
    tmp_path: Path,
) -> None:
    harness = tmp_path / "harness.js"
    harness.write_text(HARNESS, encoding="utf-8")
    proc = subprocess.run(
        [_node(), str(harness), str(SCRIPT)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout.strip())

    assert len(result["listeners"]["input"]) == 1
    assert len(result["listeners"]["click"]) == 1
    assert result["calls"]["originalSetSubject"] == 2
    assert result["calls"]["slider"] == 1
    assert result["calls"]["save"] == 1
    assert result["calls"]["weekly"] == 1
    assert result["calls"]["custom"] == 1
    assert result["calls"]["growth"] == 1
    assert result["calls"]["deleteWeekly"] == [3]
    assert result["href"] == "../../index.html"


def test_guardian_event_script_is_syntax_valid() -> None:
    proc = subprocess.run(
        [_node(), "--check", str(SCRIPT)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
