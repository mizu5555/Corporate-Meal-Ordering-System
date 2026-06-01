import { describe, test, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { getRecommendations } from "../../api/employee";
import RandomMealPage from "./RandomMealPage";

const rec = vi.hoisted(() => ({
  vendor: { id: 3, name: "Sunny Kitchen" },
  item: {
    id: 7, vendor_id: 3, name: "招牌雞腿飯", description: "",
    price_cents: 8000, available: true, daily_quota: 10,
    remaining_quantity: 6, photo_path: null, dietary_tags: ["vegetarian"],
  },
  quantity_sold: 12, remaining_quantity: 6, from_sales: true,
}));

vi.mock("../../api/employee", () => ({
  getRecommendations: vi.fn().mockResolvedValue([rec]),
  drawRandomMeal: vi.fn(),
}));
vi.mock("../../hooks/useVendors", () => ({
  useVendors: () => ({ vendors: [{ id: 3, name: "Sunny Kitchen" }], loading: false, error: null }),
}));
vi.mock("../../facility/FacilityContext", () => ({
  useFacility: () => ({ selectedFacilityId: 1, selectedFacility: null, loading: false }),
}));
vi.mock("../../facility/FacilityScopeLabel", () => ({ default: () => null }));
vi.mock("../../cart/CartContext", () => ({ useCart: () => ({ addItem: vi.fn() }) }));

describe("RandomMealPage", () => {
  test("clicking a recommendation card opens the meal-detail modal", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <RandomMealPage />
      </MemoryRouter>,
    );

    const name = await screen.findByText("招牌雞腿飯");
    await user.click(name.closest(".recommend-card"));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getAllByText("素食").length).toBeGreaterThan(0);
  });

  test("dietary filters are sent to recommendations", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <RandomMealPage />
      </MemoryRouter>,
    );

    await screen.findByText("招牌雞腿飯");
    vi.mocked(getRecommendations).mockClear();
    await user.click(screen.getByText("不含牛肉"));

    await waitFor(() => {
      expect(getRecommendations).toHaveBeenLastCalledWith(expect.objectContaining({
        excludeTags: ["contains_beef"],
      }));
    });
  });
});
