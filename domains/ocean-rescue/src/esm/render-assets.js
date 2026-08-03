import "../render-assets.generated.js";

const RenderAssets = window.OceanRescue?.RenderAssets;

if (!RenderAssets) {
  throw new Error("OceanRescue.RenderAssets was not registered");
}

export { RenderAssets };
