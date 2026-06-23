import { useState } from "react";

import NutriGainLogo from "../components/NutriGainLogo";
import { forgotPassword } from "../services/authService";

const GENERIC_MESSAGE = "Nếu email tồn tại, hướng dẫn đặt lại mật khẩu đã được gửi.";

export default function ForgotPasswordView({ onBackToLogin }) {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setError("Email không hợp lệ.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await forgotPassword(email);
      setMessage(response?.message || GENERIC_MESSAGE);
    } catch (err) {
      setError("Không thể gửi yêu cầu lúc này. Vui lòng thử lại.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-brand-mint">
      <div className="border-b border-brand-border bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8">
          <button onClick={onBackToLogin} className="text-sm font800 text-brand-text-sub transition hover:text-brand-primary">
            Quay về đăng nhập
          </button>
          <NutriGainLogo size="sm" />
        </div>
      </div>

      <div className="flex min-h-[calc(100vh-65px)] items-center justify-center px-5 py-12">
        <div className="w-full max-w-[440px] rounded-[28px] border border-brand-border bg-white p-8 shadow-2xl shadow-brand-navy/10">
          <NutriGainLogo size="sm" />
          <div className="mt-7">
            <h1 className="text-2xl font900 text-brand-navy">Quên mật khẩu</h1>
            <p className="mt-1 text-sm font600 text-brand-text-sub">Nhập email tài khoản NutriGain của bạn.</p>
          </div>

          <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
            <div>
              <label className="mb-1.5 block text-sm font800 text-brand-text-main">Email</label>
              <input
                type="email"
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value);
                  setError("");
                }}
                placeholder="ban@example.com"
                className={`h-12 w-full rounded-xl border bg-white px-4 text-sm font600 text-brand-text-main outline-none transition placeholder:text-brand-text-sub focus:ring-4 focus:ring-brand-primary/10 ${
                  error ? "border-red-400 focus:border-red-400" : "border-brand-border focus:border-brand-primary"
                }`}
              />
              {error && <p className="mt-1.5 text-xs font700 text-red-500">{error}</p>}
            </div>

            {message && (
              <div className="rounded-2xl border border-brand-primary/20 bg-brand-mint px-4 py-3 text-sm font800 text-brand-primary">
                {message}
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="flex h-12 w-full items-center justify-center rounded-2xl bg-brand-primary text-sm font900 text-white shadow-lg shadow-brand-primary/20 transition hover:bg-brand-primary-dark disabled:cursor-not-allowed disabled:opacity-55"
            >
              {isSubmitting ? <span className="flex items-center gap-2"><Spinner />Đang gửi...</span> : "Gửi hướng dẫn đặt lại mật khẩu"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

function Spinner() {
  return <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />;
}
