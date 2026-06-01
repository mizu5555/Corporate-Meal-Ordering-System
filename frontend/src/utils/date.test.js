import assert from "node:assert/strict";
import test from "node:test";

import { toLocalIso, todayIso } from "./date.js";

test("toLocalIso formats a Date as local YYYY-MM-DD", () => {
  // Local noon avoids any timezone date-rollover ambiguity.
  const d = new Date(2026, 5, 3, 12, 0, 0); // 2026-06-03 (month is 0-based)
  assert.equal(toLocalIso(d), "2026-06-03");
});

test("toLocalIso zero-pads month and day", () => {
  const d = new Date(2026, 0, 9, 12, 0, 0); // 2026-01-09
  assert.equal(toLocalIso(d), "2026-01-09");
});

test("todayIso returns today's local date as YYYY-MM-DD", () => {
  const result = todayIso();
  assert.match(result, /^\d{4}-\d{2}-\d{2}$/);
  assert.equal(result, toLocalIso(new Date()));
});
