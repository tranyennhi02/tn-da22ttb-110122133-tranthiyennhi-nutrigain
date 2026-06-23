const features = [
  {
    emoji: "👤",
    title: "Cá nhân hóa hồ sơ",
    desc: "Nhập chiều cao, cân nặng, tuổi và mức vận động. Hệ thống tự tính BMI, BMR và TDEE chính xác.",
    color: "bg-sky-50 border-sky-100",
    iconBg: "bg-sky-100 text-sky-600",
  },
  {
    emoji: "🥗",
    title: "Tạo thực đơn tăng cân",
    desc: "Thực đơn 3 bữa/ngày được cá nhân hóa dựa trên mục tiêu, chế độ ăn và ngân sách của bạn.",
    color: "bg-brand-mint border-brand-primary/20",
    iconBg: "bg-brand-primary/10 text-brand-primary",
  },
  {
    emoji: "📊",
    title: "Theo dõi tiến độ tăng cân",
    desc: "Cập nhật cân nặng định kỳ và xem xu hướng tăng, giữ nguyên hoặc giảm theo từng lần ghi nhận.",
    color: "bg-orange-50 border-orange-100",
    iconBg: "bg-orange-100 text-brand-orange",
  },
  {
    emoji: "❤️",
    title: "Nhật ký & món yêu thích",
    desc: "Lưu món ăn yêu thích, đánh dấu đã ăn và xây dựng thói quen ăn uống lành mạnh mỗi ngày.",
    color: "bg-purple-50 border-purple-100",
    iconBg: "bg-purple-100 text-purple-600",
  },
];

export default function FeatureSection() {
  return (
    <section id="features" className="py-20 bg-white sm:py-28">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <SectionLabel>Tính năng</SectionLabel>
        <h2 className="mt-4 text-3xl font900 text-brand-navy sm:text-4xl">Mọi thứ bạn cần để tăng cân lành mạnh</h2>
        <p className="mt-4 max-w-2xl text-lg font600 text-brand-text-sub">
          NutriGain tích hợp công cụ dinh dưỡng thông minh giúp bạn đạt mục tiêu cân nặng một cách khoa học và bền vững.
        </p>
        <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((f) => (
            <div key={f.title} className={`rounded-3xl border p-6 transition hover:-translate-y-1 hover:shadow-xl ${f.color}`}>
              <div className={`grid h-14 w-14 place-items-center rounded-2xl text-2xl ${f.iconBg}`}>{f.emoji}</div>
              <h3 className="mt-5 text-lg font900 text-brand-navy">{f.title}</h3>
              <p className="mt-2 text-sm font600 leading-relaxed text-brand-text-sub">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function SectionLabel({ children }) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-brand-primary/20 bg-brand-mint px-4 py-2 text-sm font800 text-brand-primary">
      <span className="h-1.5 w-1.5 rounded-full bg-brand-primary" />
      {children}
    </div>
  );
}
