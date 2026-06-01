import assert from "node:assert/strict";
import { test } from "vitest";

import { addCartItem, groupByMealDate, removeCartItem, updateCartItemQuantity } from "./cartItems.js";

const itemA = { id: 1, name: "雞腿便當" };
const itemB = { id: 2, name: "排骨飯" };

test("addCartItem appends a new pick", () => {
  const result = addCartItem([], { item: itemA, vendorId: 10, quantity: 1, mealDate: "2026-06-03" });
  assert.deepEqual(result, [{ item: itemA, vendorId: 10, quantity: 1, mealDate: "2026-06-03" }]);
});

test("addCartItem accumulates quantity for same item + same date", () => {
  const start = [{ item: itemA, vendorId: 10, quantity: 1, mealDate: "2026-06-03" }];
  const result = addCartItem(start, { item: itemA, vendorId: 10, quantity: 2, mealDate: "2026-06-03" });
  assert.equal(result.length, 1);
  assert.equal(result[0].quantity, 3);
});

test("addCartItem keeps same item on different dates as separate rows", () => {
  const start = [{ item: itemA, vendorId: 10, quantity: 1, mealDate: "2026-06-03" }];
  const result = addCartItem(start, { item: itemA, vendorId: 10, quantity: 1, mealDate: "2026-06-04" });
  assert.equal(result.length, 2);
});

test("addCartItem treats missing mealDate as the no-date row and merges with another no-date add", () => {
  const start = addCartItem([], { item: itemA, vendorId: 10, quantity: 1 });
  assert.equal(start[0].mealDate, null);
  const result = addCartItem(start, { item: itemA, vendorId: 10, quantity: 1 });
  assert.equal(result.length, 1);
  assert.equal(result[0].quantity, 2);
});

test("addCartItem does not mutate the input array", () => {
  const start = [{ item: itemA, vendorId: 10, quantity: 1, mealDate: null }];
  addCartItem(start, { item: itemB, vendorId: 10, quantity: 1, mealDate: null });
  assert.equal(start.length, 1);
});

test("addCartItem defaults quantity to 1 when omitted", () => {
  const result = addCartItem([], { item: itemA, vendorId: 10, mealDate: "2026-06-03" });
  assert.equal(result[0].quantity, 1);
});

test("updateCartItemQuantity updates only the matching item + date row", () => {
  const start = [
    { item: itemA, vendorId: 10, quantity: 1, mealDate: "2026-06-03" },
    { item: itemA, vendorId: 10, quantity: 2, mealDate: "2026-06-04" },
  ];
  const result = updateCartItemQuantity(start, {
    itemId: itemA.id,
    mealDate: "2026-06-04",
    quantity: 4,
  });
  assert.equal(result[0].quantity, 1);
  assert.equal(result[1].quantity, 4);
});

test("removeCartItem removes only the matching item + date row", () => {
  const start = [
    { item: itemA, vendorId: 10, quantity: 1, mealDate: "2026-06-03" },
    { item: itemA, vendorId: 10, quantity: 2, mealDate: "2026-06-04" },
  ];
  const result = removeCartItem(start, { itemId: itemA.id, mealDate: "2026-06-03" });
  assert.deepEqual(result, [
    { item: itemA, vendorId: 10, quantity: 2, mealDate: "2026-06-04" },
  ]);
});

test("groupByMealDate returns an empty array for an empty cart", () => {
  assert.deepEqual(groupByMealDate([], "2026-06-01"), []);
});

test("groupByMealDate puts today/no-date first then dates ascending", () => {
  const today = "2026-06-01";
  const items = [
    { item: itemA, vendorId: 10, quantity: 1, mealDate: "2026-06-03" },
    { item: itemB, vendorId: 10, quantity: 2, mealDate: null },
    { item: itemA, vendorId: 10, quantity: 1, mealDate: "2026-06-02" },
    { item: itemB, vendorId: 10, quantity: 1, mealDate: "2026-06-01" }, // explicit today
  ];
  const groups = groupByMealDate(items, today);
  assert.deepEqual(groups.map((g) => g.label), ["今日", "用餐日 6/02", "用餐日 6/03"]);
  // today group holds the no-date item AND the explicit-today item
  assert.equal(groups[0].items.length, 2);
});
