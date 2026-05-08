import { useState } from "react";
import NutriGainLogo from "../../components/NutriGainLogo";

export default function PublicHeader({ onShowAuth }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const navLinks = [
    { label: "Trang chủ", href: "#hero" },
    { label: "Tính năng", href: "#features" },
    { label: "Cách hoạt động", href: "#how-it-works" },
    { label: "FAQ", href: "#faq" },
    { label: "Liên hệ", href: "#cta" },
  ];
  return (
    <header className="sticky top-0 z-50 border-b border-brand-border bg-white/90 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8">
        <BrandMark />
        <nav className="hidden items-center gap-6 lg:flex">
          {navLinks.map((l) => (
            <a key={l.label} href={l.href} className="text-sm font700 text-brand-text-sub transition hover:text-brand-primary">
              {l.label}
            </a>
          ))}
        </nav>
        <div className="hidden items-center gap-3 lg:flex">
          <button onClick={() => onShowAuth("login")} className="rounded-xl border border-brand-border px-5 py-2.5 text-sm font800 text-brand-text-main transition hover:border-brand-primary hover:text-brand-primary">
            Đăng nhập
          </button>
          <button onClick={() => onShowAuth("register")} className="rounded-xl bg-brand-primary px-5 py-2.5 text-sm font800 text-white shadow-lg shadow-brand-primary/20 transition hover:bg-brand-primary-dark">
            Bắt đầu miễn phí
          </button>
        </div>
        <button className="grid h-10 w-10 place-items-center rounded-xl border border-brand-border lg:hidden" onClick={() => setMenuOpen(!menuOpen)}>
          <MenuIcon />
        </button>
      </div>
      {menuOpen && (
        <div className="border-t border-brand-border bg-white px-5 pb-5 pt-3 lg:hidden">
          {navLinks.map((l) => (
            <a key={l.label} href={l.href} onClick={() => setMenuOpen(false)} className="block py-2.5 text-sm font700 text-brand-text-sub hover:text-brand-primary">
              {l.label}
            </a>
          ))}
          <div className="mt-4 flex flex-col gap-3">
            <button onClick={() => { setMenuOpen(false); onShowAuth("login"); }} className="rounded-xl border border-brand-border py-3 text-sm font800 text-brand-text-main">Đăng nhập</button>
            <button onClick={() => { setMenuOpen(false); onShowAuth("register"); }} className="rounded-xl bg-brand-primary py-3 text-sm font800 text-white">Bắt đầu miễn phí</button>
          </div>
        </div>
      )}
    </header>
  );
}

function BrandMark() {
  return <NutriGainLogo size="sm" />;
}

function MenuIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  );
}
