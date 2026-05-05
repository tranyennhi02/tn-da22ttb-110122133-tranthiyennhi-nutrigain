import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

const COLORS = ["#0ea5e9", "#fb923c", "#10b981"];

export default function MacroChart({ data, compact = false }) {
  const pieData = [
    { name: "Protein", value: data.protein, unit: "g" },
    { name: "Fat", value: data.fat, unit: "g" },
    { name: "Carbs", value: data.carbs, unit: "g" },
  ];
  const total = pieData.reduce((sum, item) => sum + item.value, 0);

  return (
    <section className={`glass-panel ${compact ? "p-5" : "min-h-[360px] p-5 sm:p-6"}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">
            Macro
          </p>
          <h2 className="mt-2 text-xl font-black text-slate-950">
            Protein / Fat / Carbs
          </h2>
        </div>
        <div className="rounded-2xl bg-slate-950 px-3 py-2 text-sm font900 text-white">
          {total}g
        </div>
      </div>

      <div className={`${compact ? "h-[190px]" : "mt-6 h-[220px]"}`}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={pieData}
              dataKey="value"
              innerRadius={compact ? 52 : 68}
              outerRadius={compact ? 78 : 98}
              paddingAngle={5}
              cornerRadius={14}
              stroke="none"
            >
              {pieData.map((entry, index) => (
                <Cell key={entry.name} fill={COLORS[index]} />
              ))}
            </Pie>
            <Tooltip content={<MacroTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-3 gap-2">
        {pieData.map((item, index) => (
          <div key={item.name} className="rounded-2xl bg-white/80 p-3 text-center ring-1 ring-slate-100">
            <div className="mx-auto h-2 w-9 rounded-full" style={{ backgroundColor: COLORS[index] }} />
            <div className="mt-2 text-lg font-black text-slate-950">
              {item.value}
              <span className="text-xs text-slate-500">g</span>
            </div>
            <div className="text-xs font800 text-slate-500">{item.name}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function MacroTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const item = payload[0].payload;
  return (
    <div className="rounded-2xl border border-slate-100 bg-white px-4 py-3 text-sm shadow-2xl shadow-slate-900/10">
      <div className="font900 text-slate-950">{item.name}</div>
      <div className="font800 text-emerald-700">{item.value}{item.unit}</div>
    </div>
  );
}
