export const defaultLoginState = {
  mode: "login",
  fullName: "",
  email: "",
  password: "",
};

export function normalizeLoginPayload(state) {
  return {
    email: String(state.email || "").trim().toLowerCase(),
    password: String(state.password || ""),
    fullName: String(state.fullName || "").trim(),
  };
}
