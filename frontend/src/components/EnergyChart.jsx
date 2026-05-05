import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function EnergyChart({ bmr, tdee }) {
  const data = [
    { label: "BMR", value: bmr },
    { label: "TDEE", value: tdee },
  ];

  return (
    <section className="glass-panel min-h-[260px] p-5 sm:p-6">
      <div>
        <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">
          Năng lượng nền
        </p>
        <h2 className="mt-2 text-xl font-black text-slate-950">So sánh BMR và TDEE</h2>
      </div>
      <div className="mt-5 h-[190px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ left: -16, right: 8, top: 8, bottom: 0 }}>
            <CartesianGrid stroke="#dbeafe" strokeDasharray="4 6" vertical={false} />
            <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fill: "#475569", fontWeight: 900 }} />
            <YAxis axisLine={false} tickLine={false} tick={{ fill: "#94a3b8", fontSize: 12, fontWeight: 700 }} />
            <Tooltip cursor={{ fill: "rgba(15,118,110,0.08)" }} />
            <Bar dataKey="value" fill="#0f766e" radius={[18, 18, 8, 8]} barSize={56} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
