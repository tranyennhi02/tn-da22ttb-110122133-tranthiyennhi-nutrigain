import { forwardRef, useState, useEffect } from "react";
import NutriGainLogo from "../../components/NutriGainLogo";

export default function AuthCard({ mode, onSubmit, onSwitchMode, onGoogleLogin, onForgotPassword, isSubmitting, serverError, toast }) {
  const isRegister = mode === "register";
  const [form, setForm] = useState({ fullName: "", email: "", password: "" });
  const [showPw, setShowPw] = useState(false);
  const [errors, setErrors] = useState({});

  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
  const isGoogleConfigured = !!googleClientId && googleClientId !== "YOUR_GOOGLE_CLIENT_ID_HERE" && googleClientId !== "";

  console.log("[GOOGLE CLIENT ID]", isGoogleConfigured ? "loaded" : "missing");

  useEffect(() => {
    if (!isGoogleConfigured) return;

    let active = true;
    let interval = setInterval(() => {
      if (window.google) {
        clearInterval(interval);
        if (active) {
          initGoogleSignIn();
        }
      }
    }, 100);

    return () => {
      active = false;
      clearInterval(interval);
    };

    function initGoogleSignIn() {
      if (window.google) {
        window.google.accounts.id.initialize({
          client_id: googleClientId,
          callback: (res) => {
            if (res.credential) {
              onGoogleLogin(res.credential);
            }
          },
        });
        window.google.accounts.id.renderButton(
          document.getElementById("google-signin-btn"),
          {
            theme: "outline",
            size: "large",
            width: "376",
            text: "continue_with",
            shape: "pill",
          }
        );
      }
    }
  }, [isGoogleConfigured, onGoogleLogin, googleClientId]);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((p) => ({ ...p, [name]: value }));
    setErrors((p) => ({ ...p, [name]: "" }));
  }

  function validate() {
    const errs = {};
    if (isRegister && !form.fullName.trim()) errs.fullName = "Vui lòng nhập họ tên";
    if (!form.email.trim()) errs.email = "Vui lòng nhập email";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) errs.email = "Email không hợp lệ";
    if (!form.password) errs.password = "Vui lòng nhập mật khẩu";
    else if (form.password.length < 8) errs.password = "Mật khẩu cần có ít nhất 8 ký tự.";
    return errs;
  }

  function handleSubmit(e) {
    e.preventDefault();
    const errs = validate();
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;
    onSubmit({ ...form, mode });
  }

  return (
    <div className="w-full max-w-[440px]">
      {/* Card */}
      <div className="rounded-[28px] border border-brand-border bg-white p-8 shadow-2xl shadow-brand-navy/10">
        {/* Logo */}
        <NutriGainLogo size="sm" />

        <div className="mt-7">
          <h2 className="text-2xl font900 text-brand-navy">{isRegister ? "Tạo tài khoản" : "Chào mừng trở lại"}</h2>
          <p className="mt-1 text-sm font600 text-brand-text-sub">
            {isRegister ? "Bắt đầu hành trình tăng cân của bạn" : "Tiếp tục kế hoạch dinh dưỡng hôm nay"}
          </p>
        </div>

        {/* Google button */}
        {isGoogleConfigured ? (
          <div id="google-signin-btn" className="mt-7 flex w-full justify-center" />
        ) : (
          <>
            <button
              type="button"
              disabled
              className="mt-7 flex h-12 w-full items-center justify-center gap-3 rounded-2xl border border-slate-200 bg-white text-sm font800 text-brand-text-main opacity-60 cursor-not-allowed"
            >
              <GoogleIcon />
              Tiếp tục với Google
            </button>
            <p className="mt-2 text-center text-xs font700 text-amber-600">
              Tính năng đăng nhập Google đang được phát triển. Vui lòng đăng nhập bằng email.
            </p>
          </>
        )}

        {/* Divider */}
        <div className="my-6 flex items-center gap-4">
          <div className="h-px flex-1 bg-brand-border" />
          <span className="text-xs font700 text-brand-text-sub">hoặc đăng nhập bằng email</span>
          <div className="h-px flex-1 bg-brand-border" />
        </div>

        {/* Form */}
        <form className="space-y-4" onSubmit={handleSubmit} noValidate>
          {isRegister && (
            <Field label="Họ tên" name="fullName" placeholder="Nguyễn Văn A" value={form.fullName} error={errors.fullName} onChange={handleChange} />
          )}
          <Field label="Email" name="email" type="email" placeholder="ban@example.com" value={form.email} error={errors.email} onChange={handleChange} />
          <div>
            <div className="relative">
              <Field label="Mật khẩu" name="password" type={showPw ? "text" : "password"} placeholder="Tối thiểu 8 ký tự" value={form.password} error={errors.password} onChange={handleChange} />
              <button
                type="button"
                onClick={() => setShowPw((v) => !v)}
                className="absolute right-3 top-9 grid h-8 w-8 place-items-center rounded-lg text-brand-text-sub hover:bg-brand-mint hover:text-brand-primary"
              >
                {showPw ? <EyeOffIcon /> : <EyeIcon />}
              </button>
            </div>
            {!isRegister && (
              <div className="mt-1.5 flex justify-end">
                <button type="button" onClick={(e) => { e.preventDefault(); if (onForgotPassword) onForgotPassword(); }} className="text-xs font800 text-brand-text-sub transition hover:text-brand-primary">Quên mật khẩu?</button>
              </div>
            )}
          </div>

          {serverError && (
            <div className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm font700 text-red-600">{serverError}</div>
          )}
          {toast && (
            <div className="rounded-2xl border border-brand-primary/20 bg-brand-mint px-4 py-3 text-sm font800 text-brand-primary">{toast}</div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="flex h-12 w-full items-center justify-center rounded-2xl bg-brand-primary text-sm font900 text-white shadow-lg shadow-brand-primary/20 transition hover:bg-brand-primary-dark disabled:cursor-not-allowed disabled:opacity-55"
          >
            {isSubmitting ? (
              <span className="flex items-center gap-2"><Spinner />{isRegister ? "Đang tạo tài khoản..." : "Đang đăng nhập..."}</span>
            ) : isRegister ? "Đăng ký" : "Đăng nhập"}
          </button>
        </form>

        {/* Switch mode */}
        <p className="mt-6 text-center text-sm font700 text-brand-text-sub">
          {isRegister ? "Đã có tài khoản? " : "Chưa có tài khoản? "}
          <button type="button" onClick={onSwitchMode} className="font900 text-brand-primary transition hover:text-brand-primary-dark">
            {isRegister ? "Đăng nhập" : "Đăng ký miễn phí"}
          </button>
        </p>
      </div>

      {/* Back to home */}
      <div className="mt-5 text-center">
        <a href="#hero" className="text-sm font700 text-brand-text-sub transition hover:text-brand-primary">
          ← Quay lại trang chủ
        </a>
      </div>
    </div>
  );
}

function Field({ label, name, type = "text", placeholder, value, error, onChange }) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font800 text-brand-text-main">{label}</label>
      <input
        name={name}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        className={`h-12 w-full rounded-xl border bg-white px-4 text-sm font600 text-brand-text-main outline-none transition placeholder:text-brand-text-sub focus:ring-4 focus:ring-brand-primary/10 ${
          error ? "border-red-400 focus:border-red-400" : "border-brand-border focus:border-brand-primary"
        }`}
      />
      {error && <p className="mt-1.5 text-xs font700 text-red-500">{error}</p>}
    </div>
  );
}

function Spinner() {
  return <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />;
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" xmlns="http://www.w3.org/2000/svg">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
    </svg>
  );
}

function EyeIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" /><circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3l18 18M10.6 10.6A3 3 0 0 0 13.4 13.4" />
      <path d="M9.9 4.2A10.7 10.7 0 0 1 12 4c6.5 0 10 8 10 8a18 18 0 0 1-2.2 3.3M6.6 6.6C3.6 8.5 2 12 2 12s3.5 8 10 8a10.9 10.9 0 0 0 4.9-1.2" />
    </svg>
  );
}
