import { normalizeLoginPayload } from "../models/authModel";
import { getSession, login, logout, register } from "../services/authService";

export async function submitLogin(loginState) {
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
