import { useState } from "react";
import { SectionLabel } from "./FeatureSection";

const faqs = [
  { q: "NutriGain phù hợp với ai?", a: "NutriGain tập trung cho người thiếu cân có BMI dưới 18.5 theo chuẩn Châu Á. Hệ thống không tạo thực đơn tăng cân cho người BMI bình thường, thừa cân hoặc béo phì." },
  { q: "Hệ thống tính calories thế nào?", a: "Chúng tôi dùng công thức Mifflin-St Jeor để tính BMR, nhân hệ số vận động ra TDEE, sau đó cộng thặng dư calo phù hợp với mục tiêu tăng cân của bạn." },
  { q: "Tôi có thể tùy chỉnh thực đơn không?", a: "Có! Bạn có thể thêm món yêu thích, loại bỏ món không thích hoặc dị ứng, đổi món trong kế hoạch, và hệ thống sẽ tạo lại thực đơn phù hợp." },
  { q: "Dữ liệu của tôi có được bảo mật không?", a: "Dữ liệu cá nhân được lưu trữ bảo mật trên server. Chúng tôi không chia sẻ thông tin của bạn với bên thứ ba." },
  { q: "Tôi cần cập nhật cân nặng bao lâu một lần?", a: "Chúng tôi khuyến khích cập nhật cân nặng hàng tuần để hệ thống điều chỉnh calories chính xác và phù hợp với tiến trình của bạn." },
  { q: "Ứng dụng có miễn phí không?", a: "NutriGain hiện đang miễn phí. Bạn chỉ cần tạo tài khoản để sử dụng đầy đủ tính năng." },
];

export default function FAQSection() {
  const [open, setOpen] = useState(null);
  return (
    <section id="faq" className="py-20 bg-white sm:py-28">
      <div className="mx-auto max-w-3xl px-5 sm:px-8">
        <div className="text-center">
          <SectionLabel>FAQ</SectionLabel>
          <h2 className="mt-4 text-3xl font900 text-brand-navy sm:text-4xl">Câu hỏi thường gặp</h2>
          <p className="mt-4 text-lg font600 text-brand-text-sub">Giải đáp những thắc mắc phổ biến về NutriGain.</p>
        </div>
        <div className="mt-12 space-y-3">
          {faqs.map((faq, i) => {
            const isOpen = open === i;
            return (
              <div key={i} className={`rounded-2xl border transition-all ${isOpen ? "border-brand-primary/30 bg-brand-mint" : "border-brand-border bg-white hover:border-brand-primary/20"}`}>
                <button
                  className="flex w-full items-center justify-between px-6 py-5 text-left"
                  onClick={() => setOpen(isOpen ? null : i)}
                >
                  <span className="text-base font800 text-brand-navy">{faq.q}</span>
                  <span className={`ml-4 flex-shrink-0 text-brand-primary transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}>
                    <ChevronIcon />
                  </span>
                </button>
                {isOpen && (
                  <div className="px-6 pb-5">
                    <p className="text-sm font600 leading-relaxed text-brand-text-sub">{faq.a}</p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function ChevronIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}
