(function () {
  var State = window.OceanRescue.State;
  var Missions = window.OceanRescue.Missions;
  var Gups = window.OceanRescue.Gups;
  var Launch = window.OceanRescue.Launch;
  var Travel = window.OceanRescue.Travel || null;
  var Terrain = window.OceanRescue.Terrain || null;
  var Rescue = window.OceanRescue.Rescue || null;

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
