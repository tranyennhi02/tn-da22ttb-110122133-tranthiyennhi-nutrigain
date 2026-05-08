import { parseFoodList } from "../utils/foodList.js";

export const defaultFormState = {
  weight: "",
  height: "",
  activity: "default",
  goal_type: "gain",
  gain_speed: "slow",
  meal_complexity: "balanced",
  items_per_meal: 4,
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

export function normalizePayload(formState) {
  const gainSpeed = formState.gain_speed || "slow";
  const dislikedFoods = parseFoodList(formState.disliked_foods);
  const dislikedFoodGroups = parseFoodList(formState.disliked_food_groups);
  const typedUnfavorites = parseFoodList(formState.unfavorite_foods);
  const itemsPerMeal = formState.meal_complexity === "simple"
    ? 3
    : formState.meal_complexity === "full"
      ? 5
      : (formState.items_per_meal ?? 4);
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
    items_per_meal: itemsPerMeal,
    diet_style: formState.diet_style || "balanced",
    budget_level: formState.budget_level || "standard",
    surplus_kcal: surplusBySpeed[gainSpeed] ?? 300,
    target_weight: formState.target_weight === "" ? null : Number(formState.target_weight),
    top_n: Number(formState.top_n),
    preferred_categories: [],
    excluded_categories: [],
    favorite_foods: parseFoodList(formState.favorite_foods),
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
