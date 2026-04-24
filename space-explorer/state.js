export const BASE_ORBIT = 34;
export const ORBIT_STEP = 26;
export const TWO_PI = Math.PI * 2;

export const planets = [
  { name: "Mercury", color: "#b8b8b8", radius: 4, orbitIndex: 1, orbitSpeed: 4.15, angle: 0.1 },
  { name: "Venus", color: "#d9b26f", radius: 6, orbitIndex: 2, orbitSpeed: 1.62, angle: 1.0 },
  { name: "Earth", color: "#5ea2ff", radius: 6, orbitIndex: 3, orbitSpeed: 1.0, angle: 2.4 },
  { name: "Mars", color: "#d46a4c", radius: 5, orbitIndex: 4, orbitSpeed: 0.53, angle: 0.2 },
  { name: "Jupiter", color: "#d9ad7c", radius: 10, orbitIndex: 5, orbitSpeed: 0.084, angle: 3.2 },
  { name: "Saturn", color: "#d8c28f", radius: 9, orbitIndex: 6, orbitSpeed: 0.034, angle: 0.6 },
  { name: "Uranus", color: "#8ed8e8", radius: 8, orbitIndex: 7, orbitSpeed: 0.012, angle: 5.1 },
  { name: "Neptune", color: "#4f79ff", radius: 8, orbitIndex: 8, orbitSpeed: 0.006, angle: 1.8 },
];

export const initialAngles = planets.map((planet) => planet.angle);

export const state = {
  isPlaying: true,
  timeScale: 0.5,
  showLabels: true,
  renderMode: "2d",
  zoom: 1,
  targetZoom: 1,
  viewRotation: 0,
  targetRotation: 0,
  elapsedTime: 0,
  lastTs: 0,
  rafId: null,
};
