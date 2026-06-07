import { useEffect, useState } from "react";
import { Check } from "lucide-react";
import { getGamificationSummary, completeGamificationChallenge } from "../../services/apiService";
import { loadGamificationStats } from "../../utils/mealRank";

/* ─── Level config (mirrors mealRank.js previewPoints tiers) ─────────────── */
const LEVEL_TIERS = [
  { min: 0,    max: 99,   level: 1,  title: "Người Mới" },
  { min: 100,  max: 299,  level: 5,  title: "Ăn Uống Điều Độ" },
  { min: 300,  max: 699,  level: 10, title: "Chuyên Gia Bữa Ăn" },
  { min: 700,  max: 1499, level: 20, title: "Bậc Thầy Dinh Dưỡng" },
  { min: 1500, max: null, level: 30, title: "Cao Thủ Calories" },
];

function resolveLevel(points) {
  const p = Number(points) || 0;
  const tier = LEVEL_TIERS.slice().reverse().find((t) => p >= t.min) ?? LEVEL_TIERS[0];
  const nextTier = LEVEL_TIERS.find((t) => t.min > tier.min);
  const progress = nextTier
    ? Math.min(100, Math.round(((p - tier.min) / (nextTier.min - tier.min)) * 100))
    : 100;
  const pointsToNext = nextTier ? Math.max(0, nextTier.min - p) : 0;
  return { ...tier, progress, pointsToNext, totalPoints: p };
}

/* ─── Badge catalog ─────────────────────────────────────────────────────── */
const BADGE_META = {
  first_meal_plan:             { image: "/assets/badges/first_meal_plan.svg",             label: "Kế hoạch bữa ăn đầu tiên" },
  first_weight_log:            { image: "/assets/badges/first_weight_log.svg",            label: "Ghi cân đầu tiên" },
  first_complete_day:          { image: "/assets/badges/first_complete_day.svg",          label: "Ngày ăn đủ đầu tiên" },
  three_active_days:           { image: "/assets/badges/three_active_days.svg",           label: "3 ngày liên tục" },
  three_balanced_days_in_week: { image: "/assets/badges/three_balanced_days_in_week.svg", label: "3 ngày cân bằng trong tuần" },
  perfect_calories:            { image: "/assets/badges/perfect_calories.svg",            label: "Calories hoàn hảo" },
  discipline_eater:            { image: "/assets/badges/discipline_eater.svg",            label: "Kỷ luật ăn uống" },
  diverse_menu:                { image: "/assets/badges/diverse_menu.svg",                label: "Thực đơn đa dạng" },
};

function badgeMeta(key) {
  return BADGE_META[key] ?? { image: "/assets/badges/default.svg", label: "Huy hiệu" };
}

/* ─── Day-of-week labels ────────────────────────────────────────────────── */
const DAY_LABELS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];

