export function normalizeFoodList(value) {
  if (Array.isArray(value)) {
    return value.map((item) => String(item).trim()).filter(Boolean);
  }

  if (typeof value === "string") {
    return value
      .split(/[,\n;]+/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  return [];
}

export function parseFoodList(value) {
  return normalizeFoodList(value);
}

export function foodListToInput(value) {
  if (Array.isArray(value)) {
    return value.join(", ");
  }

  if (typeof value === "string") {
    return value;
  }

  return "";
}

export function normalizeProfilePayload(form) {
  // Prefer editable text inputs from form to avoid resurrecting stale array state.
  const rawFav = Object.prototype.hasOwnProperty.call(form, "favorite_foods")
    ? form.favorite_foods
    : "";
  const rawDisliked = Object.prototype.hasOwnProperty.call(form, "unfavorite_foods")
    ? form.unfavorite_foods
    : form.disliked_foods;

  return {
    age: form.age ? Number(form.age) : null,
    gender: form.gender || form.sex || null,
    height_cm: form.height_cm ? Number(form.height_cm) : (form.height ? Number(form.height) : null),
    weight_kg: form.weight_kg ? Number(form.weight_kg) : (form.weight ? Number(form.weight) : null),
    target_weight_kg: form.target_weight_kg
      ? Number(form.target_weight_kg)
      : (form.target_weight ? Number(form.target_weight) : null),
    weight_gain_speed: form.weight_gain_speed || form.gain_speed || null,
    activity_level: form.activity_level || form.activity || null,
    diet_type: form.diet_type || form.diet_style || null,
    budget_level: form.budget_level || null,
    items_per_meal: form.items_per_meal
      ? Number(form.items_per_meal)
      : (form.meal_complexity === "simple" ? 3 : form.meal_complexity === "full" ? 5 : 4),
    favorite_foods: normalizeFoodList(rawFav),
    disliked_foods: normalizeFoodList(rawDisliked),
    disliked_food_groups: normalizeFoodList(form.disliked_food_groups),
  };
}
