/**
 * Shared mission identifier authority for Ocean Rescue (WP-32A).
 *
 * The typed mission catalog (`src/missions/catalog.ts`) and the typed launch
 * catalog (`src/launch/launch.ts`) both reference the exact mission IDs owned
 * by the unchanged legacy progression controller (`src/missions.js`) and the
 * static launch catalog. This module is the single type-only authority for
 * those identifiers; it emits no runtime JavaScript.
 */
export type MissionId = "sea-turtle" | "crab" | "young-whale";
