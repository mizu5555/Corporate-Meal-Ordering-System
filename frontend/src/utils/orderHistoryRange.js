const HISTORY_PAST_DAYS = 30;
const ORDER_WINDOW_DAYS = 7;

function toLocalIso(date) {
  const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return localDate.toISOString().slice(0, 10);
}

function addDays(baseDate, days) {
  const date = new Date(baseDate);
  date.setHours(0, 0, 0, 0);
  date.setDate(date.getDate() + days);
  return date;
}

export function getDefaultOrderHistoryRange(baseDate = new Date()) {
  return {
    startDate: toLocalIso(addDays(baseDate, -HISTORY_PAST_DAYS)),
    endDate: toLocalIso(addDays(baseDate, ORDER_WINDOW_DAYS - 1)),
  };
}

export function getFutureMealDates(baseDate = new Date()) {
  return Array.from({ length: ORDER_WINDOW_DAYS }, (_, index) => (
    toLocalIso(addDays(baseDate, index))
  ));
}

export function datesWithoutOrders(orders, futureDates = getFutureMealDates()) {
  const orderedDates = new Set(
    orders
      .filter((order) => order.status !== "cancelled")
      .map((order) => order.meal_date)
      .filter(Boolean),
  );
  return futureDates.filter((mealDate) => !orderedDates.has(mealDate));
}
