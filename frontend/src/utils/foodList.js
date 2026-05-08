export function parseFoodList(value) {
  if (Array.isArray(value)) {
    return value.map((v) => String(v).trim()).filter(Boolean);
  }

  if (!value || typeof value !== "string") {
    return [];
  }

  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function formatFoodListInput(value) {
  return parseFoodList(value).join(", ");
}
