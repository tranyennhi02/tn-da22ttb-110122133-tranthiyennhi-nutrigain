import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, Cell, LabelList } from "recharts";

export default function EnergyChart({ bmr, tdee }) {
  const data = [
    { label: "BMR (Cơ bản)", value: bmr || 0, color: "#10B981" },
    { label: "TDEE (Tổng)", value: tdee || 0, color: "#0F766E" },
  ];

  return (
    <section className="bg-white rounded-[24px] shadow-sm border border-slate-200 p-6 lg:p-8 mt-6 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-50 rounded-full blur-3xl -mr-20 -mt-20 opacity-60 z-0 pointer-events-none" />
      <div className="relative z-10 flex flex-col md:flex-row gap-8 items-center lg:items-start">
        
        <div className="w-full md:w-1/3 flex flex-col justify-center">
          <div className="inline-flex items-center gap-2 mb-3">
            <span className="bg-orange-100 text-orange-700 text-[10px] font-bold px-2.5 py-1 uppercase rounded-md tracking-wider flex items-center gap-1">
              <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Năng lượng nền
            </span>
          </div>
          <h2 className="text-2xl font-black text-slate-900 tracking-tight">So sánh BMR và TDEE</h2>
          <p className="mt-3 text-sm font-semibold text-slate-500 leading-relaxed">
            Hiểu rõ lượng calo cơ thể bạn thực sự sử dụng để phục vụ quá trình trao đổi chất (BMR) và các hoạt động trong ngày (TDEE).
          </p>
          
          <div className="mt-6 flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-sm bg-[#10B981]" />
              <div className="text-sm">
                <span className="font-extrabold text-slate-700">{bmr}</span> <span className="font-medium text-slate-500">kcal (BMR)</span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-sm bg-[#0F766E]" />
              <div className="text-sm">
                <span className="font-extrabold text-slate-700">{tdee}</span> <span className="font-medium text-slate-500">kcal (TDEE)</span>
              </div>
            </div>
          </div>
        </div>

        <div className="w-full md:w-2/3 h-[240px] md:h-[280px] min-w-0">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ left: 0, right: 16, top: 24, bottom: 0 }} barCategoryGap="20%">
              <CartesianGrid stroke="#f1f5f9" strokeDasharray="4 4" vertical={false} />
              <XAxis 
                dataKey="label" 
                axisLine={false} 
                tickLine={false} 
                tick={{ fill: "#64748B", fontWeight: 700, fontSize: 13 }} 
                dy={12}
              />
              <YAxis 
                width={45}
                axisLine={false} 
                tickLine={false} 
                tick={{ fill: "#94a3b8", fontSize: 12, fontWeight: 600 }} 
                dx={-4}
              />
              <Tooltip 
                cursor={{ fill: "rgba(241,245,249,0.5)" }} 
                contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)", fontWeight: 700 }}
                itemStyle={{ color: "#0F172A", fontWeight: 900 }}
              />
              <Bar dataKey="value" radius={[8, 8, 0, 0]} maxBarSize={80}>
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
                <LabelList dataKey="value" position="top" fill="#475569" fontSize={13} fontWeight={900} formatter={(v) => `${v} kcal`} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

      </div>
    </section>
  );
}
