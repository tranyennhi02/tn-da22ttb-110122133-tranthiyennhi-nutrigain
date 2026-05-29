import { parseFoodList } from "../utils/foodList.js";
import { clearAuthStorage } from "./authService";

const API_BASE_URL = "";

export function getAuthToken() {
  const possibleKeys = [
    "nutrigain_auth",
    "auth_token",
    "access_token",
    "token",
    "authToken",
    "nutrigain_token",
  ];

  for (const key of possibleKeys) {
    const value = localStorage.getItem(key);
    if (!value) continue;

    if (value.trim().startsWith("{")) {
      try {
        const parsed = JSON.parse(value);
        const token =
          parsed?.accessToken ||
          parsed?.access_token ||
          parsed?.authToken ||
          parsed?.auth_token ||
          parsed?.token ||
          "";
        if (token) return token;
      } catch {}
      continue;
    }

    return value;
  }

  try {
    const authRaw = localStorage.getItem("auth");
    if (authRaw) {
      const parsed = JSON.parse(authRaw);
      return parsed?.accessToken || parsed?.access_token || parsed?.authToken || parsed?.auth_token || parsed?.token || "";
    }
  } catch {}

  try {
    const userRaw = localStorage.getItem("user");
    if (userRaw) {
      const parsed = JSON.parse(userRaw);
      return parsed?.accessToken || parsed?.access_token || parsed?.authToken || parsed?.auth_token || parsed?.token || "";
    }
  } catch {}

  return "";
}

export function getAuthHeaders() {
  const token = getAuthToken();
  return token ? { Authorization: token.startsWith("Bearer ") ? token : `Bearer ${token}` } : {};
}

function authHeaders() {
  return getAuthHeaders();
}

async function parseResponse(response, fallbackMessage) {
  const text = await response.text();

  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!response.ok) {
    let detail =
      data?.detail ||
      data?.message ||
      data?.error ||
      (typeof data === "string" ? data : null) ||
      fallbackMessage ||
      `Request failed with status ${response.status}`;

    if (Array.isArray(detail)) {
      const hasFoodListTypeError = detail.some((item) => {
        const loc = Array.isArray(item?.loc) ? item.loc.join(".") : "";
        return item?.type === "list_type" && /(favorite_foods|disliked_foods)/.test(loc);
      });
      detail = hasFoodListTypeError
        ? "favorite_foods phải là danh sách. Hệ thống đã tự chuyển input rỗng thành danh sách trống, vui lòng thử lại."
        : detail
          .map((item) => item?.msg || JSON.stringify(item))
          .join("; ");
    } else if (typeof detail === "object" && detail !== null) {
      if (detail.eligibility_check?.reason) {
        detail = detail.eligibility_check.reason;
      } else if (detail.overall_assessment?.summary) {
        detail = detail.overall_assessment.summary;
      } else if (detail.message) {
        detail = detail.message;
      } else if (detail.reason) {
        detail = detail.reason;
      } else {
        try {
          detail = JSON.stringify(detail);
        } catch {
          detail = String(detail);
        }
      }
    }

    console.error("API error detail:", {
      status: response.status,
      url: response.url,
      data,
    });

    const error = new Error(detail);
    error.status = response.status;
    error.data = data;
    if (data?.detail && typeof data.detail === "object" && data.detail !== null) {
      error.code = data.detail.code || undefined;
      error.detail = data.detail;
    }
    throw error;
  }

  return data;
}

function normalizeRegeneratePayload(payload = {}) {
  const dislikedFoods = [
    ...parseFoodList(payload.disliked_foods),
    ...parseFoodList(payload.unfavorite_foods),
  ];
  return {
    ...payload,
    favorite_foods: parseFoodList(payload.favorite_foods),
    disliked_foods: Array.from(new Set(dislikedFoods)),
    disliked_food_groups: parseFoodList(payload.disliked_food_groups),
  };
}

export async function postRecommendation(payload) {
  const response = await fetch(`${API_BASE_URL}/api/v1/recommendations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });

  return parseResponse(response, "Recommendation request failed");
}

export async function fetchTodayMealPlan() {
  const response = await fetch(`${API_BASE_URL}/api/v1/meal-plans/today`, {
    headers: authHeaders(),
  });
  return parseResponse(response, "Cannot load today's meal plan");
}

export async function fetchEatingHistory(params = {}) {
  const query = new URLSearchParams();

  if (params.mode) query.set("mode", params.mode);
  if (params.date) query.set("date", params.date);
  if (params.month) query.set("month", params.month);
  if (params.year) query.set("year", params.year);

  const response = await fetch(`${API_BASE_URL}/api/v1/nutrition/eating-history?${query.toString()}`, {
    headers: authHeaders(),
  });
  return parseResponse(response, "Cannot load eating history");
}

export async function postRegenerateMealPlan(payload) {
  const response = await fetch(`${API_BASE_URL}/api/v1/meal-plans/regenerate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(normalizeRegeneratePayload(payload)),
  });

  const data = await parseResponse(response, "Cannot regenerate meal plan");
  console.log("[REGENERATE RESPONSE PROFILE SNAPSHOT]", data?.profile_snapshot);
  return data;
}

