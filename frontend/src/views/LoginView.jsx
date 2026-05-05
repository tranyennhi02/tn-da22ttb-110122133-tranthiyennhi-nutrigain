import { forwardRef, useEffect, useMemo, useRef, useState } from "react";

import { defaultLoginState } from "../models/authModel";

const benefits = [
  "Thực đơn cá nhân hóa",
  "Theo dõi lịch sử bữa ăn",
  "Lưu món yêu thích & đánh giá món ăn",
];

export default function LoginView({ onLogin }) {
  const [loginState, setLoginState] = useState(defaultLoginState);
  const [fieldErrors, setFieldErrors] = useState({});
  const [touched, setTouched] = useState({});
  const [serverError, setServerError] = useState("");
  const [toast, setToast] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const emailInputRef = useRef(null);

  const isRegister = loginState.mode === "register";
  const validationErrors = useMemo(() => validateLogin(loginState, isRegister), [loginState, isRegister]);
  const isFormValid = Object.keys(validationErrors).length === 0;

  useEffect(() => {
    emailInputRef.current?.focus();
  }, []);

  function handleChange(event) {
    const { name, value } = event.target;
    setLoginState((prev) => ({ ...prev, [name]: value }));
    setServerError("");
    setToast("");
    setFieldErrors((prev) => {
      const nextState = { ...loginState, [name]: value };
      const nextErrors = validateLogin(nextState, isRegister);
      return { ...prev, [name]: nextErrors[name] || "" };
    });
  }

  function handleBlur(event) {
    const { name } = event.target;
    setTouched((prev) => ({ ...prev, [name]: true }));
    setFieldErrors((prev) => ({ ...prev, [name]: validationErrors[name] || "" }));
  }

  function switchMode(mode) {
    setLoginState({ ...defaultLoginState, mode });
    setFieldErrors({});
    setTouched({});
    setServerError("");
    setToast("");
    setShowPassword(false);
    requestAnimationFrame(() => emailInputRef.current?.focus());
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const nextErrors = validateLogin(loginState, isRegister);
    setFieldErrors(nextErrors);
    setTouched({ fullName: true, email: true, password: true });
    setServerError("");
    setToast("");

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setIsSubmitting(true);
    try {
      await onLogin(loginState);
      setToast("Đăng nhập thành công!");
    } catch {
      setServerError("Email hoặc mật khẩu không chính xác.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="login-shell relative flex min-h-screen items-center justify-center overflow-hidden px-6 py-8 text-slate-950 sm:px-8 lg:px-12">
      <div className="login-blob login-blob-one" />
      <div className="login-blob login-blob-two" />

      <section className="relative z-10 grid w-full max-w-7xl gap-8 lg:min-h-[760px] lg:grid-cols-[minmax(0,1.08fr)_minmax(420px,0.92fr)] lg:items-stretch">
        <BrandPanel />
        <div className="flex items-center justify-center">
          <LoginCard
            emailInputRef={emailInputRef}
            isRegister={isRegister}
            loginState={loginState}
            showPassword={showPassword}
            isSubmitting={isSubmitting}
            isFormValid={isFormValid}
            errors={fieldErrors}
            touched={touched}
            serverError={serverError}
            toast={toast}
            onBlur={handleBlur}
            onChange={handleChange}
            onSubmit={handleSubmit}
            onTogglePassword={() => setShowPassword((value) => !value)}
            onSwitchMode={switchMode}
          />
        </div>
      </section>
    </main>
  );
}

function BrandPanel() {
  return (
    <aside className="login-brand-panel relative hidden overflow-hidden rounded-[32px] shadow-2xl shadow-green-950/20 lg:flex">
      <img
        className="absolute inset-0 h-full w-full object-cover"
        src="/images/hero-food.png"
        alt="Bữa ăn healthy giàu dinh dưỡng"
      />
      <div className="absolute inset-0 bg-gradient-to-br from-[#02150b]/95 via-[#14532d]/86 to-[#0f172a]/82" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_78%_14%,transparent_0%,rgba(2,6,23,0.28)_42%,rgba(2,6,23,0.68)_100%)]" />

      <div className="relative z-10 flex h-full min-h-[760px] flex-col justify-between p-12 text-white">
        <BrandMark theme="dark" />

        <div className="max-w-2xl">
          <div className="mb-6 inline-flex items-center rounded-full border border-white/25 bg-slate-950/34 px-4 py-2 text-sm font800 text-green-50 shadow-lg shadow-slate-950/20 backdrop-blur-md">
            Nutrition tracking for healthy weight gain
          </div>
          <h1 className="login-brand-title text-5xl font900 leading-tight">
            Tăng cân khoa học, cá nhân hóa cho bạn
          </h1>
          <p className="login-brand-copy mt-5 max-w-xl text-lg font700 leading-8 text-green-50">
            Theo dõi thực đơn, lưu món yêu thích và xây dựng kế hoạch dinh dưỡng phù hợp với mục tiêu của bạn.
          </p>

          <div className="mt-8 grid gap-3">
            {benefits.map((benefit) => (
              <div key={benefit} className="flex items-center gap-3 rounded-2xl border border-white/22 bg-slate-950/34 px-4 py-3 shadow-lg shadow-slate-950/14 backdrop-blur-md">
                <span className="grid h-9 w-9 place-items-center rounded-xl bg-white text-[#166534]">
                  <CheckIcon />
                </span>
                <span className="login-brand-copy font900 text-white">{benefit}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <BrandMetric value="2.203" label="kcal mục tiêu" />
          <BrandMetric value="95g" label="protein" />
          <BrandMetric value="Live" label="tracking" />
        </div>
      </div>
    </aside>
  );
}

function LoginCard({
  emailInputRef,
  isRegister,
  loginState,
  showPassword,
  isSubmitting,
  isFormValid,
  errors,
  touched,
  serverError,
  toast,
  onBlur,
  onChange,
  onSubmit,
  onTogglePassword,
  onSwitchMode,
}) {
  return (
    <section className="login-card w-full max-w-[420px] rounded-[24px] border border-white/80 bg-white p-6 shadow-2xl shadow-slate-900/10 sm:p-8">
      <div className="login-logo-entrance">
        <BrandMark />
      </div>

      <div className="mt-8">
        <h2 className="text-3xl font900 text-[#0F172A]">
          {isRegister ? "Đăng ký" : "Đăng nhập"}
        </h2>
        <p className="mt-2 text-base font600 text-[#64748B]">
          {isRegister ? "Tạo hồ sơ dinh dưỡng của bạn" : "Tiếp tục kế hoạch tăng cân của bạn"}
        </p>
      </div>

      <form className="mt-7 space-y-5" onSubmit={onSubmit} noValidate>
        {isRegister ? (
          <InputField
            id="fullName"
            name="fullName"
            label="Họ tên"
            autoComplete="name"
            placeholder="Nguyễn Văn A"
            value={loginState.fullName}
            error={touched.fullName ? errors.fullName : ""}
            onBlur={onBlur}
            onChange={onChange}
          />
        ) : null}

        <InputField
          ref={emailInputRef}
          id="email"
          name="email"
          type="email"
          label="Email"
          autoComplete="email"
          placeholder="ban@example.com"
          value={loginState.email}
          error={touched.email ? errors.email : ""}
          onBlur={onBlur}
          onChange={onChange}
        />

        <div>
          <PasswordField
            id="password"
            name="password"
            label="Mật khẩu"
            autoComplete={isRegister ? "new-password" : "current-password"}
            placeholder="Tối thiểu 6 ký tự"
            value={loginState.password}
            showPassword={showPassword}
            error={touched.password ? errors.password : ""}
            onBlur={onBlur}
            onChange={onChange}
            onTogglePassword={onTogglePassword}
          />
          {!isRegister ? (
            <div className="mt-2 flex justify-end">
              <button type="button" className="text-sm font800 text-[#2563EB] transition hover:text-[#166534]">
                Quên mật khẩu?
              </button>
            </div>
          ) : null}
        </div>

        {serverError ? (
          <div className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm font700 text-[#EF4444]" role="alert">
            {serverError}
          </div>
        ) : null}

        {toast ? (
          <div className="rounded-2xl border border-green-100 bg-green-50 px-4 py-3 text-sm font800 text-[#166534]" role="status">
            {toast}
          </div>
        ) : null}

        <button
          type="submit"
          className="login-submit-btn flex h-12 w-full items-center justify-center gap-3 rounded-[14px] bg-gradient-to-r from-[#22C55E] to-[#2563EB] px-5 text-base font800 text-white shadow-lg shadow-green-700/20 transition disabled:cursor-not-allowed disabled:opacity-55"
          disabled={!isFormValid || isSubmitting}
        >
          {isSubmitting ? (
            <>
              <span className="login-spinner" aria-hidden="true" />
              Đang đăng nhập...
            </>
          ) : isRegister ? (
            "Đăng ký"
          ) : (
            "Đăng nhập"
          )}
        </button>
      </form>

      <div className="mt-7 text-center text-sm font700 text-[#64748B]">
        {isRegister ? "Đã có tài khoản?" : "Chưa có tài khoản?"}{" "}
        <button
          type="button"
          className="font900 text-[#2563EB] transition hover:text-[#166534]"
          onClick={() => onSwitchMode(isRegister ? "login" : "register")}
        >
          {isRegister ? "Đăng nhập" : "Đăng ký"}
        </button>
      </div>
    </section>
  );
}

const InputField = forwardRef(function InputField(
  { id, name, label, type = "text", value, placeholder, autoComplete, error, onBlur, onChange },
  ref,
) {
  return (
    <div>
      <label htmlFor={id} className="mb-2 block text-sm font800 text-[#0F172A]">
        {label}
      </label>
      <input
        ref={ref}
        id={id}
        name={name}
        type={type}
        value={value}
        placeholder={placeholder}
        autoComplete={autoComplete}
        className={`h-12 w-full rounded-xl border bg-white px-4 text-base font600 text-[#0F172A] outline-none transition placeholder:text-slate-400 focus:border-[#22C55E] focus:ring-4 focus:ring-green-100 ${
          error ? "border-[#EF4444] focus:border-[#EF4444] focus:ring-red-100" : "border-[#CBD5E1]"
        }`}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : undefined}
        onBlur={onBlur}
        onChange={onChange}
      />
      {error ? (
        <p id={`${id}-error`} className="mt-2 text-sm font700 text-[#EF4444]">
          {error}
        </p>
      ) : null}
    </div>
  );
});

function PasswordField({
  id,
  name,
  label,
  value,
  placeholder,
  autoComplete,
  showPassword,
  error,
  onBlur,
  onChange,
  onTogglePassword,
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-2 block text-sm font800 text-[#0F172A]">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          name={name}
          type={showPassword ? "text" : "password"}
          value={value}
          placeholder={placeholder}
          autoComplete={autoComplete}
          className={`h-12 w-full rounded-xl border bg-white px-4 pr-12 text-base font600 text-[#0F172A] outline-none transition placeholder:text-slate-400 focus:border-[#22C55E] focus:ring-4 focus:ring-green-100 ${
            error ? "border-[#EF4444] focus:border-[#EF4444] focus:ring-red-100" : "border-[#CBD5E1]"
          }`}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : undefined}
          onBlur={onBlur}
          onChange={onChange}
        />
        <button
          type="button"
          className="absolute right-3 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-lg text-[#64748B] transition hover:bg-[#DCFCE7] hover:text-[#166534] focus:outline-none focus:ring-4 focus:ring-green-100"
          aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
          onClick={onTogglePassword}
        >
          {showPassword ? <EyeOffIcon /> : <EyeIcon />}
        </button>
      </div>
      {error ? (
        <p id={`${id}-error`} className="mt-2 text-sm font700 text-[#EF4444]">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function BrandMark({ theme = "light" }) {
  const isDark = theme === "dark";
  return (
    <div className="flex items-center gap-3">
      <div className="grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br from-[#22C55E] to-[#2563EB] shadow-lg shadow-green-950/20">
        <LeafIcon />
      </div>
      <div>
        <div className="text-2xl font900 leading-tight">
          <span className={isDark ? "text-white" : "text-[#166534]"}>Nutri</span>
          <span className="text-[#2563EB]">Gain</span>
        </div>
        <div className={`text-xs font900 uppercase tracking-[0.16em] ${isDark ? "text-green-50/80" : "text-[#64748B]"}`}>
          Build Healthy Calories
        </div>
      </div>
    </div>
  );
}

function BrandMetric({ value, label }) {
  return (
    <div className="rounded-2xl border border-white/16 bg-white/12 px-4 py-3 backdrop-blur-md">
      <div className="text-2xl font900 text-white">{value}</div>
      <div className="mt-1 text-xs font800 uppercase text-green-50/75">{label}</div>
    </div>
  );
}

function validateLogin(state, isRegister) {
  const errors = {};
  const email = String(state.email || "").trim();
  const password = String(state.password || "");

  if (isRegister && !String(state.fullName || "").trim()) {
    errors.fullName = "Vui lòng nhập họ tên";
  }

  if (!email) {
    errors.email = "Vui lòng nhập email";
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    errors.email = "Email không hợp lệ";
  }

  if (!password) {
    errors.password = "Vui lòng nhập mật khẩu";
  } else if (password.length < 6) {
    errors.password = "Mật khẩu phải có ít nhất 6 ký tự";
  }

  return errors;
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="m20 6-11 11-5-5" />
    </svg>
  );
}

function LeafIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-7 w-7 text-white" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 4c-8 0-14 5-14 12a4 4 0 0 0 4 4c7 0 10-8 10-16z" />
      <path d="M6 18c3-4 6-6 10-8" />
    </svg>
  );
}

function EyeIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3l18 18" />
      <path d="M10.6 10.6A3 3 0 0 0 13.4 13.4" />
      <path d="M9.9 4.2A10.7 10.7 0 0 1 12 4c6.5 0 10 8 10 8a18 18 0 0 1-2.2 3.3" />
      <path d="M6.6 6.6C3.6 8.5 2 12 2 12s3.5 8 10 8a10.9 10.9 0 0 0 4.9-1.2" />
    </svg>
  );
}
