export const DIETARY_TAG_OPTIONS = [
  { value: "contains_beef", label: "含牛肉" },
  { value: "contains_pork", label: "含豬肉" },
  { value: "vegetarian", label: "素食" },
  { value: "ovo_lacto_vegetarian", label: "蛋奶素" },
];

export const DIETARY_TAG_LABELS = Object.fromEntries(
  DIETARY_TAG_OPTIONS.map((option) => [option.value, option.label]),
);

const MEAT_TAGS = new Set(["contains_beef", "contains_pork"]);
const VEGETARIAN_TAGS = new Set(["vegetarian", "ovo_lacto_vegetarian"]);

export function dietaryTagLabel(tag) {
  return DIETARY_TAG_LABELS[tag] ?? tag;
}

export function normalizeDietaryTags(tags) {
  return Array.isArray(tags) ? tags.filter((tag, index) => tags.indexOf(tag) === index) : [];
}

export function nextDietaryTags(currentTags, tag) {
  const current = new Set(normalizeDietaryTags(currentTags));
  if (current.has(tag)) {
    current.delete(tag);
    return Array.from(current);
  }

  current.add(tag);
  if (VEGETARIAN_TAGS.has(tag)) {
    for (const meatTag of MEAT_TAGS) current.delete(meatTag);
  }
  if (MEAT_TAGS.has(tag)) {
    for (const vegetarianTag of VEGETARIAN_TAGS) current.delete(vegetarianTag);
  }
  return Array.from(current);
}

export function matchesDietaryFilters(item, { includeTags = [], excludeTags = [] } = {}) {
  const tags = new Set(normalizeDietaryTags(item?.dietary_tags));
  return includeTags.every((tag) => tags.has(tag))
    && excludeTags.every((tag) => !tags.has(tag));
}
