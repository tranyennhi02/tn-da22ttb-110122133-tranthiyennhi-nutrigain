import { useEffect, useRef, useState } from "react";
import NutriGainLogo from "../../components/NutriGainLogo";
import { getGoogleOAuthUrl } from "../../services/authService";

let googleInitializedGlobally = false;

export default function AuthCard({
  mode,
  registerStep,
  verificationEmail,
  onLoginSubmit,
  onRegisterSubmit,
  onVerifyEmail,
  onResendVerification,
  onChangeEmail,
  onSwitchMode,
  onGoogleLogin,
  onForgotPassword,
  isSubmitting,
  serverError,
  toast,
}) {
  useEffect(() => {
    console.log("[AUTH FORM ACTIVE] restored old form, empty credentials");
  }, []);

  const isRegister = mode === "register";
  const isVerificationStep = isRegister && registerStep === 2;

  const [form, setForm] = useState({
    fullName: "",
    email: "",
    password: "",
    confirmPassword: "",
    verificationCode: "",
  });
  const [errors, setErrors] = useState({});
  const [showPw, setShowPw] = useState(false);
  const [showConfirmPw, setShowConfirmPw] = useState(false);

  const googleInitializedRef = useRef(false);
  const googleLoginRef = useRef(onGoogleLogin);
  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
  const isGoogleConfigured = !!googleClientId && googleClientId !== "YOUR_GOOGLE_CLIENT_ID_HERE" && googleClientId !== "" && googleClientId !== "undefined";

  useEffect(() => {
    googleLoginRef.current = onGoogleLogin;
  }, [onGoogleLogin]);

  useEffect(() => {
    setErrors({});
    setShowPw(false);
    setShowConfirmPw(false);
    setForm({
      fullName: "",
      email: "",
      password: "",
      confirmPassword: "",
      verificationCode: "",
    });
  }, [mode, registerStep]);

  useEffect(() => {
    if (!isGoogleConfigured || googleInitializedGlobally || googleInitializedRef.current) return;

    let active = true;
    const interval = window.setInterval(() => {
      if (!window.google) return;
      window.clearInterval(interval);
      if (active && !googleInitializedRef.current) {
        initGoogleSignIn();
      }
    }, 100);

    return () => {
      active = false;
      window.clearInterval(interval);
    };

    function initGoogleSignIn() {
      if (!window.google || googleInitializedRef.current || googleInitializedGlobally) return;
      googleInitializedRef.current = true;
      googleInitializedGlobally = true;
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        use_fedcm_for_prompt: false,
        callback: (response) => {
          if (response?.credential) {
            googleLoginRef.current?.(response.credential);
          }
        },
      });
      try {
        console.log("[GOOGLE CLIENT ID FRONTEND RAW]", JSON.stringify(import.meta.env.VITE_GOOGLE_CLIENT_ID));
        console.log("[APP ORIGIN]", window.location.origin);
      } catch {
        // ignore
      }
    }
  }, [isGoogleConfigured, googleClientId]);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: "" }));
  }

  function validateLogin() {
    const nextErrors = {};
    if (!form.email.trim()) nextErrors.email = "Vui lòng nhập email.";
    else if (!isValidEmail(form.email)) nextErrors.email = "Email chưa đúng định dạng.";
    if (!form.password) nextErrors.password = "Vui lòng nhập mật khẩu.";
    return nextErrors;
  }

  function validateRegister() {
    const nextErrors = {};
    if (!form.fullName.trim()) nextErrors.fullName = "Vui lòng nhập họ tên.";
    if (!form.email.trim()) nextErrors.email = "Vui lòng nhập email.";
    else if (!isValidEmail(form.email)) nextErrors.email = "Email chưa đúng định dạng.";
    if (!form.password) nextErrors.password = "Vui lòng nhập mật khẩu.";
    else if (form.password.length < 8) nextErrors.password = "Mật khẩu cần ít nhất 8 ký tự.";
    if (!form.confirmPassword) nextErrors.confirmPassword = "Vui lòng nhập lại mật khẩu.";
    else if (form.password !== form.confirmPassword) nextErrors.confirmPassword = "Mật khẩu nhập lại chưa khớp.";
    return nextErrors;
  }

  function validateVerification() {
    const nextErrors = {};
    if (!form.verificationCode.trim()) nextErrors.verificationCode = "Vui lòng nhập mã xác thực.";
    else if (!/^\d{6}$/.test(form.verificationCode.trim())) nextErrors.verificationCode = "Mã xác thực phải gồm 6 chữ số.";
    return nextErrors;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    
    // Register mode: validate registration fields
    if (isRegister) {
      const nextErrors = validateRegister();
      setErrors(nextErrors);
      if (Object.keys(nextErrors).length > 0) return;

      await onRegisterSubmit?.({
        fullName: form.fullName.trim(),
        email: form.email.trim(),
        password: form.password,
        confirmPassword: form.confirmPassword,
      });
      return;
    }

    // Login mode: validate login fields
    const nextErrors = validateLogin();
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    await onLoginSubmit?.({
      email: form.email.trim(),
      password: form.password,
    });
  }

  async function handleVerifySubmit(event) {
    event.preventDefault();
    
    // Clear all previous errors
    setErrors({});
    
    // Verify mode: only validate verification code
    const nextErrors = validateVerification();
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    await onVerifyEmail?.({
      email: verificationEmail || form.email,
      code: form.verificationCode.trim(),
    });
  }

  async function handleGoogleClick() {
    console.log("[GOOGLE LOGIN CLICK]");
    try {
      const data = await getGoogleOAuthUrl();
      console.log("[GOOGLE REDIRECT FALLBACK]");
      window.location.href = data.url;
    } catch (error) {
      console.warn("[GOOGLE FEDCM BLOCKED]", error);
    }
  }

  const title = isVerificationStep
    ? "Kiểm tra email của bạn"
    : isRegister
      ? "Tạo tài khoản mới"
      : "Chào mừng trở lại";
  const subtitle = isVerificationStep
    ? `NutriGain đã gửi mã xác thực 6 số đến ${verificationEmail || form.email}. Nhập mã để hoàn tất đăng ký.`
    : isRegister
      ? "Bắt đầu xây dựng kế hoạch dinh dưỡng của bạn."
      : "Đăng nhập để tiếp tục kế hoạch dinh dưỡng của bạn.";

  const submitLabel = isVerificationStep ? "Xác thực email" : isRegister ? "Tạo tài khoản" : "Đăng nhập";
  const submittingLabel = isVerificationStep ? "Đang xác thực..." : isRegister ? "Đang tạo tài khoản..." : "Đang đăng nhập...";
  return (
    <div className="w-full px-4 py-0 overflow-x-hidden">
      <div className="mx-auto w-full max-w-[500px] rounded-[36px] border border-emerald-100 bg-white/95 p-8 shadow-[0_28px_90px_rgba(15,23,42,0.14)] backdrop-blur md:p-10">
        <div className="mb-6 flex justify-center">
          <NutriGainLogo size="sm" />
        </div>

        <div className="mb-8 text-center">
          <h2 className="text-3xl font-black leading-tight tracking-tight text-slate-950 md:text-4xl">{title}</h2>
          <p className="mt-3 text-sm font-semibold leading-relaxed text-slate-500 md:text-base">{subtitle}</p>
        </div>

        {!isVerificationStep && (
          <>
            <button
              type="button"
              onClick={handleGoogleClick}
              disabled={!isGoogleConfigured}
              className="mb-5 flex h-12 w-full items-center justify-center gap-2.5 rounded-[16px] border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <GoogleIcon />
              <span>Tiếp tục với Google</span>
            </button>

            <div className="mb-5 flex items-center gap-4">
              <div className="h-px flex-1 bg-slate-200" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">hoặc đăng nhập bằng email</span>
              <div className="h-px flex-1 bg-slate-200" />
            </div>

            <form className="space-y-4" onSubmit={handleSubmit} noValidate>
              {isRegister && (
                <TextField
                  label="Họ tên"
                  name="fullName"
                  placeholder="Họ và tên"
                  value={form.fullName}
                  error={errors.fullName}
                  onChange={handleChange}
                  autoComplete="name"
                />
              )}

              <TextField
                label="Email"
                name="email"
                type="email"
                placeholder="email@example.com"
                value={form.email}
                error={errors.email}
                onChange={handleChange}
                autoComplete={isRegister ? "email" : "username"}
              />

              <PasswordField
                label="Mật khẩu"
                name="password"
                placeholder="Nhập mật khẩu"
                value={form.password}
                error={errors.password}
                onChange={handleChange}
                autoComplete={isRegister ? "new-password" : "current-password"}
                showPw={showPw}
                onToggleShow={() => setShowPw((current) => !current)}
              />

              {isRegister && (
                <PasswordField
                  label="Nhập lại mật khẩu"
                  name="confirmPassword"
                  placeholder="Nhập lại mật khẩu"
                  value={form.confirmPassword}
                  error={errors.confirmPassword}
                  onChange={handleChange}
                  autoComplete="new-password"
                  showPw={showConfirmPw}
                  onToggleShow={() => setShowConfirmPw((current) => !current)}
                />
              )}

              {!isRegister && (
                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={(event) => {
                      event.preventDefault();
                      onForgotPassword?.();
                    }}
                    className="text-sm font-semibold text-slate-500 transition hover:text-emerald-600"
                  >
                    Quên mật khẩu?
                  </button>
                </div>
              )}

              {serverError && <ServerErrorBox message={serverError} />}
              {toast && <ToastBox message={toast} />}

              <button
                type="submit"
                disabled={isSubmitting}
                className="flex h-14 w-full items-center justify-center rounded-2xl bg-emerald-600 text-sm font-extrabold text-white shadow-[0_16px_32px_rgba(5,150,105,0.28)] transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSubmitting ? <LoadingLabel label={submittingLabel} /> : submitLabel}
              </button>
            </form>
          </>
        )}

        {isVerificationStep && (
          <form className="space-y-4" onSubmit={handleVerifySubmit} noValidate>
            <TextField
              label="Mã xác thực"
              name="verificationCode"
              placeholder="123456"
              value={form.verificationCode}
              error={errors.verificationCode}
              onChange={handleChange}
              inputMode="numeric"
              maxLength={6}
              autoComplete="one-time-code"
            />

            <div className="flex flex-col gap-2 text-sm font-semibold text-slate-500 sm:flex-row sm:items-center sm:justify-between">
              <button type="button" onClick={onResendVerification} className="text-left transition hover:text-emerald-600">
                Gửi lại mã
              </button>
              <button type="button" onClick={onChangeEmail} className="text-left transition hover:text-emerald-600">
                Đổi email
              </button>
            </div>

            {serverError && <ServerErrorBox message={serverError} />}
            {toast && <ToastBox message={toast} />}

            <button
              type="submit"
              disabled={isSubmitting}
              className="flex h-14 w-full items-center justify-center rounded-2xl bg-emerald-600 text-sm font-extrabold text-white shadow-[0_16px_32px_rgba(5,150,105,0.28)] transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? <LoadingLabel label={submittingLabel} /> : submitLabel}
            </button>
          </form>
        )}

        <p className="mt-6 text-center text-sm font-semibold text-slate-500">
          {isRegister ? (
            <>
              Đã có tài khoản?{" "}
              <button type="button" onClick={onSwitchMode} className="font-extrabold text-emerald-600 transition hover:underline">
                Đăng nhập
              </button>
            </>
          ) : (
            <>
              Chưa có tài khoản?{" "}
              <button type="button" onClick={onSwitchMode} className="font-extrabold text-emerald-600 transition hover:underline">
                Đăng ký miễn phí
              </button>
            </>
          )}
        </p>

        <div className="mt-8 text-center">
          <a href="#hero" className="text-sm font-semibold text-slate-500 transition hover:text-emerald-600">
            ← Quay lại trang chủ
          </a>
        </div>
      </div>
    </div>
  );
}

