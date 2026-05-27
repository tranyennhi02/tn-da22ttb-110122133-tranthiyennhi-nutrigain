import healthyWeightGainImg from "../assets/education/healthy-weight-gain.png";
import proteinFoodsImg from "../assets/education/protein-foods.png";
import healthySleepImg from "../assets/education/healthy-sleep.png";
import weightGainMythsImg from "../assets/education/weight-gain-myths.png";
import { PageHeader } from "../components/PageHeader";

const coreIdeas = [
  {
    id: "eat-regularly",
    title: "Ăn đều",
    summary: "Ăn đều giúp cơ thể có năng lượng ổn định trong ngày.",
    meaning: "Cơ thể ít bị đói quá lâu, dễ giữ nhịp ăn và tránh ăn quá nhiều một lúc.",
    color: "bg-emerald-50",
  },
  {
    id: "enough-protein",
    title: "Đạm đủ",
    summary: "Đạm giúp cơ thể phục hồi và xây dựng mô khi bạn tăng cân.",
    meaning: "Tăng cân lành mạnh cần đủ nguyên liệu (đạm) để cơ thể khỏe hơn, không chỉ nhiều calo.",
    color: "bg-amber-50",
  },
  {
    id: "sleep-well",
    title: "Ngủ đủ",
    summary: "Ngủ đủ giúp cơ thể nghỉ ngơi, phục hồi và duy trì thói quen ăn uống.",
    meaning: "Khi ngủ tốt, bạn ít mệt, dễ ăn đều hơn và hấp thu tốt hơn.",
    color: "bg-sky-50",
  },
  {
    id: "healthy-gain",
    title: "Tăng cân lành mạnh",
    summary: "Tăng từ từ, đủ chất và bền vững thay vì ép ăn quá nhiều.",
    meaning: "Đa dạng thực phẩm, đủ đạm, tinh bột và rau củ giúp tăng cân khỏe hơn.",
    color: "bg-pink-50",
  },
];

function Badge({ children }) {
  return <span className="rounded-full bg-white/80 px-3 py-1 text-xs font700 text-slate-700 shadow-sm">{children}</span>;
}

function Hero() {
  return (
    <section className="rounded-[24px] bg-gradient-to-r from-emerald-50 to-white p-5 sm:p-6 lg:p-8">
      <div className="mx-auto grid gap-4 md:grid-cols-2 items-center">
        <div>
          <p className="text-xs font700 uppercase text-emerald-700">Hiểu cơ thể thật đơn giản</p>
          <h1 className="mt-3 text-2xl font-black text-slate-900 sm:text-3xl">Hiểu cơ thể để tăng cân khỏe mạnh</h1>
          <p className="mt-2 max-w-lg text-sm text-slate-600">Không cần nhiều lý thuyết — chỉ vài nguyên tắc để ăn đều, đủ chất và tăng cân bền vững.</p>
          <div className="mt-4 flex gap-2">
            <Badge>Dễ hiểu</Badge>
            <Badge>Gọn gàng</Badge>
            <Badge>Áp dụng hằng ngày</Badge>
          </div>
        </div>

        <div className="order-first md:order-last flex justify-center">
          <div className="overflow-hidden rounded-[20px] shadow-sm w-full max-w-md">
            <img src={healthyWeightGainImg} alt="Tăng cân lành mạnh" className="w-full h-[260px] md:h-[220px] object-cover object-center" />
          </div>
        </div>
      </div>
    </section>
  );
}

function UnderstandingCards() {
  return (
    <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {coreIdeas.map((idea) => (
        <article key={idea.id} className={`rounded-[20px] p-4 ${idea.color} border border-white/60 shadow-sm hover:shadow-md transition-transform hover:-translate-y-0.5` }>
          <h3 className="text-base font-bold text-slate-900">{idea.title}</h3>
          <p className="mt-1 text-sm text-slate-700">{idea.summary}</p>
          <p className="mt-2 text-xs text-slate-600">{idea.meaning}</p>
        </article>
      ))}
    </section>
  );
}

