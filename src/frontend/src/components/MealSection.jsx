import { useMemo, useState } from "react";
import MealCard from "./MealCard";
import MealScorePanel from "./MealScorePanel";

/* ─────────────────────────────────────────────────────────────────────────────
 * NutritionFeedback
 * Computes and displays realtime kcal / macro status after user swaps.
 * ─────────────────────────────────────────────────────────────────────────── */
function computeSelectionTotals(selectedItems) {
  return selectedItems.reduce(
    (acc, item) => {
      acc.kcal += Number(item.calories ?? item.kcal ?? 0);
      acc.protein += Number(item.protein ?? 0);
      acc.fat += Number(item.fat ?? 0);
      acc.carbs += Number(item.carbs ?? 0);
      return acc;
    },
    { kcal: 0, protein: 0, fat: 0, carbs: 0 }
  );
}

/**
 * Returns feedback object { status, message, color } for the current selection.
 *
 * @param {object} totals   - { kcal, protein, fat, carbs }
 * @param {number} targetKcal
 * @param {number} targetProtein
 */
function buildNutritionFeedback(totals, targetKcal, targetProtein) {
  const kcal = totals.kcal;
  const protein = totals.protein;

  // Nothing selected
  if (kcal === 0) {
    return { status: "empty", message: "Chưa chọn món nào.", color: "slate" };
  }

  const kcalOk =
    targetKcal > 0
      ? kcal >= targetKcal * 0.85 && kcal <= targetKcal * 1.15
      : true;
  const proteinOk =
    targetProtein > 0 ? protein >= targetProtein * 0.85 : true;

  const kcalLow = targetKcal > 0 && kcal < targetKcal * 0.85;
  const kcalHigh = targetKcal > 0 && kcal > targetKcal * 1.15;
  const proteinLow = targetProtein > 0 && protein < targetProtein * 0.85;

  if (kcalOk && proteinOk) {
    return {
      status: "good",
      message: "✅ Bữa ăn hiện tại phù hợp với mục tiêu tăng cân của bạn.",
      color: "green",
    };
  }

  if (kcalLow) {
    return {
      status: "low_kcal",
      message: `⚠ Năng lượng hiện tại còn thiếu (${Math.round(kcal)} / ${Math.round(targetKcal)} kcal). Hãy chọn thêm món bên dưới.`,
      color: "amber",
    };
  }

  if (kcalHigh) {
    return {
      status: "high_kcal",
      message: `⚠ Năng lượng hiện tại vượt mức khuyến nghị (${Math.round(kcal)} / ${Math.round(targetKcal)} kcal).`,
      color: "orange",
    };
  }

  if (proteinLow) {
    return {
      status: "low_protein",
      message: `⚠ Lượng protein có thể chưa đủ (${Math.round(protein)}g). Nên giữ hoặc thêm món giàu đạm.`,
      color: "amber",
    };
  }

  return {
    status: "ok",
    message: `${Math.round(kcal)} kcal · ${Math.round(protein)}g protein`,
    color: "slate",
  };
}

const feedbackColorMap = {
  green: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100",
  amber: "bg-amber-50 text-amber-700 ring-1 ring-amber-100",
  orange: "bg-orange-50 text-orange-700 ring-1 ring-orange-100",
  slate: "bg-slate-50 text-slate-600 ring-1 ring-slate-200",
};

