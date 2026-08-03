import "../profile.js";

const Profile = window.OceanRescue?.Profile;

if (!Profile) {
  throw new Error("OceanRescue.Profile was not registered");
}

export { Profile };
