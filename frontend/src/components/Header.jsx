import NutriGainLogo from "./NutriGainLogo";

export default function Header({ title, onExport, onEditProfile, onToggleMenu }) {
  const today = new Date().toLocaleDateString("vi-VN", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  });

  return (
    <header className="sticky top-0 z-20 border-b border-brand-border bg-brand-surface/86 px-4 py-4 shadow-sm shadow-brand-navy/5 backdrop-blur-2xl sm:px-6 xl:px-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <button
            className="grid h-11 w-11 place-items-center rounded-2xl bg-brand-navy text-white shadow-lg shadow-brand-navy/10 lg:hidden"
            onClick={onToggleMenu}
            aria-label="Mở menu"
          >
            <MenuIcon />
          </button>
          <div>
            <div className="flex items-center gap-2 text-xs font800 uppercase tracking-[0.14em] text-brand-primary">
              <NutriGainLogo size="sm" showText={false} />
              <span>NutriGain</span>
            </div>
            <h1 className="mt-1 text-2xl font-black text-brand-text-main sm:text-3xl">
              {title}
            </h1>
          </div>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="rounded-2xl border border-brand-border bg-brand-mint px-4 py-3 text-sm font800 text-brand-primary">
            {today}
          </div>
          <button
            className="h-12 rounded-2xl border border-brand-border bg-brand-surface px-5 text-sm font900 text-brand-text-main shadow-sm transition hover:border-brand-primary hover:text-brand-primary"
            onClick={onEditProfile}
          >
            Chỉnh hồ sơ
          </button>
          <button
            className="h-12 rounded-2xl bg-brand-orange px-5 text-sm font900 text-white shadow-lg shadow-brand-orange/20 transition hover:bg-brand-orange-dark"
            onClick={onExport}
          >
            Xuất báo cáo
          </button>
        </div>
      </div>
    </header>
  );
}

function MenuIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M4 7h16" />
      <path d="M4 12h16" />
      <path d="M4 17h16" />
    </svg>
  );
}