function NutritionFeedback({ selectedItems, targetKcal, targetProtein }) {
  const totals = useMemo(
    () => computeSelectionTotals(selectedItems),
    [selectedItems]
  );
  const feedback = useMemo(
    () => buildNutritionFeedback(totals, targetKcal, targetProtein),
    [totals, targetKcal, targetProtein]
  );

  // Don't show the "empty" state — header already communicates 0 selection
  if (feedback.status === "empty") return null;

  return (
    <div
      className={`rounded-2xl px-4 py-2.5 text-sm font-bold transition-colors ${
        feedbackColorMap[feedback.color]
      }`}
      role="status"
      aria-live="polite"
    >
      {feedback.message}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
 * SingleMealSection  — one breakfast / lunch / dinner / snack section
 * ─────────────────────────────────────────────────────────────────────────── */
function SingleMealSection({
  meal,
  favoriteMeals,
  ratings,
  onFavorite,
  onRate,
  targetKcal,
  targetProtein,
}) {
  const items = Array.isArray(meal.items) ? meal.items : [];

  // Initialise selection: core items (is_default_selected) start selected.
  const [selectedIds, setSelectedIds] = useState(() => {
    const ids = new Set();
    items.forEach((item) => {
      const defaultSelected =
        item.is_default_selected !== undefined
          ? Boolean(item.is_default_selected)
          : item.is_core !== undefined
          ? Boolean(item.is_core)
          : true; // legacy items are selected by default
      if (defaultSelected) ids.add(item.id ?? item.food_id);
    });
    return ids;
  });

  const selectedItems = useMemo(
    () => items.filter((item) => selectedIds.has(item.id ?? item.food_id)),
    [items, selectedIds]
  );

  function handleToggleSelect(item) {
    const key = item.id ?? item.food_id;
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  const totalSelectedKcal = useMemo(
    () =>
      selectedItems.reduce(
        (sum, item) => sum + Number(item.calories ?? item.kcal ?? 0),
        0
      ),
    [selectedItems]
  );

  // Separate core and optional for display order: core first, then optional
  const coreItems = items.filter((item) =>
    item.is_core !== undefined ? Boolean(item.is_core) : true
  );
  const optionalItems = items.filter(
    (item) => item.is_core !== undefined && !item.is_core
  );

  const effectiveTargetKcal = targetKcal || meal.target_kcal || 0;
  const kcalDiff = effectiveTargetKcal > 0 ? totalSelectedKcal - effectiveTargetKcal : 0;
  const kcalDiffPct = effectiveTargetKcal > 0 ? Math.abs(kcalDiff) / effectiveTargetKcal : 1;
  const kcalOnTarget = effectiveTargetKcal > 0 && kcalDiffPct <= 0.15;
  const kcalOver = effectiveTargetKcal > 0 && kcalDiff > effectiveTargetKcal * 0.15;

  return (
    <section className="glass-panel overflow-hidden p-0">
      {/* Meal header */}
      <div className="flex flex-col gap-2 border-b border-brand-border bg-brand-surface/70 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <span className={`h-10 w-1.5 rounded-full ${accentClass(meal.accent)}`} />
          <div>
            <h3 className="text-xl font-black text-brand-text-main">
              {meal.title}
            </h3>
          </div>
        </div>

        {/* Single calorie progress badge */}
        <div className={`flex items-center gap-2 self-start rounded-2xl px-4 py-2 text-sm font-black sm:self-auto ${
          totalSelectedKcal === 0
            ? "bg-slate-100 text-slate-500"
            : kcalOnTarget
            ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100"
            : kcalOver
            ? "bg-orange-50 text-orange-700 ring-1 ring-orange-100"
            : "bg-brand-surface text-brand-text-main ring-1 ring-brand-border"
        }`}>
          {effectiveTargetKcal > 0 ? (
            <span>
              {Math.round(totalSelectedKcal).toLocaleString("vi-VN")}
              <span className="mx-1 font-semibold opacity-50">/</span>
              {Math.round(effectiveTargetKcal).toLocaleString("vi-VN")} kcal
            </span>
          ) : (
            <span>{Math.round(totalSelectedKcal).toLocaleString("vi-VN")} kcal</span>
          )}
        </div>
      </div>

      {/* Gamification score panel — shown when target is set */}
      <MealScorePanel
        selectedItems={selectedItems}
        targetKcal={effectiveTargetKcal}
        mealType={meal.meal_type || meal.title}
      />

      {/* Realtime nutrition feedback — shown only when items are selected */}
      {selectedItems.length > 0 && (
        <div className="px-4 pt-1">
          <NutritionFeedback
            selectedItems={selectedItems}
            targetKcal={effectiveTargetKcal}
            targetProtein={targetProtein || 0}
          />
        </div>
      )}

      {/* ── Core items ───────────────────────────────────────────────── */}
      {coreItems.length > 0 && (
        <div className="p-4 sm:p-5">
          <div className="grid gap-4 lg:grid-cols-2 2xl:grid-cols-3">
            {coreItems.map((item) => (
              <MealCard
                key={item.id ?? item.food_id}
                item={item}
                isSelected={selectedIds.has(item.id ?? item.food_id)}
                onToggleSelect={handleToggleSelect}
                favorite={favoriteMeals.has(item.id ?? item.food_id)}
                rating={ratings[item.id ?? item.food_id]}
                onFavorite={() => onFavorite(item.id ?? item.food_id)}
                onRate={(value) => onRate(item.id ?? item.food_id, value)}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── Optional items ───────────────────────────────────────────── */}
      {optionalItems.length > 0 && (
        <div className="border-t border-brand-border/50 bg-slate-50/40 p-4 sm:p-5">
          <div className="grid gap-4 lg:grid-cols-2 2xl:grid-cols-3">
            {optionalItems.map((item) => (
              <MealCard
                key={item.id ?? item.food_id}
                item={item}
                isSelected={selectedIds.has(item.id ?? item.food_id)}
                onToggleSelect={handleToggleSelect}
                favorite={favoriteMeals.has(item.id ?? item.food_id)}
                rating={ratings[item.id ?? item.food_id]}
                onFavorite={() => onFavorite(item.id ?? item.food_id)}
                onRate={(value) => onRate(item.id ?? item.food_id, value)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Fallback: if no core/optional split available (legacy), render all */}
      {coreItems.length === 0 && optionalItems.length === 0 && items.length > 0 && (
        <div className="grid gap-4 p-4 sm:p-5 lg:grid-cols-2 2xl:grid-cols-3">
          {items.map((item) => (
            <MealCard
              key={item.id ?? item.food_id}
              item={item}
              isSelected={selectedIds.has(item.id ?? item.food_id)}
              onToggleSelect={handleToggleSelect}
              favorite={favoriteMeals.has(item.id ?? item.food_id)}
              rating={ratings[item.id ?? item.food_id]}
              onFavorite={() => onFavorite(item.id ?? item.food_id)}
              onRate={(value) => onRate(item.id ?? item.food_id, value)}
            />
          ))}
        </div>
      )}
    </section>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
 * MealSection  — top-level section rendering all meals
 * ─────────────────────────────────────────────────────────────────────────── */
export default function MealSection({
  meals,
  favoriteMeals,
  ratings,
  onFavorite,
  onRate,
  nutritionTarget,
}) {
  const totalMeals = meals.reduce((sum, meal) => sum + meal.items.length, 0);

  // Per-meal protein target = daily protein / number of meals
  const mealCount = meals.length || 1;
  const dailyProtein = Number(
    nutritionTarget?.protein_g ??
      nutritionTarget?.protein ??
      nutritionTarget?.target_protein ??
      0
  );
  const perMealProtein = dailyProtein > 0 ? dailyProtein / mealCount : 0;

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-brand-primary">
            Nhật ký ăn uống
          </p>
          <h2 className="mt-2 text-2xl font-black text-brand-text-main">
            Bữa ăn hôm nay
          </h2>
        </div>
        <div className="rounded-2xl bg-brand-surface px-4 py-3 text-sm font-black text-brand-text-sub shadow-sm ring-1 ring-brand-border">
          {totalMeals} món đã gợi ý
        </div>
      </div>

      <div className="space-y-5">
        {meals.map((meal) => (
          <SingleMealSection
            key={meal.title || meal.meal_type}
            meal={meal}
            favoriteMeals={favoriteMeals}
            ratings={ratings}
            onFavorite={onFavorite}
            onRate={onRate}
            targetKcal={meal.target_kcal || 0}
            targetProtein={perMealProtein}
          />
        ))}
      </div>
    </section>
  );
}

function accentClass(accent) {
  if (accent === "blue" || accent === "sky") return "bg-sky-500";
  if (accent === "orange" || accent === "amber") return "bg-brand-orange";
  return "bg-brand-primary";
}
