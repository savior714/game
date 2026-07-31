(function () {
  "use strict";

  var WIDTH = 1280;
  var HEIGHT = 720;
  var RUNTIME = "OceanRescue.RenderRuntime";
  var CONTAINER_NAMES = [
    "farBackground",
    "midground",
    "gameplayWorld",
    "legacyPaintBridge",
    "submarine",
    "turtleAndObstacle",
    "seaOtterRig",
    "foreground",
    "effects",
    "hud"
  ];
  var GAMEPLAY_CHILDREN = [
    "legacyPaintBridge",
    "submarine",
    "turtleAndObstacle",
    "seaOtterRig"
  ];

  var application = null;
  var bootPromise = null;
  var legacyCanvas = null;
  var legacyContext = null;
  var legacySource = null;
  var legacyTexture = null;
  var legacySprite = null;
  var sheets = [];
  var textures = {};
  var containers = {};
  var paused = false;
  var dirty = false;
  var ready = false;
  var failed = false;
  var legacyBridgeVisible = true;
  var PIXI = window.PIXI;

  function getRoot() {
    return document.getElementById("ocean-rescue-root");
  }

  function setDiagnostic(name, value) {
    var root = getRoot();
    if (root) {
      root.setAttribute(name, String(value));
    }
  }

  function setBootingDiagnostics() {
    setDiagnostic("data-render-runtime", "booting");
    setDiagnostic("data-render-logical-width", WIDTH);
    setDiagnostic("data-render-logical-height", HEIGHT);
    setDiagnostic("data-render-frame-mode", "explicit");
  }

  function setReadyDiagnostics(backend, resolution, bundleCount) {
    setDiagnostic("data-render-runtime", "ready");
    setDiagnostic("data-render-backend", backend);
    setDiagnostic("data-render-logical-width", WIDTH);
    setDiagnostic("data-render-logical-height", HEIGHT);
    setDiagnostic("data-render-resolution", resolution);
    setDiagnostic("data-render-texture-count", getTextureAliases().length);
    setDiagnostic("data-render-bundle-count", bundleCount);
    setDiagnostic("data-render-frame-mode", "explicit");
  }

  function setFailedDiagnostics() {
    failed = true;
    ready = false;
    setDiagnostic("data-render-runtime", "failed");
    setDiagnostic("data-render-backend", "");
  }

  function compatibilityMessage() {
    return "This device could not start the Ocean Rescue renderer.";
  }

  function showCompatibilityFailure() {
    var root = getRoot();
    var status = document.getElementById("ocean-rescue-status");
    setFailedDiagnostics();
    if (root) {
      root.setAttribute("data-ocean-rescue-ready", "false");
    }
    if (status) {
      status.textContent = compatibilityMessage();
    }
  }

  function getEmbeddedFile(files, path, kind) {
    var file = files && files[path];
    if (!file || typeof file !== "object") {
      throw new Error("Missing embedded " + kind + ": " + path);
    }
    if (typeof file.sha256 !== "string" || file.sha256.length !== 64) {
      throw new Error("Invalid embedded hash: " + path);
    }
    return file;
  }

  function decodeBase64(dataUri) {
    if (typeof dataUri !== "string" || dataUri.indexOf("data:image/png;base64,") !== 0) {
      throw new Error("Invalid embedded PNG data URI");
    }
    var base64 = dataUri.slice("data:image/png;base64,".length);
    var binary = window.atob(base64);
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
  }

  function utf8Bytes(text) {
    if (typeof TextEncoder === "function") {
      return new TextEncoder().encode(text);
    }
    var encoded = unescape(encodeURIComponent(text));
    var bytes = new Uint8Array(encoded.length);
    for (var i = 0; i < encoded.length; i += 1) {
      bytes[i] = encoded.charCodeAt(i);
    }
    return bytes;
  }

  function hexDigest(bytes) {
    var result = "";
    for (var i = 0; i < bytes.length; i += 1) {
      result += bytes[i].toString(16).padStart(2, "0");
    }
    return result;
  }

  function verifyDigest(bytes, expected) {
    if (!window.crypto || !window.crypto.subtle) {
      return Promise.resolve(true);
    }
    return window.crypto.subtle.digest("SHA-256", bytes).then(function (digest) {
      if (hexDigest(new Uint8Array(digest)) !== expected) {
        throw new Error("Embedded hash mismatch");
      }
      return true;
    });
  }

  function verifyEmbeddedFile(file, expectedHash, bytes) {
    if (expectedHash && file.sha256 !== expectedHash) {
      throw new Error("Embedded manifest hash mismatch");
    }
    return verifyDigest(bytes, file.sha256);
  }

  function decodeImage(dataUri) {
    return new Promise(function (resolve, reject) {
      if (typeof Image !== "function") {
        reject(new Error("Image decoding is unavailable"));
        return;
      }
      var image = new Image();
      image.onload = function () {
        resolve(image);
      };
      image.onerror = function () {
        reject(new Error("Embedded PNG decode failed"));
      };
      image.src = dataUri;
    });
  }

  function createTexture(resource, label) {
    var Source = window.PIXI.ImageSource || window.PIXI.TextureSource;
    if (typeof Source !== "function" || typeof window.PIXI.Texture !== "function") {
      throw new Error("Pixi texture source API is unavailable");
    }
    var source = new Source({ resource: resource, label: label });
    return {
      source: source,
      texture: new window.PIXI.Texture({ source: source, label: label })
    };
  }

  function parseAtlasPage(bundle, page, files) {
    var jsonPath = bundle.name + "/" + page.spritesheet;
    var imagePath = bundle.name + "/" + page.image;
    var jsonFile = getEmbeddedFile(files, jsonPath, "spritesheet JSON");
    var imageFile = getEmbeddedFile(files, imagePath, "atlas PNG");
    var jsonBytes = utf8Bytes(jsonFile.text);
    var imageBytes = decodeBase64(imageFile.dataUri);
    return Promise.all([
      verifyEmbeddedFile(jsonFile, page.spritesheetSha256, jsonBytes),
      verifyEmbeddedFile(imageFile, page.imageSha256, imageBytes)
    ]).then(function () {
      var parsedJson;
      try {
        parsedJson = JSON.parse(jsonFile.text);
      } catch (error) {
        throw new Error("Malformed spritesheet JSON");
      }
      return decodeImage(imageFile.dataUri).then(function (image) {
        var sourceAndTexture = createTexture(image, jsonPath);
        var sheet = new window.PIXI.Spritesheet({
          texture: sourceAndTexture.texture,
          data: parsedJson
        });
        sheets.push(sheet);
        return sheet.parse().then(function () {
          var aliases = page.aliases || Object.keys(sheet.textures);
          for (var i = 0; i < aliases.length; i += 1) {
            var alias = aliases[i];
            var texture = sheet.textures[alias];
            if (!texture) {
              throw new Error("Missing texture alias: " + alias);
            }
            if (textures[alias]) {
              throw new Error("Duplicate texture alias: " + alias);
            }
            textures[alias] = texture;
          }
          return sheet;
        });
      });
    });
  }

  function parseAtlases() {
    var assets = window.OceanRescue && window.OceanRescue.RenderAssets;
    var manifest = assets && assets.atlasManifest;
    if (!manifest || !Array.isArray(manifest.bundles) || !assets.files) {
      return Promise.reject(new Error("Embedded atlas manifest is unavailable"));
    }
    textures = {};
    sheets = [];
    var jobs = [];
    for (var i = 0; i < manifest.bundles.length; i += 1) {
      var bundle = manifest.bundles[i];
      if (!bundle || !Array.isArray(bundle.pages)) {
        return Promise.reject(new Error("Invalid atlas bundle"));
      }
      for (var j = 0; j < bundle.pages.length; j += 1) {
        jobs.push(parseAtlasPage(bundle, bundle.pages[j], assets.files));
      }
    }
    return Promise.all(jobs).then(function () {
      var expected = [];
      for (var b = 0; b < manifest.bundles.length; b += 1) {
        expected = expected.concat(manifest.bundles[b].aliases || []);
      }
      expected.sort();
      var actual = getTextureAliases();
      if (expected.length !== actual.length) {
        throw new Error("Embedded texture alias count mismatch");
      }
      for (var k = 0; k < expected.length; k += 1) {
        if (expected[k] !== actual[k]) {
          throw new Error("Embedded texture alias set mismatch");
        }
      }
      return manifest.bundles.length;
    });
  }

  function detectBackend(renderer) {
    if (window.PIXI.WebGLRenderer && renderer instanceof window.PIXI.WebGLRenderer) {
      return "webgl";
    }
    if (window.PIXI.CanvasRenderer && renderer instanceof window.PIXI.CanvasRenderer) {
      return "canvas";
    }
    if (renderer && (renderer.type === "webgl" || renderer.type === "canvas")) {
      return renderer.type;
    }
    return null;
  }

  function createContainers() {
    if (typeof window.PIXI.Container !== "function") {
      throw new Error("Pixi Container API is unavailable");
    }
    var stage = application.stage;
    stage.label = "stage";
    stage.name = "stage";
    stage.eventMode = "none";
    containers = {};
    for (var i = 0; i < CONTAINER_NAMES.length; i += 1) {
      var name = CONTAINER_NAMES[i];
      var container = new window.PIXI.Container();
      container.label = name;
      container.name = name;
      container.eventMode = "none";
      containers[name] = container;
    }
    stage.addChild(containers.farBackground);
    stage.addChild(containers.midground);
    stage.addChild(containers.gameplayWorld);
    stage.addChild(containers.foreground);
    stage.addChild(containers.effects);
    stage.addChild(containers.hud);
    containers.gameplayWorld.addChild(containers.legacyPaintBridge);
    containers.gameplayWorld.addChild(containers.submarine);
    containers.gameplayWorld.addChild(containers.turtleAndObstacle);
    containers.gameplayWorld.addChild(containers.seaOtterRig);
  }

  function createLegacyBridge() {
    legacyCanvas = document.createElement("canvas");
    legacyCanvas.width = WIDTH;
    legacyCanvas.height = HEIGHT;
    legacyContext = legacyCanvas.getContext("2d");
    if (!legacyContext) {
      throw new Error("Legacy canvas 2D context is unavailable");
    }
    if (typeof window.PIXI.CanvasSource !== "function" || typeof window.PIXI.Sprite !== "function") {
      throw new Error("Pixi canvas bridge API is unavailable");
    }
    legacySource = new window.PIXI.CanvasSource({ resource: legacyCanvas });
    legacyTexture = new window.PIXI.Texture({ source: legacySource });
    legacySprite = new window.PIXI.Sprite(legacyTexture);
    legacySprite.position.set(0, 0);
    legacySprite.width = WIDTH;
    legacySprite.height = HEIGHT;
    legacySprite.eventMode = "none";
    legacySprite.visible = true;
    containers.legacyPaintBridge.addChild(legacySprite);
  }

  async function initializeApplication() {
    var visibleCanvas = document.getElementById("ocean-rescue-canvas");
    if (!visibleCanvas || typeof window.PIXI.Application !== "function") {
      return Promise.reject(new Error("Ocean Rescue canvas or Pixi Application is unavailable"));
    }
    var resolution = Math.min(window.devicePixelRatio || 1, 2);
    application = new PIXI.Application();
    await application.init({
      canvas: visibleCanvas,
      width: WIDTH,
      height: HEIGHT,
      resolution: resolution,
      autoDensity: false,
      preference: ["webgl", "canvas"],
      autoStart: false,
      sharedTicker: false,
      antialias: true,
      backgroundAlpha: 1,
      backgroundColor: 0x0a1e33,
      hello: false
    });
    var backend = detectBackend(application.renderer);
    if (!backend) {
      throw new Error("Unknown Pixi renderer backend");
    }
    if (!application.renderer || !application.renderer.events) {
      throw new Error("Pixi renderer event system is unavailable");
    }
    createContainers();
    createLegacyBridge();
    var bundleCount = await parseAtlases();
    ready = true;
    failed = false;
    setReadyDiagnostics(backend, resolution, bundleCount);
    application.render();
    return api;
  }

  function cleanupFailedBoot() {
    if (application && typeof application.destroy === "function") {
      application.destroy(false, { children: true, texture: false, baseTexture: false });
    }
    application = null;
    legacyCanvas = null;
    legacyContext = null;
    legacySource = null;
    legacyTexture = null;
    legacySprite = null;
    containers = {};
    textures = {};
    sheets = [];
  }

  function boot() {
    if (ready) {
      return Promise.resolve(api);
    }
    if (bootPromise) {
      return bootPromise;
    }
    setBootingDiagnostics();
    bootPromise = initializeApplication().catch(function (error) {
      cleanupFailedBoot();
      setFailedDiagnostics();
      throw error;
    });
    return bootPromise;
  }

  function presentLegacyFrame() {
    if (!ready || !application || !legacySource) {
      return false;
    }
    if (paused) {
      dirty = true;
      return false;
    }
    legacySource.update();
    application.render();
    dirty = false;
    return true;
  }

  function renderSceneFrame() {
    if (!ready || !application) {
      return false;
    }
    if (paused) {
      dirty = true;
      return false;
    }
    application.render();
    dirty = false;
    return true;
  }

  function setLegacyBridgeVisible(value) {
    legacyBridgeVisible = value === true;
    if (legacySprite) {
      legacySprite.visible = legacyBridgeVisible;
    }
    setDiagnostic("data-render-legacy-visible", legacyBridgeVisible);
    return legacyBridgeVisible;
  }

  function mapClientToLogical(clientX, clientY) {
    var point = new window.PIXI.Point();
    if (application && application.renderer && application.renderer.events) {
      application.renderer.events.mapPositionToPoint(point, clientX, clientY);
    } else {
      var canvas = document.getElementById("ocean-rescue-canvas");
      var rect = canvas && canvas.getBoundingClientRect ? canvas.getBoundingClientRect() : null;
      if (!rect || rect.width <= 0 || rect.height <= 0) {
        return { x: NaN, y: NaN, inside: false };
      }
      point.x = (clientX - rect.left) * (WIDTH / rect.width);
      point.y = (clientY - rect.top) * (HEIGHT / rect.height);
    }
    return {
      x: point.x,
      y: point.y,
      inside: point.x >= 0 && point.x <= WIDTH && point.y >= 0 && point.y <= HEIGHT
    };
  }

  function destroy() {
    if (bootPromise && !ready) {
      bootPromise = null;
    }
    for (var i = 0; i < sheets.length; i += 1) {
      if (sheets[i] && typeof sheets[i].destroy === "function") {
        sheets[i].destroy(true);
      }
    }
    if (legacyTexture && typeof legacyTexture.destroy === "function") {
      legacyTexture.destroy(false);
    }
    if (legacySource && typeof legacySource.destroy === "function") {
      legacySource.destroy();
    }
    if (application && typeof application.destroy === "function") {
      application.destroy(false, { children: true, texture: false, baseTexture: false });
    }
    application = null;
    bootPromise = null;
    legacyCanvas = null;
    legacyContext = null;
    legacySource = null;
    legacyTexture = null;
    legacySprite = null;
    sheets = [];
    textures = {};
    containers = {};
    legacyBridgeVisible = true;
    ready = false;
    failed = false;
    paused = false;
    dirty = false;
    setDiagnostic("data-render-runtime", "");
    setDiagnostic("data-render-backend", "");
  }

  function getTexture(alias) {
    return Object.prototype.hasOwnProperty.call(textures, alias) ? textures[alias] : null;
  }

  function hasTexture(alias) {
    return !!getTexture(alias);
  }

  function getTextureAliases() {
    return Object.keys(textures).sort();
  }

  function getContainer(name) {
    return containers[name] || null;
  }

  function getContainerNames() {
    return CONTAINER_NAMES.slice();
  }

  var api = {
    boot: boot,
    destroy: destroy,
    getTexture: getTexture,
    hasTexture: hasTexture,
    getTextureAliases: getTextureAliases,
    getContainer: getContainer,
    getContainerNames: getContainerNames,
    getLegacyCanvas: function () { return legacyCanvas; },
    getLegacyContext: function () { return legacyContext; },
    presentLegacyFrame: presentLegacyFrame,
    renderSceneFrame: renderSceneFrame,
    setLegacyBridgeVisible: setLegacyBridgeVisible,
    getLegacyBridgeVisible: function () { return legacyBridgeVisible; },
    mapClientToLogical: mapClientToLogical,
    showCompatibilityFailure: showCompatibilityFailure,
    isReady: function () { return ready; },
    isPaused: function () { return paused; },
    pause: function () { paused = true; },
    resume: function () {
      var wasDirty = dirty;
      paused = false;
      if (wasDirty) {
        renderSceneFrame();
      }
    }
  };

  window.OceanRescue = window.OceanRescue || {};
  window.OceanRescue.RenderRuntime = api;
})();
