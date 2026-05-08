import { useState } from "react";

import { defaultLoginState } from "../models/authModel";
import AuthCard from "./landing/AuthCard";
import CTASection from "./landing/CTASection";
import FAQSection from "./landing/FAQSection";
import FeatureSection from "./landing/FeatureSection";
import HeroSection from "./landing/HeroSection";
import HowItWorksSection from "./landing/HowItWorksSection";
import ProductPreviewSection from "./landing/ProductPreviewSection";
import PublicHeader from "./landing/PublicHeader";
import NutriGainLogo from "../components/NutriGainLogo";

export default function LoginView({ onAuthSuccess }) {
  // null = landing page, "login" | "register" = show auth modal/overlay
  const [authMode, setAuthMode] = useState(null);
  const [serverError, setServerError] = useState("");
  const [toast, setToast] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function handleShowAuth(mode) {
    setAuthMode(mode);
    setServerError("");
    setToast("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handleSwitchMode() {
    setAuthMode((prev) => (prev === "login" ? "register" : "login"));
    setServerError("");
    setToast("");
  }

  async function handleSubmit(formData) {
    setIsSubmitting(true);
    setServerError("");
    setToast("");
    try {
      await onAuthSuccess({ ...defaultLoginState, ...formData, mode: authMode });
      setToast("Đăng nhập thành công!");
    } catch {
      setServerError("Email hoặc mật khẩu không chính xác.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleGoogleLogin() {
    // TODO: integrate Google OAuth
    setServerError("Tính năng đang được phát triển. Vui lòng dùng email.");
  }

  // ── Auth overlay ───────────────────────────────────────────────────────────
  if (authMode) {
    return (
      <div className="min-h-screen bg-brand-mint">
        {/* Simple top bar */}
        <div className="border-b border-brand-border bg-white/90 backdrop-blur-xl">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8">
            <button onClick={() => setAuthMode(null)} className="flex items-center gap-2 text-sm font800 text-brand-text-sub transition hover:text-brand-primary">
              <ArrowLeftIcon />
              Quay lại trang chủ
            </button>
            <NutriGainLogo size="sm" />
          </div>
        </div>

        {/* Centered auth card */}
        <div className="flex min-h-[calc(100vh-65px)] items-center justify-center px-5 py-12">
          <div className="relative z-10 w-full max-w-[440px]">
            <AuthCard
              mode={authMode}
              isSubmitting={isSubmitting}
              serverError={serverError}
              toast={toast}
              onSubmit={handleSubmit}
              onSwitchMode={handleSwitchMode}
              onGoogleLogin={handleGoogleLogin}
            />
          </div>
        </div>
      </div>
    );
  }

  // ── Landing page ───────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-white text-brand-text-main">
      <PublicHeader onShowAuth={handleShowAuth} />
      <HeroSection onShowAuth={handleShowAuth} />
      <FeatureSection />
      <HowItWorksSection />
      <ProductPreviewSection />
      <FAQSection />
      <CTASection onShowAuth={handleShowAuth} />
    </div>
  );
}

function ArrowLeftIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 12H5M12 5l-7 7 7 7" />
    </svg>
  );
}
