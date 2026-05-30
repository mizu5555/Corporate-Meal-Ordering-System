export function formatPrice(cents) {
  if (cents === 0) return "免費";
  const amount = cents / 100;
  return `NT$ ${Number.isInteger(amount) ? amount : amount.toFixed(1)}`;
}

// Money totals (revenue / receivables): always a currency amount, never "免費".
// Zero is a real total (NT$ 0), not a free menu item.
export function formatMoney(cents) {
  const amount = cents / 100;
  return `NT$ ${Number.isInteger(amount) ? amount : amount.toFixed(1)}`;
}

export function quotaLabel(dailyQuota) {
  if (dailyQuota === null || dailyQuota === undefined) return null;
  if (dailyQuota === 0) return "今日售完";
  return `剩餘 ${dailyQuota} 份`;
}

export function photoUrl(photoPath, version) {
  if (!photoPath) return null;
  const base = import.meta.env.BASE_URL.replace(/\/$/, "");
  const url = `${base}/uploads/${photoPath}`;
  return version ? `${url}?v=${version}` : url;
}
