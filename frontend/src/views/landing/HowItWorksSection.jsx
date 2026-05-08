import { SectionLabel } from "./FeatureSection";

const steps = [
  { num: "01", emoji: "📝", title: "Nhập hồ sơ", desc: "Điền chiều cao, cân nặng, tuổi, giới tính và mức độ vận động hàng ngày." },
  { num: "02", emoji: "🧮", title: "Tính BMI / BMR / TDEE", desc: "Hệ thống tự động tính chỉ số cơ thể và nhu cầu calo cá nhân hóa." },
  { num: "03", emoji: "🥗", title: "Tạo thực đơn", desc: "Nhận thực đơn tăng cân 4 bữa/ngày phù hợp với mục tiêu và khẩu vị." },
  { num: "04", emoji: "📈", title: "Theo dõi mỗi ngày", desc: "Đánh dấu đã ăn, xem biểu đồ macro và cập nhật cân nặng định kỳ." },
];

export default function HowItWorksSection() {
  return (
    <section id="how-it-works" className="py-20 bg-brand-mint sm:py-28">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <SectionLabel>Cách hoạt động</SectionLabel>
        <h2 className="mt-4 text-3xl font900 text-brand-navy sm:text-4xl">Chỉ 4 bước để bắt đầu</h2>
        <p className="mt-4 max-w-xl text-lg font600 text-brand-text-sub">Không cần kiến thức dinh dưỡng chuyên sâu. NutriGain làm hết phần khó, bạn chỉ cần làm theo.</p>
        <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((s, i) => (
            <div key={s.num} className="relative rounded-3xl border border-brand-border bg-white p-7 shadow-sm">
              {i < steps.length - 1 && (
                <div className="absolute top-10 -right-3 hidden h-0.5 w-6 bg-brand-primary/30 lg:block" />
              )}
              <div className="text-xs font900 uppercase tracking-widest text-brand-primary">{s.num}</div>
              <div className="mt-3 text-4xl">{s.emoji}</div>
              <h3 className="mt-4 text-lg font900 text-brand-navy">{s.title}</h3>
              <p className="mt-2 text-sm font600 leading-relaxed text-brand-text-sub">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
