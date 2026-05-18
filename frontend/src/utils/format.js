export function formatPrice(cents) {
  if (cents === 0) return "免費";
  const amount = cents / 100;
  return `NT$ ${Number.isInteger(amount) ? amount : amount.toFixed(1)}`;
}

export function quotaLabel(dailyQuota) {
  if (dailyQuota === null || dailyQuota === undefined) return null;
  if (dailyQuota === 0) return "今日售完";
  return `剩餘 ${dailyQuota} 份`;
}

export function photoUrl(photoPath) {
  if (!photoPath) return null;
  return `/uploads/${photoPath}`;
}
