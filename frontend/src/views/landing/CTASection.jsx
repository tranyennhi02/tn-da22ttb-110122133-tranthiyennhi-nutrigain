export default function CTASection({ onShowAuth }) {
  return (
    <section id="cta" className="py-20 sm:py-28">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="relative overflow-hidden rounded-[32px] bg-gradient-to-br from-brand-navy to-brand-primary-dark px-8 py-16 text-center shadow-2xl sm:px-16">
          {/* bg blobs */}
          <div className="absolute -top-20 -right-20 h-64 w-64 rounded-full bg-brand-primary/20 blur-3xl pointer-events-none" />
          <div className="absolute -bottom-16 -left-16 h-56 w-56 rounded-full bg-brand-orange/15 blur-3xl pointer-events-none" />

          <div className="relative z-10">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-2 text-sm font800 text-brand-mint backdrop-blur-sm">
              <span className="h-2 w-2 rounded-full bg-brand-primary animate-pulse" />
              Hoàn toàn miễn phí để bắt đầu
            </div>
            <h2 className="mt-6 text-3xl font900 text-white sm:text-4xl">
              Sẵn sàng bắt đầu hành trình tăng cân?
            </h2>
            <p className="mt-4 max-w-xl mx-auto text-lg font600 leading-relaxed text-brand-mint/90">
              Tham gia cùng hàng nghìn người đang sử dụng NutriGain để xây dựng lộ trình dinh dưỡng cá nhân hóa.
            </p>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
              <a
                href="#features"
                className="rounded-2xl bg-white px-8 py-4 text-base font900 text-brand-navy shadow-xl transition hover:-translate-y-0.5 hover:shadow-2xl"
              >
                Khám phá tính năng
              </a>
              <a
                href="#how-it-works"
                className="rounded-2xl border border-white/30 px-8 py-4 text-base font800 text-white backdrop-blur-sm transition hover:bg-white/10"
              >
                Cách hoạt động
              </a>
            </div>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-6 text-sm font700 text-brand-mint/80">
              <span>✓ Không cần thẻ ngân hàng</span>
              <span>✓ Bảo mật dữ liệu</span>
              <span>✓ Cập nhật liên tục</span>
            </div>
          </div>
        </div>
        {/* Footer */}
        <div className="mt-12 flex flex-col items-center gap-3 text-center text-sm font700 text-brand-text-sub">
          <div className="flex items-center gap-2">
            <div className="grid h-7 w-7 place-items-center rounded-xl bg-gradient-to-br from-brand-primary to-brand-primary-dark">
              <LeafIcon />
            </div>
            <span className="font900"><span className="text-brand-primary">Nutri</span><span className="text-brand-navy">Gain</span></span>
          </div>
          <p>© 2026 NutriGain. Build Healthy Calories.</p>
        </div>
      </div>
    </section>
  );
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

function LeafIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 text-white" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 4c-8 0-14 5-14 12a4 4 0 0 0 4 4c7 0 10-8 10-16z" />
      <path d="M6 18c3-4 6-6 10-8" />
    </svg>
  );
}
