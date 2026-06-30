const surfaceClass = "rounded-[28px] border border-slate-200/70 bg-[rgba(255,255,255,0.92)] shadow-[0_8px_24px_rgba(15,23,42,0.04)] backdrop-blur-xl";
const eyebrowClass = "text-[11px] font-black uppercase tracking-[0.18em] text-emerald-700";
const titleClass = "text-[clamp(1.9rem,3vw,2.8rem)] font-black leading-[1.06] tracking-[-0.04em] text-slate-950";
const subtitleClass = "max-w-3xl text-[15px] font-semibold leading-7 text-slate-600 sm:text-[16px]";
const badgeClass = "inline-flex items-center rounded-full border border-emerald-100 bg-emerald-50 px-3.5 py-1.5 text-[13px] font-black text-emerald-800";
const dateClass = "inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-4 py-2.5 text-[14px] font-bold text-slate-600 shadow-sm";
const buttonBaseClass = "inline-flex min-h-11 items-center justify-center rounded-full px-4 text-[14px] font-black transition focus:outline-none focus:ring-4 focus:ring-emerald-100";

export const pageHeaderStyles = {
  surfaceClass,
  eyebrowClass,
  titleClass,
  subtitleClass,
  badgeClass,
  dateClass,
  buttonBaseClass,
};

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  badges = [],
  date,
  actions,
  children,
  compact = false,
  className = "",
}) {
  const resolvedDate = date || new Date().toLocaleDateString("vi-VN", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  });

  return (
    <section className={`${surfaceClass} ${compact ? "px-4 py-4 sm:px-5 sm:py-5" : "px-5 py-5 sm:px-6 sm:py-6"} ${className}`}>
      <div className={`flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between ${compact ? "lg:gap-6" : "lg:gap-8"}`}>
        <div className="min-w-0 max-w-3xl">
          {eyebrow ? <p className={eyebrowClass}>{eyebrow}</p> : null}
          <h1 className={`${titleClass} ${eyebrow ? "mt-2" : ""}`}>{title}</h1>
          {subtitle ? <p className={`mt-3 ${subtitleClass}`}>{subtitle}</p> : null}
          {badges.length > 0 ? (
            <div className="mt-4 flex flex-wrap gap-2.5">
              {badges.map((badge) => (
                <span key={typeof badge === "string" ? badge : badge?.label} className={badgeClass}>
                  {typeof badge === "string" ? badge : badge?.label}
                </span>
              ))}
            </div>
          ) : null}
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-stretch lg:min-w-[320px] lg:flex-col lg:items-end">
          <div className={dateClass}>
            <CalendarIcon className="h-4 w-4 text-emerald-600" />
            <span className="hidden sm:inline">{resolvedDate}</span>
            <span className="sm:hidden">{shortDateLabel(resolvedDate)}</span>
          </div>
          {actions ? <div className="flex flex-wrap gap-3 lg:justify-end">{actions}</div> : null}
        </div>
      </div>

      {children ? <div className="mt-5">{children}</div> : null}
    </section>
  );
}

export function PageHeaderButton({ variant = "secondary", className = "", children, ...props }) {
  const variantClass = {
    primary: "bg-emerald-600 text-white shadow-[0_12px_28px_rgba(16,185,129,0.22)] hover:bg-emerald-700 hover:shadow-[0_16px_34px_rgba(16,185,129,0.28)]",
    secondary: "border border-emerald-200 bg-white text-emerald-700 hover:bg-emerald-50 hover:border-emerald-300",
    ghost: "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-900",
  }[variant] || "border border-emerald-200 bg-white text-emerald-700 hover:bg-emerald-50 hover:border-emerald-300";

  return (
    <button
      type="button"
      className={`${buttonBaseClass} h-11 gap-2 border px-4 ${variantClass} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function PageHeaderStat({ label, value, description, tone = "neutral" }) {
  const toneClass = {
    neutral: "border-slate-200 bg-white",
    emerald: "border-emerald-100 bg-emerald-50/60",
    teal: "border-teal-100 bg-teal-50/60",
    amber: "border-amber-100 bg-amber-50/70",
  }[tone] || "border-slate-200 bg-white";

  return (
    <div className={`rounded-[22px] border px-4 py-3 shadow-sm ${toneClass}`}>
      <p className="text-[11px] font-black uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <div className="mt-2 text-2xl font-black text-slate-950">{value}</div>
      {description ? <p className="mt-1 text-sm font-semibold leading-6 text-slate-600">{description}</p> : null}
    </div>
  );
}

function CalendarIcon({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="4" width="18" height="18" rx="4" />
      <path d="M8 2v4" />
      <path d="M16 2v4" />
      <path d="M3 10h18" />
    </svg>
  );
}

function shortDateLabel(value) {
  const date = new Date();
  if (Number.isNaN(date.getTime())) return value;
  return value
    .replace("thứ hai", "T2")
    .replace("thứ ba", "T3")
    .replace("thứ tư", "T4")
    .replace("thứ năm", "T5")
    .replace("thứ sáu", "T6")
    .replace("thứ bảy", "T7")
    .replace("chủ nhật", "CN");
}