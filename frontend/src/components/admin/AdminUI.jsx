export function cx(...classes) {
  return classes.filter(Boolean).join(" ");
}

const iconPaths = {
  overview: "M3 13h8V3H3v10Zm0 8h8v-6H3v6Zm10 0h8V11h-8v10Zm0-18v6h8V3h-8Z",
  users:
    "M16 11a4 4 0 1 0-2.98-6.67M8 13a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm0 2c-3.31 0-6 1.79-6 4v1h12v-1c0-2.21-2.69-4-6-4Zm8-1c-.71 0-1.38.08-2 .24 1.2.86 2 2.02 2 3.36V20h6v-1c0-2.21-2.69-5-6-5Z",
  foods:
    "M6 3v7a4 4 0 0 0 3 3.87V21h2v-7.13A4 4 0 0 0 14 10V3h-2v7h-1V3H9v7H8V3H6Zm12 0c-1.66 0-3 1.79-3 4v6h2v8h2V3h-1Z",
  image:
    "M4 5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5Zm3 11 3.2-3.2a1 1 0 0 1 1.42 0L14 15l1.2-1.2a1 1 0 0 1 1.42 0L19 16.17V5H6v11h1Zm10-7.5A1.5 1.5 0 1 0 17 5a1.5 1.5 0 0 0 0 3Z",
  test:
    "M9 3h6v2l-1 1v3.4l4.66 7.76A2.5 2.5 0 0 1 16.51 21H7.49a2.5 2.5 0 0 1-2.15-3.84L10 9.4V6L9 5V3Zm2.12 8L8 16.2h8L12.88 11h-1.76Z",
  meal: "M7 3h10a2 2 0 0 1 2 2v16l-7-3-7 3V5a2 2 0 0 1 2-2Zm1 4h8v2H8V7Zm0 4h8v2H8v-2Z",
  errors:
    "M12 2 1.8 20h20.4L12 2Zm1 14h-2v2h2v-2Zm0-7h-2v5h2V9Z",
  settings:
    "M19.43 12.98c.04-.32.07-.65.07-.98s-.02-.66-.07-.98l2.11-1.65-2-3.46-2.49 1a7.14 7.14 0 0 0-1.69-.98L15 3.25h-4l-.36 2.68c-.6.24-1.17.56-1.69.98l-2.49-1-2 3.46 2.11 1.65c-.04.32-.07.65-.07.98s.02.66.07.98l-2.11 1.65 2 3.46 2.49-1c.52.4 1.09.73 1.69.98L11 20.75h4l.36-2.68c.6-.25 1.17-.58 1.69-.98l2.49 1 2-3.46-2.11-1.65ZM13 15.5A3.5 3.5 0 1 1 13 8a3.5 3.5 0 0 1 0 7.5Z",
  search:
    "M10.5 3a7.5 7.5 0 0 1 5.95 12.06l4.24 4.25-1.42 1.41-4.24-4.24A7.5 7.5 0 1 1 10.5 3Zm0 2a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11Z",
  refresh:
    "M17.65 6.35A8 8 0 1 0 20 12h-2a6 6 0 1 1-1.76-4.24L13 11h8V3l-3.35 3.35Z",
  close:
    "M6.4 5 12 10.6 17.6 5 19 6.4 13.4 12 19 17.6 17.6 19 12 13.4 6.4 19 5 17.6 10.6 12 5 6.4 6.4 5Z",
  chevron: "M9.29 6.71 13.88 11.3 9.29 15.89 10.7 17.3 16.7 11.3 10.7 5.3 9.29 6.71Z",
  edit:
    "M4 17.25V21h3.75L18.81 9.94l-3.75-3.75L4 17.25ZM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83Z",
  check: "M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17Z",
  lock:
    "M17 8h-1V6a4 4 0 0 0-8 0v2H7a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-9a2 2 0 0 0-2-2Zm-7-2a2 2 0 0 1 4 0v2h-4V6Z",
  logout:
    "M10 17v-3H3v-4h7V7l5 5-5 5Zm2-14h8a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1h-8v-2h7V5h-7V3Z",
};

export function Icon({ name, className = "h-5 w-5" }) {
  const path = iconPaths[name] || iconPaths.overview;
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" fill="currentColor">
      <path d={path} />
    </svg>
  );
}

const toneClasses = {
  blue: "bg-blue-50 text-blue-700 border-blue-100",
  emerald: "bg-emerald-50 text-emerald-700 border-emerald-100",
  amber: "bg-amber-50 text-amber-700 border-amber-100",
  red: "bg-red-50 text-red-700 border-red-100",
  slate: "bg-slate-50 text-slate-700 border-slate-200",
  violet: "bg-violet-50 text-violet-700 border-violet-100",
};

export function AdminBadge({ tone = "slate", children, className = "" }) {
  return (
    <span className={cx("inline-flex h-7 max-w-full items-center gap-1 rounded-full border px-3 text-xs font-semibold leading-none", toneClasses[tone] || toneClasses.slate, className)}>
      {children}
    </span>
  );
}

