import { Calendar, Download } from "lucide-react";
import { pageHeaderStyles } from "./PageHeader";

export default function Header({
  title,
  variant = "default",
  onExport,
  onEditProfile,
  onToggleMenu,
  showExportReport = false,
  isExportingReport = false,
}) {
  const today = new Date().toLocaleDateString("vi-VN", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  });

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200/70 bg-[rgba(255,255,255,0.92)] shadow-[0_8px_24px_rgba(15,23,42,0.04)] backdrop-blur-xl">
      <div className="flex min-h-[68px] items-center justify-between gap-4 px-4 py-4 sm:px-6 xl:px-8">
        <div className="flex items-center gap-4">
          <button
            className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl border border-slate-200 bg-white text-slate-600 shadow-sm lg:hidden hover:bg-slate-50 transition-colors"
            onClick={onToggleMenu}
            aria-label="Mở menu"
            type="button"
          >
            <MenuIcon />
          </button>
          <div className="min-w-0">
            <p className={pageHeaderStyles.eyebrowClass}>NutriGain</p>
            <h1 className="mt-1 text-[clamp(1.2rem,2vw,1.8rem)] font-black tracking-[-0.03em] text-slate-950">{title}</h1>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3">
          <div className={`${pageHeaderStyles.dateClass} hidden sm:inline-flex`}>
            <Calendar className="h-4 w-4 text-emerald-600" />
            {today}
          </div>
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
