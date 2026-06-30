export default function HeroSection({ onShowAuth }) {
  const badges = [
    { icon: "🎯", text: "Cá nhân hóa theo BMI & TDEE" },
    { icon: "🥗", text: "Thực đơn tăng cân khoa học" },
    { icon: "📊", text: "Theo dõi macro & calories" },
  ];
  return (
    <section id="hero" className="relative overflow-hidden bg-brand-mint py-20 sm:py-28">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute -top-32 -left-32 h-96 w-96 rounded-full bg-brand-primary/10 blur-3xl" />
        <div className="absolute -bottom-24 -right-24 h-80 w-80 rounded-full bg-brand-orange/10 blur-3xl" />
      </div>
      <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-5 sm:px-8 lg:grid-cols-2">
        {/* Left */}
        <div className="max-w-xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-brand-primary/20 bg-white px-4 py-2 text-sm font800 text-brand-primary shadow-sm">
            <span className="h-2 w-2 rounded-full bg-brand-primary animate-pulse" />
            Hệ thống dinh dưỡng cá nhân hóa
          </div>
          <h1 className="mt-6 text-4xl font900 leading-[1.15] tracking-tight text-brand-navy sm:text-5xl">
            Tăng cân khoa học,{" "}
            <span className="bg-gradient-to-r from-brand-primary to-brand-primary-dark bg-clip-text text-transparent">
              cá nhân hóa
            </span>{" "}
            và dễ theo dõi mỗi ngày
          </h1>
          <p className="mt-5 text-lg font600 leading-relaxed text-brand-text-sub">
            NutriGain tính BMI, BMR, TDEE và tạo thực đơn tăng cân riêng cho bạn — không cần biết dinh dưỡng, chỉ cần nhập số liệu cơ thể.
          </p>
          <div className="mt-8 flex flex-wrap gap-4">
            <a
              href="#how-it-works"
              className="flex items-center gap-2 rounded-2xl bg-brand-primary px-7 py-4 text-base font800 text-white shadow-xl shadow-brand-primary/25 transition hover:-translate-y-0.5 hover:bg-brand-primary-dark"
            >
              Xem cách hoạt động
              <ArrowIcon />
            </a>
            <a
              href="#features"
              className="flex items-center gap-2 rounded-2xl border border-brand-border bg-white px-7 py-4 text-base font800 text-brand-text-main shadow-sm transition hover:border-brand-primary hover:text-brand-primary"
            >
              Tính năng
              <ArrowIcon />
            </a>
          </div>
          <div className="mt-8 flex flex-wrap gap-3">
            {badges.map((b) => (
              <span key={b.text} className="flex items-center gap-2 rounded-full border border-brand-border bg-white px-4 py-2 text-sm font700 text-brand-text-sub shadow-sm">
                <span>{b.icon}</span>
                {b.text}
              </span>
            ))}
          </div>
        </div>
        {/* Right — dashboard preview */}
        <div className="flex justify-center lg:justify-end">
          <DashboardMockup />
        </div>
      </div>
    </section>
  );
}

function DashboardMockup() {
  return (
    <div className="relative w-full max-w-[500px]">
      {/* Main card */}
      <div className="rounded-3xl border border-brand-border bg-white p-6 shadow-2xl shadow-brand-navy/10">
        <div className="flex items-center justify-between mb-5">
          <div>
            <p className="text-xs font900 uppercase tracking-widest text-brand-primary">Hôm nay</p>
            <p className="text-3xl font900 text-brand-navy mt-1">1.840 <span className="text-sm font700 text-brand-text-sub">/ 2.203 kcal</span></p>
          </div>
          <div className="grid h-14 w-14 place-items-center rounded-2xl bg-brand-mint text-brand-primary">
            <span className="text-2xl">🎯</span>
          </div>
        </div>
        {/* Progress bar */}
        <div className="h-3 rounded-full bg-brand-mint overflow-hidden">
          <div className="h-full w-[83%] rounded-full bg-gradient-to-r from-brand-primary to-brand-primary-dark" />
        </div>
        <div className="mt-5 grid grid-cols-3 gap-3">
          {[
            { label: "Protein", value: "87g", color: "bg-sky-500", pct: "w-3/4" },
            { label: "Carbs", value: "241g", color: "bg-brand-primary", pct: "w-4/5" },
            { label: "Fat", value: "58g", color: "bg-brand-orange", pct: "w-2/3" },
          ].map((m) => (
            <div key={m.label} className="rounded-2xl bg-brand-mint/60 p-3">
              <div className={`h-1.5 w-full rounded-full bg-brand-border overflow-hidden`}>
                <div className={`h-full ${m.pct} rounded-full ${m.color}`} />
              </div>
              <div className="mt-2 text-base font900 text-brand-navy">{m.value}</div>
              <div className="text-xs font700 text-brand-text-sub">{m.label}</div>
            </div>
          ))}
        </div>
        <div className="mt-5 space-y-2">
          {[
            { name: "Bữa sáng", items: "Yến mạch + Chuối + Sữa tươi", kcal: 520 },
            { name: "Bữa trưa", items: "Cơm trắng + Cá hồi + Rau cải", kcal: 710 },
          ].map((meal) => (
            <div key={meal.name} className="flex items-center justify-between rounded-2xl border border-brand-border bg-brand-soft px-4 py-3">
              <div>
                <p className="text-sm font900 text-brand-navy">{meal.name}</p>
                <p className="text-xs font600 text-brand-text-sub mt-0.5">{meal.items}</p>
              </div>
              <span className="rounded-xl bg-brand-mint px-3 py-1 text-xs font800 text-brand-primary">{meal.kcal} kcal</span>
            </div>
          ))}
        </div>
      </div>
      {/* Floating badge */}
      <div className="absolute -top-4 -right-4 flex items-center gap-2 rounded-2xl border border-brand-border bg-white px-4 py-3 shadow-xl">
        <span className="text-xl">📈</span>
        <div>
          <p className="text-xs font900 text-brand-navy">BMI</p>
          <p className="text-lg font900 text-brand-primary">17.4</p>
        </div>
      </div>
      <div className="absolute -bottom-4 -left-4 flex items-center gap-2 rounded-2xl border border-brand-border bg-white px-4 py-3 shadow-xl">
        <span className="text-xl">✅</span>
        <p className="text-sm font800 text-brand-navy">Thực đơn cá nhân hóa</p>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#fff" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#fff" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#fff" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#fff" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14M12 5l7 7-7 7" />
    </svg>
  );
}
