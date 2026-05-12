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
      setToast(authMode === "register" ? "Đăng ký thành công!" : "Đăng nhập thành công!");
    } catch (err) {
      console.error("Auth error:", err);
      const errMsg = err.message || "";
      
      if (authMode === "register") {
        if (errMsg.includes("already exists") || errMsg.includes("registered") || errMsg.includes("Conflict")) {
          setServerError("Email này đã được sử dụng. Vui lòng đăng nhập hoặc dùng email khác.");
        } else if (errMsg.includes("at least 8 characters") || errMsg.includes("too short") || formData.password.length < 8) {
          setServerError("Mật khẩu cần có ít nhất 8 ký tự.");
        } else if (errMsg.includes("Invalid email") || errMsg.includes("invalid")) {
          setServerError("Email không hợp lệ.");
        } else if (errMsg.includes("Failed to fetch") || errMsg.includes("NetworkError")) {
          setServerError("Không thể kết nối đến máy chủ. Vui lòng thử lại sau.");
        } else if (errMsg) {
          setServerError(errMsg);
        } else {
          setServerError("Không thể tạo tài khoản lúc này. Vui lòng thử lại.");
        }
      } else {
        if (errMsg.includes("Invalid email or password") || errMsg.includes("incorrect") || errMsg.includes("Unauthorized")) {
          setServerError("Email hoặc mật khẩu không chính xác.");
        } else if (errMsg.includes("disabled")) {
          setServerError("Tài khoản của bạn đã bị vô hiệu hóa.");
        } else if (errMsg) {
          setServerError(errMsg);
        } else {
          setServerError("Đăng nhập thất bại. Vui lòng kiểm tra lại thông tin.");
        }
      }
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
