import { Download } from "lucide-react";

export default function Header({ title, onExport, onEditProfile, onToggleMenu, showExportReport = false, isExportingReport = false }) {
  const today = new Date().toLocaleDateString("vi-VN", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  });

  return (
    <header className="sticky top-0 z-20 bg-white/80 backdrop-blur-md border-b border-slate-200 shadow-sm">
      <div className="flex h-16 items-center justify-between px-4 sm:px-6 xl:px-8">
        <div className="flex items-center gap-4">
          <button
            className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-slate-100 text-slate-600 lg:hidden hover:bg-slate-200 transition-colors"
            onClick={onToggleMenu}
            aria-label="Mở menu"
            type="button"
          >
            <MenuIcon />
          </button>
          <h1 className="text-xl font-black text-slate-900">{title}</h1>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden rounded-full bg-slate-100 px-4 py-1.5 text-sm font-bold text-slate-600 sm:block shadow-inner">
            {today}
          </div>
          <button className="rounded-full bg-emerald-50 px-4 py-2 text-sm font-bold text-emerald-700 ring-1 ring-emerald-200 hover:bg-emerald-100 hover:text-emerald-800 transition-colors" onClick={onEditProfile} type="button">
            Chỉnh hồ sơ
          </button>
          {showExportReport ? (
            <button className="flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-bold text-white shadow hover:bg-slate-800 transition-colors disabled:opacity-60" onClick={onExport} disabled={isExportingReport} type="button">
              <Download size={16} strokeWidth={2.6} />
              <span className="hidden sm:inline">{isExportingReport ? "Đang xuất..." : "Xuất PDF"}</span>
            </button>
          ) : null}
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
