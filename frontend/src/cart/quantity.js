// Quantity ceiling for the add-to-cart stepper.
// Prefer the selected meal date's remaining; otherwise the item's base daily quota;
// otherwise unbounded (capped at 99). null/undefined remaining means "not date-scoped".
const HARD_CAP = 99;

export function maxAddQuantity({ remaining = null, dailyQuota = null }) {
  if (remaining != null) return Math.min(remaining, HARD_CAP);
  if (dailyQuota != null && dailyQuota > 0) return Math.min(dailyQuota, HARD_CAP);
  return HARD_CAP;
}
