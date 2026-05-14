import { parseFoodList } from "../utils/foodList.js";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function authHeaders() {
  const raw = localStorage.getItem("nutrigain_auth");
  if (!raw) {
    return {};
  }
  try {
    const session = JSON.parse(raw);
    return session?.accessToken ? { Authorization: `Bearer ${session.accessToken}` } : {};
  } catch {
    return {};
  }
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

    throw new Error(detail);
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

export async function postRegenerateMealPlan(payload) {
  const response = await fetch(`${API_BASE_URL}/api/v1/meal-plans/regenerate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(normalizeRegeneratePayload(payload)),
  });

  return parseResponse(response, "Cannot regenerate meal plan");
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
  const response = await fetch(`${API_BASE_URL}/api/v1/users/me/profile`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });
  return parseResponse(response, "Cannot update user profile");
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
