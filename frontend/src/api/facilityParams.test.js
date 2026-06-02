import assert from "node:assert/strict";
import { test } from "vitest";

import { appendFacilityParam, facilityPayload } from "./facilityParams.js";

test("appendFacilityParam skips empty facility values", () => {
  assert.equal(appendFacilityParam("/employee/vendors", null), "/employee/vendors");
  assert.equal(appendFacilityParam("/employee/vendors", ""), "/employee/vendors");
});

test("appendFacilityParam appends facility_id to plain paths", () => {
  assert.equal(appendFacilityParam("/employee/vendors", 10), "/employee/vendors?facility_id=10");
});

test("appendFacilityParam preserves existing query strings", () => {
  assert.equal(
    appendFacilityParam("/employee/vendors/1/menu?available=true", 10),
    "/employee/vendors/1/menu?available=true&facility_id=10",
  );
});

test("facilityPayload serializes selected facility for JSON bodies", () => {
  assert.deepEqual(facilityPayload(10), { facility_id: 10 });
  assert.deepEqual(facilityPayload(null), {});
});
