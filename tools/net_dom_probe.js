/*
  Usage (browser console):
  1) Paste this file content in DevTools console
  2) Run: NetDomProbe.start()
  3) Reproduce net acquire/activate flows
  4) Run: NetDomProbe.stop()
  5) Inspect: NetDomProbe.getReport()
*/
(function initNetDomProbe(global) {
  const samples = [];
  let timer = null;

  function snapshot() {
    const track = document.getElementById("rp-track");
    if (!track) return;

    const netElements = track.querySelectorAll(".net-element").length;
    const indicator = document.getElementById("net-indicator");
    const indicatorClass = indicator ? indicator.className : "none";

    samples.push({
      t: Date.now(),
      netElements,
      indicatorClass,
      indicatorExists: Boolean(indicator),
    });
  }

  function start(intervalMs = 120) {
    if (timer) return false;
    samples.length = 0;
    timer = setInterval(snapshot, intervalMs);
    return true;
  }

  function stop() {
    if (!timer) return false;
    clearInterval(timer);
    timer = null;
    return true;
  }

  function getReport() {
    const maxNetElements = samples.reduce((max, s) => Math.max(max, s.netElements), 0);
    const overlapObserved = maxNetElements > 1;
    return {
      sampleCount: samples.length,
      maxNetElements,
      overlapObserved,
      samples,
    };
  }

  global.NetDomProbe = { start, stop, getReport };
})(window);
