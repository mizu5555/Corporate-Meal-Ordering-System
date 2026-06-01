// Pure cart helpers — no React. Cart item shape: { item, vendorId, quantity, mealDate }
// where mealDate is a local YYYY-MM-DD string, or null meaning "today (backend default)".

function dedupKey(itemId, mealDate) {
  return `${itemId}|${mealDate ?? ""}`;
}

export function addCartItem(items, { item, vendorId, quantity = 1, mealDate = null }) {
  const key = dedupKey(item.id, mealDate);
  const existing = items.find((i) => dedupKey(i.item.id, i.mealDate) === key);
  if (existing) {
    return items.map((i) =>
      i === existing ? { ...i, quantity: i.quantity + quantity } : i,
    );
  }
  return [...items, { item, vendorId, quantity, mealDate }];
}

function mealDateLabel(iso) {
  const [, mm, dd] = iso.split("-");
  // Intentional format: month without leading zero, day keeps it (e.g. "用餐日 6/03").
  return `用餐日 ${Number(mm)}/${dd}`;
}

export function groupByMealDate(items, todayIso) {
  const groups = new Map(); // key -> { key, label, sortKey, items }
  for (const it of items) {
    const raw = it.mealDate ?? null;
    const isToday = raw == null || raw === todayIso;
    const key = isToday ? "today" : raw;
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        label: isToday ? "今日" : mealDateLabel(raw),
        sortKey: isToday ? "" : raw, // "" sorts before any ISO date string
        items: [],
      });
    }
    groups.get(key).items.push(it);
  }
  return [...groups.values()]
    .sort((a, b) => a.sortKey.localeCompare(b.sortKey))
    .map(({ key, label, items }) => ({ key, label, items }));
}