export async function postIngredientCandidates(payload) {
  const response = await fetch(`${API_BASE_URL}/api/v1/ingredients/candidates`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });

  return parseResponse(response, "Cannot fetch ingredient candidates");
}

export async function fetchHistory(limit = 10, period = "week") {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/recommendations/history?limit=${limit}&period=${period}`,
    {
      headers: authHeaders(),
    }
  );
  return parseResponse(response, "Cannot load recommendation history");
}

export async function fetchCurrentUser() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/users/me`, {
      headers: authHeaders(),
    });
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        clearAuthStorage();
        return null;
      }
      throw new Error(`Failed to fetch current user: ${response.status} ${response.statusText}`);
    }
    return parseResponse(response, "Cannot fetch current user");
  } catch (err) {
    console.error("fetchCurrentUser error:", err);
    return null;
  }
}

export async function updateUserProfile(payload) {
  const url = `${API_BASE_URL}/api/v1/users/me/profile`;
  console.log("[UPDATE PROFILE REQUEST]", {
    url,
    payload_weight_kg: payload.weight_kg,
    payload,
  });
  const response = await fetch(url, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });
  const res = await parseResponse(response, "Cannot update user profile");
  console.log("[PROFILE PUT RESULT WEIGHT]", res?.weight_kg || res?.profile?.weight_kg);
  return res;
}

export async function fetchWeightLogs(range = "30") {
  const response = await fetch(`${API_BASE_URL}/api/v1/weight-logs?range=${encodeURIComponent(range)}&mode=milestones`, {
    headers: authHeaders(),
  });
  return parseResponse(response, "Cannot load weight logs");
}

export async function fetchWeightLogSummary() {
  const response = await fetch(`${API_BASE_URL}/api/v1/weight-logs/summary`, {
    headers: authHeaders(),
  });
  return parseResponse(response, "Cannot load weight summary");
}

export async function saveWeightLog(payload) {
  const response = await fetch(`${API_BASE_URL}/api/v1/weight-logs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });
  return parseResponse(response, "Cannot save weight log");
}

export async function favoriteFood(foodId) {
  const response = await fetch(`${API_BASE_URL}/api/v1/foods/${foodId}/favorite`, {
    method: "POST",
    headers: authHeaders(),
  });
  return parseResponse(response, "Cannot save favorite food");
}

export async function unfavoriteFood(foodId) {
  const response = await fetch(`${API_BASE_URL}/api/v1/foods/${foodId}/favorite`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  return parseResponse(response, "Cannot remove favorite food");
}

export async function rateFood(foodId, rating) {
  const response = await fetch(`${API_BASE_URL}/api/v1/foods/${foodId}/rating`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify({ rating }),
  });
  return parseResponse(response, "Cannot rate food");
}

export async function getGamificationSummary() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/gamification/summary`, {
      headers: authHeaders(),
    });
    if (!response.ok) {
      throw new Error("Gamification API not available");
    }
    return parseResponse(response, "Cannot load gamification summary");
  } catch (err) {
    console.warn("Gamification fallback activated", err);
    return {
      streak: { current: 0, best: 0 },
      achievements: [],
      today_challenge: {
        key: "fallback_challenge",
        title: "Bắt đầu nhẹ nhàng",
        description: "Ghi nhận bữa ăn đầu tiên của bạn hôm nay.",
        status: "pending"
      },
      encouragement: "Ăn đều hơn một chút cũng là tiến bộ."
    };
  }
}

export async function completeGamificationChallenge(challengeId) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/gamification/challenges/complete`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
      },
      body: JSON.stringify({ challenge_key: challengeId }),
    });
    if (!response.ok) {
      throw new Error("Gamification API not available");
    }
    return parseResponse(response, "Cannot complete challenge");
  } catch (err) {
    console.warn("Gamification fallback activated", err);
    return { success: true };
  }
}

export async function sendAiChatMessage(payload) {
  const response = await fetch(`${API_BASE_URL}/api/v1/ai-chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });
  return parseResponse(response, "Cannot send AI chat message");
}

export async function toggleMealConsumption(payload) {
  const response = await fetch(`${API_BASE_URL}/api/v1/meal-consumption/toggle`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });
  return parseResponse(response, "Cannot update meal consumption status");
}