export function AdminStatusPill({ status, children }) {
  const normalized = String(status || "").toLowerCase();
  let tone = "slate";
  if (["active", "valid", "success", "resolved", "verified_real", "real"].includes(normalized)) tone = "emerald";
  if (["minor_adjustment", "pending", "pexels_pending", "warning"].includes(normalized)) tone = "amber";
  if (["locked", "major_adjustment", "invalid", "error", "failed", "critical", "unresolved"].includes(normalized)) tone = "red";
  if (["admin", "super_admin", "info"].includes(normalized)) tone = "blue";
  return <AdminBadge tone={tone}>{children || status || "Không rõ"}</AdminBadge>;
}

export function AdminButton({ children, icon, variant = "primary", className = "", ...props }) {
  const variants = {
    primary: "bg-blue-600 text-white hover:bg-blue-700 shadow-[0_8px_18px_rgba(37,99,235,0.18)]",
    success: "bg-emerald-600 text-white hover:bg-emerald-700 shadow-[0_8px_18px_rgba(16,185,129,0.16)]",
    danger: "bg-red-600 text-white hover:bg-red-700 shadow-[0_8px_18px_rgba(239,68,68,0.14)]",
    subtle: "border border-slate-200 bg-white text-slate-700 shadow-sm shadow-slate-200/50 hover:bg-slate-50",
    ghost: "bg-transparent text-slate-600 hover:bg-slate-100",
  };
  return (
    <button
      type="button"
      className={cx(
        "inline-flex h-10 items-center justify-center gap-2 rounded-xl px-4 text-sm font-semibold transition duration-150 disabled:cursor-not-allowed disabled:opacity-60",
        variants[variant] || variants.primary,
        className
      )}
      {...props}
    >
      {icon ? <Icon name={icon} className="h-4 w-4" /> : null}
      {children}
    </button>
  );
}

export function AdminPageHeader({ title, description, actions, eyebrow }) {
  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div className="min-w-0">
        {eyebrow ? <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-600">{eyebrow}</p> : null}
        <h1 className="mt-2 truncate text-[28px] font-extrabold leading-tight tracking-tight text-slate-950 sm:text-[32px]">{title}</h1>
        {description ? <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function AdminStatCard({ label, value, helper, icon = "overview", tone = "blue", trend }) {
  const iconTone = {
    blue: "bg-blue-50 text-blue-600 ring-blue-100",
    emerald: "bg-emerald-50 text-emerald-600 ring-emerald-100",
    amber: "bg-amber-50 text-amber-600 ring-amber-100",
    red: "bg-red-50 text-red-600 ring-red-100",
    violet: "bg-violet-50 text-violet-600 ring-violet-100",
    slate: "bg-slate-100 text-slate-600 ring-slate-200",
  }[tone] || "bg-blue-50 text-blue-600 ring-blue-100";
  return (
    <div className="rounded-[20px] bg-white p-6 shadow-[0_8px_24px_rgba(15,23,42,0.06)] ring-1 ring-slate-200/70">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="truncate text-[13px] font-semibold text-slate-500">{label}</p>
          <p className="mt-4 text-[38px] font-extrabold leading-none tracking-tight text-slate-950">{value}</p>
        </div>
        <span className={cx("flex h-12 w-12 shrink-0 items-center justify-center rounded-full ring-1", iconTone)}>
          <Icon name={icon} className="h-5 w-5" />
        </span>
      </div>
      <div className="mt-4 flex items-center justify-between gap-3">
        {helper ? <p className="min-w-0 truncate text-[13px] font-medium text-slate-500" title={helper}>{helper}</p> : <span />}
        {trend ? <AdminBadge tone={trend.tone || "slate"}>{trend.label}</AdminBadge> : null}
      </div>
    </div>
  );
}

export function AdminSectionCard({ title, description, actions, children, className = "" }) {
  return (
    <section className={cx("rounded-[20px] bg-white p-6 shadow-[0_8px_24px_rgba(15,23,42,0.06)] ring-1 ring-slate-200/70", className)}>
      {(title || description || actions) && (
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            {title ? <h2 className="text-lg font-bold tracking-tight text-slate-950">{title}</h2> : null}
            {description ? <p className="mt-1 text-sm leading-5 text-slate-500">{description}</p> : null}
          </div>
          {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
        </div>
      )}
      {children}
    </section>
  );
}

export function AdminFilterChips({ items, value, onChange }) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => {
        const active = item.value === value;
        return (
          <button
            type="button"
            key={item.value}
            onClick={() => onChange(item.value)}
            className={cx(
              "inline-flex h-10 items-center gap-2 rounded-full border px-4 text-sm font-semibold transition",
              active
                ? "border-blue-200 bg-blue-50 text-blue-700 shadow-sm shadow-blue-100/70"
                : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50"
            )}
          >
            <span>{item.label}</span>
            {item.count !== undefined ? <span className="rounded-full bg-white/80 px-2 py-0.5 text-xs text-slate-500">{item.count}</span> : null}
          </button>
        );
      })}
    </div>
  );
}

