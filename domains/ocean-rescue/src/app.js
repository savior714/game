(function () {
  var State = window.OceanRescue.State;
  var Missions = window.OceanRescue.Missions;
  var Gups = window.OceanRescue.Gups;
  var Launch = window.OceanRescue.Launch;
  var Travel = window.OceanRescue.Travel || null;
  var Terrain = window.OceanRescue.Terrain || null;
  var Rescue = window.OceanRescue.Rescue || null;
  var SeaTurtle = window.OceanRescue.SeaTurtle || null;

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
    if (!SeaTurtle) {
      return false;
    }
    if (activeRescueSequence === null) {
      return false;
    }
    if (activeRescueSequence.missionId !== SeaTurtle.MissionId) {
      return false;
    }
    var snapshot = State.getSnapshot();
    if (snapshot.phase !== State.Phases.RESCUE_ACTIVE) {
      return false;
    }
    var seaTurtle = SeaTurtle.getSnapshot();
    if (!seaTurtle.active) {
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
    if (seaTurtlePointerId !== null) {
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

  function onRescuePointerDown(event) {
    if (!acceptRescuePointerEvent(event)) {
      return;
    }
    var mapped = mapRescueCoordinates(event);
    if (mapped === null) {
      return;
    }
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
    SeaTurtle.pointerMove(event.pointerId, mapped.x, mapped.y);
    renderSeaTurtleFrame();
    updateSeaTurtleRootMarkers();
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
    var result = null;
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
