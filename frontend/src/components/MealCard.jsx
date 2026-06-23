const PLACEHOLDER_SVG_DEFAULT = "/images/placeholders/food-default.svg";

/**
 * Xác định có nên hiển thị ảnh thật không:
 *  - image_verified phải là 1/true
 *  - image_source_type phải là "real"
 *  - image_url phải tồn tại
 */
function shouldShowRealImage(item) {
  const verified =
    item.image_verified === true ||
    item.image_verified === 1 ||
    item.image_verified === "1" ||
    item.image_verified === "true" ||
    item.imageVerified === true;
  const sourceType = String(
    item.image_source_type || item.imageSourceType || "placeholder"
  ).toLowerCase();
  const isReal = sourceType === "real";
  const hasUrl = Boolean(item.image_url || item.image);
  return verified && isReal && hasUrl;
}

/**
 * FoodImageArea — Component ảnh 2 lớp an toàn:
 *  • Nếu ảnh thật hợp lệ → <img> với lazy load + fallback
 *  • Ngược lại → placeholder icon
 */
function FoodImageArea({ item }) {
  const useReal = shouldShowRealImage(item);
  const imageUrl = item.image_url || item.image;
  const altText =
    item.image_alt_vi || item.image_alt || item.imageAlt || item.name;

  if (useReal) {
    return (
      <img
        src={imageUrl}
        alt={altText}
        loading="lazy"
        className="h-full w-full object-cover object-center transition duration-500 group-hover:scale-105"
        onError={(event) => {
          const img = event.currentTarget;
          if (img.dataset.usedFallback === "true") return;
          img.dataset.usedFallback = "true";
          img.style.display = "none";
          const parent = img.parentElement;
          if (parent && !parent.querySelector(".meal-card-placeholder")) {
            const icon = document.createElement("div");
            icon.className =
              "meal-card-placeholder h-full w-full flex items-center justify-center bg-brand-cream";
            icon.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>`;
            parent.appendChild(icon);
          }
        }}
      />
    );
  }

  const placeholderSrc = item.fallbackImage || PLACEHOLDER_SVG_DEFAULT;
  return (
    <img
      src={placeholderSrc}
      alt={altText}
      loading="lazy"
      className="h-full w-full object-cover object-center transition duration-500 group-hover:scale-105"
      onError={(event) => {
        event.currentTarget.style.display = "none";
      }}
    />
  );
}

/**
 * MealCard — Food card component with selection support.
 *
 * Props:
 *  item              – food item object (includes is_core, is_default_selected)
 *  isSelected        – whether this item is currently selected by the user
 *  onToggleSelect    – callback(item) when user clicks to select/deselect
 *  favorite          – boolean
 *  rating            – number | undefined
 *  onFavorite        – callback
 *  onRate            – callback(value)
 */
export default function MealCard({
  item,
  isSelected,
  onToggleSelect,
  favorite,
  rating,
  onFavorite,
  onRate,
}) {
  // is_core is used internally for default selection logic only — not shown in UI
  const isCore =
    item.is_core !== undefined
      ? Boolean(item.is_core)
      : item.meal_role_display === "core"
      ? true
      : item.is_default_selected !== undefined
      ? Boolean(item.is_default_selected)
      : true;

  const selected = isSelected !== undefined ? isSelected : isCore;

  const badgeLabel =
    item.imageBadge || item.image_badge || (shouldShowRealImage(item) ? "Ảnh thật" : null);

  // Visual ring when selected
  const ringClass = selected
    ? "ring-2 ring-brand-primary ring-offset-2"
    : "ring-1 ring-brand-border";

  return (
    <article
      className={`group overflow-hidden rounded-3xl bg-brand-surface shadow-xl shadow-brand-navy/7 transition duration-300 hover:-translate-y-1 hover:shadow-2xl ${ringClass} ${
        !selected ? "opacity-70" : ""
      }`}
    >

      {/* ── Image area ──────────────────────────────────────────────────── */}
      <div className="relative aspect-[16/10] overflow-hidden bg-brand-cream">
        <FoodImageArea item={item} />

        <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-slate-950/70 to-transparent" />

        {/* Category type pill */}
        <div className="absolute left-4 top-4 rounded-full bg-brand-surface/92 px-3 py-1.5 text-xs font-black uppercase tracking-[0.1em] text-brand-text-main backdrop-blur">
          {item.type || item.food_group || item.category}
        </div>

        {/* Real photo badge */}
        {badgeLabel === "Ảnh thật" ? (
          <div className="absolute right-4 top-4 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-black text-emerald-700 ring-1 ring-emerald-100">
            {badgeLabel}
          </div>
        ) : null}

        {/* Kcal badge */}
        <div className="absolute bottom-4 right-4 rounded-2xl bg-brand-orange px-3 py-2 text-sm font-black text-white shadow-lg shadow-brand-orange/20">
          {Math.round(item.calories ?? item.kcal ?? 0)} kcal
        </div>

        {/* Serving size badge */}
        {item.servingDisplay || item.servingGrams || item.serving_display || item.serving_grams ? (
          <div className="absolute bottom-4 left-4 rounded-2xl bg-slate-950/78 px-3 py-2 text-sm font-black text-white shadow-lg shadow-slate-950/20 backdrop-blur-md">
            {item.servingDisplay ||
              item.serving_display ||
              `~${item.servingGrams || item.serving_grams}g`}
          </div>
        ) : null}
      </div>

      {/* ── Card body ───────────────────────────────────────────────────── */}
      <div className="space-y-4 p-4">
        <div>
          <h4
            className="min-h-[3.1rem] text-lg font-black leading-snug text-brand-text-main"
            title={item.name}
            style={{
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
            }}
          >
            {item.name}
          </h4>
          <p className="mt-1 text-sm font-bold leading-6 text-brand-text-sub">
            {item.category || item.type}
            {item.subCategory ? ` · ${item.subCategory}` : ""}
          </p>
          <p className="mt-1 text-sm font-bold text-brand-text-sub">
            {Math.round(item.calories ?? item.kcal ?? 0)} kcal
            {item.servingDisplay || item.serving_display
              ? ` · ${item.servingDisplay || item.serving_display}`
              : item.servingGrams || item.serving_grams
              ? ` · ~${item.servingGrams || item.serving_grams}g`
              : ""}
          </p>
        </div>

        {/* Macros */}
        <div className="grid grid-cols-3 gap-2">
          <MacroPill label="Protein" value={item.protein} tone="sky" />
          <MacroPill label="Fat" value={item.fat} tone="orange" />
          <MacroPill label="Carbs" value={item.carbs} tone="green" />
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          {/* Select / deselect toggle */}
          {onToggleSelect && (
            <button
              type="button"
              aria-pressed={selected}
              aria-label={selected ? `Bỏ chọn ${item.name}` : `Chọn ${item.name}`}
              onClick={() => onToggleSelect(item)}
              className={`flex h-11 items-center justify-center gap-2 rounded-2xl px-4 text-sm font-black transition ${
                selected
                  ? "bg-brand-primary text-white shadow-sm"
                  : "bg-slate-100 text-slate-600 hover:bg-brand-primary/10 hover:text-brand-primary"
              }`}
            >
              {selected ? (
                <>
                  <CheckCircleIcon />
                  Đã chọn
                </>
              ) : (
                "Chọn món"
              )}
            </button>
          )}

          <button
            className={`flex h-11 items-center justify-center gap-2 rounded-2xl px-4 text-sm font-black transition ${
              favorite
                ? "bg-rose-50 text-rose-600 ring-1 ring-rose-100"
                : "bg-slate-100 text-slate-700 hover:bg-rose-50 hover:text-rose-600"
            }`}
            onClick={onFavorite}
          >
            <HeartIcon filled={favorite} />
            Yêu thích
          </button>

          <label className="flex h-11 items-center justify-center gap-2 rounded-2xl bg-brand-mint px-3 text-sm font-black text-brand-primary">
            Đánh giá
            <select
              className="bg-transparent text-sm font-black outline-none"
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

/* ── Macro pill ─────────────────────────────────────────────────────────── */
function MacroPill({ label, value, tone }) {
  const classes = {
    sky: "bg-sky-50 text-sky-700",
    orange: "bg-brand-cream text-brand-orange",
    green: "bg-brand-mint text-brand-primary",
  };

  return (
    <div className={`rounded-2xl px-3 py-3 text-center ${classes[tone]}`}>
      <div className="text-lg font-black">{Math.round(value ?? 0)}g</div>
      <div className="mt-1 text-[11px] font-black uppercase tracking-[0.09em] opacity-75">
        {label}
      </div>
    </div>
  );
}

/* ── Icons ──────────────────────────────────────────────────────────────── */
function HeartIcon({ filled }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-4 w-4"
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8z" />
    </svg>
  );
}

function CheckCircleIcon() {
  return (
    <svg
      viewBox="0 0 20 20"
      className="h-3.5 w-3.5"
      fill="currentColor"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function SwapIcon() {
  // Kept for potential future use
  return null;
}
