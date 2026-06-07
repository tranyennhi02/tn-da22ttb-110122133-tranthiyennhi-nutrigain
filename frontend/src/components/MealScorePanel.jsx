import { useMemo } from "react";
import { computeMealRank, computeAlmostPerfect, computeDiversity, previewPoints } from "../utils/mealRank";

/* ─── Rank color tokens ───────────────────────────────────────────────────── */
const RANK_STYLES = {
  SS: {
    badge:   "bg-amber-400 text-white shadow-amber-200",
    ring:    "ring-amber-300",
    glow:    "shadow-amber-100",
  },
  S: {
    badge:   "bg-emerald-500 text-white shadow-emerald-200",
    ring:    "ring-emerald-300",
    glow:    "shadow-emerald-100",
  },
  A: {
    badge:   "bg-green-500 text-white shadow-green-200",
    ring:    "ring-green-300",
    glow:    "shadow-green-100",
  },
  B: {
    badge:   "bg-blue-500 text-white shadow-blue-200",
    ring:    "ring-blue-300",
    glow:    "shadow-blue-100",
  },
  C: {
    badge:   "bg-amber-500 text-white shadow-amber-200",
    ring:    "ring-amber-300",
    glow:    "shadow-amber-100",
  },
  D: {
    badge:   "bg-red-500 text-white shadow-red-200",
    ring:    "ring-red-300",
    glow:    "shadow-red-100",
  },
};

/* ─── Component ───────────────────────────────────────────────────────────── */

/**
 * MealScorePanel
 *
 * Props:
 *  selectedItems  – array of currently selected food items
 *  targetKcal     – kcal target for this meal (0 = hidden)
 *  mealType       – "breakfast" | "lunch" | "dinner" | "snacks"
 */
export default function MealScorePanel({ selectedItems, targetKcal, mealType }) {
  const totalKcal = useMemo(
    () => selectedItems.reduce((s, item) => s + Number(item.calories ?? item.kcal ?? 0), 0),
    [selectedItems]
  );

  const rankResult   = useMemo(() => computeMealRank(totalKcal, targetKcal),       [totalKcal, targetKcal]);
  const almostResult = useMemo(() => computeAlmostPerfect(totalKcal, targetKcal),  [totalKcal, targetKcal]);
  const diversity    = useMemo(() => computeDiversity(selectedItems),               [selectedItems]);
  const points       = useMemo(
    () => rankResult ? previewPoints(rankResult.rank, diversity.diversityPoints, almostResult.active) : 0,
    [rankResult, diversity.diversityPoints, almostResult.active]
  );

  // Don't render when no target or no items
  if (!targetKcal || targetKcal <= 0) return null;

  const hasSelection = selectedItems.length > 0;
  const styles = rankResult ? RANK_STYLES[rankResult.rank] : RANK_STYLES["D"];

  return (
    <div
      className="transition-all duration-300 px-4 pb-1 pt-0"
      role="region"
      aria-label="Đánh giá bữa ăn"
    >
      <div className={`
        rounded-2xl border border-slate-100 bg-white/80 backdrop-blur-sm
        px-4 py-3 shadow-sm transition-all duration-300
        ${rankResult ? `ring-1 ${styles.ring}` : ""}
      `}>

        {/* ── Main row ── */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 sm:flex-nowrap">

          {/* Rank badge */}
          <div className="flex-shrink-0">
            {hasSelection && rankResult ? (
              <span className={`
                inline-flex items-center justify-center
                h-9 min-w-[3rem] rounded-xl px-3
                text-sm font-black tracking-wider
                transition-all duration-300 shadow-md
                ${styles.badge}
              `}>
                {rankResult.rank}
              </span>
            ) : (
              <span className="inline-flex items-center justify-center h-9 min-w-[3rem] rounded-xl px-3 text-sm font-black bg-slate-100 text-slate-400">
                –
              </span>
            )}
          </div>

          {/* Accuracy */}
          <div className="flex items-center gap-1.5 text-sm">
            <span className="text-slate-400 font-medium">📊</span>
            <span className="font-black text-slate-800">
              {hasSelection && rankResult ? `${rankResult.accuracyPct}%` : "–"}
            </span>
            <span className="text-slate-400 text-xs font-medium">chính xác</span>
          </div>

          {/* Divider */}
          <div className="hidden sm:block h-5 w-px bg-slate-200" />

          {/* Points preview */}
          <div className="flex items-center gap-1.5 text-sm">
            <span className="text-slate-400 font-medium">🏆</span>
            <span className="font-black text-slate-800">
              {hasSelection && rankResult ? `+${points}` : "+0"}
            </span>
            <span className="text-slate-400 text-xs font-medium">điểm</span>
          </div>

          {/* Divider */}
          <div className="hidden sm:block h-5 w-px bg-slate-200" />

          {/* Diversity */}
          <div className="flex items-center gap-1.5 text-sm">
            <span className="text-slate-400 font-medium">🥗</span>
            <span className={`font-black transition-all duration-300 ${
              diversity.diversityPoints > 0 ? "text-emerald-600" : "text-slate-500"
            }`}>
              {diversity.diversityPoints > 0 ? `+${diversity.diversityPoints}` : "0"}
            </span>
            <span className="text-slate-400 text-xs font-medium">đa dạng</span>
          </div>

          {/* Rank label — pushes right on desktop */}
          {hasSelection && rankResult && (
            <div className="sm:ml-auto">
              <span className="text-sm font-bold text-slate-700">
                {rankResult.label}
              </span>
            </div>
          )}
        </div>

        {/* ── Almost Perfect nudge ── */}
        {hasSelection && almostResult.active && rankResult?.rank !== "SS" && (
          <div className="mt-2.5 flex items-center gap-2 rounded-xl bg-amber-50 px-3 py-2 ring-1 ring-amber-100 transition-all duration-300">
            <span className="text-base leading-none">🔥</span>
            <span className="text-xs font-black text-amber-700">
              Chỉ còn thiếu{" "}
              <span className="text-amber-900">{almostResult.deficit} kcal</span>
              {" "}để đạt Bữa Ăn Hoàn Hảo!
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