function ExplanationSection() {
  return (
    <section className="space-y-6">
      {/* Block 1 - Eat regularly (image right) */}
      <div className="grid gap-4 items-center md:grid-cols-2">
        <div>
          <h4 className="text-base font-bold text-slate-900">Vì sao cần ăn đều?</h4>
          <p className="mt-2 text-sm text-slate-700">Ăn đều giúp cơ thể giữ năng lượng ổn định và tránh ăn bù quá nhiều một lúc.</p>
          <ul className="mt-3 text-sm text-slate-600 list-inside list-disc space-y-1">
            <li>Ít mệt hơn</li>
            <li>Đỡ bỏ bữa</li>
            <li>Dễ duy trì thói quen</li>
          </ul>
        </div>
        <div className="flex justify-center">
          <div className="overflow-hidden rounded-[20px] shadow-sm w-full max-w-md">
            <img src={healthyWeightGainImg} alt="Ăn đều" className="w-full h-48 object-cover object-center" />
          </div>
        </div>
      </div>

      {/* Block 2 - Protein (image left) */}
      <div className="grid gap-4 items-center md:grid-cols-2">
        <div className="order-last md:order-first flex justify-center">
          <div className="overflow-hidden rounded-[20px] shadow-sm w-full max-w-md">
            <img src={proteinFoodsImg} alt="Đạm" className="w-full h-48 object-cover object-center" />
          </div>
        </div>
        <div>
          <h4 className="text-base font-bold text-slate-900">Vì sao cần đủ đạm?</h4>
          <p className="mt-2 text-sm text-slate-700">Đạm là nguyên liệu để phục hồi cơ và xây dựng khi bạn tăng cân.</p>
          <ul className="mt-3 text-sm text-slate-600 list-inside list-disc space-y-1">
            <li>Hỗ trợ phục hồi</li>
            <li>Giúp tăng cơ hơn là mỡ</li>
            <li>Giữ bạn no lâu hơn</li>
          </ul>
        </div>
      </div>

      {/* Block 3 - Sleep (image right) */}
      <div className="grid gap-4 items-center md:grid-cols-2">
        <div>
          <h4 className="text-base font-bold text-slate-900">Ngủ ảnh hưởng thế nào?</h4>
          <p className="mt-2 text-sm text-slate-700">Ngủ đủ giúp cơ thể phục hồi, giảm mệt mỏi và hỗ trợ thói quen ăn uống đều đặn.</p>
          <ul className="mt-3 text-sm text-slate-600 list-inside list-disc space-y-1">
            <li>Phục hồi tốt hơn</li>
            <li>Ít mệt trong ngày</li>
            <li>Dễ ăn đều hơn</li>
          </ul>
        </div>
        <div className="flex justify-center">
          <div className="overflow-hidden rounded-[20px] shadow-sm w-full max-w-md">
            <img src={healthySleepImg} alt="Ngủ đủ" className="w-full h-48 object-cover object-center" />
          </div>
        </div>
      </div>
    </section>
  );
}

function MythTruthSection() {
  const myths = [
    {
      myth: "Muốn tăng cân thì ăn càng nhiều càng tốt.",
      truth: "Tăng cân hiệu quả là ăn đủ và đều; không cần ép bản thân ăn quá nhiều trong một lần.",
    },
    {
      myth: "Chỉ cần tăng cân là được.",
      truth: "Tăng cân lành mạnh nên đi kèm đủ đạm, đủ năng lượng và sinh hoạt ổn định.",
    },
    {
      myth: "Ngủ không ảnh hưởng đến tăng cân.",
      truth: "Ngủ đủ giúp cơ thể phục hồi và hỗ trợ thói quen ăn uống đều hơn.",
    },
  ];

  return (
    <section className="grid gap-4 sm:grid-cols-3">
      {myths.map((m, idx) => (
        <div key={idx} className="rounded-[20px] border p-4 bg-white/90 shadow-sm">
          <p className="text-xs font700 text-amber-700">Hiểu lầm</p>
          <p className="mt-2 text-sm text-slate-700">{m.myth}</p>
          <div className="mt-3 rounded-md bg-emerald-50 p-3">
            <p className="text-xs font700 text-emerald-700">Thực tế</p>
            <p className="mt-1 text-sm text-slate-700">{m.truth}</p>
          </div>
        </div>
      ))}
    </section>
  );
}

function GentleTipsSection() {
  const tips = [
    "Ăn đủ các bữa chính",
    "Thêm 1 món giàu đạm",
    "Tránh bỏ bữa quá lâu",
    "Ngủ sớm hơn một chút tối nay",
  ];
  return (
    <section className="grid gap-4 md:grid-cols-2 items-start">
      <div className="rounded-[20px] p-4 bg-white/90 shadow-sm">
        <h3 className="text-lg font-bold text-slate-900">Hôm nay bạn có thể bắt đầu từ đây</h3>
        <p className="mt-2 text-sm text-slate-700">Không cần thay đổi mọi thứ — 1–2 bước nhỏ là đủ.</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {tips.map((t) => (
            <span key={t} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-sm text-slate-700">{t}</span>
          ))}
        </div>
      </div>

      <div className="rounded-[20px] p-4 bg-emerald-50/60 shadow-sm">
        <p className="text-sm font700 text-slate-900">Chú ý nhỏ</p>
        <p className="mt-2 text-sm text-slate-700">Chỉ cần đều hơn hôm qua một chút — đó đã là tiến bộ.</p>
      </div>
    </section>
  );
}

export default function HealthEducationView({ onEditProfile }) {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="KIẾN THỨC DINH DƯỠNG"
        title="Giáo dục sức khỏe"
        subtitle="Hiểu nhanh các nguyên tắc ăn uống, nghỉ ngơi và tăng cân lành mạnh."
      />

      <Hero />

      <div className="grid gap-6">
        <UnderstandingCards />

        <ExplanationSection />

        <MythTruthSection />

        <GentleTipsSection />
      </div>
    </div>
  );
}
