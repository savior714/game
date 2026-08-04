/**
 * Typed canonical GUP catalog for Ocean Rescue (WP-31B).
 *
 * This module is the strictly typed canonical source of the static GUP catalog
 * consumed by the canonical ESM graph. It owns only static GUP data: catalog
 * order, names, and descriptions. The unchanged legacy `src/gups.js` continues
 * to own all mutable GUP state, preparation, selection, and confirmation
 * behavior.
 *
 * The catalog preserves the legacy observable runtime contract exactly: array
 * and entry immutability, entry order, and exact field values.
 */

export type GupId = "gup-c" | "gup-i" | "gup-x";

export interface GupCatalogEntry {
  readonly id: GupId;
  readonly name: string;
  readonly description: string;
}

export type GupCatalog = readonly GupCatalogEntry[];

function freeze<T>(value: T): Readonly<T> {
  return Object.freeze(value);
}

export const Catalog: GupCatalog = freeze([
  freeze<GupCatalogEntry>({
    id: "gup-c",
    name: "GUP-C",
    description: "Yellow rescue sub",
  }),
  freeze<GupCatalogEntry>({
    id: "gup-i",
    name: "GUP-I",
    description: "White and blue rescue sub",
  }),
  freeze<GupCatalogEntry>({
    id: "gup-x",
    name: "GUP-X",
    description: "Red rescue sub",
  }),
]);

export { Catalog as GupsCatalog };
