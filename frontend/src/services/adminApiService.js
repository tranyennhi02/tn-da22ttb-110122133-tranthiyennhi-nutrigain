const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function authHeaders() {
  const raw = localStorage.getItem("nutrigain_auth");
  if (!raw) return {};
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
    throw new Error(data?.detail || data?.message || fallbackMessage || "Admin request failed");
  }
  return data;
}

function queryString(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") query.set(key, value);
  });
  const text = query.toString();
  return text ? `?${text}` : "";
}

export function adminGet(path, params) {
  return fetch(`${API_BASE_URL}/api/v1/admin${path}${queryString(params)}`, {
    headers: authHeaders(),
  }).then((response) => parseResponse(response, "Cannot load admin data"));
}

export function adminPatch(path, payload) {
  return fetch(`${API_BASE_URL}/api/v1/admin${path}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  }).then((response) => parseResponse(response, "Cannot update admin data"));
}

export function adminPost(path, payload) {
  return fetch(`${API_BASE_URL}/api/v1/admin${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  }).then((response) => parseResponse(response, "Cannot run admin action"));
}
