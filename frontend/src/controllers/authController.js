import { normalizeLoginPayload } from "../models/authModel";
import { getSession, login, logout, register, loginWithGoogle } from "../services/authService";

export async function submitLogin(loginState) {
  if (loginState.mode === "google") {
    return loginWithGoogle(loginState.id_token);
  }
  const payload = normalizeLoginPayload(loginState);
  if (loginState.mode === "register") {
    return register(payload);
  }
  return login(payload);
}

export function readSession() {
  return getSession();
}

export function performLogout() {
  logout();
}
