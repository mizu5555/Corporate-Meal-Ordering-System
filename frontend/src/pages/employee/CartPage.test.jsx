import { describe, test, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import CartPage from "./CartPage";

const submitSelection = vi.fn();
vi.mock("../../api/employee", () => ({ submitSelection: (...a) => submitSelection(...a) }));

const replaceCart = vi.fn();
let cartItems;
vi.mock("../../cart/CartContext", () => ({
  useCart: () => ({
    items: cartItems,
    updateQuantity: vi.fn(),
    removeItem: vi.fn(),
    clearCart: vi.fn(),
    replaceCart,
    totalCount: cartItems.reduce((s, i) => s + i.quantity, 0),
  }),
}));

vi.mock("../../facility/FacilityContext", () => ({
  useFacility: () => ({ selectedFacilityId: 1, selectedFacility: null, loading: false }),
}));

function renderCart() {
  return render(<MemoryRouter><CartPage /></MemoryRouter>);
}

beforeEach(() => {
  submitSelection.mockReset();
  replaceCart.mockReset();
});

describe("CartPage", () => {
  test("groups rows by meal date", () => {
    cartItems = [
      { item: { id: 1, name: "今日餐", price_cents: 8000 }, vendorId: 2, quantity: 1, mealDate: null },
      { item: { id: 2, name: "未來餐", price_cents: 9000 }, vendorId: 2, quantity: 1, mealDate: "2099-01-02" },
    ];
    renderCart();
    expect(screen.getByText("今日")).toBeInTheDocument();
    expect(screen.getByText("用餐日 1/02")).toBeInTheDocument();
    expect(screen.getByText("今日餐")).toBeInTheDocument();
    expect(screen.getByText("未來餐")).toBeInTheDocument();
  });

  test("checkout submits each row and clears the cart on full success", async () => {
    const user = userEvent.setup();
    submitSelection.mockResolvedValue({});
    cartItems = [
      { item: { id: 1, name: "甲", price_cents: 8000 }, vendorId: 2, quantity: 1, mealDate: null },
      { item: { id: 2, name: "乙", price_cents: 9000 }, vendorId: 3, quantity: 2, mealDate: null },
    ];
    renderCart();
    await user.click(screen.getByRole("button", { name: "送出訂單" }));
    expect(submitSelection).toHaveBeenCalledTimes(2);
    expect(replaceCart).toHaveBeenCalledWith([]);
    expect(await screen.findByText("訂單已送出")).toBeInTheDocument();
  });

  test("partial failure keeps only the failed row", async () => {
    const user = userEvent.setup();
    const fail = { id: 2, name: "乙", price_cents: 9000 };
    cartItems = [
      { item: { id: 1, name: "甲", price_cents: 8000 }, vendorId: 2, quantity: 1, mealDate: null },
      { item: fail, vendorId: 3, quantity: 1, mealDate: null },
    ];
    submitSelection
      .mockResolvedValueOnce({})
      .mockRejectedValueOnce({ code: "QUOTA_EXHAUSTED" });
    renderCart();
    await user.click(screen.getByRole("button", { name: "送出訂單" }));
    expect(replaceCart).toHaveBeenCalledTimes(1);
    const kept = replaceCart.mock.calls[0][0];
    expect(kept).toHaveLength(1);
    expect(kept[0].item.id).toBe(2);
  });
});
