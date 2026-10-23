/**
 * Gate Dino Escape behind the shared per-entry learning session.
 * Keep the 3D entrypoint unloaded until admission is granted.
 */

function initializeAdmissionGate() {
  const gate = document.getElementById("dino-admission-gate");
  const game = document.getElementById("game-shell");
  if (!gate || !game) return;

  let gameLoaded = false;
  let loading = false;

  const admitIfEligible = () => {
    if (!window.StudyGameAdmission?.isPlaying("dino")) return false;

    gate.hidden = true;
    game.hidden = false;
    if (gameLoaded || loading) return true;

    loading = true;
    import("./dino-escape.js")
      .then(() => {
        gameLoaded = true;
      })
      .catch((error) => {
        loading = false;
        console.error("Dino Escape failed to load", error);
        gate.hidden = false;
        game.hidden = true;
        const message = document.getElementById("dino-admission-message");
        if (message) {
          message.textContent = "게임 파일을 불러오지 못했어요. 새로고침한 뒤 다시 시도해 주세요.";
        }
      });
    return true;
  };

  admitIfEligible();
  window.addEventListener("storage", (event) => {
    if (!event.key || event.key === "aiden_study_game_admission_v1") admitIfEligible();
  });
  window.addEventListener("pageshow", admitIfEligible);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") admitIfEligible();
  });
}

if (typeof document !== "undefined") {
  initializeAdmissionGate();
}
