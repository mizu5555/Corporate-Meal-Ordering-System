import { describe, test, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MealDetailModal from "./MealDetailModal";

const addItem = vi.fn();
vi.mock("../../cart/CartContext", () => ({
  useCart: () => ({ addItem }),
}));

const baseItem = {
  id: 7,
  vendor_id: 3,
  name: "雞腿便當",
  description: "經典",
  price_cents: 8000,
  available: true,
  daily_quota: 10,
  remaining_quantity: 10,
  photo_path: null,
};

beforeEach(() => addItem.mockClear());

describe("MealDetailModal", () => {
  test("renders the item and adds the chosen quantity with the meal date", async () => {
    const user = userEvent.setup();
    render(<MealDetailModal item={baseItem} mealDate="2026-06-03" remaining={5} onClose={() => {}} />);

    expect(screen.getByText("雞腿便當")).toBeInTheDocument();

    await user.click(screen.getByLabelText("增加數量")); // 1 -> 2
    await user.click(screen.getByRole("button", { name: "加入購物車" }));

    expect(addItem).toHaveBeenCalledWith(baseItem, 3, 2, "2026-06-03");
  });

  test("caps the stepper at the per-date remaining", async () => {
    const user = userEvent.setup();
    render(<MealDetailModal item={baseItem} mealDate="2026-06-03" remaining={2} onClose={() => {}} />);
    const plus = screen.getByLabelText("增加數量");
    await user.click(plus); // 1 -> 2 (cap)
    await user.click(plus); // stays 2
    expect(document.querySelector(".stepper-value").textContent).toBe("2");
    await user.click(screen.getByRole("button", { name: "加入購物車" }));
    expect(addItem).toHaveBeenCalledWith(baseItem, 3, 2, "2026-06-03");
  });

  test("the stepper floors at 1", async () => {
    const user = userEvent.setup();
    render(<MealDetailModal item={baseItem} mealDate="2026-06-03" remaining={5} onClose={() => {}} />);
    const minus = screen.getByLabelText("減少數量");
    await user.click(minus); // already 1, should stay 1 (button is disabled at 1)
    await user.click(screen.getByRole("button", { name: "加入購物車" }));
    expect(addItem).toHaveBeenCalledWith(baseItem, 3, 1, "2026-06-03");
  });

  test("a paused item hides the add button and shows 暫停供應", () => {
    render(<MealDetailModal item={{ ...baseItem, available: false }} mealDate="2026-06-03" remaining={5} onClose={() => {}} />);
    expect(screen.queryByRole("button", { name: "加入購物車" })).not.toBeInTheDocument();
    expect(screen.getByText("暫停供應")).toBeInTheDocument();
  });

  test("hides the add button when the date is sold out", () => {
    render(<MealDetailModal item={baseItem} mealDate="2026-06-03" remaining={0} onClose={() => {}} />);
    expect(screen.queryByRole("button", { name: "加入購物車" })).not.toBeInTheDocument();
    expect(screen.getByText("今日售完")).toBeInTheDocument();
  });
});
