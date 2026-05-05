const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const AUTH_STORAGE_KEY = "nutrigain_auth";

async function requestAuth(path, payload) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Authentication failed");
  }

  return response.json();
}

function persistSession(data) {
  const session = {
    accessToken: data.access_token,
    tokenType: data.token_type,
    user: data.user,
    email: data.user?.email || "",
    name: data.user?.full_name || data.user?.email || "",
    role: data.user?.role || "user",
    loggedInAt: new Date().toISOString(),
  };
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
  return session;
}

export async function login(payload) {
  if (!payload.email || !payload.password) {
    throw new Error("Vui lòng nhập email và mật khẩu.");
  }
  const data = await requestAuth("/api/v1/auth/login", {
    email: payload.email,
    password: payload.password,
  });
  return persistSession(data);
}

export async function register(payload) {
  if (!payload.email || !payload.password) {
    throw new Error("Vui lòng nhập email và mật khẩu.");
  }
  const data = await requestAuth("/api/v1/auth/register", {
    email: payload.email,
    password: payload.password,
    full_name: payload.fullName || null,
  });
  return persistSession(data);
}

export function logout() {
  localStorage.removeItem(AUTH_STORAGE_KEY);
}

export function getSession() {
  const raw = localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw);
  } catch {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    return null;
  }
}

export function getAuthToken() {
  return getSession()?.accessToken || "";
}