function TextField({ label, name, type = "text", placeholder, value, error, onChange, autoComplete, inputMode, maxLength }) {
  return (
    <div className="space-y-2">
      <label className="block text-sm font-bold text-slate-700">{label}</label>
      <input
        name={name}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        autoComplete={autoComplete}
        inputMode={inputMode}
        maxLength={maxLength}
        className="h-14 w-full rounded-2xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-emerald-400 focus:ring-4 focus:ring-emerald-100"
        style={{
          WebkitBoxShadow: "0 0 0px 1000px rgb(255,255,255) inset",
          WebkitTextFillColor: "rgb(15,23,42)",
          transition: "background-color 9999s ease-in-out 0s"
        }}
      />
      {error && <p className="text-xs font-semibold text-red-600">{error}</p>}
    </div>
  );
}

function PasswordField({ label, name, placeholder, value, error, onChange, autoComplete, showPw, onToggleShow }) {
  return (
    <div className="space-y-2">
      <label className="block text-sm font-bold text-slate-700">{label}</label>
      <div className="relative">
        <input
          name={name}
          type={showPw ? "text" : "password"}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          autoComplete={autoComplete}
          className="h-14 w-full rounded-2xl border border-slate-200 bg-white px-4 pr-12 text-sm font-semibold text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-emerald-400 focus:ring-4 focus:ring-emerald-100"
          style={{
            WebkitBoxShadow: "0 0 0px 1000px rgb(255,255,255) inset",
            WebkitTextFillColor: "rgb(15,23,42)",
            transition: "background-color 9999s ease-in-out 0s"
          }}
        />
        <button
          type="button"
          onClick={onToggleShow}
          aria-label={showPw ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
          className="absolute right-3 top-1/2 grid h-10 w-10 -translate-y-1/2 place-items-center rounded-xl text-slate-500 transition hover:bg-emerald-50 hover:text-emerald-600"
        >
          {showPw ? <EyeOffIcon /> : <EyeIcon />}
        </button>
      </div>
      {error && <p className="text-xs font-semibold text-red-600">{error}</p>}
    </div>
  );
}

function Spinner() {
  return <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />;
}

function LoadingLabel({ label }) {
  return (
    <span className="flex items-center gap-2">
      <Spinner />
      {label}
    </span>
  );
}

function ServerErrorBox({ message }) {
  return <div className="rounded-2xl border border-red-100 bg-red-50 p-4 text-sm font-semibold text-red-600">{message}</div>;
}

function ToastBox({ message }) {
  return <div className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4 text-sm font-semibold text-emerald-700">{message}</div>;
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
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" />
      <circle cx="12" cy="12" r="3" />
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

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value || "").trim());
}
