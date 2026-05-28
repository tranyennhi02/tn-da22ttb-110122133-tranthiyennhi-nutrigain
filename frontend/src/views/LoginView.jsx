import { useEffect, useState } from "react";

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
import { register, resendVerification, verifyEmail } from "../services/authService";

export default function LoginView({ onAuthSuccess, initialMode = null, onForgotPassword }) {
  // null = landing page, "login" | "register" = show auth modal/overlay
  const [authMode, setAuthMode] = useState(initialMode);
  const [serverError, setServerError] = useState("");
  const [toast, setToast] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [registerStep, setRegisterStep] = useState(1);
  const [verificationEmail, setVerificationEmail] = useState("");

  useEffect(() => {
    setAuthMode(initialMode);
    setRegisterStep(1);
    setVerificationEmail("");
  }, [initialMode]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const googleError = params.get("google_error") || "";
    if (!googleError) return;

    setAuthMode("login");
    setServerError("Không thể đăng nhập Google lúc này. Vui lòng thử lại hoặc dùng email.");
    window.history.replaceState({}, "", window.location.pathname);
  }, []);

  useEffect(() => {
    if (!authMode) {
      setRegisterStep(1);
      setVerificationEmail("");
    }
  }, [authMode]);

  function resetMessages() {
    setServerError("");
    setToast("");
  }

  function syncVerificationFlow(nextEmail) {
    setVerificationEmail(String(nextEmail || "").trim().toLowerCase());
    setRegisterStep(2);
    resetMessages();
  }

  function handleShowAuth(mode) {
    setAuthMode(mode);
    setRegisterStep(1);
    setVerificationEmail("");
    resetMessages();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handleSwitchMode() {
    setAuthMode((prev) => (prev === "login" ? "register" : "login"));
    setRegisterStep(1);
    setVerificationEmail("");
    resetMessages();
  }

  function handleChangeRegisterEmail() {
    setRegisterStep(1);
    resetMessages();
  }

  async function handleLoginSubmit(formData) {
    setIsSubmitting(true);
    resetMessages();
    try {
      await onAuthSuccess({ ...defaultLoginState, ...formData, mode: "login" });
      setToast("Đăng nhập thành công!");
    } catch (err) {
      console.error("Auth error:", err);
      const errMsg = err.message || "";
      if (errMsg.includes("xác thực") || errMsg.includes("verification")) {
        setServerError("Email chưa được xác thực. Vui lòng kiểm tra email hoặc gửi lại mã.");
      } else if (errMsg.includes("Failed to fetch") || errMsg.includes("NetworkError")) {
        setServerError("Không thể kết nối đến máy chủ. Vui lòng thử lại sau.");
      } else if (errMsg) {
        setServerError(errMsg);
      } else {
        setServerError("Email hoặc mật khẩu không đúng.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRegisterSubmit(formData) {
    setIsSubmitting(true);
    resetMessages();
    try {
      const response = await register(formData);
      syncVerificationFlow(response.email || formData.email);
      setToast(response.message || "Mã xác thực đã được gửi đến email của bạn.");
    } catch (err) {
      console.error("Register error:", err);
      const errMsg = err.message || "";
      if (errMsg.includes("already exists") || errMsg.includes("registered") || errMsg.includes("Conflict")) {
        setServerError("Email này đã được sử dụng. Vui lòng đăng nhập hoặc dùng email khác.");
      } else if (errMsg.includes("Mã xác thực") || errMsg.includes("wait")) {
        setServerError(errMsg);
      } else if (errMsg.includes("at least 8 characters") || errMsg.includes("too short")) {
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
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleVerifyEmail(payload) {
    setIsSubmitting(true);
    resetMessages();
    try {
      const authResult = await verifyEmail(payload);
      setToast("Email đã được xác thực.");
      await onAuthSuccess(authResult);
    } catch (err) {
      console.error("Email verification error:", err);
      const errMsg = err.message || "";
      if (errMsg.includes("hết hạn")) {
        setServerError("Mã xác thực đã hết hạn.");
      } else if (errMsg.includes("chưa đúng") || errMsg.includes("invalid")) {
        setServerError("Mã xác thực chưa đúng.");
      } else if (errMsg.includes("Failed to fetch") || errMsg.includes("NetworkError")) {
        setServerError("Không thể kết nối đến máy chủ. Vui lòng thử lại sau.");
      } else if (errMsg) {
        setServerError(errMsg);
      } else {
        setServerError("Không thể xác thực email lúc này.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleResendVerification() {
    setIsSubmitting(true);
    resetMessages();
    try {
      const response = await resendVerification({ email: verificationEmail });
      setToast(response.message || "Mã xác thực đã được gửi đến email của bạn.");
    } catch (err) {
      console.error("Resend verification error:", err);
      const errMsg = err.message || "";
      if (errMsg.includes("60 giây")) {
        setServerError("Vui lòng chờ 60 giây trước khi gửi lại mã.");
      } else if (errMsg.includes("đã được xác thực")) {
        setServerError("Email này đã được xác thực rồi.");
      } else if (errMsg.includes("Failed to fetch") || errMsg.includes("NetworkError")) {
        setServerError("Không thể kết nối đến máy chủ. Vui lòng thử lại sau.");
      } else if (errMsg) {
        setServerError(errMsg);
      } else {
        setServerError("Không thể gửi lại mã xác thực lúc này.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleGoogleLogin(idToken) {
    setIsSubmitting(true);
    resetMessages();
    try {
      await onAuthSuccess({ id_token: idToken, mode: "google" });
      setToast("Đăng nhập Google thành công!");
    } catch (err) {
      console.error("Google auth error:", err);
      setServerError(err.message || "Không thể đăng nhập bằng Google lúc này.");
    } finally {
      setIsSubmitting(false);
    }
  }

  // ── Auth overlay ───────────────────────────────────────────────────────────
  if (authMode) {
    return (
      <div className="relative min-h-screen overflow-x-hidden bg-[radial-gradient(circle_at_top_left,#bbf7d0,transparent_32%),radial-gradient(circle_at_bottom_right,#dbeafe,transparent_30%),linear-gradient(135deg,#ecfdf5,#f8fafc,#fff7ed)]">
        {/* Simple top bar */}
        <div className="relative z-10 border-b border-emerald-100 bg-white/70 backdrop-blur-xl">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8">
            <button onClick={() => setAuthMode(null)} className="flex items-center gap-2 text-sm font-semibold text-slate-500 transition hover:text-emerald-600">
              <ArrowLeftIcon />
              Quay lại trang chủ
            </button>
            <NutriGainLogo size="sm" />
          </div>
        </div>

        {/* Centered auth card */}
        <div className="relative z-10 flex min-h-screen items-center justify-center overflow-x-hidden px-4 py-10">
          <div className="w-full max-w-full">
            <AuthCard
              mode={authMode}
              registerStep={registerStep}
              verificationEmail={verificationEmail}
              isSubmitting={isSubmitting}
              serverError={serverError}
              toast={toast}
              onLoginSubmit={handleLoginSubmit}
              onRegisterSubmit={handleRegisterSubmit}
              onVerifyEmail={handleVerifyEmail}
              onResendVerification={handleResendVerification}
              onChangeEmail={handleChangeRegisterEmail}
              onSwitchMode={handleSwitchMode}
              onGoogleLogin={handleGoogleLogin}
              onForgotPassword={onForgotPassword}
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
