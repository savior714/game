import "../terrain.js";

const Terrain = window.OceanRescue?.Terrain;

if (!Terrain) {
  throw new Error("OceanRescue.Terrain was not registered");
}

export { Terrain };
