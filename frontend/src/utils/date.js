// Local-date helpers. Use these instead of Date.toISOString() (which is UTC and
// can roll the date over near midnight). meal_date everywhere is a local YYYY-MM-DD.
export function toLocalIso(date) {
  const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return localDate.toISOString().slice(0, 10);
}

export function todayIso() {
  return toLocalIso(new Date());
}
