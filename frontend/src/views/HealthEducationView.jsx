import { BookOpen, Flame, Sparkles, Target, UtensilsCrossed } from "lucide-react";
import HealthLessonVisual from "../components/health/HealthLessonVisual";

const quickTopics = [
  {
    title: "Ăn đều",
    text: "Chia bữa hợp lý để cơ thể có năng lượng ổn định hơn.",
    icon: Flame,
  },
  {
    title: "Đạm đủ",
    text: "Protein giúp phục hồi và hỗ trợ tăng cân bền hơn.",
    icon: Target,
  },
  {
    title: "Ngủ đủ",
    text: "Giấc ngủ tốt giúp nhịp chăm sóc cơ thể đều đặn hơn.",
    icon: BookOpen,
  },
];

const mythFactCards = [
  {
    tone: "myth",
    label: "Hiểu lầm",
    title: "Ăn càng nhiều càng tốt",
    text: "Tăng cân bền vững cần đủ năng lượng, đủ đạm và nhịp ăn đều.",
  },
  {
    tone: "fact",
    label: "Sự thật",
    title: "Tăng từ từ sẽ chắc hơn",
    text: "Đi từng bước nhỏ giúp cơ thể thích nghi và duy trì thói quen lâu hơn.",
  },
];

const learningProgress = [
  { title: "Tăng cân lành mạnh", done: true },
  { title: "Protein là gì?", done: true },
  { title: "Ngủ đủ quan trọng", done: true },
  { title: "Hiểu lầm về tăng cân", done: false },
];

export default function HealthEducationView({ userEmail }) {
  const doneCount = learningProgress.filter((item) => item.done).length;
  const progressPercent = Math.round((doneCount / learningProgress.length) * 100);
  return (
    <div className="space-y-6">
      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
        <div className="rounded-[32px] border border-white/80 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)] sm:p-8">
          <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">Bài học hôm nay</p>
          <h2 className="mt-2 text-3xl font-black leading-tight text-slate-950 sm:text-4xl">Ăn đều, ngủ đủ, tăng cân từ từ</h2>
          <p className="mt-3 max-w-2xl text-sm font800 leading-7 text-slate-600 sm:text-base">
            Mỗi bài học được rút gọn để bạn đọc nhanh, hiểu nhanh và áp dụng ngay vào nhịp chăm sóc của mình.
          </p>

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            {quickTopics.map((topic) => {
              const Icon = topic.icon;
              return (
                <article key={topic.title} className="rounded-3xl border border-slate-100 bg-slate-50 p-4">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-emerald-600 shadow-sm ring-1 ring-slate-100">
                    <Icon size={20} strokeWidth={2.4} />
                  </div>
                  <h3 className="mt-3 text-sm font900 text-slate-950">{topic.title}</h3>
                  <p className="mt-1 text-sm font700 leading-6 text-slate-500">{topic.text}</p>
                </article>
              );
            })}
          </div>

          <div className="mt-6 rounded-[28px] border border-emerald-100 bg-emerald-50/70 p-5">
            <div className="flex items-center gap-2 text-emerald-700">
              <Sparkles size={18} strokeWidth={2.4} />
              <p className="text-xs font900 uppercase tracking-[0.18em]">Nhịp học nhanh</p>
            </div>
            <p className="mt-2 text-sm font800 leading-6 text-slate-700">
              1) Ăn đều hơn một chút. 2) Giữ đủ đạm ở mỗi bữa. 3) Theo dõi cảm giác cơ thể sau vài ngày.
            </p>
          </div>
        </div>

        <div className="rounded-[32px] border border-white/80 bg-white/90 p-5 shadow-[0_18px_60px_rgba(15,23,42,0.08)] sm:p-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">Tiến độ học tập</p>
              <h3 className="mt-1 text-xl font-black text-slate-950">Đã hoàn thành {doneCount}/{learningProgress.length} mục</h3>
            </div>
            <div className="rounded-2xl bg-slate-950 px-4 py-3 text-right text-white">
              <div className="text-2xl font-black">{progressPercent}%</div>
              <div className="text-xs font800 uppercase tracking-[0.16em] text-white/70">learning</div>
            </div>
          </div>

          <div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-lime-400" style={{ width: `${progressPercent}%` }} />
          </div>

          <div className="mt-5 space-y-3">
            {learningProgress.map((item) => (
              <div key={item.title} className="flex items-center gap-3 rounded-2xl bg-slate-50 px-4 py-3">
                <div className={`flex h-9 w-9 items-center justify-center rounded-2xl text-sm font900 ${item.done ? "bg-emerald-100 text-emerald-700" : "bg-white text-slate-400 ring-1 ring-slate-100"}`}>
                  {item.done ? "✓" : "•"}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font900 text-slate-950">{item.title}</p>
                  <p className="text-xs font700 text-slate-500">{item.done ? "Đã xem qua" : "Chưa mở"}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <HealthLessonVisual lessonId="healthy-weight-gain" title="Tăng cân lành mạnh" />

        <div className="space-y-6">
          <div className="rounded-[32px] border border-white/80 bg-white/90 p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
            <div className="flex items-center gap-2 text-emerald-700">
              <UtensilsCrossed size={18} strokeWidth={2.4} />
              <p className="text-xs font900 uppercase tracking-[0.18em]">Chủ đề học nhanh</p>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {quickTopics.map((topic) => (
                <span key={topic.title} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-sm font900 text-slate-700">
                  {topic.title}
                </span>
              ))}
              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font900 text-emerald-700">Nhịp chăm sóc hôm nay</span>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {mythFactCards.map((card) => (
              <article key={card.title} className={`rounded-[28px] border p-5 ${card.tone === "myth" ? "border-amber-100 bg-amber-50/70" : "border-emerald-100 bg-emerald-50/70"}`}>
                <p className={`text-xs font900 uppercase tracking-[0.18em] ${card.tone === "myth" ? "text-amber-700" : "text-emerald-700"}`}>{card.label}</p>
                <h3 className="mt-2 text-lg font-black text-slate-950">{card.title}</h3>
                <p className="mt-2 text-sm font700 leading-6 text-slate-600">{card.text}</p>
              </article>
            ))}
          </div>

          <div className="rounded-[28px] border border-slate-100 bg-slate-50 p-6">
            <p className="text-xs font900 uppercase tracking-[0.18em] text-slate-500">Ghi nhớ</p>
            <p className="mt-2 text-sm font800 leading-7 text-slate-700">
              Tiến bộ không cần hoàn hảo. Chỉ cần đều đặn hơn một chút.
            </p>
            {userEmail ? (
              <p className="mt-3 text-xs font800 text-slate-500">Đang xem dưới tài khoản {userEmail}</p>
            ) : null}
          </div>
        </div>
      </section>
    </div>
  );
}
