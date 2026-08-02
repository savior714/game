# Ocean Rescue — otter-head-01 Head/Face-Rig Render Proof

- Task ID: `AIDENGAME-OCEAN-RESCUE-OTTER-HEAD-HANDOFF-RENDER-PROOF-01`
- Verdict: `RENDER_PROOF_READY`

## 1. Input lineage

- Brief path: `domains/ocean-rescue/assets/handoff/briefs/otter-head-01.md`
- Inbox SVG path: `domains/ocean-rescue/assets/handoff/inbox/otter-head-01.svg`
- Structure report path: `domains/ocean-rescue/assets/review/handoff-intake/otter-head-01/structure-report.json`
- Candidate SVG SHA-256: `87e6b35d67e0d856d389570614bb47abef9f6271402e881660f98f400e40c5ec`
- Structure report SHA-256: `bd5e5537247cce996f25c2f0ae3416adc67c08c1d49fe3a7675f6e4dd849cd29`
- Structure report verdict: `STRUCTURE_PASS`
- Structure report `svgSha256` equals candidate: `True`

## 2. Isolated proof findings

- Isolated 1x: 200x200 pixel SHA `4a0bd666e394ae22`
  - Visible alpha bounds: {'x': 15, 'y': 21, 'width': 170, 'height': 169}
  - Alpha channel present: True
  - Check verdict: PASS
- Isolated 2x: 400x400 pixel SHA `dee47164ab12d192`
  - Visible alpha bounds: {'x': 30, 'y': 42, 'width': 340, 'height': 338}
  - Alpha channel present: True
  - Check verdict: PASS

## 3. In-context proof findings

- Run 1: backend=webgl head=sea-otter-head texture=candidate-otter-head-01
  - Capture state: PASS
  - Head sprite identity: PASS
  - Face state visibility: PASS
  - Other textures unchanged: PASS
  - Frozen at deterministic t=0: True
- Run 2: backend=webgl head=sea-otter-head texture=candidate-otter-head-01
  - Capture state: PASS
  - Head sprite identity: PASS
  - Face state visibility: PASS
  - Other textures unchanged: PASS
  - Frozen at deterministic t=0: True

## 4. Head sprite rig contract

- Label: `sea-otter-head`
- Rig offset: (0, -42)
- Scale: 0.62x0.62
- Anchor: {'x': 0.5, 'y': 0.55}
- Candidate texture label: `candidate-otter-head-01`
- Candidate texture source: 200x200
- Display bounds: {'x': 526.314551589523, 'y': 308.27147284328487, 'width': 127.06092911161147, 'height': 127.06092911161147}

## 5. Face states captured

- `base-only`: rig-base-only.png
- `neutral`: rig-neutral.png
- `concern`: rig-concern.png
- `smile`: rig-smile.png
- Contact sheet: `face-rig-contact-sheet.png`
- Full context: `sea-turtle-context.png`

## 6. Determinism across two runs

- Two-run deterministic: PASS

## 7. Error/network findings

- Run 1: external=0 pageErrors=0 consoleErrors=0 unhandled=0 csp=0
- Run 2: external=0 pageErrors=0 consoleErrors=0 unhandled=0 csp=0

## 8. Proof limitations

- The candidate raster is applied only to the `sea-otter-head` sprite instance during the proof; the canonical atlas texture `otter.head` is never modified.
- The scene is frozen via `OceanRescue.SeaTurtleScene.pause()` in a mutation-observer microtask the moment `data-rescue-phase=active` and `data-sea-turtle-scene=active` are both set, so the scene renders at deterministic animation time t=0.
- Eye and mouth overlays are the existing production atlas textures.

## 9. Final verdict

`RENDER_PROOF_READY`

## 10. Human review checklist

This checklist is intentionally left unchecked for a human reviewer.

- [ ] 귀가 실제 게임 크기에서 잘 보인다.
- [ ] 머리가 수달처럼 읽힌다.
- [ ] 주둥이와 코가 명확하다.
- [ ] 눈 overlay가 머리 안의 자연스러운 위치에 있다.
- [ ] 입 overlay가 주둥이 위에 자연스럽게 놓인다.
- [ ] 눈이나 입이 두 겹으로 보이지 않는다.
- [ ] Neutral 표정이 자연스럽다.
- [ ] Concern 표정이 자연스럽다.
- [ ] Smile 표정이 자연스럽다.
- [ ] 기존 몸통·팔·꼬리와 디자인이 어울린다.

