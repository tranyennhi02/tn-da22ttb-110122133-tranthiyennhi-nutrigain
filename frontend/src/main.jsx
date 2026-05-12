import React, { createContext, useContext, useEffect } from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import "./index.css";

const GoogleAuthContext = createContext(null);

export function GoogleOAuthProvider({ clientId, children }) {
  console.log("[GOOGLE CLIENT ID FRONTEND]", import.meta.env.VITE_GOOGLE_CLIENT_ID);

  useEffect(() => {
    const isConfigured = !!clientId && clientId !== "YOUR_GOOGLE_CLIENT_ID_HERE" && clientId !== "";
    console.log("[GOOGLE CLIENT ID]", isConfigured ? "loaded" : "missing");
    
    if (!isConfigured) return;

    // Load GSI client script dynamically
    let script = document.getElementById("google-gsi-client");
    if (!script) {
      script = document.createElement("script");
      script.src = "https://accounts.google.com/gsi/client";
      script.id = "google-gsi-client";
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    }
  }, [clientId]);

  return (
    <GoogleAuthContext.Provider value={clientId}>
      {children}
    </GoogleAuthContext.Provider>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID}>
      <App />
    </GoogleOAuthProvider>
  </React.StrictMode>,
);
