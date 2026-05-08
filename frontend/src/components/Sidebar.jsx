import NutriGainLogo from "./NutriGainLogo";

const menuItems = [
  { id: "overview", label: "Tổng quan", icon: DashboardIcon },
  { id: "journal", label: "Nhật ký ăn uống", icon: JournalIcon },
  { id: "charts", label: "Biểu đồ", icon: ChartIcon },
  { id: "meal-plan", label: "Kế hoạch bữa ăn", icon: MealIcon },
  { id: "account", label: "Tài khoản", icon: UserIcon },
  { id: "notifications", label: "Thông báo", icon: BellIcon },
  { id: "help", label: "Hỗ trợ", icon: HelpIcon },
];

export default function Sidebar({
  userEmail,
  isOpen = false,
  activeSection = "overview",
  onClose,
  onNavigate,
  onLogout,
}) {
  const initials = (userEmail || "NG").slice(0, 2).toUpperCase();

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-brand-border bg-brand-mint shadow-2xl shadow-brand-navy/10 backdrop-blur-2xl transition-transform duration-300 lg:translate-x-0 ${
        isOpen ? "translate-x-0" : "-translate-x-full"
      }`}
    >
      <div className="flex items-center justify-between px-5 pb-4 pt-5">
        <NutriGainLogo size="sm" />
        <button
          className="grid h-10 w-10 place-items-center rounded-xl bg-white text-brand-text-sub shadow-sm lg:hidden"
          onClick={onClose}
          aria-label="Đóng menu"
        >
          <CloseIcon />
        </button>
      </div>

      <nav className="sidebar-scroll flex-1 px-3 pb-5">
        <div className="mb-3 px-4 text-xs font900 uppercase tracking-[0.18em] text-brand-text-sub">
          Workspace
        </div>
        <div className="space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;
            return (
              <button
                key={item.id}
                type="button"
                className={`group flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-sm font900 transition ${
                  isActive
                    ? "bg-brand-navy text-white shadow-xl shadow-brand-navy/20"
                    : "text-brand-text-sub hover:bg-white hover:text-brand-navy hover:shadow-sm"
                }`}
                onClick={() => onNavigate?.(item.id)}
              >
                <span
                  className={`grid h-9 w-9 place-items-center rounded-xl transition ${
                    isActive ? "bg-brand-primary text-white" : "bg-white text-brand-primary shadow-sm"
                  }`}
                >
                  <Icon />
                </span>
                <span className="min-w-0 flex-1 truncate">{item.label}</span>
              </button>
            );
          })}
        </div>
      </nav>

      <div className="m-4 rounded-3xl border border-white/80 bg-brand-surface p-4 shadow-xl shadow-brand-navy/8">
        <div className="flex items-center gap-3">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br from-brand-primary to-brand-primary-dark text-sm font-black text-white shadow-lg shadow-brand-navy/20">
            {initials}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font900 text-brand-text-main">{userEmail || "user@nutrigain.vn"}</p>
            <div className="mt-1 flex items-center gap-2 text-xs font800 text-brand-primary">
              <span className="h-2 w-2 rounded-full bg-brand-primary shadow-[0_0_0_4px_rgba(16,185,129,0.14)]" />
              Live Tracking
            </div>
          </div>
        </div>
        <button
          type="button"
          className="mt-4 flex h-11 w-full items-center justify-center gap-2 rounded-2xl bg-brand-primary px-4 text-sm font900 text-white transition hover:bg-brand-primary-dark"
          onClick={onLogout}
        >
          <LogoutIcon />
          Đăng xuất
        </button>
      </div>
    </aside>
  );
}

function IconBase({ children }) {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      {children}
    </svg>
  );
}

function DashboardIcon() {
  return <IconBase><path d="M4 13h7V4H4z" /><path d="M13 20h7V4h-7z" /><path d="M4 20h7v-5H4z" /></IconBase>;
}

function JournalIcon() {
  return <IconBase><path d="M7 4h10a2 2 0 0 1 2 2v14H7a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z" /><path d="M9 8h6" /><path d="M9 12h5" /></IconBase>;
}

function ChartIcon() {
  return <IconBase><path d="M4 19V5" /><path d="M4 19h16" /><path d="M8 15l3-4 3 2 4-6" /></IconBase>;
}

function MealIcon() {
  return <IconBase><path d="M6 3v18" /><path d="M10 3v7a4 4 0 0 1-8 0V3" /><path d="M18 3v18" /><path d="M18 3c2 2 3 4 3 7s-1 5-3 7" /></IconBase>;
}

function FoodIcon() {
  return <IconBase><path d="M12 21c4-3 7-7 7-11a7 7 0 1 0-14 0c0 4 3 8 7 11z" /><path d="M12 10h.01" /></IconBase>;
}

function UserIcon() {
  return <IconBase><path d="M20 21a8 8 0 0 0-16 0" /><path d="M12 13a5 5 0 1 0 0-10 5 5 0 0 0 0 10z" /></IconBase>;
}

function SettingsIcon() {
  return <IconBase><path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2 3.4-.2-.1a1.8 1.8 0 0 0-1.9-.3 1.8 1.8 0 0 0-1.1 1.6V22H9.4v-.3A1.8 1.8 0 0 0 8.3 20a1.8 1.8 0 0 0-1.9.3l-.2.1-2-3.4.1-.1A1.7 1.7 0 0 0 4.6 15 1.8 1.8 0 0 0 3 13.9h-.3V10h.3a1.8 1.8 0 0 0 1.6-1.1 1.7 1.7 0 0 0-.3-1.9l-.1-.1 2-3.4.2.1a1.8 1.8 0 0 0 1.9.3A1.8 1.8 0 0 0 9.4 2.3V2h5.2v.3A1.8 1.8 0 0 0 15.7 4a1.8 1.8 0 0 0 1.9-.3l.2-.1 2 3.4-.1.1a1.7 1.7 0 0 0-.3 1.9A1.8 1.8 0 0 0 21 10h.3v3.9H21a1.8 1.8 0 0 0-1.6 1.1z" /></IconBase>;
}

function BellIcon() {
  return <IconBase><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 7h18s-3 0-3-7" /><path d="M13.7 21a2 2 0 0 1-3.4 0" /></IconBase>;
}

function HelpIcon() {
  return <IconBase><path d="M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z" /><path d="M9.1 9a3 3 0 1 1 5.8 1c-.8 1.1-2 1.5-2.4 2.8" /><path d="M12 17h.01" /></IconBase>;
}

function CloseIcon() {
  return <IconBase><path d="M18 6 6 18" /><path d="m6 6 12 12" /></IconBase>;
}

function LogoutIcon() {
  return <IconBase><path d="M10 17l5-5-5-5" /><path d="M15 12H3" /><path d="M21 3v18" /></IconBase>;
}
