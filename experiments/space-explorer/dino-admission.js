/**
 * Gate Dino Escape behind completion of today's Math daily goal.
 * Keep the 3D entrypoint unloaded until admission is granted.
 */

export function isDailyGoalComplete(rawGoal, now = new Date()) {
  try {
    const goal = typeof rawGoal === "string" ? JSON.parse(rawGoal) : rawGoal;
    if (!goal || typeof goal !== "object" || Array.isArray(goal)) return false;

    const date = now instanceof Date ? now : new Date(now);
    if (!Number.isFinite(date.getTime())) return false;
    const today = [
      date.getFullYear(),
      String(date.getMonth() + 1).padStart(2, "0"),
      String(date.getDate()).padStart(2, "0"),
    ].join("-");

    return goal.schemaVersion === 1 && goal.date === today && goal.completed === true;
  } catch {
    return false;
  }
}

function hasCompletedTodayGoal() {
  try {
    return isDailyGoalComplete(
      window.localStorage.getItem("aiden_math_daily_goal_v1"),
      new Date(),
    );
  } catch {
    // Fail closed if browser storage is unavailable or blocked.
    return false;
  }
}

function initializeAdmissionGate() {
  const gate = document.getElementById("dino-admission-gate");
  const game = document.getElementById("game-shell");
  if (!gate || !game) return;

  let gameLoaded = false;
  let loading = false;

  const admitIfEligible = () => {
    if (!hasCompletedTodayGoal()) return false;

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
    if (!event.key || event.key === "aiden_math_daily_goal_v1") admitIfEligible();
  });
  window.addEventListener("pageshow", admitIfEligible);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") admitIfEligible();
  });
}

if (typeof document !== "undefined") {
  initializeAdmissionGate();
}
