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
  if (!response.ok) {
    const text = await response.text();
    try {
      const payload = JSON.parse(text);
      const detail = payload?.detail;
      const message =
        detail?.eligibility_check?.reason ||
        detail?.overall_assessment?.summary ||
        detail?.message ||
        (typeof detail === "string" ? detail : "");
      throw new Error(message || fallbackMessage);
    } catch (error) {
      if (error instanceof SyntaxError) {
        throw new Error(text || fallbackMessage);
      }
      throw error;
    }
  }
  return response.json();
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
  const response = await fetch(`${API_BASE_URL}/api/v1/users/me`, {
    headers: authHeaders(),
  });
  return parseResponse(response, "Cannot fetch current user");
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
