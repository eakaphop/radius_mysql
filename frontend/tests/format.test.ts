import { describe, expect, it } from "vitest";

import { formatBytes, formatDuration, formatKbps, fromLocalInputValue } from "@/lib/format";

describe("formatBytes", () => {
  it("renders human-readable units", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(1023)).toBe("1023 B");
    expect(formatBytes(1536)).toBe("1.5 KB");
    expect(formatBytes(5 * 1024 ** 3)).toBe("5.0 GB");
    expect(formatBytes(200 * 1024 ** 2)).toBe("200 MB");
  });

  it("renders a dash for missing values", () => {
    expect(formatBytes(null)).toBe("—");
    expect(formatBytes(undefined)).toBe("—");
  });
});

describe("formatDuration", () => {
  it("pads hours, minutes and seconds", () => {
    expect(formatDuration(3661)).toBe("01:01:01");
  });

  it("prefixes whole days", () => {
    expect(formatDuration(90061)).toBe("1d 01:01:01");
  });
});

describe("formatKbps", () => {
  it("uses Mbps when divisible by 1000", () => {
    expect(formatKbps(20000)).toBe("20 Mbps");
    expect(formatKbps(1500)).toBe("1500 kbps");
  });
});

describe("fromLocalInputValue", () => {
  it("returns undefined for empty input", () => {
    expect(fromLocalInputValue("")).toBeUndefined();
  });

  it("returns an ISO string for a datetime-local value", () => {
    expect(fromLocalInputValue("2026-09-13T10:30")).toMatch(/^\d{4}-\d{2}-\d{2}T/);
  });
});