/* ─── Component ─────────────────────────────────────────────────────────── */
export default function GentleMotivationPanel({ onAction, refreshKey = 0 }) {
  const [summary, setSummary]     = useState(null);
  const [loading, setLoading]     = useState(false);
  const [completing, setCompleting] = useState(false);
  const [localStats, setLocalStats] = useState(() => loadGamificationStats());

  // Reload stats from localStorage whenever refreshKey changes OR page becomes visible
  useEffect(() => {
    setLocalStats(loadGamificationStats());
  }, [refreshKey]);

  useEffect(() => {
    function onVisible() {
      if (document.visibilityState === "visible") {
        setLocalStats(loadGamificationStats());
      }
    }
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, []);

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true);
      try {
        const data = await getGamificationSummary();
        if (mounted) setSummary(data);
      } catch (err) {
        console.warn("Gamification load failed", err);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => (mounted = false);
  }, [refreshKey]);

  async function handleCompleteChallenge() {
    if (!summary?.today_challenge) return;
    if (summary.today_challenge.key === "first_complete_day") {
      if (onAction) onAction();
      return;
    }
    setCompleting(true);
    try {
      await completeGamificationChallenge(summary.today_challenge.key);
      const data = await getGamificationSummary();
      setSummary(data);
      if (onAction) onAction();
    } catch (err) {
      console.warn("Complete challenge error", err);
    } finally {
      setCompleting(false);
    }
  }

  /* ── Derived values ─────────────────────────────────────────────────── */
  const streakDays          = summary?.streak?.current ?? 0;
  const safeStreakDays      = Number(streakDays) || 0;
  const weeklyGoalDays      = 7;
  const weeklyCycleDay      = safeStreakDays > 0 ? ((safeStreakDays - 1) % weeklyGoalDays) + 1 : 0;
  const weeklyRemainingDays = Math.max(0, weeklyGoalDays - weeklyCycleDay);
  const isWeeklyComplete    = safeStreakDays > 0 && weeklyCycleDay === weeklyGoalDays;
  const weeklyProgress      = weeklyCycleDay > 0 ? (weeklyCycleDay / weeklyGoalDays) * 100 : 0;
  const monthCareDays       = summary?.month?.days ?? summary?.monthly?.days ?? null;
  const challengeDone       = String(summary?.today_challenge?.status || "").toLowerCase() === "completed";
  const pendingEatingStreak = summary?.today_challenge?.key === "first_complete_day" && !challengeDone;

  const totalPoints = localStats.totalPoints;
  const levelInfo   = summary?.level
    ? {
        level:        summary.level,
        title:        summary.level_title ?? resolveLevel(totalPoints).title,
        progress:     Math.round(summary.level_progress_pct ?? resolveLevel(totalPoints).progress),
        pointsToNext: summary.points_to_next_level ?? resolveLevel(totalPoints).pointsToNext,
        totalPoints,
      }
    : resolveLevel(totalPoints);

  const streakStatusPill  = safeStreakDays === 0 ? "Nghỉ nhẹ" : isWeeklyComplete ? "Tuần mới bắt đầu" : "Đang duy trì";
  const streakSupportCopy =
    safeStreakDays === 0
      ? "Không sao, hôm nay mình bắt đầu lại nhẹ nhàng."
      : isWeeklyComplete
      ? "Bạn đã hoàn thành một vòng 7 ngày. Tiếp tục nhé!"
      : "Mỗi ngày quay lại đều tính. Tiến bộ nhỏ vẫn là tiến bộ.";

  const supportMessages = [
    summary?.encouragement,
    "Ăn đều hơn một chút cũng là tiến bộ.",
    "Bạn không cần hoàn hảo, chỉ cần quay lại nhẹ nhàng.",
    "Một ngày chưa tốt không xoá đi cả hành trình.",
    "Tăng cân lành mạnh cần thời gian, bạn đang đi đúng hướng.",
  ].filter(Boolean);
  const encouragement = supportMessages.length
    ? supportMessages[(new Date().getDate() + safeStreakDays) % supportMessages.length]
    : "";

  return (
    <section className="space-y-4">

      {/* ── 1. Level & Points ─────────────────────────────────────────── */}
      <article className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400 mb-3">Cấp độ hiện tại</p>
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black text-slate-900">{levelInfo.title}</span>
            <span className="text-sm font-medium text-slate-400">Lv.{levelInfo.level}</span>
          </div>
          <span className="text-xs text-slate-400">
            {levelInfo.totalPoints.toLocaleString("vi-VN")} điểm
          </span>
        </div>
        <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden mt-3">
          <div
            className="h-full rounded-full bg-emerald-600 transition-all duration-700"
            style={{ width: `${levelInfo.progress}%` }}
          />
        </div>
        {levelInfo.pointsToNext > 0 && (
          <p className="mt-2 text-xs text-slate-400 text-right">
            còn {levelInfo.pointsToNext.toLocaleString("vi-VN")} điểm lên cấp tiếp theo
          </p>
        )}
      </article>

      {/* ── 2. Streak ─────────────────────────────────────────────────── */}
      <article className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest">Chuỗi duy trì</h3>
          <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
            isWeeklyComplete
              ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200"
              : "bg-slate-100 text-slate-600 ring-1 ring-slate-200"
          }`}>
            {isWeeklyComplete && <Check size={11} />}
            {streakStatusPill}
          </span>
        </div>

        <div className="flex items-baseline gap-2 mb-1">
          <strong className="text-5xl font-black text-slate-900 leading-none">{streakDays}</strong>
          <span className="text-base font-medium text-slate-500">ngày</span>
        </div>
        <p className="text-xs text-slate-400 mb-4">{streakSupportCopy}</p>

        {/* 7-cell day strip */}
        <div className="grid grid-cols-7 gap-1.5 mb-4">
          {DAY_LABELS.map((day, i) => {
            const filled = i < weeklyCycleDay;
            const isToday = i === weeklyCycleDay - 1 && weeklyCycleDay > 0;
            return (
              <div key={day} className="flex flex-col items-center gap-1">
                <div className={`h-7 w-full rounded-md transition-all ${
                  filled
                    ? isToday
                      ? "bg-slate-900"
                      : "bg-slate-700"
                    : "bg-slate-100"
                }`} />
                <span className={`text-[10px] font-medium ${filled ? "text-slate-700" : "text-slate-300"}`}>
                  {day}
                </span>
              </div>
            );
          })}
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center rounded-xl border border-slate-100 bg-slate-50 py-3">
            <div className="text-lg font-black text-slate-900">{weeklyCycleDay}/{weeklyGoalDays}</div>
            <div className="mt-0.5 text-[11px] text-slate-400">tuần này</div>
          </div>
          <div className="text-center rounded-xl border border-slate-100 bg-slate-50 py-3">
            <div className="text-lg font-black text-slate-900">{monthCareDays ?? "—"}</div>
            <div className="mt-0.5 text-[11px] text-slate-400">tháng này</div>
          </div>
          <div className="text-center rounded-xl border border-slate-100 bg-slate-50 py-3">
            <div className="text-lg font-black text-slate-900">{challengeDone ? "3/3" : "—"}</div>
            <div className="mt-0.5 text-[11px] text-slate-400">bữa hôm nay</div>
          </div>
        </div>
      </article>

      {/* ── 3. Today's Challenge & Badges ─────────────────────────────── */}
      <div className="grid gap-4 lg:grid-cols-2">

        {/* Today's Challenge */}
        <article className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400 mb-4">Thử thách hôm nay</p>
          <div className="mb-4">
            <div className="text-sm font-bold text-slate-900 mb-1">
              {summary?.today_challenge?.title || "Ăn đều hôm nay"}
            </div>
            <div className="text-xs text-slate-500 leading-relaxed">
              {summary?.today_challenge?.description || "Hoàn thành đủ bữa sáng, trưa và tối"}
            </div>
          </div>
          {challengeDone && (
            <p className="text-xs text-slate-500 mb-3">Hôm nay: Đã hoàn thành đầy đủ 3 bữa</p>
          )}
          <div className="flex items-center justify-between pt-3 border-t border-slate-100">
            <span className="text-xs text-slate-400">
              {pendingEatingStreak ? "Bắt đầu lần đầu" : challengeDone ? "" : "Đang thực hiện"}
            </span>
            <button
              onClick={handleCompleteChallenge}
              disabled={completing || challengeDone}
              className={`inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-semibold transition ${
                challengeDone
                  ? "bg-slate-50 text-slate-500 ring-1 ring-slate-200 cursor-default"
                  : "bg-slate-900 text-white hover:bg-slate-800"
              }`}
            >
              {challengeDone ? (
                <><Check size={13} />Đã hoàn thành</>
              ) : (
                <>{completing ? "Đang xử lý..." : "Hoàn thành"}</>
              )}
            </button>
          </div>
        </article>

        {/* Badges */}
        <article className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400 mb-4">Huy hiệu &amp; Thành tích</p>
          {loading ? (
            <div className="grid grid-cols-4 gap-3 animate-pulse">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="aspect-square rounded-xl bg-slate-100" />
              ))}
            </div>
          ) : (
            <>
              <div className="grid grid-cols-4 gap-3">
                {Object.entries(BADGE_META).map(([key, meta]) => {
                  const isUnlocked = summary?.achievements?.some((a) => a.key === key);
                  const achieved   = summary?.achievements?.find((a) => a.key === key);
                  return (
                    <div key={key} className="flex flex-col items-center gap-1.5 group">
                      <div className="relative h-12 w-12">
                        <img
                          src={meta.image}
                          alt={meta.label}
                          className={`h-12 w-12 rounded-xl object-cover transition-all ${
                            !isUnlocked ? "grayscale opacity-30" : "drop-shadow-sm"
                          }`}
                        />
                      </div>
                      <span className={`text-[10px] text-center leading-tight ${
                        isUnlocked ? "text-slate-600 font-medium" : "text-slate-300"
                      }`}>
                        {isUnlocked ? (achieved?.title ?? meta.label) : meta.label}
                      </span>
                    </div>
                  );
                })}
              </div>
              {!summary?.achievements?.length && (
                <p className="mt-4 text-xs text-slate-400 text-center">
                  Thành tích sẽ được mở khóa khi bạn đạt cột mốc
                </p>
              )}
            </>
          )}
        </article>
      </div>

      {/* ── 4. Encouragement ──────────────────────────────────────────── */}
      {encouragement && (
        <blockquote className="border-l-2 border-slate-300 pl-4 py-1 mx-1">
          <p className="text-sm text-slate-500 italic">{encouragement}</p>
        </blockquote>
      )}

    </section>
  );
}
