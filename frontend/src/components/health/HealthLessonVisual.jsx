import { useEffect, useMemo, useState } from "react";

const LESSON_VISUALS = {
  "healthy-weight-gain": {
    icon: "🍽️",
    title: "Tăng cân lành mạnh",
    flow: ["Ăn đủ bữa", "Bữa phụ", "Ngủ đủ", "Theo dõi"],
    chips: ["🍚 Cơm", "🥛 Sữa", "🍌 Chuối", "🌙", "⚖️"],
    theme: "mint",
  },
  "protein-basics": {
    icon: "🥚",
    title: "Protein là gì?",
    flow: ["Trứng", "Sữa", "Thịt", "Cá", "Đậu"],
    subtitle: "Giúp xây cơ và phục hồi",
    theme: "cream",
  },
  "protein-carb-fat": {
    icon: "🥚",
    title: "Protein là gì?",
    flow: ["Trứng", "Sữa", "Thịt", "Cá", "Đậu"],
    subtitle: "Giúp xây cơ và phục hồi",
    theme: "cream",
  },
  "sleep-importance": {
    icon: "🌙",
    title: "Ngủ đủ quan trọng",
    flow: ["Ngủ đủ", "Đỡ mệt", "Ăn đều hơn"],
    theme: "sky",
  },
  "sleep-recovery": {
    icon: "🌙",
    title: "Ngủ đủ quan trọng",
    flow: ["Ngủ đủ", "Đỡ mệt", "Ăn đều hơn"],
    theme: "sky",
  },
  "weight-gain-myths": {
    icon: "💡",
    title: "Hiểu lầm về tăng cân",
    cards: ["Không chỉ đồ chiên", "Không bỏ bữa rồi ăn bù", "Tăng từ từ sẽ bền hơn"],
    theme: "sun",
  },
  "myth-busting": {
    icon: "💡",
    title: "Hiểu lầm về tăng cân",
    cards: ["Không chỉ đồ chiên", "Không bỏ bữa rồi ăn bù", "Tăng từ từ sẽ bền hơn"],
    theme: "sun",
  },
};

function themeClasses(theme) {
  switch (theme) {
    case "cream":
      return {
        shell: "bg-gradient-to-br from-brand-cream via-white to-amber-50 text-slate-900",
        band: "bg-amber-100 text-amber-800",
        chip: "bg-white text-slate-700 border-slate-100",
        arrow: "text-amber-400",
      };
    case "sky":
      return {
        shell: "bg-gradient-to-br from-brand-soft via-white to-sky-50 text-slate-900",
        band: "bg-sky-100 text-sky-800",
        chip: "bg-white text-slate-700 border-slate-100",
        arrow: "text-sky-400",
      };
    case "sun":
      return {
        shell: "bg-gradient-to-br from-brand-cream via-white to-yellow-50 text-slate-900",
        band: "bg-yellow-100 text-yellow-800",
        chip: "bg-white text-slate-700 border-slate-100",
        arrow: "text-yellow-400",
      };
    default:
      return {
        shell: "bg-gradient-to-br from-brand-mint via-white to-emerald-50 text-slate-900",
        band: "bg-emerald-100 text-emerald-800",
        chip: "bg-white text-slate-700 border-slate-100",
        arrow: "text-emerald-400",
      };
  }
}

export default function HealthLessonVisual({ lessonId, title, imageUrl }) {
  const [imageFailed, setImageFailed] = useState(false);
  const resolved = useMemo(() => LESSON_VISUALS[lessonId] || LESSON_VISUALS[title] || null, [lessonId, title]);
  const theme = themeClasses(resolved?.theme || "mint");
  const resolvedTitle = title || resolved?.title || "Bài học hôm nay";
  const imageSrc = imageFailed ? null : imageUrl || null;

  useEffect(() => {
    setImageFailed(false);
  }, [imageUrl, lessonId]);

  if (imageSrc) {
    return (
      <div className={`overflow-hidden rounded-[28px] border border-white/80 shadow-[0_18px_50px_rgba(16,185,129,0.12)] ${theme.shell}`}>
        <img
          src={imageSrc}
          alt={resolvedTitle}
          className="h-full w-full object-cover"
          onError={() => setImageFailed(true)}
          loading="lazy"
        />
      </div>
    );
  }

  return (
    <div className={`overflow-hidden rounded-[28px] border border-white/80 p-5 shadow-[0_18px_50px_rgba(16,185,129,0.12)] sm:p-6 ${theme.shell}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="text-[56px] leading-none sm:text-[72px]">{resolved?.icon || "🌿"}</div>
          <h3 className="mt-4 text-2xl font-black leading-tight sm:text-[28px]">{resolved?.title || resolvedTitle}</h3>
        </div>
        <div className={`rounded-full px-3 py-1 text-xs font900 uppercase tracking-[0.14em] ${theme.band}`}>Infographic</div>
      </div>

      {resolved?.flow ? (
        <div className="mt-5 flex flex-wrap items-center gap-2">
          {resolved.flow.map((step, index) => (
            <div key={step} className="flex items-center gap-2">
              <span className={`rounded-full border px-3 py-2 text-sm font900 ${theme.chip}`}>{step}</span>
              {index < resolved.flow.length - 1 ? <span className={`text-lg font-black ${theme.arrow}`}>→</span> : null}
            </div>
          ))}
        </div>
      ) : null}

      {resolved?.subtitle ? (
        <p className="mt-4 max-w-md text-sm font800 leading-6 text-slate-600">{resolved.subtitle}</p>
      ) : null}

      {resolved?.cards ? (
        <div className="mt-5 grid gap-2">
          {resolved.cards.map((card) => (
            <div key={card} className="rounded-2xl border border-white/80 bg-white/80 px-4 py-3 text-sm font900 text-slate-700 shadow-sm backdrop-blur">
              {card}
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-5 flex flex-wrap gap-2">
          {(resolved?.chips || ["🍚", "🥛", "🍌", "🌙", "⚖️"]).map((chip) => (
            <span key={chip} className="inline-flex items-center gap-2 rounded-full border border-white/80 bg-white/85 px-3 py-2 text-sm font900 text-slate-700 shadow-sm backdrop-blur">
              {chip}
            </span>
          ))}
        </div>
      )}

      <div className="mt-5 rounded-2xl border border-white/80 bg-white/70 p-4 shadow-sm">
        <div className="flex items-center justify-between gap-3 text-sm font900 text-slate-700">
          <span>Mini infographic</span>
          <span className="text-slate-500">Không video, chỉ hình minh họa</span>
        </div>
      </div>
    </div>
  );
}
