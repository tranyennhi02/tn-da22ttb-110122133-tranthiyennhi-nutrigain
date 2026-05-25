import { Download } from "lucide-react";

export default function Header({ title, onExport, onEditProfile, onToggleMenu, showExportReport = false, isExportingReport = false }) {
  const today = new Date().toLocaleDateString("vi-VN", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  });

  return (
    <header className="app-topbar account-header sticky top-0 z-20">
      <div className="app-topbar-inner account-header-inner">
        <div className="topbar-heading">
          <button
            className="topbar-menu-button grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-[#081832] text-white shadow-lg shadow-slate-900/10 lg:hidden"
            onClick={onToggleMenu}
            aria-label="Mở menu"
            type="button"
          >
            <MenuIcon />
          </button>
          <h1 className="topbar-title account-header-title">{title}</h1>
        </div>

        <div className="topbar-actions account-header-actions">
          <div className="topbar-date account-date-pill">{today}</div>
          <button className="topbar-button account-header-btn secondary" onClick={onEditProfile} type="button">
            Chỉnh hồ sơ
          </button>
          {showExportReport ? (
            <button className="topbar-button account-header-btn export" onClick={onExport} disabled={isExportingReport} type="button">
              <Download size={16} strokeWidth={2.6} />
              <span>{isExportingReport ? "Đang xuất..." : "Xuất báo cáo"}</span>
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
