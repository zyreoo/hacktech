/**
 * Frontend-only map layout for the airport digital twin.
 * Coordinate system: 0–1000 x and y. Designed to read as:
 * - Top: runways (airside)
 * - Middle: terminals with concourses and gate rows
 * - Bottom: landside strip
 *
 * Edit positions here to adjust the map. No coordinates from backend.
 */

export interface MapPoint {
  x: number;
  y: number;
}

export interface GatePosition {
  gate: string;
  terminal: string;
  point: MapPoint;
  label?: string;
}

export interface RunwayPosition {
  runwayCode: string;
  /** Start point (threshold) */
  start: MapPoint;
  /** End point */
  end: MapPoint;
  length: number; // 0–100, for stroke width / styling
}

export interface TerminalZone {
  id: string;
  label: string;
  /** Building footprint polygon (no labels drawn inside map) */
  polygon: MapPoint[];
  center: MapPoint;
  /** Concourse line(s): [start, end] for drawing concourse spine */
  concourses: { start: MapPoint; end: MapPoint }[];
  /** Gate row Y range and count for this terminal (for visual gate ticks) */
  gateRow?: { yMin: number; yMax: number; count: number; side: "left" | "right" };
}

// ─── Layout constants (readable airport diagram) ─────────────────────────────
const LANDSIDE_Y = 720;       // landside strip top edge
const TERMINAL_TOP = 220;     // terminal building top
const TERMINAL_BOTTOM = 580;  // terminal building bottom
const APRON_TOP = 120;        // apron / airside below runways
const RUNWAY_TOP = 0;         // runways in top 120px

// ─── Terminals: three buildings with concourses and gate rows ────────────────

export const TERMINAL_ZONES: TerminalZone[] = [
  {
    id: "T1",
    label: "Terminal 1",
    center: { x: 200, y: 400 },
    polygon: [
      { x: 40, y: TERMINAL_TOP },
      { x: 320, y: TERMINAL_TOP },
      { x: 320, y: TERMINAL_BOTTOM },
      { x: 40, y: TERMINAL_BOTTOM },
    ],
    concourses: [
      { start: { x: 80, y: 320 }, end: { x: 280, y: 320 } },
      { start: { x: 80, y: 420 }, end: { x: 280, y: 420 } },
      { start: { x: 80, y: 500 }, end: { x: 280, y: 500 } },
    ],
    gateRow: { yMin: 300, yMax: 520, count: 8, side: "left" },
  },
  {
    id: "T2",
    label: "Terminal 2",
    center: { x: 500, y: 400 },
    polygon: [
      { x: 340, y: TERMINAL_TOP },
      { x: 660, y: TERMINAL_TOP },
      { x: 660, y: TERMINAL_BOTTOM },
      { x: 340, y: TERMINAL_BOTTOM },
    ],
    concourses: [
      { start: { x: 380, y: 320 }, end: { x: 620, y: 320 } },
      { start: { x: 380, y: 420 }, end: { x: 620, y: 420 } },
      { start: { x: 380, y: 500 }, end: { x: 620, y: 500 } },
    ],
    gateRow: { yMin: 300, yMax: 520, count: 10, side: "left" },
  },
  {
    id: "T3",
    label: "Terminal 3",
    center: { x: 800, y: 400 },
    polygon: [
      { x: 680, y: TERMINAL_TOP },
      { x: 960, y: TERMINAL_TOP },
      { x: 960, y: TERMINAL_BOTTOM },
      { x: 680, y: TERMINAL_BOTTOM },
    ],
    concourses: [
      { start: { x: 720, y: 320 }, end: { x: 920, y: 320 } },
      { start: { x: 720, y: 420 }, end: { x: 920, y: 420 } },
      { start: { x: 720, y: 500 }, end: { x: 920, y: 500 } },
    ],
    gateRow: { yMin: 300, yMax: 520, count: 8, side: "left" },
  },
];

// Landside: single strip at bottom (for background only)
export const LANDSIDE_POLYGON: MapPoint[] = [
  { x: 0, y: LANDSIDE_Y },
  { x: 1000, y: LANDSIDE_Y },
  { x: 1000, y: 1000 },
  { x: 0, y: 1000 },
];

// Apron / airside between runways and terminals (lighter band)
export const APRON_POLYGON: MapPoint[] = [
  { x: 0, y: APRON_TOP },
  { x: 1000, y: APRON_TOP },
  { x: 1000, y: TERMINAL_TOP },
  { x: 0, y: TERMINAL_TOP },
];

