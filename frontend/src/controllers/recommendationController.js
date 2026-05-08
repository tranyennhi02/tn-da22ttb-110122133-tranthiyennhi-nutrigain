import { normalizePayload } from "../models/recommendationModel";
import { favoriteFood, fetchHistory, fetchTodayMealPlan, postRecommendation, postRegenerateMealPlan, rateFood, unfavoriteFood, updateUserProfile } from "../services/apiService";
import { parseFoodList } from "../utils/foodList.js";

export async function submitRecommendation(formState) {
  const payload = normalizePayload(formState);
  return postRecommendation(payload);
}

export async function loadTodayMealPlan() {
  return fetchTodayMealPlan();
}

export async function regenerateMealPlan(formState, options = {}) {
  const payload = normalizePayload(formState);
  return postRegenerateMealPlan({
    ...payload,
    userId: options.userId || undefined,
    date: options.date || new Date().toISOString().slice(0, 10),
    previousMealPlanId: options.previousMealPlanId || undefined,
    targetKcal: options.targetKcal || payload.target_calories || undefined,
    excludePreviousItems: options.excludePreviousItems !== false,
    randomSeed: options.randomSeed || Date.now(),
  });
}

export async function loadHistory(limit = 10) {
  return fetchHistory(limit);
}

export async function loadHistoryByPeriod(limit = 10, period = "week") {
  return fetchHistory(limit, period);
}

export async function saveFavorite(foodId) {
  return favoriteFood(foodId);
}

export async function removeFavorite(foodId) {
  return unfavoriteFood(foodId);
}

export async function submitFoodRating(foodId, rating) {
  return rateFood(foodId, rating);
}

export async function saveUserProfile(payload) {
  return updateUserProfile(toUserProfilePayload(payload));
}

function toUserProfilePayload(payload = {}) {
  const numberOrNull = (value) => {
    if (value === "" || value === null || value === undefined) return null;
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  };
  
  const typedDislikedFoods = payload.unfavorite_foods !== undefined
    ? parseFoodList(payload.unfavorite_foods)
    : parseFoodList(payload.disliked_foods);

  const next = {
    age: numberOrNull(payload.age),
    sex: payload.sex === "" ? null : (payload.sex || null),
    gender: payload.sex === "" ? null : (payload.sex || null),
    height_cm: payload.height_cm ?? numberOrNull(payload.height),
    weight_kg: payload.weight_kg ?? numberOrNull(payload.weight),
    target_weight_kg: payload.target_weight_kg ?? numberOrNull(payload.target_weight),
    weight_gain_speed: payload.gain_speed || payload.weight_gain_speed || "slow",
    activity_level: payload.activity || payload.activity_level || "moderate",
    diet_type: payload.diet_style || payload.diet_type || "balanced",
    budget_level: payload.budget_level || "standard",
    items_per_meal: payload.items_per_meal ?? (payload.meal_complexity === "simple" ? 3 : payload.meal_complexity === "full" ? 5 : 4),
    favorite_foods: parseFoodList(payload.favorite_foods).join(", "),
    disliked_foods: typedDislikedFoods,
    disliked_food_groups: parseFoodList(payload.disliked_food_groups),
  };

  return next;
}
