/**
 * Pointer coordinate boundary types for Ocean Rescue (WP-32B).
 *
 * This module is the single type-only authority for the normalized pointer
 * boundary shared by the canonical ESM lane and the legacy ordered-script
 * lane:
 *
 * - browser client coordinates -> Ocean Rescue logical coordinates
 * - travel pointer event -> logical stage Y
 * - rescue pointer event -> logical `{ x, y }`
 * - the normalized `{ active, x, y }` pointer intent delivered to authored
 *   scenes
 * - the minimal RenderRuntime coordinate-mapper API (`isReady` +
 *   `mapClientToLogical`) that the pointer boundary depends on.
 *
 * The module emits no runtime JavaScript: every export is a type. It must
 * never appear as a runtime module in the production bundle. Only the
 * coordinate-mapping subset of the renderer is typed here; the full
 * RenderRuntime API and the Pixi display-object model are explicitly out of
 * scope.
 */

export interface LogicalPoint {
  readonly x: number;
  readonly y: number;
}

export interface RenderMappedPoint extends LogicalPoint {
  readonly inside: boolean;
}

export interface RenderCoordinateMapperApi {
  readonly isReady: () => boolean;
  readonly mapClientToLogical: (
    clientX: number,
    clientY: number,
  ) => RenderMappedPoint;
}

export interface ActivePointerIntent {
  readonly active: true;
  readonly x: number;
  readonly y: number;
}

export interface InactivePointerIntent {
  readonly active: false;
  readonly x: null;
  readonly y: null;
}

export type PointerIntent = ActivePointerIntent | InactivePointerIntent;

export interface ClientCoordinateCarrier {
  readonly clientX: number;
  readonly clientY: number;
}

export interface BoundingRect {
  readonly left: number;
  readonly top: number;
  readonly width: number;
  readonly height: number;
}

export interface RectProvider {
  readonly getBoundingClientRect: () => BoundingRect;
}

export interface PointerInputApi {
  readonly mapTravelStageY: (
    event: ClientCoordinateCarrier,
    canvas: RectProvider | null | undefined,
  ) => number | null;
  readonly mapRescuePoint: (
    event: ClientCoordinateCarrier,
    canvas: RectProvider | null | undefined,
  ) => LogicalPoint | null;
  readonly activeIntent: (
    point: LogicalPoint | null | undefined,
  ) => PointerIntent;
  readonly inactiveIntent: () => InactivePointerIntent;
}
