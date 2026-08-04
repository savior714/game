/**
 * Typed canonical mission catalog for Ocean Rescue (WP-31B).
 *
 * This module is the strictly typed canonical source of the static mission
 * catalog consumed by the canonical ESM graph. It owns only static mission
 * data: catalog order, titles, companions, and summaries. The unchanged legacy
 * `src/missions.js` continues to own all mutable progression state, selected
 * mission state, unlock/completion/new-badge behavior, localStorage schema and
 * persistence, payload validation and cleanup, and the progression API
 * methods.
 *
 * The catalog preserves the legacy observable runtime contract exactly: array
 * and entry immutability, entry order, and exact field values. Catalog order is
 * behavior because unlock progression uses catalog position.
 */

export type MissionId = "sea-turtle" | "crab" | "young-whale";

export interface MissionCatalogEntry {
  readonly id: MissionId;
  readonly order: number;
  readonly title: string;
  readonly companion: string;
  readonly summary: string;
}

export type MissionCatalog = readonly MissionCatalogEntry[];

function freeze<T>(value: T): Readonly<T> {
  return Object.freeze(value);
}

export const Catalog: MissionCatalog = freeze([
  freeze<MissionCatalogEntry>({
    id: "sea-turtle",
    order: 1,
    title: "Sea Turtle Rescue",
    companion: "Peso",
    summary: "Cut the ropes and free the trapped sea turtle.",
  }),
  freeze<MissionCatalogEntry>({
    id: "crab",
    order: 2,
    title: "Crab Rescue",
    companion: "Tweak",
    summary: "Move the rocks and help the trapped crab.",
  }),
  freeze<MissionCatalogEntry>({
    id: "young-whale",
    order: 3,
    title: "Young Whale Rescue",
    companion: "Captain Barnacles",
    summary: "Tow the debris and clear a path for the young whale.",
  }),
]);

export { Catalog as MissionsCatalog };
