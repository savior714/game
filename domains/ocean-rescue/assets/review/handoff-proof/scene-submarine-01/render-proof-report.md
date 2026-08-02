# Ocean Rescue — scene-submarine-01 Post-Canonical Render Proof

- Task ID: `AIDENGAME-OCEAN-RESCUE-SUBMARINE-HANDOFF-POSTCANONICAL-RENDER-PROOF-01`
- Verdict: `RENDER_PROOF_READY`

## 1. Input lineage

- Brief SHA-256: `498c104090bf7739189d6618c08c264f6aa38e6d8dd5b1d462a0f269d0c637ce`
- Inbox SVG SHA-256: `338e71c483e9e01eba7ddc154e68ef858482c85d39d899eda493e9112df714e9`
- Inbox SVG working-copy path: `/Users/seungjulee/Desktop/Dev/.worktrees/game/AIDENGAME-OCEAN-RESCUE-SUBMARINE-HANDOFF-POSTCANONICAL-RENDER-PROOF-01/domains/ocean-rescue/assets/handoff/inbox/scene-submarine-01.svg`
- Inbox SVG canonical-checkout path: `/Users/seungjulee/Desktop/Dev/game/domains/ocean-rescue/assets/handoff/inbox/scene-submarine-01.svg`
- Structure report SVG SHA-256: `338e71c483e9e01eba7ddc154e68ef858482c85d39d899eda493e9112df714e9`
- Canonical source SHA-256: `338e71c483e9e01eba7ddc154e68ef858482c85d39d899eda493e9112df714e9`
- Art-packet `scene.submarine.sourceSha256`: `338e71c483e9e01eba7ddc154e68ef858482c85d39d899eda493e9112df714e9`
- Candidate == canonical: `True`
- Candidate == art-packet source SHA: `True`

## 2. Preexisting out-of-order canonicalization

- This asset was canonicalized before this proof (commit `9336240d8462d47cbe94bcb65935f86cb82f8318`).
- Structure gate commit: `ecf2b7aa56e4c6bb7bcf21370dbf1a3fd9aa7cf9`
- The preexisting approval metadata is recorded as preexisting state and is not re-justified here.

## 3. Structure PASS binding

- Structure report verdict: `STRUCTURE_PASS`
- Structure report asset ID: `scene-submarine-01`
- Structure report alias: `scene.submarine`
- The current inbox SVG SHA equals the structure report `svgSha256`.

## 4. Candidate/canonical/art-packet hash comparison

- `[PASS]` candidateStructureCanonicalPacket
  - inbox=338e71c483e9 structure=338e71c483e9 canonical=338e71c483e9 packet=338e71c483e9
- `[PASS]` artPacketShaMatchesApproval
  - packet=5a3e2f8cf2ee approval.artPacket=5a3e2f8cf2ee
- `[PASS]` artPacketShaMatchesAtlas
  - packet=5a3e2f8cf2ee atlas.sourcePacket=5a3e2f8cf2ee
- `[PASS]` approvalShaMatchesAtlas
  - approval=39cda1702e89 atlas.approval=39cda1702e89
- `[PASS]` sourceSetMatchesApprovalAndAtlas
  - approval.sourceSet=e45009b2953a atlas.sourceSet=e45009b2953a
- `[PASS]` sceneAtlasJsonMatchesManifest
  - file=cf2ef1f330a9 manifest=cf2ef1f330a9
- `[PASS]` sceneAtlasPngMatchesManifest
  - file=3b925f566343 manifest=3b925f566343

## 5. Atlas/runtime lineage

- Art packet SHA-256: `5a3e2f8cf2ee1bdd62ebdacae7836907baa222966822553817aa4ffc74d2542f`
- Art approval `artPacketSha256`: `5a3e2f8cf2ee1bdd62ebdacae7836907baa222966822553817aa4ffc74d2542f`
- Atlas manifest `sourcePacketSha256`: `5a3e2f8cf2ee1bdd62ebdacae7836907baa222966822553817aa4ffc74d2542f`
- Atlas manifest `sourceSetSha256`: `e45009b2953a3f6321afc3cab5a20b2f3588f1fdda03b0d1244db17514e87588`
- Scene atlas JSON SHA-256: `cf2ef1f330a9da6859d3539f6145dd1776428273acc6867afd2832a196410daf`
- Scene atlas PNG SHA-256: `3b925f566343c6b945015b3ec22d4ad13f3679109f8694b1eb2e00b89276b848`
- Render-assets.generated.js SHA-256: `30e60981540d17d7854221d725306eb16984041e76af76911e36ca47e928552f`
- Single HTML SHA-256: `978474e31585f2a0a7589808b1ae088f14780e73467b50647a304e271046382e`
- Existing validators: `validate_art_approval`, `validate_atlases`, `validate_pixi_vendor` all passed.

## 6. Isolated proof findings

- Isolated 1x: 320x200 pixel SHA `e0a53d6aaa2cff39`
  - Visible alpha bounds: {'x': 17, 'y': 15, 'width': 272, 'height': 161}
  - Alpha channel present: True
  - Check verdict: PASS
- Isolated 2x: 640x400 pixel SHA `c47145bdf6f11f95`
  - Visible alpha bounds: {'x': 35, 'y': 31, 'width': 543, 'height': 320}
  - Alpha channel present: True
  - Check verdict: PASS

## 7. In-context proof findings

- Run 1: backend=webgl sprite=travel-submarine texture=scene.submarine frame={'x': 2, 'y': 2, 'w': 271.5, 'h': 160, 'finite': True, 'nonzero': True}
  - Capture state: PASS
  - Sprite identity: PASS
  - Screenshot pixel SHA-256: `5cbd3149ef6a9dc2`
- Run 2: backend=webgl sprite=travel-submarine texture=scene.submarine frame={'x': 2, 'y': 2, 'w': 271.5, 'h': 160, 'finite': True, 'nonzero': True}
  - Capture state: PASS
  - Sprite identity: PASS
  - Screenshot pixel SHA-256: `5cbd3149ef6a9dc2`

## 8. Collision/impact-free capture state

- Terrain collision count: 0 across runs
- Terrain collision active: false
- Impact mode: contact-burst-v1, impact active: false, phase: idle
- `travel-collision-impact-root` and `travel-submarine-impact-flash` invisible

## 9. Error/network findings

- Run 1: external=0 reference=0 pageErrors=0 consoleErrors=0 unhandled=0 csp=0
- Run 2: external=0 reference=0 pageErrors=0 consoleErrors=0 unhandled=0 csp=0

## 10. Proof limitations

- The deterministic freeze uses the public `OceanRescue.TravelScene.pause()` and `OceanRescue.Travel.stop()` runtime namespaces at the moment the travel scene becomes active; the product DOM flow (mission -> GUP -> launch -> skip) is driven normally.
- Screenshot determinism was verified across two independent runs.

## 11. Final verdict

`RENDER_PROOF_READY`

## 12. Human review checklist

This checklist is intentionally left unchecked for a human reviewer.

- [ ] 오른쪽 진행 방향이 즉시 읽힌다.
- [ ] cockpit이 실제 TravelScene 크기에서 구분된다.
- [ ] rear propulsion이 hull과 구분된다.
- [ ] rescue cradle/bay가 보호형 구조 장비로 읽힌다.
- [ ] generic toy submarine보다 mission craft로 보인다.
- [ ] 장애물과 foreground 안에서도 silhouette가 유지된다.
- [ ] 주변 Ocean Rescue 자산과 색면·outline 밀도가 어울린다.
- [ ] 실제 SVG 결과를 APPROVED 또는 REJECTED로 명시했다.

