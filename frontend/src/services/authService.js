const API_BASE_URL = "";
const AUTH_STORAGE_KEY = "nutrigain_auth";
const AUTH_CACHE_KEYS = [
  "access_token",
  "token",
  "authToken",
  "refresh_token",
  "user",
  "currentUser",
  "googleUser",
  "nutrigain_user",
  "profile",
  "nutrigain_profile",
  AUTH_STORAGE_KEY,
];
const PROFILE_CACHE_KEYS = [
  "nutritionProfile",
  "onboardingData",
  "userProfile",
  "currentUser",
  "dislikedFoods",
  "favoriteFoods",
  "mealPlan",
  "progressSummary",
  "dashboardData",
  "nutrigain_disliked_foods",
  "nutrigain_disliked_food_groups",
];

export function clearAuthStorage() {
  for (const key of AUTH_CACHE_KEYS) {
    localStorage.removeItem(key);
    sessionStorage.removeItem(key);
  }

  for (const key of PROFILE_CACHE_KEYS) {
    localStorage.removeItem(key);
    sessionStorage.removeItem(key);
  }

  try {
    const keysToRemove = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && (
        key.startsWith("profile") ||
        key.startsWith("mealPlan") ||
        key.startsWith("weightSummary") ||
        key.startsWith("nutritionProfile") ||
        key.startsWith("nutrigain_gami_stats") ||
        key.startsWith("nutrigain_goal_dialog_dismissed_")
      )) {
        keysToRemove.push(key);
      }
    }
    for (const k of keysToRemove) {
      localStorage.removeItem(k);
      sessionStorage.removeItem(k);
    }
  } catch {}

  try {
    if (window?.google?.accounts?.id?.disableAutoSelect) {
      window.google.accounts.id.disableAutoSelect();
    }
  } catch {}
}

async function requestAuth(path, payload) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let errorMsg = "";
    try {
      const clone = response.clone();
      const errJson = await clone.json();
      if (errJson && errJson.detail) {
        if (typeof errJson.detail === "string") {
          errorMsg = errJson.detail;
        } else if (Array.isArray(errJson.detail)) {
          errorMsg = errJson.detail.map(d => d.msg || JSON.stringify(d)).join(", ");
        } else {
          errorMsg = JSON.stringify(errJson.detail);
        }
      }
    } catch {
      try {
        errorMsg = await response.text();
      } catch {}
    }

    if (path.includes("/api/v1/auth/google")) {
      if (response.status === 401 || response.status === 403) {
        throw new Error(errorMsg || "Google credential không hợp lệ hoặc client ID chưa đúng.");
      }
      if (response.status >= 500) {
        throw new Error(errorMsg || "Máy chủ đăng nhập đang lỗi. Vui lòng kiểm tra backend log.");
      }
    }

    const error = new Error(errorMsg || "Authentication failed");
    error.statusCode = response.status;
    error.status = response.status;
    throw error;
  }

  return response.json();
}

async function requestAuthGet(path) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    let errorMsg = "";
    try {
      const clone = response.clone();
      const errJson = await clone.json();
      if (errJson && errJson.detail) {
        errorMsg = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      try {
        errorMsg = await response.text();
      } catch {}
    }
    throw new Error(errorMsg || "Authentication failed");
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
    role: (data.user?.role || "USER").toUpperCase(),
    status: (data.user?.status || "ACTIVE").toUpperCase(),
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
  return requestAuth("/api/v1/auth/register", {
    email: payload.email,
    password: payload.password,
    full_name: payload.fullName || null,
  });
}

export async function verifyEmail({ email, code }) {
  if (!email || !code) {
    throw new Error("Vui lòng nhập mã xác thực.");
  }
  console.log("[VERIFY EMAIL API CALL]", { email: email.substring(0, 3) + "***" });
  const data = await requestAuth("/api/v1/auth/verify-email", {
    email: String(email).trim().toLowerCase(),
    code: String(code).trim(),
  });
  console.log("[VERIFY EMAIL API SUCCESS]", {
    hasAccessToken: Boolean(data?.access_token),
    hasUser: Boolean(data?.user),
    emailVerified: data?.user?.email_verified,
  });
  return persistSession(data);
}

export async function resendVerification({ email }) {
  if (!email) {
    throw new Error("Vui lòng nhập email.");
  }
  return requestAuth("/api/v1/auth/resend-verification", {
    email: String(email).trim().toLowerCase(),
  });
}

export async function loginWithGoogle(idToken) {
  if (!idToken) {
    throw new Error("Token Google không hợp lệ.");
  }

  clearAuthStorage();
  console.log("[GOOGLE AUTH PAYLOAD]", { hasCredential: Boolean(idToken) });

  const data = await requestAuth("/api/v1/auth/google", {
    credential: idToken,
    id_token: idToken,
  });
  return persistSession(data);
}

export async function getGoogleOAuthUrl() {
  const data = await requestAuthGet("/api/v1/auth/google/url");
  if (!data?.url) {
    throw new Error("Không lấy được liên kết đăng nhập Google.");
  }
  return data;
}
export async function forgotPassword(email) {
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email).trim())) {
    throw new Error("Email không hợp lệ.");
  }
  return requestAuth("/api/v1/auth/forgot-password", {
    email: String(email).trim().toLowerCase(),
  });
}

export async function resetPassword({ token, newPassword, confirmPassword }) {
  if (!token) {
    throw new Error("Liên kết đặt lại mật khẩu không hợp lệ.");
  }
  if (!newPassword || newPassword.length < 8) {
    throw new Error("Mật khẩu mới cần có ít nhất 8 ký tự.");
  }
  if (newPassword !== confirmPassword) {
    throw new Error("Mật khẩu xác nhận không khớp.");
  }
  return requestAuth("/api/v1/auth/reset-password", {
    token,
    new_password: newPassword,
    confirm_password: confirmPassword,
  });
}


export function logout() {
  clearAuthStorage();
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