// Taxiway segments (lines on apron: connect runway ends toward terminals)
export const TAXIWAY_SEGMENTS: { start: MapPoint; end: MapPoint }[] = [
  { start: { x: 120, y: 95 }, end: { x: 180, y: 220 } },
  { start: { x: 880, y: 95 }, end: { x: 820, y: 220 } },
  { start: { x: 500, y: 60 }, end: { x: 500, y: 220 } },
  { start: { x: 200, y: 220 }, end: { x: 200, y: TERMINAL_TOP } },
  { start: { x: 500, y: 220 }, end: { x: 500, y: TERMINAL_TOP } },
  { start: { x: 800, y: 220 }, end: { x: 800, y: TERMINAL_TOP } },
];

// ─── Gates (exact positions for flight placement) ────────────────────────────

const GATE_LIST: GatePosition[] = [
  { gate: "A1", terminal: "T1", point: { x: 100, y: 300 }, label: "A1" },
  { gate: "A2", terminal: "T1", point: { x: 100, y: 350 }, label: "A2" },
  { gate: "A3", terminal: "T1", point: { x: 100, y: 400 }, label: "A3" },
  { gate: "A4", terminal: "T1", point: { x: 100, y: 460 }, label: "A4" },
  { gate: "A5", terminal: "T1", point: { x: 100, y: 520 }, label: "A5" },
  { gate: "S1", terminal: "T1", point: { x: 260, y: 360 }, label: "S1" },
  { gate: "S2", terminal: "T1", point: { x: 260, y: 460 }, label: "S2" },
  { gate: "B1", terminal: "T2", point: { x: 360, y: 300 }, label: "B1" },
  { gate: "B2", terminal: "T2", point: { x: 360, y: 360 }, label: "B2" },
  { gate: "B3", terminal: "T2", point: { x: 360, y: 420 }, label: "B3" },
  { gate: "B4", terminal: "T2", point: { x: 360, y: 480 }, label: "B4" },
  { gate: "B5", terminal: "T2", point: { x: 360, y: 520 }, label: "B5" },
  { gate: "S3", terminal: "T2", point: { x: 520, y: 380 }, label: "S3" },
  { gate: "S4", terminal: "T2", point: { x: 520, y: 460 }, label: "S4" },
  { gate: "C1", terminal: "T3", point: { x: 700, y: 300 }, label: "C1" },
  { gate: "C2", terminal: "T3", point: { x: 700, y: 360 }, label: "C2" },
  { gate: "C3", terminal: "T3", point: { x: 700, y: 420 }, label: "C3" },
  { gate: "C4", terminal: "T3", point: { x: 700, y: 480 }, label: "C4" },
  { gate: "C5", terminal: "T3", point: { x: 700, y: 520 }, label: "C5" },
  { gate: "S5", terminal: "T3", point: { x: 860, y: 400 }, label: "S5" },
];

export const GATE_MAP = new Map<string, GatePosition>(GATE_LIST.map((g) => [g.gate, g]));

// ─── Runways (start/end for clear runway strips) ─────────────────────────────

export const RUNWAY_POSITIONS: RunwayPosition[] = [
  { runwayCode: "09L", start: { x: 120, y: 95 }, end: { x: 120, y: 25 }, length: 70 },
  { runwayCode: "27R", start: { x: 880, y: 95 }, end: { x: 880, y: 25 }, length: 70 },
  { runwayCode: "09R", start: { x: 500, y: 60 }, end: { x: 500, y: 20 }, length: 40 },
  { runwayCode: "27L", start: { x: 500, y: 100 }, end: { x: 500, y: 60 }, length: 40 },
];

export const RUNWAY_MAP = new Map<string, RunwayPosition>(
  RUNWAY_POSITIONS.map((r) => [r.runwayCode, r])
);

/** Get map point for a gate or stand. Falls back to terminal center if unknown. */
export function getPointForGateOrStand(gateOrStand: string | null, terminalId?: string | null): MapPoint {
  if (gateOrStand) {
    const exact = GATE_MAP.get(gateOrStand);
    if (exact) return exact.point;
    const t = terminalId ?? gateOrStand.charAt(0);
    const zone = TERMINAL_ZONES.find((z) => z.id === t || z.id === `T${t}`);
    if (zone) return zone.center;
  }
  const zone = TERMINAL_ZONES.find((z) => z.id === (terminalId ?? "T2"));
  return zone?.center ?? { x: 500, y: 400 };
}

export function getRunwayPosition(runwayCode: string): RunwayPosition | undefined {
  return RUNWAY_MAP.get(runwayCode);
}

export function getTerminalZone(zoneIdOrLabel: string | null | undefined): TerminalZone | undefined {
  if (!zoneIdOrLabel) return undefined;
  return (
    TERMINAL_ZONES.find((z) => z.id === zoneIdOrLabel || z.label === zoneIdOrLabel) ??
    TERMINAL_ZONES.find((z) => zoneIdOrLabel.includes(z.id) || zoneIdOrLabel.includes(z.label))
  );
}

export const VIEWBOX_SIZE = 1000;
