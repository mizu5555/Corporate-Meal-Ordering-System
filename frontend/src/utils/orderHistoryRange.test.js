import assert from "node:assert/strict";
import { test } from "vitest";

import {
  datesWithoutOrders,
  getDefaultOrderHistoryRange,
  getFutureMealDates,
} from "./orderHistoryRange.js";

test("getDefaultOrderHistoryRange covers the last 30 days and next 7 days including today", () => {
  const range = getDefaultOrderHistoryRange(new Date(2026, 5, 1));

  assert.deepEqual(range, {
    startDate: "2026-05-02",
    endDate: "2026-06-07",
  });
});

test("getFutureMealDates returns today through the next six days", () => {
  assert.deepEqual(getFutureMealDates(new Date(2026, 5, 1)), [
    "2026-06-01",
    "2026-06-02",
    "2026-06-03",
    "2026-06-04",
    "2026-06-05",
    "2026-06-06",
    "2026-06-07",
  ]);
});

test("datesWithoutOrders ignores cancelled orders when building go-order dates", () => {
  const missing = datesWithoutOrders(
    [
      { meal_date: "2026-06-01", status: "pending" },
      { meal_date: "2026-06-02", status: "cancelled" },
    ],
    ["2026-06-01", "2026-06-02", "2026-06-03"],
  );

  assert.deepEqual(missing, ["2026-06-02", "2026-06-03"]);
});
