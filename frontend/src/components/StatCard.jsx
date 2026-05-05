const toneMap = {
  green: "from-emerald-500 to-teal-500 text-white",
  navy: "from-slate-950 to-navy text-white",
  blue: "from-sky-500 to-cyan-500 text-white",
  orange: "from-orange-400 to-amber-400 text-white",
  sky: "from-white to-sky-50 text-slate-950",
  amber: "from-white to-orange-50 text-slate-950",
  emerald: "from-white to-emerald-50 text-slate-950",
  mint: "from-white to-teal-50 text-slate-950",
};

export default function StatCard({ label, value, unit, tone = "mint" }) {
  const isDark = ["green", "navy", "blue", "orange"].includes(tone);

  return (
    <article
      className={`group overflow-hidden rounded-3xl border border-white/80 bg-gradient-to-br ${
        toneMap[tone] || toneMap.mint
      } p-5 shadow-xl shadow-slate-900/8 transition duration-300 hover:-translate-y-1 hover:shadow-2xl`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className={`text-sm font900 uppercase tracking-[0.12em] ${isDark ? "text-white/72" : "text-slate-500"}`}>
            {label}
          </p>
          <div className="mt-4 flex items-end gap-2">
            <strong className="text-3xl font-black leading-none tracking-[-0.03em] sm:text-4xl">
              {typeof value === "number" ? value.toLocaleString("vi-VN") : value}
            </strong>
            {unit ? (
              <span className={`max-w-[8rem] pb-1 text-sm font900 leading-tight ${isDark ? "text-white/76" : "text-slate-500"}`}>
                {unit}
              </span>
            ) : null}
          </div>
        </div>
        <div className={`h-12 w-12 rounded-2xl ${isDark ? "bg-white/14" : "bg-white"} shadow-sm`} />
      </div>
      <div className={`mt-5 h-2 overflow-hidden rounded-full ${isDark ? "bg-white/16" : "bg-slate-100"}`}>
        <div className={`h-full w-3/4 rounded-full ${isDark ? "bg-white" : "bg-emerald-400"}`} />
      </div>
    </article>
  );
}
