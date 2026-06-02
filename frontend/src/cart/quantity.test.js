import assert from "node:assert/strict";
import { test } from "vitest";

import { maxAddQuantity } from "./quantity.js";

test("uses remaining when provided", () => {
  assert.equal(maxAddQuantity({ remaining: 5, dailyQuota: 100 }), 5);
});

test("clamps remaining to 99", () => {
  assert.equal(maxAddQuantity({ remaining: 250, dailyQuota: null }), 99);
});

test("falls back to dailyQuota when remaining is null", () => {
  assert.equal(maxAddQuantity({ remaining: null, dailyQuota: 8 }), 8);
});

test("clamps dailyQuota to 99", () => {
  assert.equal(maxAddQuantity({ remaining: null, dailyQuota: 250 }), 99);
});

test("returns 99 when neither remaining nor a positive dailyQuota is set", () => {
  assert.equal(maxAddQuantity({ remaining: null, dailyQuota: null }), 99);
  assert.equal(maxAddQuantity({ remaining: null, dailyQuota: 0 }), 99);
});

test("treats undefined remaining like null", () => {
  assert.equal(maxAddQuantity({ dailyQuota: 3 }), 3);
});
