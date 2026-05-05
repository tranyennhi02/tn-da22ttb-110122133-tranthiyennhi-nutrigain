export const defaultFormState = {
  weight: "",
  height: "",
  activity: "default",
  goal_type: "gain",
  gain_speed: "slow",
  meal_complexity: "balanced",
  diet_style: "balanced",
  budget_level: "standard",
  age: "",
  sex: "",
  target_weight: "",
  top_n: 10,
  favorite_foods: "",
  unfavorite_foods: "",
  disliked_foods: [],
  disliked_food_groups: [],
  save_user_data: false,
};

function parseCategoryText(value) {
  if (!value || typeof value !== "string") {
    return [];
  }
  return value
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter((item) => item.length > 0);
}

export function normalizePayload(formState) {
  const gainSpeed = formState.gain_speed || "slow";
  const dislikedFoods = Array.isArray(formState.disliked_foods) ? formState.disliked_foods : [];
  const dislikedFoodGroups = Array.isArray(formState.disliked_food_groups) ? formState.disliked_food_groups : [];
  const typedUnfavorites = parseCategoryText(formState.unfavorite_foods);
  const surplusBySpeed = {
    slow: 300,
    medium: 400,
    fast: 500,
  };

  return {
    weight: Number(formState.weight),
    height: Number(formState.height),
    activity: formState.activity,
    age: formState.age === "" ? null : Number(formState.age),
    sex: formState.sex === "" ? null : formState.sex,
    goal_type: formState.goal_type || "gain",
    weight_gain_speed: gainSpeed,
    gain_speed: gainSpeed,
    meal_complexity: formState.meal_complexity || "balanced",
    diet_style: formState.diet_style || "balanced",
    budget_level: formState.budget_level || "standard",
    surplus_kcal: surplusBySpeed[gainSpeed] ?? 300,
    target_weight: formState.target_weight === "" ? null : Number(formState.target_weight),
    top_n: Number(formState.top_n),
    preferred_categories: [],
    excluded_categories: [],
    favorites: parseCategoryText(formState.favorite_foods),
    allergens: typedUnfavorites,
    disliked_foods: Array.from(new Set([...dislikedFoods, ...typedUnfavorites])),
    disliked_food_groups: Array.from(new Set(dislikedFoodGroups)),
    energy_tolerance_kcal: 80,
    use_personalization: true,
    min_protein_ratio: 0.9,
    min_fat_ratio: 0.9,
    macro_backtracking_attempts: 30,
    save_user_data: Boolean(formState.save_user_data),
  };
}
