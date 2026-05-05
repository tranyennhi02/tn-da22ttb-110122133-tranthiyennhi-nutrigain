import { useMemo, useState } from "react";

import { performLogout, readSession, submitLogin } from "./controllers/authController";
import DashboardView from "./views/DashboardView";
import LoginView from "./views/LoginView";

export default function App() {
  const [session, setSession] = useState(() => readSession());

  const userEmail = useMemo(() => session?.email || "", [session]);

  async function handleLogin(loginState) {
    const nextSession = await submitLogin(loginState);
    setSession(nextSession);
  }

  function handleLogout() {
    performLogout();
    setSession(null);
  }

  if (!session) {
    return <LoginView onLogin={handleLogin} />;
  }

  return <DashboardView userEmail={userEmail} onLogout={handleLogout} />;
}
