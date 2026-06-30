import { useMemo, useState } from "react";

import NutriGainLogo from "../components/NutriGainLogo";
import { resetPassword } from "../services/authService";

export default function ResetPasswordView({ onBackToLogin, onForgotPassword }) {
  const token = useMemo(() => new URLSearchParams(window.location.search).get("token") || "", []);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(token ? "" : "Liên kết đặt lại mật khẩu không hợp lệ.");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!token) {
      setError("Liên kết đặt lại mật khẩu không hợp lệ.");
      return;
    }
    if (newPassword.length < 8) {
      setError("Mật khẩu mới cần có ít nhất 8 ký tự.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Mật khẩu xác nhận không khớp.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await resetPassword({ token, newPassword, confirmPassword });
      setMessage(response?.message || "Đặt lại mật khẩu thành công.");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(err.message || "Không thể đặt lại mật khẩu lúc này.");
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
            <h1 className="text-2xl font900 text-brand-navy">Đặt lại mật khẩu</h1>
            <p className="mt-1 text-sm font600 text-brand-text-sub">Tạo mật khẩu mới cho tài khoản của bạn.</p>
          </div>

          <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
            <PasswordField label="Mật khẩu mới" value={newPassword} onChange={setNewPassword} disabled={!token || Boolean(message)} />
            <PasswordField label="Xác nhận mật khẩu mới" value={confirmPassword} onChange={setConfirmPassword} disabled={!token || Boolean(message)} />

            {error && (
              <div className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm font700 text-red-600">
                {error}
              </div>
            )}
            {message && (
              <div className="rounded-2xl border border-brand-primary/20 bg-brand-mint px-4 py-3 text-sm font800 text-brand-primary">
                {message}
              </div>
            )}

            {!message ? (
              <button
                type="submit"
                disabled={isSubmitting || !token}
                className="flex h-12 w-full items-center justify-center rounded-2xl bg-brand-primary text-sm font900 text-white shadow-lg shadow-brand-primary/20 transition hover:bg-brand-primary-dark disabled:cursor-not-allowed disabled:opacity-55"
              >
                {isSubmitting ? <span className="flex items-center gap-2"><Spinner />Đang cập nhật...</span> : "Đặt lại mật khẩu"}
              </button>
            ) : (
              <button
                type="button"
                onClick={onBackToLogin}
                className="flex h-12 w-full items-center justify-center rounded-2xl bg-brand-primary text-sm font900 text-white shadow-lg shadow-brand-primary/20 transition hover:bg-brand-primary-dark"
              >
                Quay về đăng nhập
              </button>
            )}

            {error && !message && (
              <button
                type="button"
                onClick={onForgotPassword}
                className="h-11 w-full rounded-2xl border border-brand-border bg-white text-sm font900 text-brand-text-main transition hover:border-brand-primary hover:text-brand-primary"
              >
                Gửi lại hướng dẫn
              </button>
            )}
          </form>
        </div>
      </div>
    </div>
  );
}

function PasswordField({ label, value, onChange, disabled }) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font800 text-brand-text-main">{label}</label>
      <input
        type="password"
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Tối thiểu 8 ký tự"
        className="h-12 w-full rounded-xl border border-brand-border bg-white px-4 text-sm font600 text-brand-text-main outline-none transition placeholder:text-brand-text-sub focus:border-brand-primary focus:ring-4 focus:ring-brand-primary/10 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
      />
    </div>
  );
}

function Spinner() {
  return <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />;
}
