import assert from "node:assert/strict";
import test from "node:test";

import { chooseFacilityId, facilityDisplayName } from "./facilitySelection.js";

const facilities = [
  { id: 10, code: "F12A", name: "Fab 12A" },
  { id: 20, code: "F14B", name: "Fab 14B" },
];

test("chooseFacilityId keeps a valid current facility", () => {
  assert.equal(chooseFacilityId(facilities, 20), 20);
  assert.equal(chooseFacilityId(facilities, "20"), 20);
});

test("chooseFacilityId falls back to the first available facility", () => {
  assert.equal(chooseFacilityId(facilities, null), 10);
  assert.equal(chooseFacilityId(facilities, 99), 10);
});

test("chooseFacilityId returns null when no facilities are available", () => {
  assert.equal(chooseFacilityId([], 10), null);
});

test("facilityDisplayName prefers code and name", () => {
  assert.equal(facilityDisplayName(facilities[0]), "F12A - Fab 12A");
  assert.equal(facilityDisplayName({ id: 30, name: "Headquarters" }), "Headquarters");
});