export function AdminDataTable({ columns, children, empty, minWidth = "780px" }) {
  const rows = Array.isArray(children) ? children.filter(Boolean) : children;
  const hasRows = Array.isArray(rows) ? rows.length > 0 : Boolean(rows);
  return (
    <div className="overflow-hidden rounded-[20px] bg-white shadow-[0_8px_24px_rgba(15,23,42,0.06)] ring-1 ring-slate-200/70">
      <div className="overflow-x-auto">
        <table className="w-full text-left" style={{ minWidth }}>
          <thead className="bg-[#F8FAFC]">
            <tr>
              {columns.map((column) => (
                <th key={column.key || column.label} className={cx("px-5 py-3.5 text-[12px] font-bold uppercase tracking-wide text-slate-400", column.align === "right" && "text-right", column.align === "center" && "text-center")}>
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">{hasRows ? rows : null}</tbody>
        </table>
      </div>
      {!hasRows ? <div className="p-4">{empty || <AdminEmptyState />}</div> : null}
    </div>
  );
}

export function AdminDrawer({ open, onClose, title, subtitle, children, footer, width = "max-w-[520px]" }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end overflow-hidden">
      <button type="button" aria-label="Đóng" className="absolute inset-0 bg-slate-950/35 backdrop-blur-sm" onClick={onClose} />
      <aside className={cx("relative flex h-full w-full flex-col bg-white shadow-2xl", width)}>
        <header className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-100 bg-white/95 px-6 py-5 backdrop-blur">
          <div className="min-w-0">
            <h3 className="truncate text-lg font-extrabold text-slate-900">{title}</h3>
            {subtitle ? <p className="mt-1 truncate text-sm text-slate-500">{subtitle}</p> : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-500 transition hover:bg-slate-200 hover:text-slate-800"
            aria-label="Đóng"
          >
            <Icon name="close" className="h-4 w-4" />
          </button>
        </header>
        <div className="flex-1 overflow-y-auto px-6 py-6">{children}</div>
        {footer ? <footer className="sticky bottom-0 border-t border-slate-100 bg-white/95 px-6 py-4 backdrop-blur">{footer}</footer> : null}
      </aside>
    </div>
  );
}

export function AdminEmptyState({ title = "Chưa có dữ liệu", description = "Không có bản ghi phù hợp với bộ lọc hiện tại.", icon = "overview", actions }) {
  return (
    <div className="flex min-h-[220px] flex-col items-center justify-center rounded-[20px] bg-[#F8FAFC] px-6 py-8 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-white text-slate-400 shadow-sm ring-1 ring-slate-200">
        <Icon name={icon} className="h-6 w-6" />
      </span>
      <h3 className="mt-4 text-base font-bold text-slate-900">{title}</h3>
      <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">{description}</p>
      {actions ? <div className="mt-4 flex flex-wrap justify-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function AdminLoadingSkeleton({ rows = 5, cards = 0 }) {
  return (
    <div className="space-y-5">
      {cards > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: cards }).map((_, index) => (
            <div key={index} className="h-36 animate-pulse rounded-[20px] bg-white shadow-[0_8px_24px_rgba(15,23,42,0.06)] ring-1 ring-slate-200/70">
              <div className="h-full rounded-[20px] bg-gradient-to-r from-slate-100 via-slate-50 to-slate-100" />
            </div>
          ))}
        </div>
      ) : null}
      <div className="rounded-[20px] bg-white p-5 shadow-[0_8px_24px_rgba(15,23,42,0.06)] ring-1 ring-slate-200/70">
        <div className="space-y-3">
          {Array.from({ length: rows }).map((_, index) => (
            <div key={index} className="h-12 animate-pulse rounded-2xl bg-slate-100" />
          ))}
        </div>
      </div>
    </div>
  );
}

export function AdminQuickActionCard({ title, description, icon = "chevron", tone = "blue", onClick }) {
  const toneClass = {
    blue: "text-blue-600 bg-blue-50",
    emerald: "text-emerald-600 bg-emerald-50",
    amber: "text-amber-600 bg-amber-50",
    red: "text-red-600 bg-red-50",
  }[tone] || "text-blue-600 bg-blue-50";
  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex min-h-[112px] flex-col justify-between rounded-[20px] bg-white p-5 text-left shadow-[0_8px_24px_rgba(15,23,42,0.06)] ring-1 ring-slate-200/70 transition hover:-translate-y-0.5 hover:shadow-[0_14px_34px_rgba(15,23,42,0.08)]"
    >
      <span className={cx("flex h-11 w-11 items-center justify-center rounded-full", toneClass)}>
        <Icon name={icon} className="h-5 w-5" />
      </span>
      <span>
        <span className="flex items-center justify-between gap-3 text-sm font-bold text-slate-900">
          {title}
          <Icon name="chevron" className="h-4 w-4 text-slate-300 transition group-hover:text-slate-500" />
        </span>
        <span className="mt-1 block text-[13px] leading-5 text-slate-500">{description}</span>
      </span>
    </button>
  );
}
