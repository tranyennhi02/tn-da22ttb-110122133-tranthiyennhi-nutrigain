import { normalizePayload } from "../models/recommendationModel";
import { favoriteFood, fetchHistory, postRecommendation, rateFood, unfavoriteFood, updateUserProfile } from "../services/apiService";

export async function submitRecommendation(formState) {
  const payload = normalizePayload(formState);
  return postRecommendation(payload);
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
  return updateUserProfile(payload);
}
