import "../young-whale.js";

const YoungWhale = window.OceanRescue?.YoungWhale;

if (!YoungWhale) {
  throw new Error("OceanRescue.YoungWhale was not registered");
}

export { YoungWhale };
