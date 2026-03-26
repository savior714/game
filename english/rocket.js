if (typeof RocketCore === "undefined") {
  throw new Error("RocketCore is not loaded. Check script order.");
}

RocketCore.install(window);
