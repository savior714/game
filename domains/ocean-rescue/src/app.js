(function () {
  var State = window.OceanRescue.State;
  var Missions = window.OceanRescue.Missions;
  var Gups = window.OceanRescue.Gups;
  var Launch = window.OceanRescue.Launch;

  var controlsBound = false;
  var launchSequenceCounter = 0;
  var activeLaunchSequence = null;
  var launchTimerId = null;
  var goalTimerId = null;
  var goalSequenceId = null;

  function missionById(missionId) {
    var catalog = Missions.Catalog;
    for (var i = 0; i < catalog.length; i += 1) {
      if (catalog[i].id === missionId) {
        return catalog[i];
      }
    }
    return null;
  }

  function missionTitleById(missionId) {
    var mission = missionById(missionId);
    return mission === null ? null : mission.title;
  }

  function gupById(gupId) {
    var catalog = Gups.Catalog;
    for (var i = 0; i < catalog.length; i += 1) {
      if (catalog[i].id === gupId) {
        return catalog[i];
      }
    }
    return null;
  }

  function renderMissionSelect(options) {
    var section = document.getElementById("ocean-rescue-mission-select");
    var list = document.getElementById("ocean-rescue-mission-list");
    if (!section || !list) {
      return false;
    }
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.MISSION_SELECT) {
      return false;
    }
    list.innerHTML = "";
    var focusMissionId = null;
    if (
      options &&
      typeof options === "object" &&
      typeof options.focusMissionId === "string"
    ) {
      focusMissionId = options.focusMissionId;
    }
    var progression = Missions.getSnapshot();
    var catalog = Missions.Catalog;
    var focusCard = null;
    for (var i = 0; i < catalog.length; i += 1) {
      var mission = catalog[i];
      var unlocked =
        progression.unlockedMissionIds.indexOf(mission.id) !== -1;
      var completed =
        progression.completedMissionIds.indexOf(mission.id) !== -1;
      var isNew = progression.newMissionIds.indexOf(mission.id) !== -1;

      var button = document.createElement("button");
      button.type = "button";
      button.setAttribute("data-mission-id", mission.id);
      button.disabled = !unlocked;

      var title = document.createElement("span");
      title.className = "ocean-rescue-mission-title";
      title.textContent = mission.title;

      var companion = document.createElement("span");
      companion.className = "ocean-rescue-mission-companion";
      companion.textContent = mission.companion;

      var summary = document.createElement("span");
      summary.className = "ocean-rescue-mission-summary";
      summary.textContent = mission.summary;

      var status = document.createElement("span");
      status.className = "ocean-rescue-mission-status";
      if (completed) {
        status.textContent = "Completed";
      } else if (unlocked) {
        status.textContent = "Available";
      } else {
        status.textContent = "Locked";
      }

      button.appendChild(title);
      button.appendChild(companion);
      button.appendChild(summary);
      button.appendChild(status);

      if (isNew) {
        var newBadge = document.createElement("span");
        newBadge.className = "ocean-rescue-mission-new";
        newBadge.textContent = "New!";
        button.appendChild(newBadge);
      }

      if (unlocked && typeof button.addEventListener === "function") {
        button.addEventListener("click", (function (id) {
          return function () {
            selectMission(id);
          };
        })(mission.id));
      }

      list.appendChild(button);

      if (focusMissionId === mission.id && unlocked && isNew) {
        focusCard = button;
      }
    }
    section.style.display = "block";
    if (focusCard) {
      focusCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
    return true;
  }

  function renderGupSelect() {
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.GUP_SELECT) {
      return false;
    }
    var progression = Missions.getSnapshot();
    var mission = missionById(progression.selectedMissionId);
    if (mission === null) {
      return false;
    }
    var section = document.getElementById("ocean-rescue-gup-select");
    var list = document.getElementById("ocean-rescue-gup-list");
    if (!section || !list) {
      return false;
    }
    list.innerHTML = "";
    var gupSnapshot = Gups.getSnapshot();
    var catalog = Gups.Catalog;
    for (var i = 0; i < catalog.length; i += 1) {
      var gup = catalog[i];
      var button = document.createElement("button");
      button.type = "button";
      button.setAttribute("data-gup-id", gup.id);
      button.setAttribute(
        "aria-pressed",
        gup.id === gupSnapshot.selectedGupId ? "true" : "false"
      );
      button.disabled = false;

      var name = document.createElement("span");
      name.className = "ocean-rescue-gup-name";
      name.textContent = gup.name;

      var description = document.createElement("span");
      description.className = "ocean-rescue-gup-description";
      description.textContent = gup.description;

      button.appendChild(name);
      button.appendChild(description);

      if (typeof button.addEventListener === "function") {
        button.addEventListener("click", (function (id) {
          return function () {
            selectGup(id);
          };
        })(gup.id));
      }

      list.appendChild(button);
    }
    var missionSection = document.getElementById("ocean-rescue-mission-select");
    if (missionSection) {
      missionSection.style.display = "none";
    }
    var missionText = document.getElementById("ocean-rescue-gup-mission");
    if (missionText) {
      missionText.textContent = "Mission: " + mission.title;
    }
    section.hidden = false;
    return true;
  }

  function selectGup(gupId) {
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.GUP_SELECT) {
      return false;
    }
    if (!Gups.selectGup(gupId)) {
      return false;
    }
    var gup = gupById(gupId);
    if (gup === null) {
      return false;
    }
    var section = document.getElementById("ocean-rescue-gup-select");
    var list = document.getElementById("ocean-rescue-gup-list");
    if (section) {
      section.setAttribute("data-selected-gup-id", gupId);
    }
    if (list) {
      var buttons = list.querySelectorAll("button");
      for (var i = 0; i < buttons.length; i += 1) {
        var id = buttons[i].getAttribute("data-gup-id");
        buttons[i].setAttribute(
          "aria-pressed",
          id === gupId ? "true" : "false"
        );
      }
    }
    var launch = document.getElementById("ocean-rescue-gup-launch");
    if (launch) {
      launch.disabled = false;
    }
    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = "Selected GUP: " + gup.name;
    }
    return true;
  }

  function backToMissionSelect() {
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.GUP_SELECT) {
      return false;
    }
    var token = State.beginTransition(State.Phases.MISSION_SELECT);
    if (token === null) {
      return false;
    }
    if (!State.completeTransition(token)) {
      return false;
    }
    var gupSection = document.getElementById("ocean-rescue-gup-select");
    if (gupSection) {
      gupSection.hidden = true;
      gupSection.removeAttribute("data-selected-gup-id");
    }
    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.removeAttribute("data-launch-mission-id");
      root.removeAttribute("data-launch-gup-id");
      root.removeAttribute("data-launch-ready");
    }
    var missionSection = document.getElementById("ocean-rescue-mission-select");
    if (missionSection) {
      missionSection.removeAttribute("data-selected-mission-id");
    }
    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = "Choose a mission";
    }
    renderMissionSelect();
    return true;
  }

  function launchSelectedGup() {
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.GUP_SELECT) {
      return false;
    }
    var progression = Missions.getSnapshot();
    var mission = missionById(progression.selectedMissionId);
    if (mission === null) {
      return false;
    }
    var gupSnapshot = Gups.getSnapshot();
    var gup = gupById(gupSnapshot.selectedGupId);
    if (gup === null) {
      return false;
    }
    var token = State.beginTransition(State.Phases.LAUNCH);
    if (token === null) {
      return false;
    }
    if (!State.completeTransition(token)) {
      return false;
    }
    Gups.confirmSelection();

    var list = document.getElementById("ocean-rescue-gup-list");
    if (list) {
      var buttons = list.querySelectorAll("button");
      for (var i = 0; i < buttons.length; i += 1) {
        buttons[i].disabled = true;
      }
    }
    var back = document.getElementById("ocean-rescue-gup-back");
    if (back) {
      back.disabled = true;
    }
    var launch = document.getElementById("ocean-rescue-gup-launch");
    if (launch) {
      launch.disabled = true;
    }
    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-launch-mission-id", mission.id);
      root.setAttribute("data-launch-gup-id", gup.id);
      root.setAttribute("data-launch-ready", "true");
    }
    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent =
        "Launch ready: " + gup.name + " — " + mission.title;
    }
    var launchEls = resolveLaunchElements();
    if (launchEls !== null) {
      var content = Launch.getMissionContent(mission.id);
      if (content !== null) {
        startLaunchPresentation(mission, gup, content, launchEls);
      }
    }
    return true;
  }

  function resolveLaunchElements() {
    var launchSection = document.getElementById("ocean-rescue-launch");
    var gupName = document.getElementById("ocean-rescue-launch-gup-name");
    var companion = document.getElementById("ocean-rescue-launch-companion");
    var briefing = document.getElementById("ocean-rescue-launch-briefing");
    var goalBanner = document.getElementById("ocean-rescue-goal-banner");
    if (!launchSection || !gupName || !companion || !briefing || !goalBanner) {
      return null;
    }
    return {
      launchSection: launchSection,
      gupName: gupName,
      companion: companion,
      briefing: briefing,
      goalBanner: goalBanner
    };
  }

  function setLaunchActiveClass(launchSection, active) {
    if (
      typeof launchSection.classList === "object" &&
      typeof launchSection.classList.add === "function" &&
      typeof launchSection.classList.remove === "function"
    ) {
      if (active) {
        launchSection.classList.add("ocean-rescue-launch-active");
      } else {
        launchSection.classList.remove("ocean-rescue-launch-active");
      }
      return;
    }
    var token = "ocean-rescue-launch-active";
    var names = String(launchSection.className || "").split(/\s+/);
    var index = names.indexOf(token);
    if (active && index === -1) {
      names.push(token);
    }
    if (!active && index !== -1) {
      names.splice(index, 1);
    }
    launchSection.className = names.join(" ").trim();
  }

  function clearLaunchTimer() {
    if (launchTimerId === null) {
      return;
    }
    if (typeof window.clearTimeout === "function") {
      window.clearTimeout(launchTimerId);
    }
    launchTimerId = null;
  }

  function clearGoalTimer() {
    if (goalTimerId === null) {
      return;
    }
    if (typeof window.clearTimeout === "function") {
      window.clearTimeout(goalTimerId);
    }
    goalTimerId = null;
    goalSequenceId = null;
  }

  function clearGoalBanner(goalBanner) {
    if (!goalBanner) {
      return;
    }
    goalBanner.hidden = true;
    goalBanner.textContent = "";
  }

  function startLaunchPresentation(mission, gup, content, els) {
    launchSequenceCounter += 1;
    var sequence = {
      sequenceId: launchSequenceCounter,
      missionId: mission.id,
      gupId: gup.id,
      missionContent: content
    };
    activeLaunchSequence = sequence;

    clearGoalTimer();

    var gupSection = document.getElementById("ocean-rescue-gup-select");
    if (gupSection) {
      gupSection.hidden = true;
    }
    clearGoalBanner(els.goalBanner);

    els.gupName.textContent = gup.name;
    els.companion.textContent = mission.companion + ":";
    els.briefing.textContent = content.briefing;

    els.launchSection.hidden = false;
    setLaunchActiveClass(els.launchSection, true);

    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-launch-sequence", "active");
      root.setAttribute("data-launch-skipped", "false");
    }

    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = content.briefing;
    }

    scheduleLaunchCompletion(sequence);
  }

  function scheduleLaunchCompletion(sequence) {
    clearLaunchTimer();
    if (typeof window.setTimeout !== "function") {
      return;
    }
    launchTimerId = window.setTimeout(function () {
      completeLaunchPresentation(sequence);
    }, Launch.DurationMs);
  }

  function completeLaunchPresentation(sequence) {
    if (activeLaunchSequence === null) {
      return false;
    }
    if (!sequence || typeof sequence !== "object") {
      return false;
    }
    if (sequence.sequenceId !== activeLaunchSequence.sequenceId) {
      return false;
    }
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.LAUNCH) {
      return false;
    }
    return finalizeLaunch(sequence, false);
  }

  function skipLaunch() {
    var sequence = activeLaunchSequence;
    if (sequence === null) {
      return false;
    }
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.LAUNCH) {
      return false;
    }
    clearLaunchTimer();
    return finalizeLaunch(sequence, true);
  }

  function finalizeLaunch(sequence, skipped) {
    var token = State.beginTransition(State.Phases.TRAVEL);
    if (token === null) {
      return false;
    }
    if (!State.completeTransition(token)) {
      return false;
    }
    activeLaunchSequence = null;
    clearLaunchTimer();

    var launchSection = document.getElementById("ocean-rescue-launch");
    if (launchSection) {
      launchSection.hidden = true;
      setLaunchActiveClass(launchSection, false);
    }
    var stage = document.getElementById("ocean-rescue-stage");
    if (stage) {
      stage.hidden = false;
      stage.setAttribute("aria-hidden", "false");
    }

    var goalBanner = document.getElementById("ocean-rescue-goal-banner");
    if (goalBanner) {
      showGoalBanner(goalBanner, sequence);
    }

    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-travel-mission-id", sequence.missionId);
      root.setAttribute("data-travel-gup-id", sequence.gupId);
      root.setAttribute("data-travel-ready", "true");
      root.setAttribute("data-launch-skipped", skipped ? "true" : "false");
      root.removeAttribute("data-launch-ready");
      root.removeAttribute("data-launch-sequence");
    }

    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = "Travel ready: " + sequence.missionContent.goal;
    }

    return true;
  }

  function showGoalBanner(goalBanner, sequence) {
    clearGoalTimer();
    goalSequenceId = sequence.sequenceId;
    goalBanner.hidden = false;
    goalBanner.textContent = sequence.missionContent.goal;
    if (typeof window.setTimeout !== "function") {
      return;
    }
    goalTimerId = window.setTimeout(function () {
      hideGoalBanner(sequence.sequenceId);
    }, Launch.GoalDurationMs);
  }

  function hideGoalBanner(sequenceId) {
    if (goalSequenceId !== sequenceId) {
      return;
    }
    if (activeLaunchSequence !== null) {
      return;
    }
    var goalBanner = document.getElementById("ocean-rescue-goal-banner");
    if (!goalBanner) {
      return;
    }
    goalBanner.hidden = true;
    goalBanner.textContent = "";
    goalTimerId = null;
    goalSequenceId = null;
  }

  function selectMission(missionId) {
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.MISSION_SELECT) {
      return false;
    }
    if (!Missions.isUnlocked(missionId)) {
      return false;
    }
    var token = State.beginTransition(State.Phases.GUP_SELECT);
    if (token === null) {
      return false;
    }
    if (!State.completeTransition(token)) {
      return false;
    }
    Missions.selectMission(missionId);
    Missions.markMissionViewed(missionId);

    var gupSection = document.getElementById("ocean-rescue-gup-select");
    if (gupSection) {
      Gups.prepareSelection();
      renderGupSelect();
      var status = document.getElementById("ocean-rescue-status");
      if (status) {
        var title = missionTitleById(missionId);
        status.textContent =
          "Choose a GUP for " + (title === null ? missionId : title);
      }
      return true;
    }

    var section = document.getElementById("ocean-rescue-mission-select");
    var list = document.getElementById("ocean-rescue-mission-list");
    if (section) {
      section.setAttribute("data-selected-mission-id", missionId);
    }
    if (list) {
      var buttons = list.querySelectorAll("button");
      for (var i = 0; i < buttons.length; i += 1) {
        buttons[i].disabled = true;
      }
    }
    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      var title = missionTitleById(missionId);
      status.textContent =
        "Mission selected: " + (title === null ? missionId : title);
    }
    return true;
  }

  function bindStaticControls() {
    if (controlsBound) {
      return;
    }
    var back = document.getElementById("ocean-rescue-gup-back");
    if (back && typeof back.addEventListener === "function") {
      back.addEventListener("click", function () {
        backToMissionSelect();
      });
    }
    var launch = document.getElementById("ocean-rescue-gup-launch");
    if (launch && typeof launch.addEventListener === "function") {
      launch.addEventListener("click", function () {
        launchSelectedGup();
      });
    }
    var launchSection = document.getElementById("ocean-rescue-launch");
    if (launchSection && typeof launchSection.addEventListener === "function") {
      launchSection.addEventListener("click", function () {
        skipLaunch();
      });
    }
    var skipButton = document.getElementById("ocean-rescue-launch-skip");
    if (skipButton && typeof skipButton.addEventListener === "function") {
      skipButton.addEventListener("click", function (event) {
        if (event && typeof event.stopPropagation === "function") {
          event.stopPropagation();
        }
        skipLaunch();
      });
    }
    controlsBound = true;
  }

  var App = {
    boot: function () {
      var root = document.getElementById("ocean-rescue-root");
      var status = document.getElementById("ocean-rescue-status");
      if (!root || !status) {
        return false;
      }
      if (root.getAttribute("data-ocean-rescue-ready") === "true") {
        bindStaticControls();
        return true;
      }
      var snapshot = State.getSnapshot();
      if (snapshot.phase === State.Phases.BOOT) {
        var token = State.beginTransition(State.Phases.MISSION_SELECT);
        if (token === null) {
          return false;
        }
        if (!State.completeTransition(token)) {
          return false;
        }
      }
      State.markReady();
      root.setAttribute("data-ocean-rescue-ready", "true");
      status.textContent = "Ocean Rescue ready";
      var section = document.getElementById("ocean-rescue-mission-select");
      var list = document.getElementById("ocean-rescue-mission-list");
      if (section && list) {
        renderMissionSelect();
      }
      bindStaticControls();
      return true;
    },
    renderMissionSelect: renderMissionSelect,
    selectMission: selectMission,
    renderGupSelect: renderGupSelect,
    selectGup: selectGup,
    backToMissionSelect: backToMissionSelect,
    launchSelectedGup: launchSelectedGup
  };

  window.OceanRescue.App = App;

  document.addEventListener("DOMContentLoaded", function () {
    App.boot();
  });
})();
