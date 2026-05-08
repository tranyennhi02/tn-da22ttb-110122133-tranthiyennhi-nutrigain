const toneMap = {
  green: "from-brand-primary to-brand-primary-dark text-white",
  navy: "from-brand-navy to-brand-primary-dark text-white",
  blue: "from-sky-500 to-cyan-500 text-white",
  orange: "from-brand-orange to-brand-orange text-white",
  sky: "from-white to-sky-50 text-brand-text-main",
  amber: "from-white to-brand-cream text-brand-text-main",
  emerald: "from-white to-brand-mint text-brand-text-main",
  mint: "from-white to-brand-soft text-brand-text-main",
};

export default function StatCard({ label, value, unit, tone = "mint" }) {
  const isDark = ["green", "navy", "blue", "orange"].includes(tone);

  return (
    <article
      className={`group overflow-hidden rounded-3xl border border-brand-border bg-gradient-to-br ${
        toneMap[tone] || toneMap.mint
      } p-5 shadow-xl shadow-brand-navy/8 transition duration-300 hover:-translate-y-1 hover:shadow-2xl`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className={`text-sm font900 uppercase tracking-[0.12em] ${isDark ? "text-white/72" : "text-brand-text-sub"}`}>
            {label}
          </p>
          <div className="mt-4 flex items-end gap-2">
            <strong className="text-3xl font-black leading-none tracking-[-0.03em] sm:text-4xl">
              {typeof value === "number" ? value.toLocaleString("vi-VN") : value}
            </strong>
            {unit ? (
              <span className={`max-w-[8rem] pb-1 text-sm font900 leading-tight ${isDark ? "text-white/76" : "text-brand-text-sub"}`}>
                {unit}
              </span>
            ) : null}
          </div>
        </div>
        <div className={`h-12 w-12 rounded-2xl ${isDark ? "bg-white/14" : "bg-white"} shadow-sm`} />
      </div>
      <div className={`mt-5 h-2 overflow-hidden rounded-full ${isDark ? "bg-white/16" : "bg-brand-soft"}`}>
        <div className={`h-full w-3/4 rounded-full ${isDark ? "bg-white" : "bg-brand-primary"}`} />
      </div>
    </article>
  );
}
