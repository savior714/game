# Ocean Rescue — otter-head-01 Post-Canonical Render Proof

- Task ID: `AIDENGAME-OCEAN-RESCUE-OTTER-HEAD-POST-CANONICAL-RENDER-PROOF-02`
- Verdict: `POST_CANONICAL_RENDER_PROOF_READY`

## 1. Input lineage

- Canonical SVG path: `domains/ocean-rescue/assets/source/characters/otter-head.svg`
- Structure report path: `domains/ocean-rescue/assets/review/handoff-intake/otter-head-01/structure-report.json`
- Pre-canonical proof manifest path: `domains/ocean-rescue/assets/review/handoff-proof/otter-head-01/manifest.json`
- Canonical source SHA-256: `87e6b35d67e0d856d389570614bb47abef9f6271402e881660f98f400e40c5ec`
- Structure report SHA-256: `bd5e5537247cce996f25c2f0ae3416adc67c08c1d49fe3a7675f6e4dd849cd29`
- Pre-canonical manifest SHA-256: `d845045d198bfbc8dc16053f4fda70d22666fa41c3d9254ae564b81fd8ac7670`

## 2. Human approval binding

- Decision: `APPROVED`
- Date: `2026-08-02`
- Input: `승인`
- Approved candidate SHA-256: `87e6b35d67e0d856d389570614bb47abef9f6271402e881660f98f400e40c5ec`
- Approved proof task: `AIDENGAME-OCEAN-RESCUE-OTTER-HEAD-HANDOFF-RENDER-PROOF-01`

## 3. Atlas repair predecessor

- Atlas repair commit: `e8bb970c0c8dac394c662bead5fbc3d4160927c3`
- Repair ancestry of HEAD: `PASS`
- Unmasked production paste `page_img.paste(trimmed_img, (content_x, content_y))`

## 4. Canonical source and packet binding

- Canonical source SHA-256: `87e6b35d67e0d856d389570614bb47abef9f6271402e881660f98f400e40c5ec`
- Art packet SHA-256: `320b6f6dae13e161e00ea9e1ba79e837096b9cfd1e2e443af0b1c20882796ea8`
- Art packet asset sourceSha256: `87e6b35d67e0d856d389570614bb47abef9f6271402e881660f98f400e40c5ec`
- Art approval SHA-256: `7921e21e25098a36593117a5e3cabb525726cd4afc07364a040d9f834250ddd4`
- Atlas manifest SHA-256: `6de43eb8e56e944fadb22d6d2b247b118e7f2346b27a921bae6dbdf51f73c071`

## 5. Canonical isolated render

- Isolated 1x: 200x200 pixel SHA `4a0bd666e394ae222b6d64d050996de56988b38d47ecf262fe4742f1d68b577b`
  - Approved pixel SHA: `4a0bd666e394ae222b6d64d050996de56988b38d47ecf262fe4742f1d68b577b`
  - Visible alpha bounds: {'x': 15, 'y': 21, 'width': 170, 'height': 169}
  - Check verdict: PASS
- Isolated 2x: 400x400 pixel SHA `dee47164ab12d192d93fd66efdbb0909febac683a0be09aafe56c3ae92221d14`
  - Approved pixel SHA: `dee47164ab12d192d93fd66efdbb0909febac683a0be09aafe56c3ae92221d14`
  - Visible alpha bounds: {'x': 30, 'y': 42, 'width': 340, 'height': 338}
  - Check verdict: PASS

## 6. Atlas-frame RGBA reconstruction

- Frame: {'x': 4, 'y': 4, 'w': 340, 'h': 338}
- sourceSize: {'w': 400, 'h': 400}
- spriteSourceSize: {'x': 30, 'y': 42, 'w': 340, 'h': 338}
- rotated: False
- trimmed: True
- Reconstructed size: [400, 400]
- Reconstructed pixel SHA-256: `dee47164ab12d192d93fd66efdbb0909febac683a0be09aafe56c3ae92221d14`
- Canonical 2x pixel SHA-256: `dee47164ab12d192d93fd66efdbb0909febac683a0be09aafe56c3ae92221d14`
- Mismatched pixels: 0
- Mismatched channels: 0
- Byte-exact: `PASS`

## 7. Production runtime texture identity

- Run 1: head sprite `sea-otter-head` texture `otter.head` backend=webgl
  - Texture orig 200x200 resolution 2
  - Position (0, -42) scale 0.62x0.62 anchor {'x': 0.5, 'y': 0.55}
  - Candidate injection absent: PASS
  - Overlay texture identities: PASS
  - Frozen at deterministic t=0: True
- Run 2: head sprite `sea-otter-head` texture `otter.head` backend=webgl
  - Texture orig 200x200 resolution 2
  - Position (0, -42) scale 0.62x0.62 anchor {'x': 0.5, 'y': 0.55}
  - Candidate injection absent: PASS
  - Overlay texture identities: PASS
  - Frozen at deterministic t=0: True

## 8. Face-state assembly

- `base-only`: PASS
- `neutral`: PASS
- `concern`: PASS
- `smile`: PASS
- Contact sheet: `face-rig-contact-sheet.png`
- Full context: `sea-turtle-context.png`

## 9. Two-run determinism

- Two-run deterministic: PASS

## 10. Error and network findings

- Run 1: external=0 pageErrors=0 consoleErrors=0 unhandled=0 csp=0
- Run 2: external=0 pageErrors=0 consoleErrors=0 unhandled=0 csp=0

## 11. Production/evidence immutability

- Production files byte-unchanged: `True`
- Pre-canonical evidence byte-unchanged: `True`

## 12. Final verdict

`POST_CANONICAL_RENDER_PROOF_READY`

