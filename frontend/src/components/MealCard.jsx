const defaultFoodImage = "/images/placeholders/food-default.svg";

export default function MealCard({ item, favorite, rating, onFavorite, onRate }) {
  return (
    <article className="group overflow-hidden rounded-3xl border border-brand-border bg-brand-surface shadow-xl shadow-brand-navy/7 transition duration-300 hover:-translate-y-1 hover:shadow-2xl">
      <div className="relative aspect-[16/10] overflow-hidden bg-brand-cream">
        <img
          src={item.image}
          alt={item.imageAlt || item.name}
          className="h-full w-full object-cover transition duration-500 group-hover:scale-105"
          onError={(event) => {
            const image = event.currentTarget;
            if (image.dataset.usedFallback === "true") return;
            image.dataset.usedFallback = "true";
            image.src = item.fallbackImage || defaultFoodImage;
          }}
        />
        <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-slate-950/70 to-transparent" />
        <div className="absolute left-4 top-4 rounded-full bg-brand-surface/92 px-3 py-1.5 text-xs font900 uppercase tracking-[0.1em] text-brand-text-main backdrop-blur">
          {item.type}
        </div>
        {item.imageBadge ? (
          <div className="absolute right-4 top-4 rounded-full bg-amber-50 px-3 py-1.5 text-xs font900 text-amber-800 ring-1 ring-amber-100">
            {item.imageBadge}
          </div>
        ) : null}
        <div className="absolute bottom-4 right-4 rounded-2xl bg-brand-orange px-3 py-2 text-sm font-black text-white shadow-lg shadow-brand-orange/20">
          {item.calories} kcal
        </div>
        {item.servingDisplay || item.servingGrams ? (
          <div className="absolute bottom-4 left-4 rounded-2xl bg-slate-950/78 px-3 py-2 text-sm font-black text-white shadow-lg shadow-slate-950/20 backdrop-blur-md">
            {item.servingDisplay || `~${item.servingGrams}g`}
          </div>
        ) : null}
      </div>

      <div className="space-y-4 p-4">
        <div>
          <h4 className="text-lg font-black leading-snug text-brand-text-main">{item.name}</h4>
          <p className="mt-1 text-sm font800 leading-6 text-brand-text-sub">
            {item.category || item.type}{item.subCategory ? ` · ${item.subCategory}` : ""}
          </p>
          <p className="mt-1 text-sm font700 text-brand-text-sub">
            {item.calories} kcal{item.servingDisplay ? ` · ${item.servingDisplay}` : item.servingGrams ? ` · ~${item.servingGrams}g` : ""}
          </p>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <MacroPill label="Protein" value={item.protein} tone="sky" />
          <MacroPill label="Fat" value={item.fat} tone="orange" />
          <MacroPill label="Carbs" value={item.carbs} tone="green" />
        </div>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <button
            className={`flex h-11 items-center justify-center gap-2 rounded-2xl px-4 text-sm font900 transition ${
              favorite
                ? "bg-rose-50 text-rose-600 ring-1 ring-rose-100"
                : "bg-slate-100 text-slate-700 hover:bg-rose-50 hover:text-rose-600"
            }`}
            onClick={onFavorite}
          >
            <HeartIcon filled={favorite} />
            Yêu thích
          </button>

          <label className="flex h-11 items-center justify-center gap-2 rounded-2xl bg-brand-mint px-3 text-sm font900 text-brand-primary">
            Đánh giá
            <select
              className="bg-transparent text-sm font900 outline-none"
              value={rating || ""}
              onChange={(event) => onRate(Number(event.target.value))}
              aria-label={`Đánh giá ${item.name}`}
            >
              <option value="">--</option>
              <option value="5">5</option>
              <option value="4">4</option>
              <option value="3">3</option>
            </select>
          </label>
        </div>
      </div>
    </article>
  );
}

function MacroPill({ label, value, tone }) {
  const classes = {
    sky: "bg-sky-50 text-sky-700",
    orange: "bg-brand-cream text-brand-orange",
    green: "bg-brand-mint text-brand-primary",
  };

  return (
    <div className={`rounded-2xl px-3 py-3 text-center ${classes[tone]}`}>
      <div className="text-lg font-black">{value}g</div>
      <div className="mt-1 text-[11px] font900 uppercase tracking-[0.09em] opacity-75">
        {label}
      </div>
    </div>
  );
}

function HeartIcon({ filled }) {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill={filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8z" />
    </svg>
  );
}
