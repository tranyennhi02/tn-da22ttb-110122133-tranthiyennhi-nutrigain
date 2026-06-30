import { useState } from "react";
import { SectionLabel } from "./FeatureSection";

const screens = [
  {
    id: "dashboard",
    label: "Dashboard",
    emoji: "📊",
    title: "Dashboard tổng quan",
    desc: "Xem calories, macro và tiến độ ngày hôm nay chỉ trong một màn hình.",
    preview: <DashboardPreview />,
  },
  {
    id: "meal-plan",
    label: "Kế hoạch bữa ăn",
    emoji: "🥗",
    title: "Kế hoạch bữa ăn",
    desc: "Thực đơn 4 bữa cá nhân hóa: sáng, trưa, tối, phụ — đổi món dễ dàng.",
    preview: <MealPlanPreview />,
  },
  {
    id: "charts",
    label: "Theo dõi cân nặng",
    emoji: "📈",
    title: "Theo dõi tăng cân",
    desc: "Cập nhật cân nặng định kỳ và xem xu hướng tăng cân theo dữ liệu thật bạn nhập.",
    preview: <ChartsPreview />,
  },
  {
    id: "journal",
    label: "Nhật ký",
    emoji: "📝",
    title: "Nhật ký ăn uống",
    desc: "Ghi lại từng bữa ăn, đánh dấu đã ăn và xem tổng kết ngày.",
    preview: <JournalPreview />,
  },
];

export default function ProductPreviewSection() {
  const [active, setActive] = useState("dashboard");
  const current = screens.find((s) => s.id === active);

  return (
    <section id="preview" className="py-20 bg-brand-mint sm:py-28">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="text-center">
          <SectionLabel>Giao diện sản phẩm</SectionLabel>
          <h2 className="mt-4 text-3xl font900 text-brand-navy sm:text-4xl">Xem trước các tính năng</h2>
          <p className="mt-4 max-w-xl mx-auto text-lg font600 text-brand-text-sub">Giao diện sạch, trực quan và dễ sử dụng ngay từ lần đầu.</p>
        </div>

        {/* Tab bar */}
        <div className="mt-10 flex flex-wrap justify-center gap-2">
          {screens.map((s) => (
            <button
              key={s.id}
              onClick={() => setActive(s.id)}
              className={`flex items-center gap-2 rounded-2xl border px-5 py-3 text-sm font800 transition ${
                active === s.id
                  ? "border-brand-primary bg-brand-primary text-white shadow-lg shadow-brand-primary/20"
                  : "border-brand-border bg-white text-brand-text-sub hover:border-brand-primary hover:text-brand-primary"
              }`}
            >
              <span>{s.emoji}</span>
              {s.label}
            </button>
          ))}
        </div>

        {/* Preview area */}
        <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_2fr] lg:items-center">
          <div>
            <h3 className="text-2xl font900 text-brand-navy">{current.title}</h3>
            <p className="mt-3 text-base font600 leading-relaxed text-brand-text-sub">{current.desc}</p>
          </div>
          <div className="rounded-3xl border border-brand-border bg-white p-6 shadow-xl shadow-brand-navy/8 overflow-hidden">
            {current.preview}
          </div>
        </div>
      </div>
    </section>
  );
}

