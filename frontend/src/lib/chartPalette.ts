/**
 * Validated chart palette, light and dark. Values and pairing come from the
 * dataviz skill's reference palette (references/palette.md) — dark mode is
 * its own validated set of steps, not an automatic flip of the light values.
 * The two categorical slots used here (blue, orange) and the two status
 * colors (good, critical) clear the adjacent-pair CVD/contrast gates in both
 * modes; status colors are fixed and identical across modes by design.
 */
export interface ChartColors {
  surface: string;
  gridline: string;
  axis: string;
  mutedText: string;
  primaryText: string;
  seriesDownload: string;
  seriesUpload: string;
  statusGood: string;
  statusCritical: string;
}

const LIGHT: ChartColors = {
  surface: "#fcfcfb",
  gridline: "#e1e0d9",
  axis: "#c3c2b7",
  mutedText: "#898781",
  primaryText: "#0b0b0b",
  seriesDownload: "#2a78d6", // categorical slot 1: blue
  seriesUpload: "#eb6834", // categorical slot 2: orange
  statusGood: "#0ca30c", // Access-Accept — fixed, never themed
  statusCritical: "#d03b3b", // Access-Reject — fixed, never themed
};

const DARK: ChartColors = {
  surface: "#1a1a19",
  gridline: "#2c2c2a",
  axis: "#383835",
  mutedText: "#898781",
  primaryText: "#ffffff",
  seriesDownload: "#3987e5", // categorical slot 1, dark step
  seriesUpload: "#d95926", // categorical slot 2, dark step
  statusGood: "#0ca30c",
  statusCritical: "#d03b3b",
};

export function chartColors(theme: "light" | "dark"): ChartColors {
  return theme === "dark" ? DARK : LIGHT;
}
