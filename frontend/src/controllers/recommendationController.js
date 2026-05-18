import { normalizePayload } from "../models/recommendationModel";
import { favoriteFood, fetchHistory, fetchTodayMealPlan, postRecommendation, postRegenerateMealPlan, rateFood, unfavoriteFood, updateUserProfile } from "../services/apiService";
import { normalizeProfilePayload } from "../utils/profileFormUtils.js";

function getMealPlanItems(mealPlan) {
  if (!mealPlan) return [];
  if (Array.isArray(mealPlan.meals)) {
    return mealPlan.meals.flatMap((meal) => (Array.isArray(meal.items) ? meal.items : []));
  }
  if (Array.isArray(mealPlan)) {
    return mealPlan.flatMap((meal) => (Array.isArray(meal.items) ? meal.items : []));
  }
  return Object.values(mealPlan).flatMap((items) => (Array.isArray(items) ? items : []));
}

function getMealPlanKcal(mealPlan) {
  if (!mealPlan) return 0;
  const explicit = Number(mealPlan.total_kcal ?? mealPlan.totalKcal ?? mealPlan.total_calories ?? 0);
  if (Number.isFinite(explicit) && explicit > 0) return explicit;
  const items = getMealPlanItems(mealPlan);
  return items.reduce((sum, item) => sum + Number(item?.calories ?? item?.kcal ?? 0), 0);
}

function assertNonEmptyMealPlan(result) {
  if (!result || result.eligible === false) {
    return result;
  }
  const mealPlan = result.meal_plan;
  const items = getMealPlanItems(mealPlan);
  const totalKcal = getMealPlanKcal(mealPlan);
  if (!items.length || totalKcal <= 0) {
    throw new Error("Không thể tạo thực đơn hợp lệ. Meal plan đang rỗng hoặc kcal bằng 0.");
  }
  return result;
}

export async function submitRecommendation(formState) {
  const payload = normalizePayload(formState);
  const result = await postRecommendation(payload);
  return assertNonEmptyMealPlan(result);
}

export async function loadTodayMealPlan() {
  return fetchTodayMealPlan();
}

function getVietnamDateString() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Ho_Chi_Minh",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

function mealComplexityFromItems(itemsPerMeal) {
  const count = Number(itemsPerMeal);
  if (count <= 3) return "simple";
  if (count >= 5) return "full";
  return "balanced";
}

function profileToRegenerateForm(profile, fallback = {}) {
  if (!profile) return fallback;
  return {
    ...fallback,
    weight: profile.weight_kg ?? fallback.weight,
    height: profile.height_cm ?? fallback.height,
    age: profile.age ?? fallback.age,
    sex: profile.sex || profile.gender || fallback.sex,
    activity: profile.activity_level || fallback.activity,
    gain_speed: profile.weight_gain_speed || fallback.gain_speed,
    weight_gain_speed: profile.weight_gain_speed || fallback.weight_gain_speed,
    target_weight: profile.target_weight_kg ?? fallback.target_weight,
    meal_complexity: mealComplexityFromItems(profile.items_per_meal ?? fallback.items_per_meal),
    items_per_meal: profile.items_per_meal ?? fallback.items_per_meal,
    diet_style: profile.diet_type || fallback.diet_style,
    diet_type: profile.diet_type || fallback.diet_type,
    budget_level: profile.budget_level || fallback.budget_level,
    favorite_foods: profile.favorite_foods ?? fallback.favorite_foods,
    unfavorite_foods: profile.disliked_foods ?? fallback.unfavorite_foods,
    disliked_foods: profile.disliked_foods ?? fallback.disliked_foods,
    disliked_food_groups: profile.disliked_food_groups ?? fallback.disliked_food_groups,
  };
}

export async function regenerateMealPlan(formState, options = {}) {
  const freshProfile = options.profile || formState?.profile || null;
  const payload = normalizePayload(profileToRegenerateForm(freshProfile, formState));
  const result = await postRegenerateMealPlan({
    ...payload,
    userId: options.userId || undefined,
    date: options.date || getVietnamDateString(),
    previousMealPlanId: options.previousMealPlanId || undefined,
    targetKcal: options.targetKcal || payload.target_calories || undefined,
    excludePreviousItems: options.excludePreviousItems !== false,
    randomSeed: options.randomSeed || Date.now(),
    force_regenerate: true,
    profile: freshProfile || undefined,
  });
  return assertNonEmptyMealPlan(result);
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
  const normalizedPayload = toUserProfilePayload(payload);
  console.log("[PROFILE SUBMIT] payload =", normalizedPayload);
  const result = await updateUserProfile(normalizedPayload);
  console.log("[PROFILE PUT RESULT] =", result);
  return result;
}

function toUserProfilePayload(payload = {}) {
  return normalizeProfilePayload(payload);
}
