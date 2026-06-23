import {
  Area,
  AreaChart,
  Bar,
  CartesianGrid,
  ComposedChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function CaloriesChart({ data }) {
  const targetLabel = data?.[0]?.target ? Number(data[0].target).toLocaleString("vi-VN") : "N/A";
  return (
    <section className="glass-panel min-h-[360px] p-5 sm:p-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font900 uppercase tracking-[0.18em] text-brand-primary">
            Biểu đồ calories
          </p>
          <h2 className="mt-2 text-xl font-black text-brand-text-main">Calories theo ngày trong tuần</h2>
        </div>
        <div className="rounded-2xl bg-brand-mint px-4 py-2 text-sm font900 text-brand-primary">
          Mục tiêu {targetLabel} kcal
        </div>
      </div>

      <div className="mt-8 h-[280px] w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ left: 0, right: 16, top: 8, bottom: 0 }}>
            <defs>
              <linearGradient id="calorieArea" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#10b981" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#f1f5f9" strokeDasharray="4 6" vertical={false} />
            <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: "#64748b", fontSize: 12, fontWeight: 700 }} dy={8} />
            <YAxis width={45} axisLine={false} tickLine={false} tick={{ fill: "#94a3b8", fontSize: 12, fontWeight: 600 }} dx={-4} />
            <Tooltip content={<CaloriesTooltip />} cursor={{ fill: "rgba(16,185,129,0.08)" }} />
            <Bar dataKey="target" fill="#e2e8f0" radius={[10, 10, 0, 0]} maxBarSize={32} />
            <Area type="monotone" dataKey="calories" stroke="#10b981" strokeWidth={3} fill="url(#calorieArea)" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function CaloriesTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const calories = payload.find((item) => item.dataKey === "calories")?.value;
  const target = payload.find((item) => item.dataKey === "target")?.value;

  return (
    <div className="rounded-2xl border border-brand-border bg-brand-surface px-4 py-3 text-sm shadow-2xl shadow-brand-navy/10">
      <div className="font900 text-brand-text-main">{label}</div>
      <div className="mt-1 font800 text-brand-primary">{calories} kcal đã ăn</div>
      <div className="font700 text-brand-text-sub">{target} kcal mục tiêu</div>
    </div>
  );
}
