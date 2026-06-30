export default function AccountPanel({ email }) {
  const initials = (email || "NG").slice(0, 2).toUpperCase();

  return (
    <section id="account-panel" className="glass-panel p-5">
      <div className="flex items-center gap-4">
        <div className="grid h-16 w-16 place-items-center rounded-3xl bg-gradient-to-br from-brand-primary to-sys-info text-lg font-black text-white shadow-lg shadow-brand-navy/20">
          {initials}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font900 text-brand-text-main">{email || "user@nutrigain.vn"}</p>
          <p className="mt-1 text-sm font700 text-brand-text-sub">Premium nutrition profile</p>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3">
        <div className="rounded-2xl bg-brand-mint p-4">
          <div className="text-xs font900 uppercase tracking-[0.12em] text-brand-primary">Status</div>
          <div className="mt-2 flex items-center gap-2 text-sm font900 text-brand-text-main">
            <span className="h-2.5 w-2.5 rounded-full bg-brand-primary" />
            Live
          </div>
        </div>
        <div className="rounded-2xl bg-brand-cream p-4">
          <div className="text-xs font900 uppercase tracking-[0.12em] text-brand-orange">Plan</div>
          <div className="mt-2 text-sm font900 text-brand-text-main">Gain</div>
        </div>
      </div>
    </section>
  );
}
