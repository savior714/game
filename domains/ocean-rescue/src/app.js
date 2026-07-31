(function () {
  var State = window.OceanRescue.State;
  var Missions = window.OceanRescue.Missions;
  var Gups = window.OceanRescue.Gups;
  var Launch = window.OceanRescue.Launch;
  var Travel = window.OceanRescue.Travel || null;
  var Terrain = window.OceanRescue.Terrain || null;
  var Rescue = window.OceanRescue.Rescue || null;
  var SeaTurtle = window.OceanRescue.SeaTurtle || null;
  var Crab = window.OceanRescue.Crab || null;
  var YoungWhale = window.OceanRescue.YoungWhale || null;
  var MissionSuccess = window.OceanRescue.MissionSuccess || null;

  var controlsBound = false;
  var launchSequenceCounter = 0;
  var activeLaunchSequence = null;
  var launchTimerId = null;
  var goalTimerId = null;
  var goalSequenceId = null;

  var travelRunIdCounter = 0;
  var activeTravelRunId = null;
  var travelFrameId = null;
  var travelLastTimestamp = null;
  var travelInputBound = false;
  var travelCanvas = null;

  var rescueSequenceCounter = 0;
  var activeRescueSequence = null;
  var siteTransitionTimerId = null;
  var tutorialTimerId = null;
  var rescueInputBound = false;

  var seaTurtleTimerId = null;
  var seaTurtleFeedbackSequence = null;
  var seaTurtlePointerId = null;
  var seaTurtlePointerCaptureEl = null;
  var seaTurtleInputBound = false;
  var seaTurtleRenderMarker = false;

  var crabTimerId = null;
  var crabFeedbackSequence = null;
  var crabHoldTimerId = null;
  var crabPointerId = null;
  var crabPointerCaptureEl = null;

  var youngWhaleTimerId = null;
  var youngWhaleFeedbackSequence = null;
  var youngWhalePointerId = null;
  var youngWhalePointerCaptureEl = null;

  var missionSuccessSequenceCounter = 0;
  var activeMissionSuccessSequence = null;
  var missionSuccessTimerId = null;
  var missionSuccessInputBound = false;
  var missionCompleteActionsBound = false;
  var missionCompleteActionLock = false;

  var pointerActive = false;
  var pointerId = null;
  var pointerStartClientY = null;
  var pointerStartStageY = null;
  var pointerDragging = false;

  var terrainPalettes = {
    "coral-reef": ["#ff6b6b", "#ff9ff3", "#3ddad7"],
    "sandy-reef": ["#e2c290", "#d4a373", "#a47551"],
    "rocky-canyon": ["#7a8b99", "#5c6b7a", "#3f4b57"]
  };

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

  function resolveContinueFocusMissionId(newlyUnlockedMissionId) {
    if (typeof newlyUnlockedMissionId === "string") {
      return newlyUnlockedMissionId;
    }
    var progression = Missions.getSnapshot();
    if (progression.newMissionIds.length === 0) {
      return null;
    }
    var catalog = Missions.Catalog;
    for (var i = 0; i < catalog.length; i += 1) {
      if (progression.newMissionIds.indexOf(catalog[i].id) !== -1) {
        return catalog[i].id;
      }
    }
    return null;
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
    if (focusCard && typeof focusCard.scrollIntoView === "function") {
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

    startTravelRuntime();

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

  function startTerrainRuntime() {
    if (!Terrain) {
      return;
    }
    var root = document.getElementById("ocean-rescue-root");
    var missionId = root ? root.getAttribute("data-travel-mission-id") : null;
    if (typeof missionId !== "string") {
      missionId = Missions.getSnapshot().selectedMissionId;
    }
    if (typeof missionId === "string") {
      Terrain.start(missionId);
    }
  }

  function startTravelRuntime() {
    if (!Travel) {
      return;
    }
    Travel.start();
    startTerrainRuntime();
    travelRunIdCounter += 1;
    var runId = travelRunIdCounter;
    activeTravelRunId = runId;
    travelLastTimestamp = null;
    if (travelFrameId !== null && typeof window.cancelAnimationFrame === "function") {
      window.cancelAnimationFrame(travelFrameId);
    }
    travelFrameId = null;

    var canvas = document.getElementById("ocean-rescue-canvas");
    var context = null;
    if (canvas && typeof canvas.getContext === "function") {
      context = canvas.getContext("2d");
    }
    travelCanvas = canvas;
    bindTravelPointerInput(canvas);
    renderTravelFrame(canvas, context);

    if (typeof window.requestAnimationFrame === "function") {
      travelFrameId = window.requestAnimationFrame(function (timestamp) {
        travelAnimationFrame(runId, timestamp);
      });
    }

    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-travel-runtime", "active");
      root.setAttribute("data-travel-input", "enabled");
    }
  }

  function travelAnimationFrame(runId, timestamp) {
    if (runId !== activeTravelRunId) {
      return;
    }
    travelFrameId = null;
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.TRAVEL) {
      return;
    }
    var travel = Travel.getSnapshot();
    if (!travel.active) {
      return;
    }
    if (travelLastTimestamp !== null) {
      var deltaMs = timestamp - travelLastTimestamp;
      if (deltaMs > 0) {
        if (Terrain && Terrain.getSnapshot().active) {
          var terrainStepTravelSnapshot = Travel.getSnapshot();
          Terrain.step(deltaMs, terrainStepTravelSnapshot);
          var terrainFrameSnapshot = Terrain.getSnapshot();
          Travel.step(deltaMs, terrainFrameSnapshot.forwardSpeedMultiplier);
        } else {
          Travel.step(deltaMs);
        }
      }
    }
    travelLastTimestamp = timestamp;
    if (tryBeginRescueArrival()) {
      renderRescueSiteFrame(travelCanvas, resolveTravelContext());
      return;
    }
    renderTravelFrame(travelCanvas, resolveTravelContext());
    if (typeof window.requestAnimationFrame === "function") {
      travelFrameId = window.requestAnimationFrame(function (nextTimestamp) {
        travelAnimationFrame(runId, nextTimestamp);
      });
    }
  }

  function resolveTravelContext() {
    if (!travelCanvas || typeof travelCanvas.getContext !== "function") {
      return null;
    }
    return travelCanvas.getContext("2d");
  }

  function bindTravelPointerInput(canvas) {
    if (travelInputBound) {
      return;
    }
    if (!canvas) {
      return;
    }
    if (typeof canvas.addEventListener !== "function") {
      return;
    }
    canvas.addEventListener("pointerdown", onPointerDown);
    canvas.addEventListener("pointermove", onPointerMove);
    canvas.addEventListener("pointerup", onPointerUp);
    canvas.addEventListener("pointercancel", onPointerCancel);
    travelInputBound = true;
  }

  function acceptPointerEvent(event) {
    if (!event || typeof event !== "object") {
      return false;
    }
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.TRAVEL) {
      return false;
    }
    var travel = Travel.getSnapshot();
    if (!travel.active) {
      return false;
    }
    if (event.isPrimary === false) {
      return false;
    }
    if (typeof event.button === "number" && event.button !== 0) {
      return false;
    }
    return true;
  }

  function mapClientYToStage(event) {
    if (typeof event.clientY !== "number" || !isFinite(event.clientY)) {
      return null;
    }
    if (!travelCanvas) {
      return null;
    }
    if (typeof travelCanvas.getBoundingClientRect !== "function") {
      return null;
    }
    var rect = travelCanvas.getBoundingClientRect();
    if (!rect || typeof rect !== "object") {
      return null;
    }
    if (typeof rect.height !== "number" || !isFinite(rect.height) || rect.height <= 0) {
      return null;
    }
    if (typeof travelCanvas.height !== "number" || !isFinite(travelCanvas.height) || travelCanvas.height <= 0) {
      return null;
    }
    return event.clientY * (travelCanvas.height / rect.height);
  }

  function resetPointerGesture() {
    pointerActive = false;
    pointerId = null;
    pointerStartClientY = null;
    pointerStartStageY = null;
    pointerDragging = false;
  }

  function onPointerDown(event) {
    if (!acceptPointerEvent(event)) {
      return;
    }
    if (pointerActive) {
      return;
    }
    var stageY = mapClientYToStage(event);
    if (stageY === null) {
      return;
    }
    pointerActive = true;
    pointerId = event.pointerId;
    pointerStartClientY = event.clientY;
    pointerStartStageY = stageY;
    pointerDragging = false;
    if (travelCanvas && typeof travelCanvas.setPointerCapture === "function") {
      travelCanvas.setPointerCapture(event.pointerId);
    }
    if (typeof event.preventDefault === "function") {
      event.preventDefault();
    }
  }

  function onPointerMove(event) {
    if (!acceptPointerEvent(event)) {
      return;
    }
    if (!pointerActive) {
      return;
    }
    if (event.pointerId !== pointerId) {
      return;
    }
    var stageY = mapClientYToStage(event);
    if (stageY === null) {
      return;
    }
    if (!pointerDragging) {
      if (Math.abs(event.clientY - pointerStartClientY) < 8) {
        return;
      }
      pointerDragging = true;
      Travel.beginDrag(pointerId, pointerStartStageY);
      Travel.moveDrag(pointerId, stageY);
    } else {
      Travel.moveDrag(pointerId, stageY);
    }
    if (typeof event.preventDefault === "function") {
      event.preventDefault();
    }
  }

  function onPointerUp(event) {
    if (!acceptPointerEvent(event)) {
      return;
    }
    if (!pointerActive) {
      return;
    }
    if (event.pointerId !== pointerId) {
      return;
    }
    var stageY = mapClientYToStage(event);
    if (pointerDragging) {
      if (stageY !== null) {
        Travel.moveDrag(pointerId, stageY);
      }
      Travel.endDrag(pointerId);
    } else if (stageY !== null) {
      Travel.tapTo(stageY);
    }
    resetPointerGesture();
    if (travelCanvas && typeof travelCanvas.releasePointerCapture === "function") {
      travelCanvas.releasePointerCapture(event.pointerId);
    }
    if (typeof event.preventDefault === "function") {
      event.preventDefault();
    }
  }

  function onPointerCancel(event) {
    if (!pointerActive) {
      return;
    }
    if (event.pointerId !== pointerId) {
      return;
    }
    if (pointerDragging) {
      Travel.endDrag(pointerId);
    }
    resetPointerGesture();
  }

  function renderTravelFrame(canvas, context) {
    if (!canvas || !context) {
      return;
    }
    if (typeof context.clearRect !== "function") {
      return;
    }
    var snapshot = Travel.getSnapshot();
    var terrainSnapshot = Terrain ? Terrain.getSnapshot() : null;
    var width = canvas.width;
    var height = canvas.height;
    if (typeof width !== "number" || typeof height !== "number") {
      return;
    }
    context.clearRect(0, 0, width, height);
    drawTravelBackground(context, width, height);
    drawTravelWater(context, width, height, snapshot.distance);
    if (terrainSnapshot && terrainSnapshot.active) {
      drawTravelTerrain(context, terrainSnapshot, snapshot.distance);
    }
    drawTravelGup(context, width, height, snapshot.y, terrainSnapshot);
    if (terrainSnapshot && terrainSnapshot.collisionActive) {
      drawCollisionFeedback(context, terrainSnapshot, snapshot.y);
    }
    updateRootCollisionMarkers(terrainSnapshot);
  }

  function drawTravelBackground(context, width, height) {
    context.fillStyle = "#0a1e33";
    context.fillRect(0, 0, width, height);
    context.fillStyle = "#123451";
    context.fillRect(0, 0, width, Math.floor(height * 0.45));
  }

  function drawTravelWater(context, width, height, distance) {
    var spacing = 96;
    var offset = distance % spacing;
    context.fillStyle = "rgba(180, 220, 255, 0.35)";
    var x = offset;
    while (x < width) {
      context.beginPath();
      context.arc(x, height * 0.62, 5, 0, Math.PI * 2);
      context.fill();
      x += spacing;
    }
  }

  function drawTravelTerrain(context, terrainSnapshot, distance) {
    var layout = Terrain.getLayout(terrainSnapshot.missionId);
    if (layout === null) {
      return;
    }
    var palette = terrainPalettes[layout.environment] || terrainPalettes["coral-reef"];
    var obstacles = layout.obstacles;
    for (var i = 0; i < obstacles.length; i += 1) {
      drawTerrainObstacle(context, obstacles[i], distance, palette);
    }
  }

  function drawTerrainObstacle(context, obstacle, distance, palette) {
    var screenX = obstacle.worldX - distance;
    var rectX = screenX - obstacle.width / 2;
    var rectY = obstacle.y - obstacle.height / 2;
    var inset = 8 + (obstacle.kind.length % 5);
    context.fillStyle = palette[0];
    context.fillRect(rectX, rectY, obstacle.width, obstacle.height);
    context.fillStyle = palette[1];
    context.fillRect(
      rectX + inset,
      rectY + inset,
      obstacle.width - inset * 2,
      obstacle.height - inset * 2
    );
  }

  function drawCollisionFeedback(context, terrainSnapshot, travelY) {
    var x = 320 - terrainSnapshot.knockbackOffsetX;
    var y = travelY + terrainSnapshot.shakeOffsetY;
    context.fillStyle = "rgba(255, 255, 255, 0.30)";
    context.beginPath();
    context.arc(x, y, 54, 0, Math.PI * 2);
    context.fill();
    context.fillStyle = "#ffffff";
    context.font = "16px system-ui, sans-serif";
    context.textAlign = "center";
    context.fillText("Whoa!", x, y - 48);
  }

  function updateRootCollisionMarkers(terrainSnapshot) {
    if (!Terrain) {
      return;
    }
    if (!terrainSnapshot || !terrainSnapshot.active) {
      return;
    }
    var root = document.getElementById("ocean-rescue-root");
    if (!root) {
      return;
    }
    root.setAttribute(
      "data-travel-collision-count",
      String(terrainSnapshot.collisionCount)
    );
    root.setAttribute(
      "data-travel-collision-active",
      terrainSnapshot.collisionActive ? "true" : "false"
    );
    root.setAttribute(
      "data-travel-slowed",
      terrainSnapshot.forwardSpeedMultiplier < 1 ? "true" : "false"
    );
    if (terrainSnapshot.lastCollisionObstacleId !== null) {
      root.setAttribute(
        "data-travel-last-collision-obstacle-id",
        terrainSnapshot.lastCollisionObstacleId
      );
    } else {
      root.removeAttribute("data-travel-last-collision-obstacle-id");
    }
  }

  function drawTravelGup(context, width, height, y, terrainSnapshot) {
    var gupSnapshot = Gups.getSnapshot();
    var gup = gupById(gupSnapshot.lastGupId);
    var name = gup === null ? String(gupSnapshot.lastGupId) : gup.name;
    var x = 320;
    var drawY = y;
    if (terrainSnapshot && terrainSnapshot.active) {
      x = 320 - terrainSnapshot.knockbackOffsetX;
      drawY = y + terrainSnapshot.shakeOffsetY;
    }
    context.beginPath();
    context.arc(x, drawY, 36, 0, Math.PI * 2);
    context.fillStyle = "#ffd166";
    context.fill();
    context.fillStyle = "#0a1e33";
    context.font = "18px system-ui, sans-serif";
    context.textAlign = "center";
    context.fillText(name, x, drawY);
  }

  function resolveRescueElements() {
    var stage = document.getElementById("ocean-rescue-stage");
    var canvas = document.getElementById("ocean-rescue-canvas");
    var overlay = document.getElementById("ocean-rescue-rescue-overlay");
    var companion = document.getElementById("ocean-rescue-rescue-companion");
    var situation = document.getElementById("ocean-rescue-rescue-situation");
    var ready = document.getElementById("ocean-rescue-rescue-ready");
    var tutorial = document.getElementById("ocean-rescue-rescue-tutorial");
    var instruction = document.getElementById("ocean-rescue-rescue-instruction");
    var hand = document.getElementById("ocean-rescue-rescue-hand");
    if (
      !stage ||
      !canvas ||
      !overlay ||
      !companion ||
      !situation ||
      !ready ||
      !tutorial ||
      !instruction ||
      !hand
    ) {
      return null;
    }
    return {
      stage: stage,
      canvas: canvas,
      overlay: overlay,
      companion: companion,
      situation: situation,
      ready: ready,
      tutorial: tutorial,
      instruction: instruction,
      hand: hand
    };
  }

  function tryBeginRescueArrival() {
    if (!Rescue) {
      return false;
    }
    if (activeRescueSequence !== null) {
      return false;
    }
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.TRAVEL) {
      return false;
    }
    if (!Travel) {
      return false;
    }
    var travel = Travel.getSnapshot();
    if (!travel.active) {
      return false;
    }
    if (!Rescue.hasArrived(travel)) {
      return false;
    }
    var progression = Missions.getSnapshot();
    var mission = missionById(progression.selectedMissionId);
    if (mission === null) {
      return false;
    }
    var content = Rescue.getMissionContent(mission.id);
    if (content === null) {
      return false;
    }
    var gup = gupById(Gups.getSnapshot().lastGupId);
    if (gup === null) {
      return false;
    }
    var els = resolveRescueElements();
    if (els === null) {
      return false;
    }
    return beginRescueArrival(mission, gup, content, els);
  }

  function beginRescueArrival(mission, gup, content, els) {
    var token = State.beginTransition(State.Phases.RESCUE_SITE_TRANSITION);
    if (token === null) {
      return false;
    }
    if (!State.completeTransition(token)) {
      return false;
    }
    rescueSequenceCounter += 1;
    var sequence = {
      sequenceId: rescueSequenceCounter,
      missionId: mission.id,
      gupId: gup.id,
      missionContent: content,
      tutorialComplete: false,
      tutorialSkipped: false
    };
    activeRescueSequence = sequence;

    activeTravelRunId = null;
    if (
      travelFrameId !== null &&
      typeof window.cancelAnimationFrame === "function"
    ) {
      window.cancelAnimationFrame(travelFrameId);
    }
    travelFrameId = null;
    travelLastTimestamp = null;

    if (Travel) {
      Travel.stop();
    }
    if (Terrain && Terrain.getSnapshot().active) {
      Terrain.stop();
    }
    shutdownActivePointer();

    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-travel-runtime", "stopped");
      root.setAttribute("data-travel-input", "disabled");
      root.setAttribute("data-rescue-sequence", "active");
      root.setAttribute("data-rescue-phase", "site-transition");
      root.setAttribute("data-rescue-input", "disabled");
      root.setAttribute("data-rescue-mission-id", mission.id);
      root.setAttribute("data-rescue-gup-id", gup.id);
    }

    els.overlay.hidden = false;
    els.companion.textContent = mission.companion + ":";
    els.situation.textContent = content.situation;
    els.ready.hidden = false;
    els.tutorial.hidden = true;

    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = "Rescue site: " + content.situation;
    }

    scheduleSiteTransitionCompletion(sequence);
    return true;
  }

  function shutdownActivePointer() {
    if (pointerActive && pointerDragging && pointerId !== null && Travel) {
      Travel.endDrag(pointerId);
    }
    if (
      pointerId !== null &&
      travelCanvas &&
      typeof travelCanvas.releasePointerCapture === "function"
    ) {
      travelCanvas.releasePointerCapture(pointerId);
    }
    resetPointerGesture();
  }

  function scheduleSiteTransitionCompletion(sequence) {
    if (typeof window.setTimeout !== "function") {
      return;
    }
    siteTransitionTimerId = window.setTimeout(function () {
      completeSiteTransition(sequence);
    }, Rescue.SiteTransitionMs);
  }

  function completeSiteTransition(sequence) {
    siteTransitionTimerId = null;
    if (activeRescueSequence === null) {
      return false;
    }
    if (!sequence || typeof sequence !== "object") {
      return false;
    }
    if (sequence.sequenceId !== activeRescueSequence.sequenceId) {
      return false;
    }
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.RESCUE_SITE_TRANSITION) {
      return false;
    }
    var els = resolveRescueElements();
    if (els === null) {
      return false;
    }
    var token = State.beginTransition(State.Phases.RESCUE_TUTORIAL);
    if (token === null) {
      return false;
    }
    if (!State.completeTransition(token)) {
      return false;
    }
    els.ready.hidden = true;
    els.tutorial.hidden = false;
    els.instruction.textContent = sequence.missionContent.tutorial;
    setTutorialActiveClass(els.tutorial, true);
    if (sequence.missionId === "crab") {
      setTutorialHoldClass(els.tutorial, true);
    }
    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-rescue-phase", "tutorial");
      root.setAttribute("data-rescue-input", "disabled");
    }
    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = sequence.missionContent.tutorial;
    }
    scheduleTutorialCompletion(sequence);
    return true;
  }

  function scheduleTutorialCompletion(sequence) {
    if (typeof window.setTimeout !== "function") {
      return;
    }
    tutorialTimerId = window.setTimeout(function () {
      completeTutorial(sequence);
    }, Rescue.TutorialDurationMs);
  }

  function completeTutorial(sequence) {
    tutorialTimerId = null;
    if (activeRescueSequence === null) {
      return false;
    }
    if (!sequence || typeof sequence !== "object") {
      return false;
    }
    if (sequence.sequenceId !== activeRescueSequence.sequenceId) {
      return false;
    }
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.RESCUE_TUTORIAL) {
      return false;
    }
    return finalizeTutorial(sequence, false);
  }

  function skipTutorial() {
    var sequence = activeRescueSequence;
    if (sequence === null) {
      return false;
    }
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.RESCUE_TUTORIAL) {
      return false;
    }
    if (sequence.tutorialComplete) {
      return false;
    }
    clearTutorialTimer();
    return finalizeTutorial(sequence, true);
  }

  function finalizeTutorial(sequence, skipped) {
    if (activeRescueSequence === null) {
      return false;
    }
    if (!sequence || typeof sequence !== "object") {
      return false;
    }
    if (sequence.sequenceId !== activeRescueSequence.sequenceId) {
      return false;
    }
    if (sequence.tutorialComplete) {
      return false;
    }
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.RESCUE_TUTORIAL) {
      return false;
    }
    var els = resolveRescueElements();
    if (els === null) {
      return false;
    }
    var token = State.beginTransition(State.Phases.RESCUE_ACTIVE);
    if (token === null) {
      return false;
    }
    if (!State.completeTransition(token)) {
      return false;
    }
    sequence.tutorialComplete = true;
    sequence.tutorialSkipped = skipped ? true : false;
    clearTutorialTimer();
    setTutorialActiveClass(els.tutorial, false);
    setTutorialHoldClass(els.tutorial, false);
    els.hand.hidden = true;
    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-rescue-phase", "active");
      root.setAttribute("data-rescue-input", "enabled");
      root.setAttribute(
        "data-rescue-tutorial-skipped",
        skipped ? "true" : "false"
      );
    }
    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = "Rescue controls ready";
    }
    startSeaTurtleInteraction(sequence);
    startCrabInteraction(sequence);
    startYoungWhaleInteraction(sequence);
    return true;
  }

  function clearTutorialTimer() {
    if (tutorialTimerId === null) {
      return;
    }
    if (typeof window.clearTimeout === "function") {
      window.clearTimeout(tutorialTimerId);
    }
    tutorialTimerId = null;
  }

  function setTutorialClass(container, token, active) {
    if (
      typeof container.classList === "object" &&
      typeof container.classList.add === "function" &&
      typeof container.classList.remove === "function"
    ) {
      if (active) {
        container.classList.add(token);
      } else {
        container.classList.remove(token);
      }
      return;
    }
    var names = String(container.className || "").split(/\s+/);
    var index = names.indexOf(token);
    if (active && index === -1) {
      names.push(token);
    }
    if (!active && index !== -1) {
      names.splice(index, 1);
    }
    container.className = names.join(" ").trim();
  }

  function setTutorialActiveClass(container, active) {
    setTutorialClass(container, "ocean-rescue-tutorial-active", active);
  }

  function setTutorialHoldClass(container, active) {
    setTutorialClass(container, "ocean-rescue-tutorial-hold", active);
  }

  function onRescueStagePointerDown(event) {
    if (!event || typeof event !== "object") {
      return;
    }
    var snapshot = State.getSnapshot();
    if (snapshot.phase === State.Phases.RESCUE_SITE_TRANSITION) {
      if (typeof event.preventDefault === "function") {
        event.preventDefault();
      }
      if (typeof event.stopPropagation === "function") {
        event.stopPropagation();
      }
      return;
    }
    if (snapshot.phase === State.Phases.RESCUE_TUTORIAL) {
      if (typeof event.preventDefault === "function") {
        event.preventDefault();
      }
      if (typeof event.stopPropagation === "function") {
        event.stopPropagation();
      }
      skipTutorial();
    }
  }

  function renderRescueSiteFrame(canvas, context) {
    if (!canvas || !context) {
      return;
    }
    if (typeof context.clearRect !== "function") {
      return;
    }
    if (activeRescueSequence === null) {
      return;
    }
    var width = canvas.width;
    var height = canvas.height;
    if (typeof width !== "number" || typeof height !== "number") {
      return;
    }
    var sequence = activeRescueSequence;
    var layout = null;
    if (Terrain && typeof Terrain.getLayout === "function") {
      layout = Terrain.getLayout(sequence.missionId);
    }
    var palette = terrainPalettes["coral-reef"];
    if (layout && layout.environment && terrainPalettes[layout.environment]) {
      palette = terrainPalettes[layout.environment];
    }
    context.clearRect(0, 0, width, height);
    drawRescueSiteBackground(context, width, height, palette);

    var gup = gupById(sequence.gupId);
    var gupName = gup === null ? sequence.gupId : gup.name;
    var gupY = Math.floor(height * 0.72);
    context.beginPath();
    context.arc(220, gupY, 36, 0, Math.PI * 2);
    context.fillStyle = "#ffd166";
    context.fill();
    context.fillStyle = "#0a1e33";
    context.font = "18px system-ui, sans-serif";
    context.textAlign = "center";
    context.fillText(gupName, 220, gupY);

    context.beginPath();
    context.arc(520, gupY, 30, 0, Math.PI * 2);
    context.fillStyle = "#9ad0ff";
    context.fill();
    context.fillStyle = "#0a1e33";
    context.font = "16px system-ui, sans-serif";
    context.fillText(sequence.missionContent.toolLabel, 520, gupY - 44);

    context.beginPath();
    context.arc(900, gupY, 48, 0, Math.PI * 2);
    context.fillStyle = "#8fd3a8";
    context.fill();
    context.fillStyle = "#0a1e33";
    context.font = "18px system-ui, sans-serif";
    context.fillText(sequence.missionContent.targetLabel, 900, gupY);
  }

  function drawRescueSiteBackground(context, width, height, palette) {
    context.fillStyle = "#0a1e33";
    context.fillRect(0, 0, width, height);
    var bubbleSpacing = 96;
    context.fillStyle = "rgba(180, 220, 255, 0.30)";
    var bx = 40 - bubbleSpacing;
    while (bx < width) {
      context.beginPath();
      context.arc(bx + 40, Math.floor(height * 0.6), 5, 0, Math.PI * 2);
      context.fill();
      bx += bubbleSpacing;
    }
    context.fillStyle = palette[0];
    context.fillRect(0, Math.floor(height * 0.55), width, Math.floor(height * 0.45));
    context.fillStyle = palette[2];
    context.fillRect(0, Math.floor(height * 0.55), width, 8);
  }

  function startSeaTurtleInteraction(sequence) {
    if (!sequence || typeof sequence !== "object") {
      return false;
    }
    if (!SeaTurtle) {
      return false;
    }
    if (sequence.missionId !== SeaTurtle.MissionId) {
      return false;
    }
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.RESCUE_ACTIVE) {
      return false;
    }
    if (seaTurtleRenderMarker) {
      return true;
    }
    var canvas = document.getElementById("ocean-rescue-canvas");
    var context = null;
    if (canvas && typeof canvas.getContext === "function") {
      context = canvas.getContext("2d");
    }
    var overlay = document.getElementById("ocean-rescue-rescue-overlay");
    if (!canvas || !context || !overlay) {
      return false;
    }
    SeaTurtle.start();
    bindRescuePointerInput(canvas);
    renderSeaTurtleFrame();
    seaTurtleRenderMarker = true;
    var progress = document.getElementById("ocean-rescue-rescue-progress");
    if (progress) {
      progress.textContent = "Rope 1 of 3";
    }
    hideAssistHand();
    updateSeaTurtleRootMarkers();
    return true;
  }

  function startCrabInteraction(sequence) {
    if (!sequence || typeof sequence !== "object") {
      return false;
    }
    if (!Crab) {
      return false;
    }
    if (sequence.missionId !== Crab.MissionId) {
      return false;
    }
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.RESCUE_ACTIVE) {
      return false;
    }
    var canvas = document.getElementById("ocean-rescue-canvas");
    var context = null;
    if (canvas && typeof canvas.getContext === "function") {
      context = canvas.getContext("2d");
    }
    var overlay = document.getElementById("ocean-rescue-rescue-overlay");
    if (!canvas || !context || !overlay) {
      return false;
    }
    Crab.start();
    bindRescuePointerInput(canvas);
    renderCrabFrame();
    var progress = document.getElementById("ocean-rescue-rescue-progress");
    if (progress) {
      progress.textContent = "Rock 1 of 3";
    }
    hideAssistHand();
    updateCrabRootMarkers();
    return true;
  }

  function startYoungWhaleInteraction(sequence) {
    if (!sequence || typeof sequence !== "object") {
      return false;
    }
    if (!YoungWhale) {
      return false;
    }
    if (sequence.missionId !== YoungWhale.MissionId) {
      return false;
    }
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.RESCUE_ACTIVE) {
      return false;
    }
    var canvas = document.getElementById("ocean-rescue-canvas");
    var context = null;
    if (canvas && typeof canvas.getContext === "function") {
      context = canvas.getContext("2d");
    }
    var overlay = document.getElementById("ocean-rescue-rescue-overlay");
    if (!canvas || !context || !overlay) {
      return false;
    }
    YoungWhale.start();
    bindRescuePointerInput(canvas);
    renderYoungWhaleFrame();
    var progress = document.getElementById("ocean-rescue-rescue-progress");
    if (progress) {
      progress.textContent = "Debris 1 of 3";
    }
    updateYoungWhaleInstruction();
    hideAssistHand();
    updateYoungWhaleRootMarkers();
    return true;
  }

  function bindRescuePointerInput(canvas) {
    if (seaTurtleInputBound) {
      return;
    }
    if (!canvas) {
      return;
    }
    if (typeof canvas.addEventListener !== "function") {
      return;
    }
    canvas.addEventListener("pointerdown", onRescuePointerDown);
    canvas.addEventListener("pointermove", onRescuePointerMove);
    canvas.addEventListener("pointerup", onRescuePointerUp);
    canvas.addEventListener("pointercancel", onRescuePointerCancel);
    seaTurtleInputBound = true;
  }

  function acceptRescuePointerEvent(event) {
    if (!event || typeof event !== "object") {
      return false;
    }
    if (activeRescueSequence === null) {
      return false;
    }
    var missionId = activeRescueSequence.missionId;
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.RESCUE_ACTIVE) {
      return false;
    }
    if (missionId === SeaTurtle.MissionId) {
      if (!SeaTurtle) {
        return false;
      }
      var seaTurtle = SeaTurtle.getSnapshot();
      if (!seaTurtle.active) {
        return false;
      }
      if (seaTurtlePointerId !== null) {
        return false;
      }
    } else if (Crab && missionId === Crab.MissionId) {
      var crab = Crab.getSnapshot();
      if (!crab.active) {
        return false;
      }
      if (crabPointerId !== null) {
        return false;
      }
    } else if (YoungWhale && missionId === YoungWhale.MissionId) {
      var youngWhale = YoungWhale.getSnapshot();
      if (!youngWhale.active) {
        return false;
      }
      if (youngWhalePointerId !== null) {
        return false;
      }
    } else {
      return false;
    }
    var root = document.getElementById("ocean-rescue-root");
    if (root && root.getAttribute("data-rescue-input") === "disabled") {
      return false;
    }
    if (event.isPrimary === false) {
      return false;
    }
    if (typeof event.button === "number" && event.button !== 0) {
      return false;
    }
    if (typeof event.clientX !== "number" || !isFinite(event.clientX)) {
      return false;
    }
    if (typeof event.clientY !== "number" || !isFinite(event.clientY)) {
      return false;
    }
    return true;
  }

  function isTrackedRescuePointer(event) {
    if (!event || typeof event !== "object") {
      return false;
    }
    if (activeRescueSequence === null) {
      return false;
    }
    var missionId = activeRescueSequence.missionId;
    if (missionId === SeaTurtle.MissionId) {
      if (!SeaTurtle) {
        return false;
      }
      if (seaTurtlePointerId === null) {
        return false;
      }
      if (typeof event.pointerId !== "number" || !isFinite(event.pointerId)) {
        return false;
      }
      if (event.pointerId !== seaTurtlePointerId) {
        return false;
      }
    } else if (Crab && missionId === Crab.MissionId) {
      if (crabPointerId === null) {
        return false;
      }
      if (typeof event.pointerId !== "number" || !isFinite(event.pointerId)) {
        return false;
      }
      if (event.pointerId !== crabPointerId) {
        return false;
      }
    } else if (YoungWhale && missionId === YoungWhale.MissionId) {
      if (youngWhalePointerId === null) {
        return false;
      }
      if (typeof event.pointerId !== "number" || !isFinite(event.pointerId)) {
        return false;
      }
      if (event.pointerId !== youngWhalePointerId) {
        return false;
      }
    } else {
      return false;
    }
    if (typeof event.clientX !== "number" || !isFinite(event.clientX)) {
      return false;
    }
    if (typeof event.clientY !== "number" || !isFinite(event.clientY)) {
      return false;
    }
    return true;
  }

  function mapRescueCoordinates(event) {
    var canvas = document.getElementById("ocean-rescue-canvas");
    if (!canvas) {
      return null;
    }
    if (typeof canvas.getBoundingClientRect !== "function") {
      return null;
    }
    var rect = canvas.getBoundingClientRect();
    if (!rect || typeof rect !== "object") {
      return null;
    }
    if (typeof rect.left !== "number" || !isFinite(rect.left)) {
      return null;
    }
    if (typeof rect.top !== "number" || !isFinite(rect.top)) {
      return null;
    }
    if (typeof rect.width !== "number" || !isFinite(rect.width) || rect.width <= 0) {
      return null;
    }
    if (typeof rect.height !== "number" || !isFinite(rect.height) || rect.height <= 0) {
      return null;
    }
    if (typeof canvas.width !== "number" || !isFinite(canvas.width) || canvas.width <= 0) {
      return null;
    }
    if (typeof canvas.height !== "number" || !isFinite(canvas.height) || canvas.height <= 0) {
      return null;
    }
    var x = (event.clientX - rect.left) * (canvas.width / rect.width);
    var y = (event.clientY - rect.top) * (canvas.height / rect.height);
    if (!isFinite(x) || !isFinite(y)) {
      return null;
    }
    return { x: x, y: y };
  }

  function releaseSeaTurtlePointerCapture(pointerId) {
    if (
      seaTurtlePointerCaptureEl &&
      typeof seaTurtlePointerCaptureEl.releasePointerCapture === "function"
    ) {
      seaTurtlePointerCaptureEl.releasePointerCapture(pointerId);
    }
  }

  function releaseCrabPointerCapture(pointerId) {
    if (
      crabPointerCaptureEl &&
      typeof crabPointerCaptureEl.releasePointerCapture === "function"
    ) {
      crabPointerCaptureEl.releasePointerCapture(pointerId);
    }
  }

  function releaseYoungWhalePointerCapture(pointerId) {
    if (
      youngWhalePointerCaptureEl &&
      typeof youngWhalePointerCaptureEl.releasePointerCapture === "function"
    ) {
      youngWhalePointerCaptureEl.releasePointerCapture(pointerId);
    }
  }

  function onRescuePointerDown(event) {
    if (!acceptRescuePointerEvent(event)) {
      return;
    }
    var mapped = mapRescueCoordinates(event);
    if (mapped === null) {
      return;
    }
    var missionId = activeRescueSequence.missionId;
    if (missionId === SeaTurtle.MissionId) {
      handleSeaTurtlePointerDown(event, mapped);
      return;
    }
    if (Crab && missionId === Crab.MissionId) {
      handleCrabPointerDown(event, mapped);
      return;
    }
    if (YoungWhale && missionId === YoungWhale.MissionId) {
      handleYoungWhalePointerDown(event, mapped);
    }
  }

  function handleSeaTurtlePointerDown(event, mapped) {
    if (!SeaTurtle.pointerDown(event.pointerId, mapped.x, mapped.y)) {
      return;
    }
    seaTurtlePointerId = event.pointerId;
    seaTurtlePointerCaptureEl = document.getElementById("ocean-rescue-canvas");
    if (
      seaTurtlePointerCaptureEl &&
      typeof seaTurtlePointerCaptureEl.setPointerCapture === "function"
    ) {
      seaTurtlePointerCaptureEl.setPointerCapture(event.pointerId);
    }
    hideAssistHand();
    renderSeaTurtleFrame();
    updateSeaTurtleRootMarkers();
    if (typeof event.preventDefault === "function") {
      event.preventDefault();
    }
    if (typeof event.stopPropagation === "function") {
      event.stopPropagation();
    }
  }

  function handleCrabPointerDown(event, mapped) {
    if (!Crab.pointerDown(event.pointerId, mapped.x, mapped.y)) {
      return;
    }
    crabPointerId = event.pointerId;
    crabPointerCaptureEl = document.getElementById("ocean-rescue-canvas");
    if (
      crabPointerCaptureEl &&
      typeof crabPointerCaptureEl.setPointerCapture === "function"
    ) {
      crabPointerCaptureEl.setPointerCapture(event.pointerId);
    }
    var snap = Crab.getSnapshot();
    if (snap.holding && typeof window.setTimeout === "function") {
      clearCrabHoldTimer();
      var sequence = activeRescueSequence;
      var rockId = snap.activeRockId;
      crabHoldTimerId = window.setTimeout(function () {
        completeCrabHold(sequence, rockId);
      }, Crab.Constants.holdDurationMs);
    }
    hideAssistHand();
    renderCrabFrame();
    updateCrabRootMarkers();
    if (typeof event.preventDefault === "function") {
      event.preventDefault();
    }
    if (typeof event.stopPropagation === "function") {
      event.stopPropagation();
    }
  }

  function handleYoungWhalePointerDown(event, mapped) {
    if (!YoungWhale.pointerDown(event.pointerId, mapped.x, mapped.y)) {
      return;
    }
    youngWhalePointerId = event.pointerId;
    youngWhalePointerCaptureEl = document.getElementById("ocean-rescue-canvas");
    if (
      youngWhalePointerCaptureEl &&
      typeof youngWhalePointerCaptureEl.setPointerCapture === "function"
    ) {
      youngWhalePointerCaptureEl.setPointerCapture(event.pointerId);
    }
    hideAssistHand();
    renderYoungWhaleFrame(mapped.x, mapped.y);
    updateYoungWhaleRootMarkers();
    if (typeof event.preventDefault === "function") {
      event.preventDefault();
    }
    if (typeof event.stopPropagation === "function") {
      event.stopPropagation();
    }
  }

  function onRescuePointerMove(event) {
    if (!isTrackedRescuePointer(event)) {
      return;
    }
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.RESCUE_ACTIVE) {
      return;
    }
    var mapped = mapRescueCoordinates(event);
    if (mapped === null) {
      return;
    }
    var missionId = activeRescueSequence.missionId;
    if (missionId === SeaTurtle.MissionId) {
      SeaTurtle.pointerMove(event.pointerId, mapped.x, mapped.y);
      renderSeaTurtleFrame();
      updateSeaTurtleRootMarkers();
    } else if (Crab && missionId === Crab.MissionId) {
      Crab.pointerMove(event.pointerId, mapped.x, mapped.y);
      renderCrabFrame();
      updateCrabRootMarkers();
    } else if (YoungWhale && missionId === YoungWhale.MissionId) {
      YoungWhale.pointerMove(event.pointerId, mapped.x, mapped.y);
      renderYoungWhaleFrame(mapped.x, mapped.y);
      updateYoungWhaleRootMarkers();
    }
    if (typeof event.preventDefault === "function") {
      event.preventDefault();
    }
    if (typeof event.stopPropagation === "function") {
      event.stopPropagation();
    }
  }

  function onRescuePointerUp(event) {
    if (!isTrackedRescuePointer(event)) {
      return;
    }
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.RESCUE_ACTIVE) {
      return;
    }
    var mapped = mapRescueCoordinates(event);
    var missionId = activeRescueSequence.missionId;
    var result = null;
    if (missionId === SeaTurtle.MissionId) {
      if (mapped !== null) {
        result = SeaTurtle.pointerUp(event.pointerId, mapped.x, mapped.y);
      } else {
        SeaTurtle.pointerCancel(event.pointerId);
      }
      releaseSeaTurtlePointerCapture(event.pointerId);
      seaTurtlePointerId = null;
      seaTurtlePointerCaptureEl = null;
      if (result && result.accepted) {
        renderSeaTurtleFrame();
        updateSeaTurtleRootMarkers();
        routeRescueFeedback(result);
      }
    } else if (Crab && missionId === Crab.MissionId) {
      clearCrabHoldTimer();
      if (mapped !== null) {
        result = Crab.pointerUp(event.pointerId, mapped.x, mapped.y);
      } else {
        Crab.pointerCancel(event.pointerId);
      }
      releaseCrabPointerCapture(event.pointerId);
      crabPointerId = null;
      crabPointerCaptureEl = null;
      if (result && result.accepted) {
        renderCrabFrame();
        updateCrabRootMarkers();
        routeCrabFeedback(result);
      }
    } else if (YoungWhale && missionId === YoungWhale.MissionId) {
      if (mapped !== null) {
        result = YoungWhale.pointerUp(event.pointerId, mapped.x, mapped.y);
      } else {
        YoungWhale.pointerCancel(event.pointerId);
      }
      releaseYoungWhalePointerCapture(event.pointerId);
      youngWhalePointerId = null;
      youngWhalePointerCaptureEl = null;
      if (result && result.accepted) {
        renderYoungWhaleFrame(
          mapped === null ? null : mapped.x,
          mapped === null ? null : mapped.y
        );
        updateYoungWhaleRootMarkers();
        routeYoungWhaleFeedback(result);
      }
    }
    if (typeof event.preventDefault === "function") {
      event.preventDefault();
    }
    if (typeof event.stopPropagation === "function") {
      event.stopPropagation();
    }
  }

  function onRescuePointerCancel(event) {
    if (!event || typeof event !== "object") {
      return;
    }
    if (activeRescueSequence === null) {
      return;
    }
    var missionId = activeRescueSequence.missionId;
    if (missionId === SeaTurtle.MissionId) {
      if (!SeaTurtle) {
        return;
      }
      if (seaTurtlePointerId === null) {
        return;
      }
      if (typeof event.pointerId !== "number" || !isFinite(event.pointerId)) {
        return;
      }
      if (event.pointerId !== seaTurtlePointerId) {
        return;
      }
      SeaTurtle.pointerCancel(event.pointerId);
      releaseSeaTurtlePointerCapture(event.pointerId);
      seaTurtlePointerId = null;
      seaTurtlePointerCaptureEl = null;
      return;
    }
    if (!Crab || missionId !== Crab.MissionId) {
      if (!YoungWhale || missionId !== YoungWhale.MissionId) {
        return;
      }
      if (youngWhalePointerId === null) {
        return;
      }
      if (typeof event.pointerId !== "number" || !isFinite(event.pointerId)) {
        return;
      }
      if (event.pointerId !== youngWhalePointerId) {
        return;
      }
      YoungWhale.pointerCancel(event.pointerId);
      releaseYoungWhalePointerCapture(event.pointerId);
      youngWhalePointerId = null;
      youngWhalePointerCaptureEl = null;
      renderYoungWhaleFrame();
      updateYoungWhaleRootMarkers();
      return;
    }
    if (crabPointerId === null) {
      return;
    }
    if (typeof event.pointerId !== "number" || !isFinite(event.pointerId)) {
      return;
    }
    if (event.pointerId !== crabPointerId) {
      return;
    }
    clearCrabHoldTimer();
    Crab.pointerCancel(event.pointerId);
    releaseCrabPointerCapture(event.pointerId);
    crabPointerId = null;
    crabPointerCaptureEl = null;
    renderCrabFrame();
    updateCrabRootMarkers();
  }

  function routeRescueFeedback(result) {
    if (!result || typeof result !== "object") {
      return;
    }
    if (result.accepted !== true) {
      return;
    }
    if (result.outcome === "success") {
      beginSeaTurtleSuccessFeedback(result.ropeId);
      return;
    }
    if (result.outcome === "failure") {
      beginSeaTurtleFailureFeedback(result.ropeId);
    }
  }

  function clearSeaTurtleFeedbackTimer() {
    if (seaTurtleTimerId === null) {
      return;
    }
    if (typeof window.clearTimeout === "function") {
      window.clearTimeout(seaTurtleTimerId);
    }
    seaTurtleTimerId = null;
  }

  function ropeById(ropeId) {
    if (!SeaTurtle) {
      return null;
    }
    for (var i = 0; i < SeaTurtle.Ropes.length; i += 1) {
      if (SeaTurtle.Ropes[i].id === ropeId) {
        return SeaTurtle.Ropes[i];
      }
    }
    return null;
  }

  function ropeOrderIndexById(ropeId) {
    if (!SeaTurtle) {
      return -1;
    }
    for (var i = 0; i < SeaTurtle.Ropes.length; i += 1) {
      if (SeaTurtle.Ropes[i].id === ropeId) {
        return i;
      }
    }
    return -1;
  }

  function setSeaTurtleDialogue(ropeId) {
    var index = ropeOrderIndexById(ropeId);
    if (index < 0 || index >= SeaTurtle.Dialogues.length) {
      return;
    }
    var dialogue = SeaTurtle.Dialogues[index];
    var progress = document.getElementById("ocean-rescue-rescue-progress");
    if (progress) {
      progress.textContent = dialogue;
    }
    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = dialogue;
    }
  }

  function applySeaTurtleClass(token, active) {
    var overlay = document.getElementById("ocean-rescue-rescue-overlay");
    if (!overlay) {
      return;
    }
    if (
      typeof overlay.classList === "object" &&
      typeof overlay.classList.add === "function" &&
      typeof overlay.classList.remove === "function"
    ) {
      if (active) {
        overlay.classList.add(token);
      } else {
        overlay.classList.remove(token);
      }
      return;
    }
    var names = String(overlay.className || "").split(/\s+/);
    var index = names.indexOf(token);
    if (active && index === -1) {
      names.push(token);
    }
    if (!active && index !== -1) {
      names.splice(index, 1);
    }
    overlay.className = names.join(" ").trim();
  }

  function applySeaTurtleSuccessVisual() {
    applySeaTurtleClass("ocean-rescue-sea-turtle-success", true);
  }

  function clearSeaTurtleSuccessVisual() {
    applySeaTurtleClass("ocean-rescue-sea-turtle-success", false);
  }

  function applySeaTurtleFailureVisual() {
    applySeaTurtleClass("ocean-rescue-sea-turtle-failure", true);
  }

  function clearSeaTurtleFailureVisual() {
    applySeaTurtleClass("ocean-rescue-sea-turtle-failure", false);
  }

  function showAssistHand() {
    var hand = document.getElementById("ocean-rescue-rescue-assist-hand");
    if (!hand) {
      return;
    }
    if (
      typeof hand.classList === "object" &&
      typeof hand.classList.add === "function" &&
      typeof hand.classList.remove === "function"
    ) {
      hand.classList.remove("ocean-rescue-assist-hand-visible");
      hand.classList.add("ocean-rescue-assist-hand-visible");
    }
    hand.hidden = false;
  }

  function hideAssistHand() {
    var hand = document.getElementById("ocean-rescue-rescue-assist-hand");
    if (!hand) {
      return;
    }
    if (
      typeof hand.classList === "object" &&
      typeof hand.classList.remove === "function"
    ) {
      hand.classList.remove("ocean-rescue-assist-hand-visible");
    }
    hand.hidden = true;
  }

  function updateAssistVisuals(snapshot) {
    if (snapshot.helpLevel >= 1) {
      showAssistHand();
    } else {
      hideAssistHand();
    }
  }

  function updateSeaTurtleRootMarkers() {
    var root = document.getElementById("ocean-rescue-root");
    if (!root) {
      return;
    }
    var snapshot = SeaTurtle.getSnapshot();
    root.setAttribute(
      "data-sea-turtle-active",
      snapshot.active ? "true" : "false"
    );
    root.setAttribute(
      "data-sea-turtle-rope-id",
      snapshot.activeRopeId === null ? "" : snapshot.activeRopeId
    );
    root.setAttribute(
      "data-sea-turtle-completed-count",
      String(snapshot.completedRopeIds.length)
    );
    root.setAttribute(
      "data-sea-turtle-help-level",
      String(snapshot.helpLevel)
    );
    root.setAttribute(
      "data-sea-turtle-feedback",
      snapshot.feedback === null ? "none" : snapshot.feedback
    );
    root.setAttribute(
      "data-sea-turtle-complete",
      snapshot.complete ? "true" : "false"
    );
  }

  function beginSeaTurtleSuccessFeedback(ropeId) {
    clearSeaTurtleFeedbackTimer();
    applySeaTurtleSuccessVisual();
    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-sea-turtle-feedback", "success");
    }
    setSeaTurtleDialogue(ropeId);
    seaTurtleFeedbackSequence = {
      sequenceId:
        activeRescueSequence === null ? null : activeRescueSequence.sequenceId,
      ropeId: ropeId,
      kind: "success"
    };
    if (typeof window.setTimeout === "function") {
      seaTurtleTimerId = window.setTimeout(function () {
        completeSeaTurtleFeedback(seaTurtleFeedbackSequence);
      }, SeaTurtle.Constants.successFeedbackMs);
    }
  }

  function beginSeaTurtleFailureFeedback(ropeId) {
    clearSeaTurtleFeedbackTimer();
    applySeaTurtleFailureVisual();
    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-sea-turtle-feedback", "failure");
    }
    var rope = ropeById(ropeId);
    var progress = document.getElementById("ocean-rescue-rescue-progress");
    if (progress && rope) {
      progress.textContent = "Try rope " + rope.order + " again";
    }
    seaTurtleFeedbackSequence = {
      sequenceId:
        activeRescueSequence === null ? null : activeRescueSequence.sequenceId,
      ropeId: ropeId,
      kind: "failure"
    };
    if (typeof window.setTimeout === "function") {
      seaTurtleTimerId = window.setTimeout(function () {
        completeSeaTurtleFeedback(seaTurtleFeedbackSequence);
      }, SeaTurtle.Constants.failureFeedbackMs);
    }
  }

  function completeSeaTurtleFeedback(sequence) {
    seaTurtleTimerId = null;
    if (!sequence || typeof sequence !== "object") {
      return;
    }
    if (activeRescueSequence === null) {
      return;
    }
    if (sequence.sequenceId !== activeRescueSequence.sequenceId) {
      return;
    }
    var snapshot = SeaTurtle.getSnapshot();
    if (snapshot.feedback === null) {
      return;
    }
    if (snapshot.feedback !== sequence.kind) {
      return;
    }
    if (snapshot.activeRopeId !== sequence.ropeId) {
      return;
    }
    var result = SeaTurtle.finishFeedback();
    if (!result.changed) {
      return;
    }
    if (result.complete) {
      completeSeaTurtleSuccess();
      return;
    }
    finishSeaTurtleFeedbackVisuals(sequence, result);
  }

  function finishSeaTurtleFeedbackVisuals(sequence, result) {
    var snapshot = SeaTurtle.getSnapshot();
    if (sequence.kind === "failure") {
      clearSeaTurtleFailureVisual();
      var rope = ropeById(snapshot.activeRopeId);
      var progress = document.getElementById("ocean-rescue-rescue-progress");
      if (progress && rope) {
        progress.textContent = "Rope " + rope.order + " of 3";
      }
      updateAssistVisuals(snapshot);
    } else {
      clearSeaTurtleSuccessVisual();
      var nextRope = ropeById(result.nextRopeId);
      var progressEl = document.getElementById("ocean-rescue-rescue-progress");
      if (progressEl && nextRope) {
        progressEl.textContent = "Rope " + nextRope.order + " of 3";
      }
      hideAssistHand();
    }
    updateSeaTurtleRootMarkers();
    renderSeaTurtleFrame();
  }

  function completeSeaTurtleSuccess() {
    clearSeaTurtleSuccessVisual();
    hideAssistHand();
    var sequence = activeRescueSequence;
    if (sequence === null) {
      return;
    }
    var token = State.beginTransition(State.Phases.RESCUE_SUCCESS);
    if (token !== null) {
      State.completeTransition(token);
    }
    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-rescue-phase", "success");
      root.setAttribute("data-rescue-input", "disabled");
    }
    updateSeaTurtleRootMarkers();
    var progress = document.getElementById("ocean-rescue-rescue-progress");
    if (progress) {
      progress.textContent = SeaTurtle.Dialogues[2];
    }
    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = SeaTurtle.Dialogues[2];
    }
    renderSeaTurtleFrame();
    startMissionSuccessPresentation(sequence);
  }

  function clearCrabHoldTimer() {
    if (crabHoldTimerId === null) {
      return;
    }
    if (typeof window.clearTimeout === "function") {
      window.clearTimeout(crabHoldTimerId);
    }
    crabHoldTimerId = null;
  }

  function completeCrabHold(sequence, rockId) {
    crabHoldTimerId = null;
    if (activeRescueSequence === null) {
      return;
    }
    if (!sequence || typeof sequence !== "object") {
      return;
    }
    if (sequence.sequenceId !== activeRescueSequence.sequenceId) {
      return;
    }
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.RESCUE_ACTIVE) {
      return;
    }
    var crab = Crab.getSnapshot();
    if (crab.activeRockId !== rockId) {
      return;
    }
    if (!crab.holding) {
      return;
    }
    var result = Crab.finishHold();
    if (!result.accepted) {
      return;
    }
    renderCrabFrame();
    updateCrabRootMarkers();
  }

  function routeCrabFeedback(result) {
    if (!result || typeof result !== "object") {
      return;
    }
    if (result.accepted !== true) {
      return;
    }
    if (result.outcome === "success") {
      beginCrabSuccessFeedback(result.rockId);
      return;
    }
    if (result.outcome === "failure") {
      beginCrabFailureFeedback(result.rockId);
    }
  }

  function clearCrabFeedbackTimer() {
    if (crabTimerId === null) {
      return;
    }
    if (typeof window.clearTimeout === "function") {
      window.clearTimeout(crabTimerId);
    }
    crabTimerId = null;
  }

  function crabRockById(rockId) {
    if (!Crab) {
      return null;
    }
    for (var i = 0; i < Crab.Rocks.length; i += 1) {
      if (Crab.Rocks[i].id === rockId) {
        return Crab.Rocks[i];
      }
    }
    return null;
  }

  function crabRockOrderIndexById(rockId) {
    for (var i = 0; i < Crab.Rocks.length; i += 1) {
      if (Crab.Rocks[i].id === rockId) {
        return i;
      }
    }
    return -1;
  }

  function setCrabDialogue(rockId) {
    var index = crabRockOrderIndexById(rockId);
    if (index < 0 || index >= Crab.Dialogues.length) {
      return;
    }
    var dialogue = Crab.Dialogues[index];
    var progress = document.getElementById("ocean-rescue-rescue-progress");
    if (progress) {
      progress.textContent = dialogue;
    }
    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = dialogue;
    }
  }

  function applyCrabClass(token, active) {
    var overlay = document.getElementById("ocean-rescue-rescue-overlay");
    if (!overlay) {
      return;
    }
    if (
      typeof overlay.classList === "object" &&
      typeof overlay.classList.add === "function" &&
      typeof overlay.classList.remove === "function"
    ) {
      if (active) {
        overlay.classList.add(token);
      } else {
        overlay.classList.remove(token);
      }
      return;
    }
    var names = String(overlay.className || "").split(/\s+/);
    var index = names.indexOf(token);
    if (active && index === -1) {
      names.push(token);
    }
    if (!active && index !== -1) {
      names.splice(index, 1);
    }
    overlay.className = names.join(" ").trim();
  }

  function applyCrabSuccessVisual() {
    applyCrabClass("ocean-rescue-crab-success", true);
  }

  function clearCrabSuccessVisual() {
    applyCrabClass("ocean-rescue-crab-success", false);
  }

  function applyCrabFailureVisual() {
    applyCrabClass("ocean-rescue-crab-failure", true);
  }

  function clearCrabFailureVisual() {
    applyCrabClass("ocean-rescue-crab-failure", false);
  }

  function updateCrabRootMarkers() {
    var root = document.getElementById("ocean-rescue-root");
    if (!root) {
      return;
    }
    var snapshot = Crab.getSnapshot();
    root.setAttribute(
      "data-crab-active",
      snapshot.active ? "true" : "false"
    );
    root.setAttribute(
      "data-crab-rock-id",
      snapshot.activeRockId === null ? "" : snapshot.activeRockId
    );
    root.setAttribute(
      "data-crab-completed-count",
      String(snapshot.completedRockIds.length)
    );
    root.setAttribute(
      "data-crab-help-level",
      String(snapshot.helpLevel)
    );
    root.setAttribute(
      "data-crab-feedback",
      snapshot.feedback === null ? "none" : snapshot.feedback
    );
    root.setAttribute(
      "data-crab-grabbed",
      snapshot.grabbed ? "true" : "false"
    );
    root.setAttribute(
      "data-crab-complete",
      snapshot.complete ? "true" : "false"
    );
  }

  function beginCrabSuccessFeedback(rockId) {
    clearCrabFeedbackTimer();
    applyCrabSuccessVisual();
    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-crab-feedback", "success");
    }
    setCrabDialogue(rockId);
    crabFeedbackSequence = {
      sequenceId:
        activeRescueSequence === null ? null : activeRescueSequence.sequenceId,
      rockId: rockId,
      kind: "success"
    };
    if (typeof window.setTimeout === "function") {
      crabTimerId = window.setTimeout(function () {
        completeCrabFeedback(crabFeedbackSequence);
      }, Crab.Constants.successFeedbackMs);
    }
  }

  function beginCrabFailureFeedback(rockId) {
    clearCrabFeedbackTimer();
    applyCrabFailureVisual();
    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-crab-feedback", "failure");
    }
    var rock = crabRockById(rockId);
    var progress = document.getElementById("ocean-rescue-rescue-progress");
    if (progress && rock) {
      progress.textContent = "Try rock " + rock.order + " again";
    }
    crabFeedbackSequence = {
      sequenceId:
        activeRescueSequence === null ? null : activeRescueSequence.sequenceId,
      rockId: rockId,
      kind: "failure"
    };
    if (typeof window.setTimeout === "function") {
      crabTimerId = window.setTimeout(function () {
        completeCrabFeedback(crabFeedbackSequence);
      }, Crab.Constants.failureFeedbackMs);
    }
  }

  function completeCrabFeedback(sequence) {
    crabTimerId = null;
    if (!sequence || typeof sequence !== "object") {
      return;
    }
    if (activeRescueSequence === null) {
      return;
    }
    if (sequence.sequenceId !== activeRescueSequence.sequenceId) {
      return;
    }
    var snapshot = Crab.getSnapshot();
    if (snapshot.feedback === null) {
      return;
    }
    if (snapshot.feedback !== sequence.kind) {
      return;
    }
    if (snapshot.activeRockId !== sequence.rockId) {
      return;
    }
    var result = Crab.finishFeedback();
    if (!result.changed) {
      return;
    }
    if (result.complete) {
      completeCrabSuccess();
      return;
    }
    finishCrabFeedbackVisuals(sequence, result);
  }

  function finishCrabFeedbackVisuals(sequence, result) {
    var snapshot = Crab.getSnapshot();
    if (sequence.kind === "failure") {
      clearCrabFailureVisual();
      var rock = crabRockById(snapshot.activeRockId);
      var progress = document.getElementById("ocean-rescue-rescue-progress");
      if (progress && rock) {
        progress.textContent = "Rock " + rock.order + " of 3";
      }
      updateAssistVisuals(snapshot);
    } else {
      clearCrabSuccessVisual();
      var nextRock = crabRockById(result.nextRockId);
      var progressEl = document.getElementById("ocean-rescue-rescue-progress");
      if (progressEl && nextRock) {
        progressEl.textContent = "Rock " + nextRock.order + " of 3";
      }
      hideAssistHand();
    }
    updateCrabRootMarkers();
    renderCrabFrame();
  }

  function completeCrabSuccess() {
    clearCrabSuccessVisual();
    hideAssistHand();
    var sequence = activeRescueSequence;
    if (sequence === null) {
      return;
    }
    var token = State.beginTransition(State.Phases.RESCUE_SUCCESS);
    if (token !== null) {
      State.completeTransition(token);
    }
    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-rescue-phase", "success");
      root.setAttribute("data-rescue-input", "disabled");
    }
    updateCrabRootMarkers();
    var progress = document.getElementById("ocean-rescue-rescue-progress");
    if (progress) {
      progress.textContent = Crab.Dialogues[2];
    }
    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = Crab.Dialogues[2];
    }
    renderCrabFrame();
    startMissionSuccessPresentation(sequence);
  }

  function routeYoungWhaleFeedback(result) {
    if (!result || typeof result !== "object") {
      return;
    }
    if (result.accepted !== true) {
      return;
    }
    if (result.outcome === "success") {
      beginYoungWhaleSuccessFeedback(result.debrisId);
      return;
    }
    if (result.outcome === "failure") {
      beginYoungWhaleFailureFeedback(result.debrisId);
    }
  }

  function clearYoungWhaleFeedbackTimer() {
    if (youngWhaleTimerId === null) {
      return;
    }
    if (typeof window.clearTimeout === "function") {
      window.clearTimeout(youngWhaleTimerId);
    }
    youngWhaleTimerId = null;
  }

  function youngWhaleDebrisById(debrisId) {
    if (!YoungWhale) {
      return null;
    }
    for (var i = 0; i < YoungWhale.Debris.length; i += 1) {
      if (YoungWhale.Debris[i].id === debrisId) {
        return YoungWhale.Debris[i];
      }
    }
    return null;
  }

  function youngWhaleDebrisOrderIndexById(debrisId) {
    for (var i = 0; i < YoungWhale.Debris.length; i += 1) {
      if (YoungWhale.Debris[i].id === debrisId) {
        return i;
      }
    }
    return -1;
  }

  function setYoungWhaleDialogue(debrisId) {
    var index = youngWhaleDebrisOrderIndexById(debrisId);
    if (index < 0 || index >= YoungWhale.Dialogues.length) {
      return;
    }
    var dialogue = YoungWhale.Dialogues[index];
    var progress = document.getElementById("ocean-rescue-rescue-progress");
    if (progress) {
      progress.textContent = dialogue;
    }
    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = dialogue;
    }
  }

  function updateYoungWhaleInstruction() {
    if (!YoungWhale) {
      return;
    }
    var instruction = document.getElementById("ocean-rescue-rescue-instruction");
    if (!instruction) {
      return;
    }
    var snapshot = YoungWhale.getSnapshot();
    var text = null;
    if (snapshot.stage === "connection") {
      text = YoungWhale.Instructions.connection;
    } else if (snapshot.stage === "towing") {
      text = YoungWhale.Instructions.towing;
    }
    if (text !== null) {
      instruction.textContent = text;
    }
  }

  function applyYoungWhaleClass(token, active) {
    var overlay = document.getElementById("ocean-rescue-rescue-overlay");
    if (!overlay) {
      return;
    }
    if (
      typeof overlay.classList === "object" &&
      typeof overlay.classList.add === "function" &&
      typeof overlay.classList.remove === "function"
    ) {
      if (active) {
        overlay.classList.add(token);
      } else {
        overlay.classList.remove(token);
      }
      return;
    }
    var names = String(overlay.className || "").split(/\s+/);
    var index = names.indexOf(token);
    if (active && index === -1) {
      names.push(token);
    }
    if (!active && index !== -1) {
      names.splice(index, 1);
    }
    overlay.className = names.join(" ").trim();
  }

  function applyYoungWhaleSuccessVisual() {
    applyYoungWhaleClass("ocean-rescue-young-whale-success", true);
  }

  function clearYoungWhaleSuccessVisual() {
    applyYoungWhaleClass("ocean-rescue-young-whale-success", false);
  }

  function applyYoungWhaleFailureVisual() {
    applyYoungWhaleClass("ocean-rescue-young-whale-failure", true);
  }

  function clearYoungWhaleFailureVisual() {
    applyYoungWhaleClass("ocean-rescue-young-whale-failure", false);
  }

  function updateYoungWhaleRootMarkers() {
    var root = document.getElementById("ocean-rescue-root");
    if (!root) {
      return;
    }
    if (!YoungWhale) {
      return;
    }
    var snapshot = YoungWhale.getSnapshot();
    root.setAttribute(
      "data-young-whale-active",
      snapshot.active ? "true" : "false"
    );
    root.setAttribute(
      "data-young-whale-debris-id",
      snapshot.activeDebrisId === null ? "" : snapshot.activeDebrisId
    );
    root.setAttribute(
      "data-young-whale-stage",
      snapshot.stage === null ? "" : snapshot.stage
    );
    root.setAttribute(
      "data-young-whale-completed-count",
      String(snapshot.completedDebrisIds.length)
    );
    root.setAttribute(
      "data-young-whale-help-level",
      String(snapshot.helpLevel)
    );
    root.setAttribute(
      "data-young-whale-feedback",
      snapshot.feedback === null ? "none" : snapshot.feedback
    );
    root.setAttribute(
      "data-young-whale-connected",
      snapshot.connected ? "true" : "false"
    );
    root.setAttribute(
      "data-young-whale-complete",
      snapshot.complete ? "true" : "false"
    );
  }

  function beginYoungWhaleSuccessFeedback(debrisId) {
    clearYoungWhaleFeedbackTimer();
    applyYoungWhaleSuccessVisual();
    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-young-whale-feedback", "success");
    }
    var snapshot = YoungWhale.getSnapshot();
    if (snapshot.stage === "towing") {
      setYoungWhaleDialogue(debrisId);
    }
    youngWhaleFeedbackSequence = {
      sequenceId:
        activeRescueSequence === null ? null : activeRescueSequence.sequenceId,
      debrisId: debrisId,
      stage: snapshot.stage,
      kind: "success"
    };
    if (typeof window.setTimeout === "function") {
      youngWhaleTimerId = window.setTimeout(function () {
        completeYoungWhaleFeedback(youngWhaleFeedbackSequence);
      }, YoungWhale.Constants.successFeedbackMs);
    }
  }

  function beginYoungWhaleFailureFeedback(debrisId) {
    clearYoungWhaleFeedbackTimer();
    applyYoungWhaleFailureVisual();
    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-young-whale-feedback", "failure");
    }
    var debris = youngWhaleDebrisById(debrisId);
    var progress = document.getElementById("ocean-rescue-rescue-progress");
    var snapshot = YoungWhale.getSnapshot();
    if (progress && debris) {
      if (snapshot.stage === "towing") {
        progress.textContent = "Try towing debris " + debris.order + " again";
      } else {
        progress.textContent =
          "Try connecting debris " + debris.order + " again";
      }
    }
    youngWhaleFeedbackSequence = {
      sequenceId:
        activeRescueSequence === null ? null : activeRescueSequence.sequenceId,
      debrisId: debrisId,
      stage: snapshot.stage,
      kind: "failure"
    };
    if (typeof window.setTimeout === "function") {
      youngWhaleTimerId = window.setTimeout(function () {
        completeYoungWhaleFeedback(youngWhaleFeedbackSequence);
      }, YoungWhale.Constants.failureFeedbackMs);
    }
  }

  function completeYoungWhaleFeedback(sequence) {
    youngWhaleTimerId = null;
    if (!sequence || typeof sequence !== "object") {
      return;
    }
    if (activeRescueSequence === null) {
      return;
    }
    if (sequence.sequenceId !== activeRescueSequence.sequenceId) {
      return;
    }
    var snapshot = YoungWhale.getSnapshot();
    if (snapshot.feedback === null) {
      return;
    }
    if (snapshot.feedback !== sequence.kind) {
      return;
    }
    if (snapshot.activeDebrisId !== sequence.debrisId) {
      return;
    }
    if (snapshot.stage !== sequence.stage) {
      return;
    }
    var result = YoungWhale.finishFeedback();
    if (!result.changed) {
      return;
    }
    if (result.complete) {
      completeYoungWhaleSuccess();
      return;
    }
    finishYoungWhaleFeedbackVisuals(sequence, result);
  }

  function finishYoungWhaleFeedbackVisuals(sequence, result) {
    var snapshot = YoungWhale.getSnapshot();
    if (sequence.kind === "failure") {
      clearYoungWhaleFailureVisual();
      var debris = youngWhaleDebrisById(snapshot.activeDebrisId);
      var progress = document.getElementById("ocean-rescue-rescue-progress");
      if (progress && debris) {
        progress.textContent = "Debris " + debris.order + " of 3";
      }
      updateYoungWhaleInstruction();
      updateAssistVisuals(snapshot);
    } else {
      clearYoungWhaleSuccessVisual();
      var nextDebris = youngWhaleDebrisById(result.nextDebrisId);
      var progressEl = document.getElementById("ocean-rescue-rescue-progress");
      if (progressEl && nextDebris) {
        progressEl.textContent = "Debris " + nextDebris.order + " of 3";
      }
      updateYoungWhaleInstruction();
      hideAssistHand();
    }
    updateYoungWhaleRootMarkers();
    renderYoungWhaleFrame();
  }

  function completeYoungWhaleSuccess() {
    clearYoungWhaleSuccessVisual();
    hideAssistHand();
    var sequence = activeRescueSequence;
    if (sequence === null) {
      return;
    }
    var token = State.beginTransition(State.Phases.RESCUE_SUCCESS);
    if (token !== null) {
      State.completeTransition(token);
    }
    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-rescue-phase", "success");
      root.setAttribute("data-rescue-input", "disabled");
    }
    updateYoungWhaleRootMarkers();
    var progress = document.getElementById("ocean-rescue-rescue-progress");
    if (progress) {
      progress.textContent = YoungWhale.Dialogues[2];
    }
    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = YoungWhale.Dialogues[2];
    }
    renderYoungWhaleFrame();
    startMissionSuccessPresentation(sequence);
  }

  function resolveMissionSuccessElements() {
    var section = document.getElementById("ocean-rescue-mission-success");
    var visual = document.getElementById("ocean-rescue-mission-success-visual");
    var animal = document.getElementById("ocean-rescue-mission-success-animal");
    var secondaryAnimal = document.getElementById(
      "ocean-rescue-mission-success-secondary-animal"
    );
    var destination = document.getElementById(
      "ocean-rescue-mission-success-destination"
    );
    var ecology = document.getElementById("ocean-rescue-mission-success-ecology");
    var narration = document.getElementById(
      "ocean-rescue-mission-success-narration"
    );
    var speaker = document.getElementById("ocean-rescue-mission-success-speaker");
    var line = document.getElementById("ocean-rescue-mission-success-line");
    var tapHelp = document.getElementById("ocean-rescue-mission-success-tap-help");
    var card = document.getElementById("ocean-rescue-mission-complete-card");
    var cardName = document.getElementById("ocean-rescue-mission-complete-name");
    var cardEcology = document.getElementById(
      "ocean-rescue-mission-complete-ecology"
    );
    if (
      !section ||
      !visual ||
      !animal ||
      !secondaryAnimal ||
      !destination ||
      !ecology ||
      !narration ||
      !speaker ||
      !line ||
      !tapHelp ||
      !card ||
      !cardName ||
      !cardEcology
    ) {
      return null;
    }
    return {
      section: section,
      visual: visual,
      animal: animal,
      secondaryAnimal: secondaryAnimal,
      destination: destination,
      ecology: ecology,
      narration: narration,
      speaker: speaker,
      line: line,
      tapHelp: tapHelp,
      card: card,
      cardName: cardName,
      cardEcology: cardEcology
    };
  }

  function clearMissionSuccessTimer() {
    if (missionSuccessTimerId === null) {
      return;
    }
    if (typeof window.clearTimeout === "function") {
      window.clearTimeout(missionSuccessTimerId);
    }
    missionSuccessTimerId = null;
  }

  function shutdownRescueInteractionState() {
    clearSeaTurtleFeedbackTimer();
    clearCrabFeedbackTimer();
    clearYoungWhaleFeedbackTimer();
    clearCrabHoldTimer();
    if (
      seaTurtlePointerId !== null &&
      seaTurtlePointerCaptureEl &&
      typeof seaTurtlePointerCaptureEl.releasePointerCapture === "function"
    ) {
      seaTurtlePointerCaptureEl.releasePointerCapture(seaTurtlePointerId);
    }
    seaTurtlePointerId = null;
    seaTurtlePointerCaptureEl = null;
    if (
      crabPointerId !== null &&
      crabPointerCaptureEl &&
      typeof crabPointerCaptureEl.releasePointerCapture === "function"
    ) {
      crabPointerCaptureEl.releasePointerCapture(crabPointerId);
    }
    crabPointerId = null;
    crabPointerCaptureEl = null;
    if (
      youngWhalePointerId !== null &&
      youngWhalePointerCaptureEl &&
      typeof youngWhalePointerCaptureEl.releasePointerCapture === "function"
    ) {
      youngWhalePointerCaptureEl.releasePointerCapture(youngWhalePointerId);
    }
    youngWhalePointerId = null;
    youngWhalePointerCaptureEl = null;
    seaTurtleRenderMarker = false;
  }

  function setMissionSuccessAnimClass(visual, active) {
    var token = "ocean-rescue-mission-success-anim-active";
    if (
      typeof visual.classList === "object" &&
      typeof visual.classList.add === "function" &&
      typeof visual.classList.remove === "function"
    ) {
      if (active) {
        visual.classList.add(token);
      } else {
        visual.classList.remove(token);
      }
      return;
    }
    var names = String(visual.className || "").split(/\s+/);
    var index = names.indexOf(token);
    if (active && index === -1) {
      names.push(token);
    }
    if (!active && index !== -1) {
      names.splice(index, 1);
    }
    visual.className = names.join(" ").trim();
  }

  function applyMissionSuccessAnimation(els, sequence) {
    els.section.hidden = false;
    els.visual.setAttribute(
      "data-mission-success-anim",
      sequence.content.animationKey
    );
    setMissionSuccessAnimClass(els.visual, true);
    els.animal.className = "ocean-rescue-mission-success-shape";
    els.secondaryAnimal.className = "ocean-rescue-mission-success-shape";
    els.destination.className = "ocean-rescue-mission-success-shape";
    els.animal.setAttribute("data-mission-success-animal", sequence.missionId);
    els.secondaryAnimal.setAttribute(
      "data-mission-success-secondary-animal",
      sequence.missionId
    );
    els.destination.setAttribute(
      "data-mission-success-destination",
      sequence.missionId
    );
  }

  function clearMissionSuccessAnimation(els) {
    setMissionSuccessAnimClass(els.visual, false);
  }

  function isMissionSuccessStageValid(sequence, expectedStage) {
    if (activeMissionSuccessSequence === null) {
      return false;
    }
    if (!sequence || typeof sequence !== "object") {
      return false;
    }
    if (sequence.sequenceId !== activeMissionSuccessSequence.sequenceId) {
      return false;
    }
    if (activeMissionSuccessSequence.stage !== expectedStage) {
      return false;
    }
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.RESCUE_SUCCESS) {
      return false;
    }
    return true;
  }

  function scheduleMissionSuccessTimer(sequence, expectedStage, delayMs, fn) {
    clearMissionSuccessTimer();
    if (typeof window.setTimeout !== "function") {
      return false;
    }
    missionSuccessTimerId = window.setTimeout(function () {
      missionSuccessTimerId = null;
      if (!isMissionSuccessStageValid(sequence, expectedStage)) {
        return;
      }
      fn(sequence);
    }, delayMs);
    return true;
  }

  function enterMissionSuccessEcology(sequence) {
    var els = resolveMissionSuccessElements();
    if (els === null) {
      return false;
    }
    clearMissionSuccessAnimation(els);
    els.ecology.textContent = sequence.content.ecology;
    els.ecology.hidden = false;
    els.narration.hidden = true;
    els.card.hidden = true;
    sequence.stage = "ecology";
    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-mission-success-stage", "ecology");
      root.setAttribute("data-mission-success-input", "disabled");
    }
    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = sequence.content.ecology;
    }
    return scheduleMissionSuccessTimer(
      sequence,
      "ecology",
      MissionSuccess.EcologyDurationMs,
      enterMissionSuccessNarration1
    );
  }

  function enterMissionSuccessNarration1(sequence) {
    var els = resolveMissionSuccessElements();
    if (els === null) {
      return false;
    }
    els.narration.hidden = false;
    els.speaker.textContent = sequence.companion + ":";
    els.line.textContent = sequence.content.companionLine;
    els.tapHelp.hidden = false;
    sequence.stage = "narration-1";
    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-mission-success-stage", "narration-1");
      root.setAttribute("data-mission-success-input", "enabled");
    }
    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = sequence.content.companionLine;
    }
    return scheduleMissionSuccessTimer(
      sequence,
      "narration-1",
      MissionSuccess.NarrationSentenceMs,
      enterMissionSuccessNarration2
    );
  }

  function enterMissionSuccessNarration2(sequence) {
    var els = resolveMissionSuccessElements();
    if (els === null) {
      return false;
    }
    els.speaker.textContent = "Narrator:";
    els.line.textContent = sequence.content.animalLine;
    els.tapHelp.hidden = false;
    sequence.stage = "narration-2";
    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-mission-success-stage", "narration-2");
      root.setAttribute("data-mission-success-input", "enabled");
    }
    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = sequence.content.animalLine;
    }
    return scheduleMissionSuccessTimer(
      sequence,
      "narration-2",
      MissionSuccess.NarrationSentenceMs,
      finalizeMissionSuccess
    );
  }

  function finalizeMissionSuccess(sequence) {
    if (!isMissionSuccessStageValid(sequence, "narration-2")) {
      return false;
    }
    var token = State.beginTransition(State.Phases.MISSION_COMPLETE);
    if (token === null) {
      return false;
    }
    if (!State.completeTransition(token)) {
      return false;
    }
    clearMissionSuccessTimer();
    var completionResult = Missions.completeMission(sequence.missionId);
    sequence.firstCompletion = completionResult.changed ? true : false;
    sequence.newlyUnlockedMissionId =
      completionResult.newlyUnlockedMissionId;
    sequence.continueFocusMissionId = resolveContinueFocusMissionId(
      sequence.newlyUnlockedMissionId
    );
    var els = resolveMissionSuccessElements();
    if (els === null) {
      return false;
    }
    els.visual.hidden = true;
    els.ecology.hidden = true;
    els.narration.hidden = true;
    els.tapHelp.hidden = true;
    els.card.hidden = false;
    els.cardName.textContent = sequence.missionTitle;
    els.cardEcology.textContent = sequence.content.ecology;
    sequence.stage = "complete";
    var unlock = document.getElementById(
      "ocean-rescue-mission-complete-unlock"
    );
    var unlockName = document.getElementById(
      "ocean-rescue-mission-complete-unlock-name"
    );
    if (sequence.newlyUnlockedMissionId !== null) {
      if (unlock) {
        unlock.hidden = false;
      }
      if (unlockName) {
        unlockName.textContent =
          missionTitleById(sequence.newlyUnlockedMissionId) || "";
      }
    } else {
      if (unlock) {
        unlock.hidden = true;
      }
      if (unlockName) {
        unlockName.textContent = "";
      }
    }
    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-rescue-phase", "mission-complete");
      root.setAttribute("data-rescue-input", "disabled");
      root.setAttribute("data-mission-success-active", "false");
      root.setAttribute("data-mission-success-stage", "complete");
      root.setAttribute("data-mission-success-input", "disabled");
      root.setAttribute("data-mission-completion-recorded", "true");
      root.setAttribute(
        "data-mission-first-completion",
        sequence.firstCompletion ? "true" : "false"
      );
      root.setAttribute(
        "data-mission-newly-unlocked-id",
        sequence.newlyUnlockedMissionId || ""
      );
      root.setAttribute(
        "data-mission-continue-focus-id",
        sequence.continueFocusMissionId || ""
      );
      root.setAttribute("data-mission-complete-action", "ready");
      root.setAttribute("data-mission-complete-ready", "true");
    }
    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = "Mission complete: " + sequence.missionTitle;
    }
    resetMissionCompleteActionState();
    return true;
  }

  function bindMissionCompleteActions() {
    if (missionCompleteActionsBound) {
      return;
    }
    var continueButton = document.getElementById(
      "ocean-rescue-mission-complete-continue"
    );
    if (
      continueButton &&
      typeof continueButton.addEventListener === "function"
    ) {
      continueButton.addEventListener(
        "click",
        onMissionCompleteContinueClick
      );
    }
    var replayButton = document.getElementById(
      "ocean-rescue-mission-complete-replay"
    );
    if (replayButton && typeof replayButton.addEventListener === "function") {
      replayButton.addEventListener("click", onMissionCompleteReplayClick);
    }
    missionCompleteActionsBound = true;
  }

  function disableMissionCompleteButtons() {
    var continueButton = document.getElementById(
      "ocean-rescue-mission-complete-continue"
    );
    if (continueButton) {
      continueButton.disabled = true;
    }
    var replayButton = document.getElementById(
      "ocean-rescue-mission-complete-replay"
    );
    if (replayButton) {
      replayButton.disabled = true;
    }
  }

  function enableMissionCompleteButtons() {
    var continueButton = document.getElementById(
      "ocean-rescue-mission-complete-continue"
    );
    if (continueButton) {
      continueButton.disabled = false;
    }
    var replayButton = document.getElementById(
      "ocean-rescue-mission-complete-replay"
    );
    if (replayButton) {
      replayButton.disabled = false;
    }
  }

  function resetMissionCompleteActionState() {
    missionCompleteActionLock = false;
    enableMissionCompleteButtons();
  }

  function isMissionCompleteActionReady() {
    if (missionCompleteActionLock) {
      return false;
    }
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.MISSION_COMPLETE) {
      return false;
    }
    var sequence = activeMissionSuccessSequence;
    if (sequence === null) {
      return false;
    }
    if (sequence.stage !== "complete") {
      return false;
    }
    var root = document.getElementById("ocean-rescue-root");
    if (
      root === null ||
      root.getAttribute("data-mission-complete-ready") !== "true"
    ) {
      return false;
    }
    return true;
  }

  function cleanupMissionCompletePresentation() {
    clearMissionSuccessTimer();
    var els = resolveMissionSuccessElements();
    if (els !== null) {
      clearMissionSuccessAnimation(els);
      els.visual.hidden = true;
      els.ecology.hidden = true;
      els.narration.hidden = true;
      els.tapHelp.hidden = true;
      els.card.hidden = true;
      els.section.hidden = true;
    }
    var unlock = document.getElementById(
      "ocean-rescue-mission-complete-unlock"
    );
    if (unlock) {
      unlock.hidden = true;
    }
    var unlockName = document.getElementById(
      "ocean-rescue-mission-complete-unlock-name"
    );
    if (unlockName) {
      unlockName.textContent = "";
    }
    shutdownRescueInteractionState();
  }

  function onMissionCompleteContinueClick(event) {
    if (!isMissionCompleteActionReady()) {
      return;
    }
    if (event && typeof event.preventDefault === "function") {
      event.preventDefault();
    }
    if (event && typeof event.stopPropagation === "function") {
      event.stopPropagation();
    }
    missionCompleteActionLock = true;
    disableMissionCompleteButtons();
    var sequence = activeMissionSuccessSequence;
    var focusMissionId = sequence.continueFocusMissionId;
    var token = State.beginTransition(State.Phases.MISSION_SELECT);
    if (token === null || !State.completeTransition(token)) {
      missionCompleteActionLock = false;
      enableMissionCompleteButtons();
      return;
    }
    cleanupMissionCompletePresentation();
    activeMissionSuccessSequence = null;
    activeRescueSequence = null;
    var stage = document.getElementById("ocean-rescue-stage");
    if (stage) {
      stage.hidden = true;
    }
    var launchSection = document.getElementById("ocean-rescue-launch");
    if (launchSection) {
      launchSection.hidden = true;
    }
    var gupSection = document.getElementById("ocean-rescue-gup-select");
    if (gupSection) {
      gupSection.hidden = true;
    }
    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-mission-complete-action", "continue");
      root.setAttribute("data-rescue-phase", "inactive");
      root.setAttribute("data-rescue-input", "disabled");
      root.removeAttribute("data-mission-complete-ready");
    }
    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = "Choose a mission";
    }
    renderMissionSelect({ focusMissionId: focusMissionId });
    missionCompleteActionLock = false;
  }

  function onMissionCompleteReplayClick(event) {
    if (!isMissionCompleteActionReady()) {
      return;
    }
    if (event && typeof event.preventDefault === "function") {
      event.preventDefault();
    }
    if (event && typeof event.stopPropagation === "function") {
      event.stopPropagation();
    }
    missionCompleteActionLock = true;
    disableMissionCompleteButtons();
    var sequence = activeMissionSuccessSequence;
    var missionId = sequence.missionId;
    var mission = missionById(missionId);
    if (mission === null) {
      missionCompleteActionLock = false;
      enableMissionCompleteButtons();
      return;
    }
    var gupSnapshot = Gups.getSnapshot();
    var gup = gupById(gupSnapshot.lastGupId);
    if (gup === null) {
      missionCompleteActionLock = false;
      enableMissionCompleteButtons();
      return;
    }
    var content = Launch.getMissionContent(missionId);
    var token = State.beginTransition(State.Phases.LAUNCH);
    if (token === null || !State.completeTransition(token)) {
      missionCompleteActionLock = false;
      enableMissionCompleteButtons();
      return;
    }
    cleanupMissionCompletePresentation();
    activeMissionSuccessSequence = null;
    activeRescueSequence = null;
    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-launch-mission-id", mission.id);
      root.setAttribute("data-launch-gup-id", gup.id);
      root.setAttribute("data-launch-ready", "true");
      root.setAttribute("data-mission-complete-action", "replay");
      root.removeAttribute("data-mission-complete-ready");
    }
    var launchEls = resolveLaunchElements();
    if (launchEls !== null && content !== null) {
      startLaunchPresentation(mission, gup, content, launchEls);
    }
  }

  function bindMissionSuccessPointerInput(section) {
    if (missionSuccessInputBound) {
      return;
    }
    if (typeof section.addEventListener !== "function") {
      return;
    }
    section.addEventListener("pointerdown", onMissionSuccessPointerDown);
    missionSuccessInputBound = true;
  }

  function onMissionSuccessPointerDown(event) {
    if (!event || typeof event !== "object") {
      return;
    }
    if (event.isPrimary === false) {
      return;
    }
    if (typeof event.button === "number" && event.button !== 0) {
      return;
    }
    if (activeMissionSuccessSequence === null) {
      return;
    }
    var sequence = activeMissionSuccessSequence;
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.RESCUE_SUCCESS) {
      return;
    }
    if (typeof event.preventDefault === "function") {
      event.preventDefault();
    }
    if (typeof event.stopPropagation === "function") {
      event.stopPropagation();
    }
    if (sequence.stage === "animation") {
      return;
    }
    if (sequence.stage === "ecology") {
      return;
    }
    if (sequence.stage === "narration-1") {
      clearMissionSuccessTimer();
      enterMissionSuccessNarration2(sequence);
      return;
    }
    if (sequence.stage === "narration-2") {
      clearMissionSuccessTimer();
      finalizeMissionSuccess(sequence);
    }
  }

  function startMissionSuccessPresentation(sequence) {
    if (activeMissionSuccessSequence !== null) {
      return false;
    }
    if (!MissionSuccess) {
      return false;
    }
    if (!sequence || typeof sequence !== "object") {
      return false;
    }
    if (typeof sequence.missionId !== "string") {
      return false;
    }
    var content = MissionSuccess.getContent(sequence.missionId);
    if (content === null) {
      return false;
    }
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.RESCUE_SUCCESS) {
      return false;
    }
    var mission = missionById(sequence.missionId);
    if (mission === null) {
      return false;
    }
    var els = resolveMissionSuccessElements();
    if (els === null) {
      return false;
    }
    if (typeof window.setTimeout !== "function") {
      return false;
    }
    shutdownRescueInteractionState();

    missionSuccessSequenceCounter += 1;
    var successSequence = {
      sequenceId: missionSuccessSequenceCounter,
      missionId: mission.id,
      missionTitle: mission.title,
      companion: mission.companion,
      content: content,
      stage: "animation"
    };
    activeMissionSuccessSequence = successSequence;

    var stageEl = document.getElementById("ocean-rescue-stage");
    if (stageEl) {
      stageEl.hidden = true;
    }
    var overlay = document.getElementById("ocean-rescue-rescue-overlay");
    if (overlay) {
      overlay.hidden = true;
    }

    bindMissionSuccessPointerInput(els.section);
    applyMissionSuccessAnimation(els, successSequence);

    var root = document.getElementById("ocean-rescue-root");
    if (root) {
      root.setAttribute("data-rescue-phase", "success-presentation");
      root.setAttribute("data-rescue-input", "disabled");
      root.setAttribute("data-mission-success-active", "true");
      root.setAttribute("data-mission-success-mission-id", mission.id);
      root.setAttribute("data-mission-success-stage", "animation");
      root.setAttribute("data-mission-success-input", "disabled");
      root.removeAttribute("data-mission-complete-ready");
    }

    var status = document.getElementById("ocean-rescue-status");
    if (status) {
      status.textContent = "Mission success: " + mission.title;
    }

    return scheduleMissionSuccessTimer(
      successSequence,
      "animation",
      MissionSuccess.SuccessAnimationMs,
      enterMissionSuccessEcology
    );
  }

  function drawRopeLine(context, rope, color, lineWidth) {
    drawRopeLineOffset(context, rope, color, lineWidth, 0);
  }

  function drawRopeLineOffset(context, rope, color, lineWidth, offsetX) {
    context.save();
    context.strokeStyle = color;
    context.lineWidth = lineWidth;
    context.lineCap = "round";
    context.beginPath();
    context.moveTo(rope.start.x + offsetX, rope.start.y);
    context.lineTo(rope.end.x + offsetX, rope.end.y);
    context.stroke();
    context.restore();
  }

  function drawCutRope(context, rope, color, lineWidth) {
    var mx = (rope.start.x + rope.end.x) / 2;
    var my = (rope.start.y + rope.end.y) / 2;
    var gap = 18;
    var dx = rope.end.x - rope.start.x;
    var dy = rope.end.y - rope.start.y;
    var length = Math.sqrt(dx * dx + dy * dy) || 1;
    var ux = dx / length;
    var uy = dy / length;
    context.save();
    context.strokeStyle = color;
    context.lineWidth = lineWidth;
    context.lineCap = "round";
    context.beginPath();
    context.moveTo(rope.start.x, rope.start.y);
    context.lineTo(mx - ux * gap, my - uy * gap);
    context.stroke();
    context.beginPath();
    context.moveTo(mx + ux * gap, my + uy * gap);
    context.lineTo(rope.end.x, rope.end.y);
    context.stroke();
    context.restore();
  }

  function seaTurtleShakeOffset(failureCount) {
    if (failureCount % 2 === 0) {
      return -6;
    }
    return 6;
  }

  function drawSeaTurtleRope(context, rope, snapshot) {
    var completed = snapshot.completedRopeIds.indexOf(rope.id) !== -1;
    var isActive = snapshot.activeRopeId === rope.id;
    var feedback = snapshot.feedback;
    if (completed) {
      if (snapshot.complete) {
        drawCutRope(context, rope, "rgba(180, 190, 200, 0.25)", 4);
      } else {
        drawCutRope(context, rope, "rgba(180, 190, 200, 0.40)", 5);
      }
      return;
    }
    if (isActive) {
      if (feedback === "success") {
        drawRopeLine(context, rope, "rgba(143, 211, 168, 0.85)", 10);
        return;
      }
      if (feedback === "failure") {
        drawRopeLineOffset(
          context,
          rope,
          "#ff6b6b",
          8,
          seaTurtleShakeOffset(snapshot.failureCount)
        );
        return;
      }
      drawRopeLine(context, rope, "#ffd166", 8);
      return;
    }
    drawRopeLine(context, rope, "rgba(214, 226, 238, 0.55)", 4);
  }

  function drawSeaTurtleTurtle(context, snapshot) {
    var x = 930;
    var y = 420;
    if (snapshot.complete) {
      context.beginPath();
      context.arc(x, y, 66, 0, Math.PI * 2);
      context.fillStyle = "#8fd3a8";
      context.fill();
      context.beginPath();
      context.arc(x + 64, y - 20, 22, 0, Math.PI * 2);
      context.fillStyle = "#b8e3c4";
      context.fill();
      context.beginPath();
      context.arc(x - 64, y - 30, 14, 0, Math.PI * 2);
      context.fillStyle = "#9fd6b4";
      context.fill();
      context.beginPath();
      context.arc(x - 62, y + 34, 14, 0, Math.PI * 2);
      context.fillStyle = "#9fd6b4";
      context.fill();
      context.fillStyle = "#0a1e33";
      context.font = "16px system-ui, sans-serif";
      context.textAlign = "center";
      context.fillText("Free!", x, y + 4);
      return;
    }
    context.beginPath();
    context.arc(x, y, 60, 0, Math.PI * 2);
    context.fillStyle = "#6fae87";
    context.fill();
    context.beginPath();
    context.arc(x + 58, y - 18, 20, 0, Math.PI * 2);
    context.fillStyle = "#9ad0a8";
    context.fill();
    context.beginPath();
    context.arc(x - 54, y - 24, 12, 0, Math.PI * 2);
    context.fillStyle = "#8ec9a2";
    context.fill();
    context.beginPath();
    context.arc(x - 50, y + 26, 12, 0, Math.PI * 2);
    context.fillStyle = "#8ec9a2";
    context.fill();
  }

  function drawSeaTurtleActiveMarkers(context, snapshot) {
    if (snapshot.activeRopeId === null) {
      return;
    }
    var rope = ropeById(snapshot.activeRopeId);
    if (rope === null) {
      return;
    }
    var enlarged = snapshot.helpLevel >= 2;
    var startRadius = enlarged ? 30 : 22;
    var endRadius = enlarged ? 22 : 15;
    var startFill = enlarged ? "#ffffff" : "#ffd166";
    context.beginPath();
    context.arc(rope.start.x, rope.start.y, startRadius + 8, 0, Math.PI * 2);
    context.fillStyle = "rgba(255, 209, 102, 0.25)";
    context.fill();
    context.beginPath();
    context.arc(rope.start.x, rope.start.y, startRadius, 0, Math.PI * 2);
    context.fillStyle = startFill;
    context.fill();
    context.beginPath();
    context.arc(rope.end.x, rope.end.y, endRadius, 0, Math.PI * 2);
    context.fillStyle = "#9ad0ff";
    context.fill();
    context.beginPath();
    context.arc(rope.end.x, rope.end.y, endRadius + 4, 0, Math.PI * 2);
    context.strokeStyle = "#ffffff";
    context.lineWidth = 3;
    context.stroke();
  }

  function drawSeaTurtleAssistedGuide(context, snapshot) {
    var rope = ropeById(snapshot.activeRopeId);
    if (rope === null) {
      return;
    }
    context.save();
    context.globalAlpha = 0.16;
    context.strokeStyle = "#bcd6ee";
    context.lineWidth = 200;
    context.lineCap = "round";
    context.beginPath();
    context.moveTo(rope.start.x, rope.start.y);
    context.lineTo(rope.end.x, rope.end.y);
    context.stroke();
    context.restore();
    context.save();
    context.strokeStyle = "#ffd166";
    context.lineWidth = 4;
    context.lineCap = "round";
    context.setLineDash([14, 12]);
    context.beginPath();
    context.moveTo(rope.start.x, rope.start.y);
    context.lineTo(rope.end.x, rope.end.y);
    context.stroke();
    context.restore();
  }

  function renderSeaTurtleFrame() {
    var canvas = document.getElementById("ocean-rescue-canvas");
    var context = null;
    if (canvas && typeof canvas.getContext === "function") {
      context = canvas.getContext("2d");
    }
    if (!canvas || !context) {
      return;
    }
    if (typeof context.clearRect !== "function") {
      return;
    }
    if (activeRescueSequence === null) {
      return;
    }
    if (!SeaTurtle) {
      return;
    }
    var width = canvas.width;
    var height = canvas.height;
    if (typeof width !== "number" || typeof height !== "number") {
      return;
    }
    var snapshot = SeaTurtle.getSnapshot();
    context.clearRect(0, 0, width, height);
    var layout = null;
    if (Terrain && typeof Terrain.getLayout === "function") {
      layout = Terrain.getLayout(activeRescueSequence.missionId);
    }
    var palette = terrainPalettes["coral-reef"];
    if (layout && layout.environment && terrainPalettes[layout.environment]) {
      palette = terrainPalettes[layout.environment];
    }
    drawRescueSiteBackground(context, width, height, palette);
    drawSeaTurtleGup(context, height);
    drawSeaTurtleCutter(context, height);
    drawSeaTurtleTurtle(context, snapshot);
    var ropes = SeaTurtle.Ropes;
    for (var i = 0; i < ropes.length; i += 1) {
      drawSeaTurtleRope(context, ropes[i], snapshot);
    }
    drawSeaTurtleActiveMarkers(context, snapshot);
    if (snapshot.helpLevel >= 3) {
      drawSeaTurtleAssistedGuide(context, snapshot);
    }
  }

  function drawSeaTurtleGup(context, height) {
    var gup = gupById(activeRescueSequence.gupId);
    var gupName = gup === null ? activeRescueSequence.gupId : gup.name;
    var gupY = Math.floor(height * 0.72);
    context.beginPath();
    context.arc(220, gupY, 36, 0, Math.PI * 2);
    context.fillStyle = "#ffd166";
    context.fill();
    context.fillStyle = "#0a1e33";
    context.font = "18px system-ui, sans-serif";
    context.textAlign = "center";
    context.fillText(gupName, 220, gupY);
  }

  function drawSeaTurtleCutter(context, height) {
    var gupY = Math.floor(height * 0.72);
    context.beginPath();
    context.arc(520, gupY, 30, 0, Math.PI * 2);
    context.fillStyle = "#9ad0ff";
    context.fill();
    context.fillStyle = "#0a1e33";
    context.font = "16px system-ui, sans-serif";
    context.textAlign = "center";
    context.fillText(activeRescueSequence.missionContent.toolLabel, 520, gupY - 44);
  }

  function renderCrabFrame() {
    var canvas = document.getElementById("ocean-rescue-canvas");
    var context = null;
    if (canvas && typeof canvas.getContext === "function") {
      context = canvas.getContext("2d");
    }
    if (!canvas || !context) {
      return;
    }
    if (typeof context.clearRect !== "function") {
      return;
    }
    if (activeRescueSequence === null) {
      return;
    }
    if (!Crab) {
      return;
    }
    var width = canvas.width;
    var height = canvas.height;
    if (typeof width !== "number" || typeof height !== "number") {
      return;
    }
    var snapshot = Crab.getSnapshot();
    context.clearRect(0, 0, width, height);
    var layout = null;
    if (Terrain && typeof Terrain.getLayout === "function") {
      layout = Terrain.getLayout(activeRescueSequence.missionId);
    }
    var palette = terrainPalettes["coral-reef"];
    if (layout && layout.environment && terrainPalettes[layout.environment]) {
      palette = terrainPalettes[layout.environment];
    }
    drawRescueSiteBackground(context, width, height, palette);
    drawCrabGup(context, height);
    drawCrabGrabber(context, height);
    drawCrabDropZone(context, snapshot);
    drawCrabArm(context, snapshot, height);
    drawCrabRocks(context, snapshot);
    drawCrabScene(context, snapshot);
    if (snapshot.helpLevel >= 2) {
      drawCrabHelpMarkers(context, snapshot);
    }
    if (snapshot.helpLevel >= 3) {
      drawCrabAssistedGuide(context, snapshot);
    }
  }

  function drawCrabGup(context, height) {
    var gup = gupById(activeRescueSequence.gupId);
    var gupName = gup === null ? activeRescueSequence.gupId : gup.name;
    var gupY = Math.floor(height * 0.72);
    context.beginPath();
    context.arc(220, gupY, 36, 0, Math.PI * 2);
    context.fillStyle = "#ffd166";
    context.fill();
    context.fillStyle = "#0a1e33";
    context.font = "18px system-ui, sans-serif";
    context.textAlign = "center";
    context.fillText(gupName, 220, gupY);
  }

  function drawCrabGrabber(context, height) {
    var gupY = Math.floor(height * 0.72);
    context.beginPath();
    context.arc(520, gupY, 30, 0, Math.PI * 2);
    context.fillStyle = "#9ad0ff";
    context.fill();
    context.fillStyle = "#0a1e33";
    context.font = "16px system-ui, sans-serif";
    context.textAlign = "center";
    context.fillText(activeRescueSequence.missionContent.toolLabel, 520, gupY - 44);
  }

  function drawRectOutline(context, x1, y1, x2, y2) {
    context.beginPath();
    context.moveTo(x1, y1);
    context.lineTo(x2, y1);
    context.lineTo(x2, y2);
    context.lineTo(x1, y2);
    context.lineTo(x1, y1);
    context.stroke();
  }

  function drawCrabDropZone(context, snapshot) {
    var zone = Crab.DropZone;
    var x1 = zone.x - zone.width / 2;
    var x2 = zone.x + zone.width / 2;
    var y1 = zone.y - zone.height / 2;
    var y2 = zone.y + zone.height / 2;
    var highlight = snapshot.helpLevel >= 2;
    context.fillStyle = "rgba(154, 208, 255, 0.08)";
    context.fillRect(x1, y1, zone.width, zone.height);
    context.save();
    context.strokeStyle = highlight ? "#ffffff" : "rgba(154, 208, 255, 0.55)";
    context.lineWidth = highlight ? 4 : 3;
    drawRectOutline(context, x1, y1, x2, y2);
    context.restore();
    context.fillStyle = "rgba(214, 226, 238, 0.9)";
    context.font = "15px system-ui, sans-serif";
    context.textAlign = "center";
    context.fillText("Drop zone", zone.x, y2 + 24);
    if (snapshot.helpLevel >= 3) {
      var margin = Crab.Constants.assistedZoneMargin;
      context.save();
      context.strokeStyle = "rgba(255, 209, 102, 0.85)";
      context.lineWidth = 2;
      context.setLineDash([10, 8]);
      drawRectOutline(context, x1 - margin, y1 - margin, x2 + margin, y2 + margin);
      context.restore();
    }
  }

  function drawCrabArm(context, snapshot, height) {
    if (snapshot.activeRockId === null) {
      return;
    }
    var rock = crabRockById(snapshot.activeRockId);
    if (rock === null) {
      return;
    }
    var center = snapshot.currentRockCenter;
    var targetX = center === null ? rock.start.x : center.x;
    var targetY = center === null ? rock.start.y : center.y;
    var gupY = Math.floor(height * 0.72);
    context.save();
    if (snapshot.grabbed) {
      context.strokeStyle = "rgba(154, 208, 255, 0.9)";
      context.lineWidth = 6;
    } else if (snapshot.holding) {
      context.strokeStyle = "rgba(154, 208, 255, 0.6)";
      context.lineWidth = 4;
      context.setLineDash([10, 8]);
    } else {
      context.strokeStyle = "rgba(154, 208, 255, 0.35)";
      context.lineWidth = 3;
      context.setLineDash([8, 10]);
    }
    context.lineCap = "round";
    context.beginPath();
    context.moveTo(520, gupY);
    context.lineTo(targetX, targetY);
    context.stroke();
    context.restore();
  }

  function drawCrabRocks(context, snapshot) {
    for (var i = 0; i < Crab.Rocks.length; i += 1) {
      var rock = Crab.Rocks[i];
      if (snapshot.completedRockIds.indexOf(rock.id) !== -1) {
        drawCrabCompletedRock(context, rock);
        continue;
      }
      if (snapshot.activeRockId === rock.id) {
        drawCrabActiveRock(context, rock, snapshot);
        continue;
      }
      drawCrabPendingRock(context, rock);
    }
  }

  function drawCrabCompletedRock(context, rock) {
    context.beginPath();
    context.arc(rock.placed.x, rock.placed.y, rock.radius, 0, Math.PI * 2);
    context.fillStyle = "#8fd3a8";
    context.fill();
    context.beginPath();
    context.arc(rock.placed.x, rock.placed.y, rock.radius - 6, 0, Math.PI * 2);
    context.strokeStyle = "rgba(10, 30, 51, 0.4)";
    context.lineWidth = 2;
    context.stroke();
  }

  function drawCrabPendingRock(context, rock) {
    context.beginPath();
    context.arc(rock.start.x, rock.start.y, rock.radius, 0, Math.PI * 2);
    context.fillStyle = "#5c6b7a";
    context.fill();
    context.beginPath();
    context.arc(rock.start.x, rock.start.y, rock.radius - 6, 0, Math.PI * 2);
    context.strokeStyle = "rgba(10, 30, 51, 0.35)";
    context.lineWidth = 2;
    context.stroke();
  }

  function drawCrabActiveRock(context, rock, snapshot) {
    var center = snapshot.currentRockCenter;
    var x = center === null ? rock.start.x : center.x;
    var y = center === null ? rock.start.y : center.y;
    var feedback = snapshot.feedback;
    if (feedback === "failure") {
      x += seaTurtleShakeOffset(snapshot.failureCount);
    }
    if (feedback === "success") {
      context.beginPath();
      context.arc(x, y, rock.radius + 16, 0, Math.PI * 2);
      context.fillStyle = "rgba(143, 211, 168, 0.25)";
      context.fill();
    }
    context.beginPath();
    context.arc(x, y, rock.radius, 0, Math.PI * 2);
    if (feedback === "success") {
      context.fillStyle = "#8fd3a8";
    } else if (feedback === "failure") {
      context.fillStyle = "#ff6b6b";
    } else {
      context.fillStyle = "#ffd166";
    }
    context.fill();
    context.beginPath();
    context.arc(x, y, rock.radius + 8, 0, Math.PI * 2);
    context.strokeStyle = "#ffffff";
    context.lineWidth = 3;
    context.stroke();
  }

  function drawCrabScene(context, snapshot) {
    var x = 900;
    var y = 500;
    if (snapshot.complete) {
      context.beginPath();
      context.arc(x, y, 60, 0, Math.PI * 2);
      context.fillStyle = "#d98a5f";
      context.fill();
      context.beginPath();
      context.arc(x - 66, y - 6, 16, 0, Math.PI * 2);
      context.fillStyle = "#e8a06f";
      context.fill();
      context.beginPath();
      context.arc(x + 66, y - 6, 16, 0, Math.PI * 2);
      context.fillStyle = "#e8a06f";
      context.fill();
      context.fillStyle = "#0a1e33";
      context.font = "16px system-ui, sans-serif";
      context.textAlign = "center";
      context.fillText("Free!", x, y + 4);
      return;
    }
    var count = snapshot.completedRockIds.length;
    var lift = count * 14;
    context.beginPath();
    context.arc(x, y - lift, 42 + count * 6, 0, Math.PI * 2);
    context.fillStyle = "#c97b56";
    context.fill();
    if (count >= 1) {
      context.fillStyle = "#0a1e33";
      context.beginPath();
      context.arc(x - 16, y - lift - 6, 5, 0, Math.PI * 2);
      context.fill();
      context.beginPath();
      context.arc(x + 16, y - lift - 6, 5, 0, Math.PI * 2);
      context.fill();
    }
    if (count >= 2) {
      context.beginPath();
      context.arc(x - 44 - lift, y - lift + 6, 12, 0, Math.PI * 2);
      context.fillStyle = "#e8a06f";
      context.fill();
      context.beginPath();
      context.arc(x + 44 + lift, y - lift + 6, 12, 0, Math.PI * 2);
      context.fillStyle = "#e8a06f";
      context.fill();
    }
  }

  function drawCrabHelpMarkers(context, snapshot) {
    if (snapshot.activeRockId === null) {
      return;
    }
    var rock = crabRockById(snapshot.activeRockId);
    if (rock === null) {
      return;
    }
    var center = snapshot.currentRockCenter;
    var x = center === null ? rock.start.x : center.x;
    var y = center === null ? rock.start.y : center.y;
    var hitRadius = Crab.Constants.assistedHitRadius;
    context.beginPath();
    context.arc(x, y, hitRadius, 0, Math.PI * 2);
    context.fillStyle = "rgba(255, 209, 102, 0.22)";
    context.fill();
    context.beginPath();
    context.arc(x, y, hitRadius, 0, Math.PI * 2);
    context.strokeStyle = "#ffffff";
    context.lineWidth = 3;
    context.stroke();
  }

  function drawCrabAssistedGuide(context, snapshot) {
    if (snapshot.activeRockId === null) {
      return;
    }
    var rock = crabRockById(snapshot.activeRockId);
    if (rock === null) {
      return;
    }
    context.save();
    context.strokeStyle = "#ffd166";
    context.lineWidth = 4;
    context.lineCap = "round";
    context.setLineDash([14, 12]);
    context.beginPath();
    context.moveTo(rock.start.x, rock.start.y);
    context.lineTo(Crab.DropZone.x, Crab.DropZone.y);
    context.stroke();
    context.restore();
  }

  function youngWhaleShakeOffset(failureCount) {
    if (failureCount % 2 === 0) {
      return -6;
    }
    return 6;
  }

  function drawYoungWhaleGup(context, snapshot) {
    var gup = gupById(activeRescueSequence.gupId);
    var gupName = gup === null ? activeRescueSequence.gupId : gup.name;
    var center =
      snapshot.currentGupCenter === null
        ? YoungWhale.GupStart
        : snapshot.currentGupCenter;
    context.beginPath();
    context.arc(center.x, center.y, 36, 0, Math.PI * 2);
    context.fillStyle = "#ffd166";
    context.fill();
    context.fillStyle = "#0a1e33";
    context.font = "18px system-ui, sans-serif";
    context.textAlign = "center";
    context.fillText(gupName, center.x, center.y);
  }

  function drawYoungWhaleHook(context, snapshot) {
    var radius =
      snapshot.helpLevel >= 2
        ? YoungWhale.Constants.assistedHookRadius
        : YoungWhale.Constants.hookRadius;
    context.beginPath();
    context.arc(YoungWhale.GupHook.x, YoungWhale.GupHook.y, radius, 0, Math.PI * 2);
    context.strokeStyle = "#9ad0ff";
    context.lineWidth = 3;
    context.stroke();
    context.beginPath();
    context.arc(YoungWhale.GupHook.x, YoungWhale.GupHook.y, 12, 0, Math.PI * 2);
    context.fillStyle = "#9ad0ff";
    context.fill();
  }

  function drawYoungWhaleSafeSpot(context, snapshot) {
    if (snapshot.stage !== "towing") {
      return;
    }
    var debris = youngWhaleDebrisById(snapshot.activeDebrisId);
    if (debris === null) {
      return;
    }
    if (snapshot.completedDebrisIds.indexOf(debris.id) !== -1) {
      return;
    }
    var radius =
      snapshot.helpLevel >= 3
        ? YoungWhale.Constants.assistedSafeSpotRadius
        : YoungWhale.Constants.safeSpotRadius;
    var enlarged = snapshot.helpLevel >= 2;
    context.beginPath();
    context.arc(debris.safeSpot.x, debris.safeSpot.y, radius, 0, Math.PI * 2);
    context.fillStyle = "rgba(143, 211, 168, 0.18)";
    context.fill();
    context.beginPath();
    context.arc(debris.safeSpot.x, debris.safeSpot.y, radius, 0, Math.PI * 2);
    context.strokeStyle = enlarged ? "#ffffff" : "rgba(143, 211, 168, 0.7)";
    context.lineWidth = enlarged ? 4 : 3;
    context.stroke();
    context.fillStyle = "rgba(214, 226, 238, 0.9)";
    context.font = "15px system-ui, sans-serif";
    context.textAlign = "center";
    context.fillText("Safe spot", debris.safeSpot.x, debris.safeSpot.y + radius + 18);
  }

  function drawYoungWhaleDebris(context, snapshot) {
    for (var i = 0; i < YoungWhale.Debris.length; i += 1) {
      var debris = YoungWhale.Debris[i];
      if (snapshot.completedDebrisIds.indexOf(debris.id) !== -1) {
        drawYoungWhaleCompletedDebris(context, debris, snapshot);
        continue;
      }
      if (snapshot.activeDebrisId === debris.id) {
        drawYoungWhaleActiveDebris(context, debris, snapshot);
        continue;
      }
      drawYoungWhalePendingDebris(context, debris);
    }
  }

  function drawYoungWhaleCompletedDebris(context, debris, snapshot) {
    var x = debris.cleared.x;
    var y = debris.cleared.y;
    if (snapshot.feedback === "success") {
      context.beginPath();
      context.arc(x, y, debris.radius + 14, 0, Math.PI * 2);
      context.fillStyle = "rgba(143, 211, 168, 0.25)";
      context.fill();
    }
    context.beginPath();
    context.arc(x, y, debris.radius, 0, Math.PI * 2);
    context.fillStyle = "rgba(143, 211, 168, 0.65)";
    context.fill();
    context.beginPath();
    context.arc(x, y, debris.radius - 6, 0, Math.PI * 2);
    context.strokeStyle = "rgba(10, 30, 51, 0.4)";
    context.lineWidth = 2;
    context.stroke();
  }

  function drawYoungWhalePendingDebris(context, debris) {
    context.beginPath();
    context.arc(debris.start.x, debris.start.y, debris.radius, 0, Math.PI * 2);
    context.fillStyle = "#5c6b7a";
    context.fill();
  }

  function drawYoungWhaleActiveDebris(context, debris, snapshot) {
    var center = snapshot.currentDebrisCenter;
    var x = center === null ? debris.start.x : center.x;
    var y = center === null ? debris.start.y : center.y;
    var feedback = snapshot.feedback;
    if (feedback === "failure") {
      x += youngWhaleShakeOffset(snapshot.failureCount);
    }
    if (feedback === "success") {
      context.beginPath();
      context.arc(x, y, debris.radius + 14, 0, Math.PI * 2);
      context.fillStyle = "rgba(143, 211, 168, 0.25)";
      context.fill();
    }
    context.beginPath();
    context.arc(x, y, debris.radius, 0, Math.PI * 2);
    if (feedback === "success") {
      context.fillStyle = "#8fd3a8";
    } else if (feedback === "failure") {
      context.fillStyle = "#ff6b6b";
    } else {
      context.fillStyle = "#ffd166";
    }
    context.fill();
  }

  function drawYoungWhaleConnectionLine(context, snapshot, pointerX, pointerY) {
    if (snapshot.connected) {
      return;
    }
    if (snapshot.stage !== "connection") {
      return;
    }
    if (!snapshot.pointerActive) {
      return;
    }
    var debris = youngWhaleDebrisById(snapshot.activeDebrisId);
    if (debris === null) {
      return;
    }
    if (typeof pointerX !== "number" || typeof pointerY !== "number") {
      return;
    }
    context.save();
    if (snapshot.feedback === "failure") {
      context.strokeStyle = "#ff6b6b";
      context.lineWidth = 6;
    } else {
      context.strokeStyle = "rgba(154, 208, 255, 0.85)";
      context.lineWidth = 5;
    }
    context.lineCap = "round";
    context.beginPath();
    context.moveTo(debris.connection.x, debris.connection.y);
    context.lineTo(pointerX, pointerY);
    context.stroke();
    context.restore();
  }

  function drawYoungWhaleTowLine(context, snapshot) {
    if (!snapshot.connected) {
      return;
    }
    var debris = youngWhaleDebrisById(snapshot.activeDebrisId);
    if (debris === null) {
      return;
    }
    context.save();
    context.strokeStyle = "rgba(154, 208, 255, 0.9)";
    context.lineWidth = 6;
    context.lineCap = "round";
    context.beginPath();
    context.moveTo(debris.connection.x, debris.connection.y);
    context.lineTo(YoungWhale.GupHook.x, YoungWhale.GupHook.y);
    context.stroke();
    context.restore();
  }

  function drawYoungWhaleActiveMarkers(context, snapshot) {
    if (snapshot.stage === "connection") {
      var debris = youngWhaleDebrisById(snapshot.activeDebrisId);
      if (debris === null) {
        return;
      }
      var startRadius =
        snapshot.helpLevel >= 2
          ? YoungWhale.Constants.assistedConnectionStartRadius
          : YoungWhale.Constants.connectionStartRadius;
      var hookRadiusMarker =
        snapshot.helpLevel >= 2
          ? YoungWhale.Constants.assistedHookRadius
          : YoungWhale.Constants.hookRadius;
      context.beginPath();
      context.arc(debris.connection.x, debris.connection.y, startRadius + 6, 0, Math.PI * 2);
      context.fillStyle = "rgba(255, 209, 102, 0.25)";
      context.fill();
      context.beginPath();
      context.arc(debris.connection.x, debris.connection.y, startRadius, 0, Math.PI * 2);
      context.strokeStyle = "#ffffff";
      context.lineWidth = 3;
      context.stroke();
      context.beginPath();
      context.arc(YoungWhale.GupHook.x, YoungWhale.GupHook.y, hookRadiusMarker, 0, Math.PI * 2);
      context.strokeStyle = "#ffffff";
      context.lineWidth = 3;
      context.stroke();
    }
    if (snapshot.stage === "towing") {
      var gupRadius =
        snapshot.helpLevel >= 2
          ? YoungWhale.Constants.assistedGupHitRadius
          : YoungWhale.Constants.gupHitRadius;
      var center =
        snapshot.currentGupCenter === null
          ? YoungWhale.GupStart
          : snapshot.currentGupCenter;
      context.beginPath();
      context.arc(center.x, center.y, gupRadius, 0, Math.PI * 2);
      context.strokeStyle = "#ffffff";
      context.lineWidth = 3;
      context.stroke();
    }
  }

  function drawYoungWhaleAssistedGuide(context, snapshot) {
    var debris = youngWhaleDebrisById(snapshot.activeDebrisId);
    if (debris === null) {
      return;
    }
    context.save();
    context.strokeStyle = "#ffd166";
    context.lineWidth = 4;
    context.lineCap = "round";
    context.setLineDash([14, 12]);
    if (snapshot.stage === "connection") {
      context.beginPath();
      context.moveTo(debris.connection.x, debris.connection.y);
      context.lineTo(YoungWhale.GupHook.x, YoungWhale.GupHook.y);
    } else if (snapshot.stage === "towing") {
      context.beginPath();
      context.moveTo(YoungWhale.GupStart.x, YoungWhale.GupStart.y);
      context.lineTo(debris.safeSpot.x, debris.safeSpot.y);
    }
    context.stroke();
    context.restore();
  }

  function drawYoungWhaleWhale(context, snapshot) {
    var count = snapshot.completedDebrisIds.length;
    var x = 1040;
    var y = 410;
    if (count >= 2) {
      x = 1000;
      y = 400;
    }
    if (snapshot.complete) {
      x = 880;
      y = 330;
    }
    context.beginPath();
    context.arc(x, y, 66, 0, Math.PI * 2);
    context.fillStyle = "#5b8fbc";
    context.fill();
    context.beginPath();
    context.arc(x, y - 66, 34, 0, Math.PI * 2);
    context.fillStyle = "#7aa9d4";
    context.fill();
    if (count >= 1) {
      context.beginPath();
      context.arc(x - 12, y - 8, 7, 0, Math.PI * 2);
      context.fillStyle = "#0a1e33";
      context.fill();
      context.beginPath();
      context.arc(x - 12, y + 18, 7, 0, Math.PI * 2);
      context.fillStyle = "#0a1e33";
      context.fill();
    } else {
      context.beginPath();
      context.arc(x - 10, y - 8, 3, 0, Math.PI * 2);
      context.fillStyle = "#0a1e33";
      context.fill();
      context.beginPath();
      context.arc(x - 10, y + 18, 3, 0, Math.PI * 2);
      context.fillStyle = "#0a1e33";
      context.fill();
    }
  }

  function renderYoungWhaleFrame(pointerX, pointerY) {
    var canvas = document.getElementById("ocean-rescue-canvas");
    var context = null;
    if (canvas && typeof canvas.getContext === "function") {
      context = canvas.getContext("2d");
    }
    if (!canvas || !context) {
      return;
    }
    if (typeof context.clearRect !== "function") {
      return;
    }
    if (activeRescueSequence === null) {
      return;
    }
    if (!YoungWhale) {
      return;
    }
    var width = canvas.width;
    var height = canvas.height;
    if (typeof width !== "number" || typeof height !== "number") {
      return;
    }
    var snapshot = YoungWhale.getSnapshot();
    context.clearRect(0, 0, width, height);
    var layout = null;
    if (Terrain && typeof Terrain.getLayout === "function") {
      layout = Terrain.getLayout(activeRescueSequence.missionId);
    }
    var palette = terrainPalettes["coral-reef"];
    if (layout && layout.environment && terrainPalettes[layout.environment]) {
      palette = terrainPalettes[layout.environment];
    }
    drawRescueSiteBackground(context, width, height, palette);
    drawYoungWhaleWhale(context, snapshot);
    drawYoungWhaleGup(context, snapshot);
    drawYoungWhaleHook(context, snapshot);
    drawYoungWhaleDebris(context, snapshot);
    drawYoungWhaleSafeSpot(context, snapshot);
    drawYoungWhaleConnectionLine(context, snapshot, pointerX, pointerY);
    drawYoungWhaleTowLine(context, snapshot);
    drawYoungWhaleActiveMarkers(context, snapshot);
    if (snapshot.helpLevel >= 3) {
      drawYoungWhaleAssistedGuide(context, snapshot);
    }
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
    if (!rescueInputBound) {
      var stage = document.getElementById("ocean-rescue-stage");
      if (stage && typeof stage.addEventListener === "function") {
        stage.addEventListener("pointerdown", onRescueStagePointerDown);
        rescueInputBound = true;
      }
    }
    bindMissionCompleteActions();
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
