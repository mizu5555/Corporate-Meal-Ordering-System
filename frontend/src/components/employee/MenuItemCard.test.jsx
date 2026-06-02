import { describe, test, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MenuItemCard from "./MenuItemCard";

const available = {
  id: 1, vendor_id: 2, name: "排骨飯", price_cents: 9000,
  available: true, daily_quota: 5, remaining_quantity: 5, photo_path: null,
  dietary_tags: ["ovo_lacto_vegetarian"],
};
const soldOut = { ...available, id: 2, name: "賣完飯", remaining_quantity: 0 };

describe("MenuItemCard", () => {
  test("available item shows 供應中 and fires onClick", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<MenuItemCard item={available} onClick={onClick} />);
    expect(screen.getByText("排骨飯")).toBeInTheDocument();
    expect(screen.getByText("供應中")).toBeInTheDocument();
    expect(screen.getByText("蛋奶素")).toBeInTheDocument();
    await user.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  test("sold-out item shows 今日售完 and the unavailable class", () => {
    render(<MenuItemCard item={soldOut} onClick={() => {}} />);
    expect(screen.getByText("今日售完")).toBeInTheDocument();
    expect(screen.getByRole("button").className).toContain("unavailable");
  });
});
