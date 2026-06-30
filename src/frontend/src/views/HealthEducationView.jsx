import { 
  HeartPulse, 
  TrendingUp, 
  Utensils, 
  Apple, 
  Moon, 
  ShieldCheck, 
  Dumbbell, 
  Sparkles, 
  Play, 
  CheckCircle2, 
  XCircle, 
  Egg, 
  Fish, 
  Milk,
  Clock,
  Zap,
  Target
} from "lucide-react";
import { PageHeader } from "../components/PageHeader";

// ============================================================================
// VISUAL COMPONENTS - Thay thế ảnh bằng icon + CSS
// ============================================================================

function EducationVisual({ type }) {
  if (type === "hero") {
    return (
      <div className="relative h-[280px] w-full rounded-[28px] bg-gradient-to-br from-emerald-100 via-white to-orange-100 p-8 shadow-sm">
        {/* Center icon */}
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
          <div className="flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br from-emerald-500 to-emerald-600 shadow-lg">
            <HeartPulse className="h-12 w-12 text-white" strokeWidth={2.5} />
          </div>
        </div>
        
        {/* Floating chips */}
        <div className="absolute left-8 top-12 rounded-full bg-white px-4 py-2 text-sm font-bold text-emerald-700 shadow-md">
          Ăn đủ
        </div>
        <div className="absolute right-8 top-16 rounded-full bg-white px-4 py-2 text-sm font-bold text-orange-600 shadow-md">
          Protein
        </div>
        <div className="absolute bottom-16 left-12 rounded-full bg-white px-4 py-2 text-sm font-bold text-blue-600 shadow-md">
          Ngủ tốt
        </div>
        <div className="absolute bottom-12 right-12 rounded-full bg-white px-4 py-2 text-sm font-bold text-purple-600 shadow-md">
          Vận động
        </div>
      </div>
    );
  }

  if (type === "weight") {
    return (
      <div className="flex h-[240px] w-full items-center justify-center rounded-[28px] bg-gradient-to-br from-emerald-50 to-emerald-100 p-6">
        <div className="text-center">
          <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-emerald-500 shadow-lg">
            <TrendingUp className="h-10 w-10 text-white" strokeWidth={2.5} />
          </div>
          <div className="mt-4 space-y-2">
            <div className="rounded-full bg-white px-4 py-1.5 text-sm font-bold text-emerald-700 shadow-sm">
              Ăn đủ hơn
            </div>
            <div className="rounded-full bg-white px-4 py-1.5 text-sm font-bold text-emerald-700 shadow-sm">
              Đủ protein
            </div>
            <div className="rounded-full bg-white px-4 py-1.5 text-sm font-bold text-emerald-700 shadow-sm">
              Kiên trì
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (type === "protein") {
    return (
      <div className="flex h-[240px] w-full items-center justify-center rounded-[28px] bg-gradient-to-br from-orange-50 to-orange-100 p-6">
        <div className="grid grid-cols-3 gap-3">
          {[
            { icon: Egg, label: "Trứng", color: "bg-yellow-500" },
            { icon: Fish, label: "Cá", color: "bg-blue-500" },
            { icon: Milk, label: "Sữa", color: "bg-white border-2 border-orange-200" },
            { icon: Utensils, label: "Thịt", color: "bg-red-500" },
            { icon: Apple, label: "Đậu", color: "bg-green-500" },
            { icon: Sparkles, label: "Hạt", color: "bg-amber-600" },
          ].map((item, idx) => (
            <div key={idx} className="flex flex-col items-center gap-1">
              <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${item.color} shadow-md`}>
                <item.icon className="h-6 w-6 text-white" strokeWidth={2} />
              </div>
              <span className="text-xs font-bold text-slate-700">{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (type === "sleep") {
    return (
      <div className="flex h-[240px] w-full items-center justify-center rounded-[28px] bg-gradient-to-br from-blue-50 via-purple-50 to-blue-100 p-6">
        <div className="text-center">
          <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-purple-500 shadow-lg">
            <Moon className="h-10 w-10 text-white" strokeWidth={2.5} />
          </div>
          <div className="mt-4 space-y-2">
            <div className="rounded-full bg-white px-4 py-1.5 text-sm font-bold text-blue-700 shadow-sm">
              Phục hồi
            </div>
            <div className="rounded-full bg-white px-4 py-1.5 text-sm font-bold text-purple-700 shadow-sm">
              Ăn ngon hơn
            </div>
            <div className="rounded-full bg-white px-4 py-1.5 text-sm font-bold text-blue-700 shadow-sm">
              Ít mệt
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (type === "myth") {
    return (
      <div className="grid h-[240px] w-full grid-cols-2 gap-2 rounded-[28px] bg-gradient-to-br from-slate-50 to-slate-100 p-6">
        <div className="flex flex-col items-center justify-center rounded-2xl bg-red-50 p-4">
          <XCircle className="h-12 w-12 text-red-500" strokeWidth={2.5} />
          <span className="mt-2 text-xs font-bold text-red-700">Hiểu lầm</span>
        </div>
        <div className="flex flex-col items-center justify-center rounded-2xl bg-emerald-50 p-4">
          <CheckCircle2 className="h-12 w-12 text-emerald-500" strokeWidth={2.5} />
          <span className="mt-2 text-xs font-bold text-emerald-700">Thực ra</span>
        </div>
      </div>
    );
  }

  if (type === "video") {
    return (
      <div className="relative flex h-[200px] w-full items-center justify-center overflow-hidden rounded-[28px] bg-gradient-to-br from-slate-800 to-slate-900">
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/20 to-orange-500/20" />
        <button className="relative flex h-16 w-16 items-center justify-center rounded-full bg-white shadow-xl transition hover:scale-110">
          <Play className="ml-1 h-8 w-8 text-emerald-600" fill="currentColor" />
        </button>
        {/* Progress bar */}
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-white/20">
          <div className="h-full w-1/3 bg-emerald-500" />
        </div>
      </div>
    );
  }

  return null;
}

// ============================================================================
// HERO SECTION
// ============================================================================

function Hero() {
  return (
    <section className="rounded-[36px] border border-emerald-100 bg-white/85 p-8 shadow-sm md:p-10">
      <div className="mx-auto grid items-center gap-8 md:grid-cols-2">
        <div>
          <p className="text-xs font-black uppercase tracking-wide text-emerald-600">GIÁO DỤC SỨC KHỎE</p>
          <h1 className="mt-3 text-4xl font-black leading-tight tracking-tight text-slate-950 md:text-5xl">
            Hiểu cơ thể để tăng cân khỏe mạnh
          </h1>
          <p className="mt-4 max-w-lg text-base leading-relaxed text-slate-600">
            NutriGain tóm gọn những điều quan trọng nhất: ăn đủ hơn, thêm protein, ngủ tốt và tránh các hiểu lầm phổ biến khi tăng cân.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <button className="rounded-full bg-emerald-600 px-6 py-3 text-sm font-black text-white shadow-lg transition hover:bg-emerald-700">
              Bắt đầu tìm hiểu
            </button>
            <button className="rounded-full border border-emerald-100 bg-white px-6 py-3 text-sm font-black text-slate-800 shadow-sm transition hover:bg-slate-50">
              Xem hiểu lầm phổ biến
            </button>
          </div>
        </div>

        <div className="order-first md:order-last">
          <EducationVisual type="hero" />
        </div>
      </div>
    </section>
  );
}

// ============================================================================
// INSIGHT CARDS
// ============================================================================

function InsightCards() {
  const insights = [
    {
      icon: Utensils,
      title: "Ăn đủ",
      text: "Cơ thể cần thêm năng lượng đều đặn, không phải ăn thật nhiều trong một lúc.",
      color: "from-emerald-500 to-emerald-600",
    },
    {
      icon: Sparkles,
      title: "Protein",
      text: "Protein giúp phục hồi và xây dựng mô, hỗ trợ tăng cân có chất hơn.",
      color: "from-orange-500 to-orange-600",
    },
    {
      icon: Moon,
      title: "Ngủ tốt",
      text: "Ngủ đủ giúp cơ thể phục hồi, ăn ngon hơn và duy trì thói quen tốt hơn.",
      color: "from-blue-500 to-purple-500",
    },
    {
      icon: Target,
      title: "Tăng từ từ",
      text: "Tăng cân bền vững là tăng đều, đủ chất và dễ duy trì.",
      color: "from-pink-500 to-rose-500",
    },
  ];

  return (
    <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {insights.map((item, idx) => (
        <article
          key={idx}
          className="group rounded-[28px] border border-emerald-100 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-md"
        >
          <div className={`inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${item.color} shadow-md`}>
            <item.icon className="h-6 w-6 text-white" strokeWidth={2.5} />
          </div>
          <h3 className="mt-4 text-lg font-black text-slate-900">{item.title}</h3>
          <p className="mt-2 text-sm leading-relaxed text-slate-600">{item.text}</p>
        </article>
      ))}
    </section>
  );
}

// ============================================================================
// STORY SECTIONS
// ============================================================================

function StorySection({ visual, headline, children, reverse = false }) {
  return (
    <section className={`grid items-center gap-8 md:grid-cols-2 ${reverse ? "md:flex-row-reverse" : ""}`}>
      <div className={reverse ? "md:order-last" : ""}>
        {children}
      </div>
      <div className={reverse ? "md:order-first" : ""}>
        <EducationVisual type={visual} />
      </div>
    </section>
  );
}

function WeightSection() {
  return (
    <StorySection visual="weight" headline="Tăng cân khỏe không phải là ăn bừa">
      <div>
        <h2 className="text-3xl font-black tracking-tight text-slate-950">Tăng cân khỏe không phải là ăn bừa</h2>
        <p className="mt-4 leading-relaxed text-slate-600">
          Tăng cân lành mạnh là nạp đủ năng lượng, đủ chất, ngủ đủ và duy trì thói quen ổn định. Mục tiêu không phải là ăn thật nhiều đồ ngọt hay đồ chiên, mà là giúp cơ thể khỏe hơn và tăng cân bền vững hơn.
        </p>
        <div className="mt-6 rounded-[24px] border border-emerald-100 bg-emerald-50 p-6">
          <p className="text-sm font-black text-emerald-900">Công thức tăng cân khỏe:</p>
          <p className="mt-2 text-sm leading-relaxed text-emerald-800">
            Ăn đủ hơn + Đủ protein + Ngủ tốt + Vận động nhẹ + Kiên trì
          </p>
        </div>
      </div>
    </StorySection>
  );
}

function ProteinSection() {
  const foods = ["Trứng", "Thịt gà", "Cá", "Sữa", "Sữa chua", "Đậu hũ", "Đậu nành", "Các loại hạt"];

  return (
    <StorySection visual="protein" headline="Protein là phần giúp cơ thể phục hồi" reverse>
      <div>
        <h2 className="text-3xl font-black tracking-tight text-slate-950">Protein là phần giúp cơ thể phục hồi</h2>
        <p className="mt-4 leading-relaxed text-slate-600">
          Protein, hay còn gọi là chất đạm, giúp cơ thể xây dựng mô cơ và phục hồi sau vận động. Khi muốn tăng cân, protein giúp bạn tăng cân "có chất" hơn, không chỉ tăng calo.
        </p>
        <div className="mt-6 flex flex-wrap gap-2">
          {foods.map((food) => (
            <span key={food} className="rounded-full border border-orange-200 bg-orange-50 px-4 py-2 text-sm font-bold text-orange-800">
              {food}
            </span>
          ))}
        </div>
        <p className="mt-4 text-sm italic text-slate-500">
          Mỗi bữa chỉ cần có một món giàu protein là đã tốt hơn rồi.
        </p>
      </div>
    </StorySection>
  );
}

function SleepSection() {
  const comparison = {
    less: ["Dễ mệt", "Dễ chán ăn", "Khó phục hồi"],
    enough: ["Có năng lượng", "Ăn ngon hơn", "Phục hồi tốt hơn"],
  };

  return (
    <StorySection visual="sleep" headline="Ngủ là lúc cơ thể phục hồi">
      <div>
        <h2 className="text-3xl font-black tracking-tight text-slate-950">Ngủ là lúc cơ thể phục hồi</h2>
        <p className="mt-4 leading-relaxed text-slate-600">
          Nếu ăn tốt nhưng ngủ quá ít, cơ thể dễ mệt, chán ăn và khó phục hồi. Ngủ đủ giúp bạn có năng lượng hơn, ăn ngon miệng hơn và duy trì thói quen đều hơn.
        </p>
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <div className="rounded-[20px] border border-red-100 bg-red-50 p-4">
            <p className="text-sm font-black text-red-900">Ngủ ít:</p>
            <ul className="mt-2 space-y-1 text-sm text-red-800">
              {comparison.less.map((item) => (
                <li key={item}>• {item}</li>
              ))}
            </ul>
          </div>
          <div className="rounded-[20px] border border-emerald-100 bg-emerald-50 p-4">
            <p className="text-sm font-black text-emerald-900">Ngủ đủ:</p>
            <ul className="mt-2 space-y-1 text-sm text-emerald-800">
              {comparison.enough.map((item) => (
                <li key={item}>• {item}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </StorySection>
  );
}

function MythIntroSection() {
  return (
    <StorySection visual="myth" headline="Đừng tăng cân bằng những hiểu lầm" reverse>
      <div>
        <h2 className="text-3xl font-black tracking-tight text-slate-950">Đừng tăng cân bằng những hiểu lầm</h2>
        <p className="mt-4 leading-relaxed text-slate-600">
          Tăng cân không có nghĩa là ăn càng nhiều đồ ngọt càng tốt. Điều quan trọng là đủ năng lượng, đủ đạm, ăn đều và ngủ tốt.
        </p>
      </div>
    </StorySection>
  );
}

// ============================================================================
// MYTH VS FACT SECTION
// ============================================================================

function MythSection() {
  const myths = [
    {
      myth: "Cứ ăn thật nhiều đồ ngọt là tăng cân tốt.",
      fact: "Đồ ngọt có thể làm cân nặng tăng nhanh, nhưng dễ làm tăng mỡ và khiến cơ thể mệt hơn. Hãy ưu tiên cơm, khoai, sữa, trứng, thịt, cá, hạt và trái cây.",
    },
    {
      myth: "Người gầy không cần tập luyện.",
      fact: "Vận động nhẹ giúp ăn ngon hơn, ngủ tốt hơn và hỗ trợ tăng cơ tốt hơn.",
    },
    {
      myth: "Bỏ bữa sáng không sao, tối ăn bù là được.",
      fact: "Ăn đều trong ngày giúp cơ thể dễ nạp đủ năng lượng hơn.",
    },
    {
      myth: "Tăng cân càng nhanh càng tốt.",
      fact: "Tăng chậm nhưng đều thường dễ duy trì và lành mạnh hơn.",
    },
  ];

  return (
    <section>
      <h2 className="text-3xl font-black tracking-tight text-slate-950">Những hiểu lầm phổ biến</h2>
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {myths.map((item, idx) => (
          <article key={idx} className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-start gap-3">
              <XCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-orange-500" strokeWidth={2.5} />
              <div>
                <p className="text-xs font-black uppercase text-orange-600">Nhiều người nghĩ</p>
                <p className="mt-1 text-sm leading-relaxed text-slate-700">{item.myth}</p>
              </div>
            </div>
            <div className="mt-4 flex items-start gap-3 rounded-[20px] bg-emerald-50 p-4">
              <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-emerald-600" strokeWidth={2.5} />
              <div>
                <p className="text-xs font-black uppercase text-emerald-700">Thực ra</p>
                <p className="mt-1 text-sm leading-relaxed text-emerald-900">{item.fact}</p>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

// ============================================================================
// MEAL DAY TIMELINE
// ============================================================================

function MealDayTimeline() {
  const meals = [
    { time: "Sáng", meal: "Bánh mì trứng + sữa", icon: Clock },
    { time: "Bữa phụ", meal: "Chuối + sữa chua", icon: Apple },
    { time: "Trưa", meal: "Cơm + thịt/cá + rau", icon: Utensils },
    { time: "Chiều", meal: "Sinh tố sữa + bơ đậu phộng", icon: Zap },
    { time: "Tối", meal: "Cơm + đậu hũ/thịt/cá + canh", icon: Utensils },
    { time: "Trước ngủ", meal: "Một ly sữa ấm nếu còn đói", icon: Moon },
  ];

  return (
    <section>
      <h2 className="text-3xl font-black tracking-tight text-slate-950">Một ngày ăn uống đơn giản có thể bắt đầu như này</h2>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {meals.map((item, idx) => (
          <div key={idx} className="flex items-start gap-4 rounded-[24px] border border-emerald-100 bg-white p-4 shadow-sm">
            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-emerald-100">
              <item.icon className="h-5 w-5 text-emerald-600" strokeWidth={2.5} />
            </div>
            <div>
              <p className="text-sm font-black text-slate-900">{item.time}</p>
              <p className="mt-1 text-sm text-slate-600">{item.meal}</p>
            </div>
          </div>
        ))}
      </div>
      <p className="mt-4 text-sm italic text-slate-500">
        Không cần hoàn hảo ngay từ ngày đầu. Chỉ cần thêm một bữa phụ là đã có tiến bộ.
      </p>
    </section>
  );
}

// ============================================================================
// VIDEO PREVIEW
// ============================================================================

function VideoPreview() {
  const points = [
    "Ăn đủ hơn mỗi ngày",
    "Thêm protein vào bữa ăn",
    "Ngủ đủ để cơ thể phục hồi",
  ];

  return (
    <section className="rounded-[36px] border border-slate-200 bg-gradient-to-br from-slate-50 to-white p-8 shadow-sm">
      <div className="grid items-center gap-8 md:grid-cols-2">
        <div>
          <h2 className="text-2xl font-black tracking-tight text-slate-950">Video 30 giây: 3 điều cần nhớ</h2>
          <ul className="mt-4 space-y-2">
            {points.map((point, idx) => (
              <li key={idx} className="flex items-start gap-3">
                <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-emerald-600" strokeWidth={2.5} />
                <span className="text-sm text-slate-700">{point}</span>
              </li>
            ))}
          </ul>
        </div>
        <EducationVisual type="video" />
      </div>
    </section>
  );
}

// ============================================================================
// CTA SECTION
// ============================================================================

function EducationCTA() {
  return (
    <section className="rounded-[36px] border border-emerald-100 bg-gradient-to-br from-emerald-50 to-white p-8 text-center shadow-sm md:p-12">
      <div className="mx-auto max-w-2xl">
        <h2 className="text-3xl font-black tracking-tight text-slate-950 md:text-4xl">
          Sẵn sàng tăng cân theo cách khỏe hơn?
        </h2>
        <p className="mt-4 leading-relaxed text-slate-600">
          Bắt đầu bằng một việc nhỏ hôm nay: thêm một bữa phụ, ăn đủ protein hơn hoặc ngủ sớm hơn 30 phút.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-4">
          <button className="rounded-full bg-emerald-600 px-8 py-4 text-base font-black text-white shadow-lg transition hover:bg-emerald-700">
            Tạo kế hoạch ăn uống của tôi
          </button>
          <button className="rounded-full border border-emerald-100 bg-white px-8 py-4 text-base font-black text-slate-800 shadow-sm transition hover:bg-slate-50">
            Xem thực đơn mẫu 7 ngày
          </button>
        </div>
        <p className="mt-8 text-xs text-slate-500">
          Nội dung chỉ mang tính tham khảo. Nếu bạn có bệnh lý nền hoặc vấn đề sức khỏe đặc biệt, hãy hỏi chuyên gia y tế hoặc chuyên gia dinh dưỡng.
        </p>
      </div>
    </section>
  );
}

// ============================================================================
// MAIN VIEW
// ============================================================================

export default function HealthEducationView({ onEditProfile }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-orange-50">
      <div className="mx-auto max-w-[1280px] space-y-8 px-6 py-8 md:px-10">
        <PageHeader
          eyebrow="KIẾN THỨC DINH DƯỠNG"
          title="Giáo dục sức khỏe"
          subtitle="Hiểu cơ thể, ăn đúng hơn và tăng cân lành mạnh hơn mỗi ngày."
        />

        <Hero />

        <InsightCards />

        <div className="space-y-16">
          <WeightSection />
          <ProteinSection />
          <SleepSection />
          <MythIntroSection />
        </div>

        <MythSection />

        <MealDayTimeline />

        <VideoPreview />

        <EducationCTA />
      </div>
    </div>
  );
}