function DashboardPreview() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font900 uppercase tracking-widest text-brand-primary">Hôm nay</p>
          <p className="text-2xl font900 text-brand-navy mt-1">1.840 <span className="text-sm text-brand-text-sub">/ 2.203 kcal</span></p>
        </div>
        <span className="rounded-full bg-brand-mint px-4 py-2 text-sm font800 text-brand-primary">83% hoàn thành</span>
      </div>
      <div className="h-3 rounded-full bg-brand-mint overflow-hidden">
        <div className="h-full w-[83%] rounded-full bg-gradient-to-r from-brand-primary to-brand-primary-dark" />
      </div>
      <div className="grid grid-cols-4 gap-3 pt-2">
        {[{ l: "Protein", v: "87g", c: "bg-sky-100 text-sky-700" }, { l: "Carbs", v: "241g", c: "bg-brand-mint text-brand-primary" }, { l: "Fat", v: "58g", c: "bg-orange-100 text-orange-700" }, { l: "BMI", v: "17.4", c: "bg-purple-100 text-purple-700" }].map((m) => (
          <div key={m.l} className={`rounded-2xl p-3 text-center ${m.c}`}>
            <div className="text-lg font900">{m.v}</div>
            <div className="text-xs font700 mt-1">{m.l}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MealPlanPreview() {
  const meals = [
    { name: "Bữa sáng", items: "Yến mạch + Chuối + Sữa", kcal: 520 },
    { name: "Bữa trưa", items: "Cơm + Cá hồi + Rau cải", kcal: 710 },
    { name: "Bữa tối", items: "Mì ý + Bò bằm + Salad", kcal: 680 },
    { name: "Bữa phụ", items: "Bánh mì + Trứng + Phô mai", kcal: 380 },
  ];
  return (
    <div className="space-y-3">
      {meals.map((m) => (
        <div key={m.name} className="flex items-center justify-between rounded-2xl border border-brand-border bg-brand-soft px-4 py-3">
          <div>
            <p className="text-sm font900 text-brand-navy">{m.name}</p>
            <p className="text-xs font600 text-brand-text-sub mt-0.5">{m.items}</p>
          </div>
          <span className="rounded-xl bg-brand-mint px-3 py-1.5 text-xs font900 text-brand-primary">{m.kcal} kcal</span>
        </div>
      ))}
    </div>
  );
}

function ChartsPreview() {
  const bars = [65, 80, 72, 90, 85, 78, 95];
  const days = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];
  return (
    <div>
      <div className="flex items-end justify-between gap-2 h-32">
        {bars.map((h, i) => (
          <div key={i} className="flex flex-1 flex-col items-center gap-1">
            <div className="w-full rounded-xl bg-brand-primary/20 overflow-hidden" style={{ height: "100px" }}>
              <div className="w-full rounded-xl bg-gradient-to-t from-brand-primary to-brand-primary-dark transition-all" style={{ height: `${h}%`, marginTop: `${100 - h}%` }} />
            </div>
            <span className="text-xs font700 text-brand-text-sub">{days[i]}</span>
          </div>
        ))}
      </div>
      <div className="mt-4 flex gap-4 text-xs font800 text-brand-text-sub">
        <span className="flex items-center gap-1.5"><span className="h-2 w-4 rounded-full bg-brand-primary inline-block" />Calories</span>
        <span className="flex items-center gap-1.5"><span className="h-2 w-4 rounded-full bg-brand-orange inline-block" />Protein</span>
      </div>
    </div>
  );
}

function JournalPreview() {
  const entries = [
    { meal: "Bữa sáng", time: "07:30", done: true, kcal: 520 },
    { meal: "Bữa trưa", time: "12:00", done: true, kcal: 710 },
    { meal: "Bữa tối", time: "18:30", done: false, kcal: 680 },
    { meal: "Bữa phụ", time: "21:00", done: false, kcal: 380 },
  ];
  return (
    <div className="space-y-3">
      {entries.map((e) => (
        <div key={e.meal} className={`flex items-center justify-between rounded-2xl border px-4 py-3 ${e.done ? "border-brand-primary/20 bg-brand-mint" : "border-brand-border bg-white"}`}>
          <div className="flex items-center gap-3">
            <div className={`grid h-8 w-8 place-items-center rounded-xl ${e.done ? "bg-brand-primary text-white" : "bg-brand-border text-brand-text-sub"}`}>
              {e.done ? <CheckIcon /> : <ClockIcon />}
            </div>
            <div>
              <p className="text-sm font900 text-brand-navy">{e.meal}</p>
              <p className="text-xs font600 text-brand-text-sub">{e.time}</p>
            </div>
          </div>
          <span className={`text-xs font800 ${e.done ? "text-brand-primary" : "text-brand-text-sub"}`}>{e.kcal} kcal</span>
        </div>
      ))}
    </div>
  );
}

function CheckIcon() {
  return <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m20 6-11 11-5-5" /></svg>;
}
function ClockIcon() {
  return <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></svg>;
}
