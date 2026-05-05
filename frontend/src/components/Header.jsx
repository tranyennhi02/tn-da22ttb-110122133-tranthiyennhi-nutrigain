export default function Header({ title, onExport, onEditProfile, onToggleMenu }) {
  const today = new Date().toLocaleDateString("vi-VN", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  });

  return (
    <header className="sticky top-0 z-20 border-b border-white/60 bg-white/72 px-4 py-4 backdrop-blur-2xl sm:px-6 xl:px-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <button
            className="grid h-11 w-11 place-items-center rounded-2xl bg-slate-950 text-white shadow-lg shadow-slate-900/10 lg:hidden"
            onClick={onToggleMenu}
            aria-label="Mở menu"
          >
            <MenuIcon />
          </button>
          <div>
            <div className="text-xs font800 uppercase tracking-[0.18em] text-emerald-700">
              NutriGain Dashboard
            </div>
            <h1 className="mt-1 text-2xl font-black tracking-[-0.02em] text-slate-950 sm:text-3xl">
              {title}
            </h1>
          </div>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm font800 text-emerald-800">
            {today}
          </div>
          <button
            className="h-12 rounded-2xl border border-slate-200 bg-white px-5 text-sm font900 text-slate-800 shadow-sm transition hover:border-emerald-200 hover:text-emerald-800"
            onClick={onEditProfile}
          >
            Chỉnh hồ sơ
          </button>
          <button
            className="h-12 rounded-2xl bg-accent px-5 text-sm font900 text-white shadow-lg shadow-orange-500/20 transition hover:bg-orange-500"
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
