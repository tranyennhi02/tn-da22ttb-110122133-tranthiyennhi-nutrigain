import { useEffect, useState } from "react";
import { Check, Flame, Target, Trophy, Sparkles } from "lucide-react";
import { getGamificationSummary, completeGamificationChallenge } from "../../services/apiService";
import { loadGamificationStats } from "../../utils/mealRank";

/* ─── Level config ───────────────────────────────────────────────────────── */
const LEVEL_TIERS = [
  { min: 0,    max: 100,  level: 1, title: "Người Mới" },
  { min: 101,  max: 250,  level: 2, title: "Khởi Động Tốt" },
  { min: 251,  max: 500,  level: 3, title: "Ăn Uống Điều Độ" },
  { min: 501,  max: 900,  level: 4, title: "Chuyên Gia Bữa Ăn" },
  { min: 901,  max: 1400, level: 5, title: "Bậc Thầy Dinh Dưỡng" },
  { min: 1401, max: 2000, level: 6, title: "Cao Thủ Calories" },
  { min: 2001, max: 2800, level: 7, title: "Nhà Vô Địch Sức Khỏe" },
  { min: 2801, max: null, level: 8, title: "Huyền Thoại NutriGain" },
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
// Action-based badges — unlocked by backend when user completes real actions
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

// Level-based badges — unlocked automatically when totalPoints reaches the threshold
const LEVEL_BADGE_META = [
  { key: "level_1", image: "/assets/badges/default.svg", label: "Người Mới",           minPoints: 0    },
  { key: "level_2", image: "/assets/badges/default.svg", label: "Khởi Động Tốt",       minPoints: 101  },
  { key: "level_3", image: "/assets/badges/default.svg", label: "Ăn Uống Điều Độ",    minPoints: 251  },
  { key: "level_4", image: "/assets/badges/default.svg", label: "Chuyên Gia Bữa Ăn",  minPoints: 501  },
  { key: "level_5", image: "/assets/badges/default.svg", label: "Bậc Thầy Dinh Dưỡng", minPoints: 901  },
  { key: "level_6", image: "/assets/badges/default.svg", label: "Cao Thủ Calories",    minPoints: 1401 },
  { key: "level_7", image: "/assets/badges/default.svg", label: "Nhà Vô Địch",         minPoints: 2001 },
  { key: "level_8", image: "/assets/badges/default.svg", label: "Huyền Thoại",         minPoints: 2801 },
];

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
      ? "Tuyệt vời! Bạn đã hoàn thành vòng 7 ngày."
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
    <section className="space-y-6">

      {/* ── 1. Level & Points ─────────────────────────────────────────── */}
      <article className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-teal-500 to-emerald-500 p-6 shadow-lg shadow-emerald-200/50 border border-teal-400">
        <div className="absolute top-0 right-0 -mt-4 -mr-4 h-32 w-32 rounded-full bg-white opacity-20 blur-2xl"></div>
        <div className="absolute bottom-0 left-0 -mb-4 -ml-4 h-24 w-24 rounded-full bg-teal-900 opacity-20 blur-xl"></div>
        
        <div className="relative z-10">
          <p className="text-[11px] font-bold uppercase tracking-widest text-emerald-50 mb-3 drop-shadow-sm">Cấp độ hiện tại</p>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-baseline gap-2">
              <span className="text-3xl sm:text-4xl font-black text-white drop-shadow-md tracking-tight">{levelInfo.title}</span>
              <span className="text-sm font-bold text-teal-900 bg-emerald-100 shadow-sm px-2.5 py-0.5 rounded-lg">Lv.{levelInfo.level}</span>
            </div>
            <span className="text-sm font-bold text-white bg-white/20 px-4 py-1.5 rounded-full backdrop-blur-sm shadow-inner border border-white/30">
              {levelInfo.totalPoints.toLocaleString("vi-VN")} điểm
            </span>
          </div>
          <div className="h-2.5 rounded-full bg-teal-900/30 overflow-hidden mt-5 backdrop-blur-sm shadow-inner">
            <div
              className="h-full rounded-full bg-white shadow-[0_0_12px_rgba(255,255,255,0.8)] transition-all duration-1000 ease-out"
              style={{ width: `${levelInfo.progress}%` }}
            />
          </div>
          {levelInfo.pointsToNext > 0 && (
            <p className="mt-3 text-xs font-medium text-emerald-50 text-right drop-shadow-sm">
              Còn <span className="font-extrabold text-white">{levelInfo.pointsToNext.toLocaleString("vi-VN")}</span> điểm lên cấp tiếp theo
            </p>
          )}
        </div>
      </article>

      {/* ── 2. Streak ─────────────────────────────────────────────────── */}
      <article className="rounded-3xl border border-teal-100 bg-white p-6 sm:p-8 shadow-xl shadow-teal-100/40">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-orange-100 text-orange-500 shadow-inner">
              <Flame size={20} fill="currentColor" />
            </div>
            <h3 className="text-sm font-extrabold text-teal-800 uppercase tracking-widest">Chuỗi duy trì</h3>
          </div>
          <span className={`inline-flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-bold shadow-sm transition-colors ${
            isWeeklyComplete
              ? "bg-gradient-to-r from-emerald-100 to-teal-100 text-teal-700 border border-teal-200"
              : "bg-slate-50 text-slate-500 border border-slate-200"
          }`}>
            {isWeeklyComplete && <Check size={14} strokeWidth={3} />}
            {streakStatusPill}
          </span>
        </div>

        <div className="flex flex-col lg:flex-row gap-8 items-center">
          <div className="flex flex-col items-center justify-center p-6 rounded-3xl bg-gradient-to-b from-orange-50 to-white border border-orange-100 min-w-[160px] shadow-[inset_0_2px_10px_rgba(0,0,0,0.02)]">
            <div className="flex items-baseline gap-1">
              <strong className="text-7xl font-black text-orange-500 tracking-tighter drop-shadow-sm">{streakDays}</strong>
              <span className="text-lg font-bold text-orange-300">ngày</span>
            </div>
            <p className="text-[11px] font-medium text-orange-400 mt-2 text-center leading-tight max-w-[130px]">{streakSupportCopy}</p>
          </div>

          <div className="flex-1 w-full">
            {/* 7-cell day strip */}
            <div className="flex justify-between gap-2 sm:gap-3 mb-8">
              {DAY_LABELS.map((day, i) => {
                const filled = i < weeklyCycleDay;
                const isToday = i === weeklyCycleDay - 1 && weeklyCycleDay > 0;
                return (
                  <div key={day} className="flex flex-col items-center gap-2 flex-1">
                    <div className={`h-10 w-full rounded-xl transition-all duration-300 flex items-center justify-center ${
                      filled
                        ? isToday
                          ? "bg-teal-500 shadow-md shadow-teal-200 scale-105"
                          : "bg-teal-100"
                        : "bg-slate-100"
                    }`}>
                      {filled && <Check size={16} className={isToday ? "text-white" : "text-teal-600"} strokeWidth={3} />}
                    </div>
                    <span className={`text-xs font-bold ${filled ? (isToday ? "text-teal-600" : "text-teal-400") : "text-slate-300"}`}>
                      {day}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-3 gap-4 sm:gap-6">
              <div className="flex flex-col items-center justify-center rounded-2xl border border-teal-50 bg-teal-50/50 py-4 transition-colors hover:bg-teal-50">
                <div className="text-2xl font-black text-teal-700">{weeklyCycleDay}/{weeklyGoalDays}</div>
                <div className="mt-1 text-[10px] sm:text-xs font-bold text-teal-400 uppercase tracking-wider">Tuần này</div>
              </div>
              <div className="flex flex-col items-center justify-center rounded-2xl border border-indigo-50 bg-indigo-50/50 py-4 transition-colors hover:bg-indigo-50">
                <div className="text-2xl font-black text-indigo-700">{monthCareDays ?? "—"}</div>
                <div className="mt-1 text-[10px] sm:text-xs font-bold text-indigo-400 uppercase tracking-wider">Tháng này</div>
              </div>
              <div className="flex flex-col items-center justify-center rounded-2xl border border-sky-50 bg-sky-50/50 py-4 transition-colors hover:bg-sky-50">
                <div className="text-2xl font-black text-sky-700">{challengeDone ? "3/3" : "—"}</div>
                <div className="mt-1 text-[10px] sm:text-xs font-bold text-sky-400 uppercase tracking-wider">Hôm nay</div>
              </div>
            </div>
          </div>
        </div>
      </article>

      {/* ── 3. Today's Challenge & Badges ─────────────────────────────── */}
      <div className="grid gap-6 lg:grid-cols-2">

        {/* Today's Challenge */}
        <article className="rounded-3xl border border-blue-100 bg-white p-6 shadow-xl shadow-blue-50/40 flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 right-0 p-8 opacity-5">
            <Target size={120} />
          </div>
          <div className="relative z-10">
            <div className="flex items-center gap-3 mb-6">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 text-blue-600 shadow-inner">
                <Target size={20} strokeWidth={2.5} />
              </div>
              <p className="text-sm font-extrabold uppercase tracking-widest text-blue-800">Thử thách hôm nay</p>
            </div>
            
            <div className="mb-6 p-5 rounded-2xl bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100/50 shadow-sm">
              <h4 className="text-xl font-black text-blue-900 mb-2">
                {summary?.today_challenge?.title || "Ăn đều hôm nay"}
              </h4>
              <p className="text-sm text-blue-700/80 font-medium leading-relaxed">
                {summary?.today_challenge?.description || "Hoàn thành đủ bữa sáng, trưa và tối để duy trì thói quen tốt."}
              </p>
            </div>
            
            {challengeDone && (
              <div className="flex items-center gap-2 text-sm font-bold text-emerald-700 mb-6 bg-emerald-50 px-4 py-2.5 rounded-xl border border-emerald-100 w-fit">
                <Check size={18} strokeWidth={3} className="text-emerald-500" />
                <span>Bạn đã hoàn thành xuất sắc!</span>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between pt-5 border-t border-slate-100 mt-auto relative z-10">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              {pendingEatingStreak ? "Sẵn sàng" : challengeDone ? "Hoàn tất" : "Đang thực hiện"}
            </span>
            <button
              onClick={handleCompleteChallenge}
              disabled={completing || challengeDone}
              className={`inline-flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-bold transition-all shadow-md ${
                challengeDone
                  ? "bg-slate-50 text-slate-400 ring-1 ring-slate-200 cursor-default shadow-none"
                  : "bg-blue-600 text-white hover:bg-blue-700 hover:shadow-lg hover:shadow-blue-200 hover:-translate-y-0.5 active:translate-y-0"
              }`}
            >
              {challengeDone ? (
                <><Check size={18} strokeWidth={3} />Đã hoàn thành</>
              ) : (
                <>{completing ? "Đang xử lý..." : "Xác nhận hoàn thành"}</>
              )}
            </button>
          </div>
        </article>

        {/* Badges */}
        <article className="rounded-3xl border border-violet-100 bg-white p-6 shadow-xl shadow-violet-50/40">
          <div className="flex items-center gap-3 mb-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-violet-100 text-violet-600 shadow-inner">
              <Trophy size={20} strokeWidth={2.5} />
            </div>
            <p className="text-sm font-extrabold uppercase tracking-widest text-violet-800">Bộ sưu tập huy hiệu</p>
          </div>

          {loading ? (
            <div className="grid grid-cols-4 gap-4 animate-pulse">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="aspect-square rounded-2xl bg-slate-100" />
              ))}
            </div>
          ) : (
            <div className="space-y-6">
              {/* Action-based badges */}
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-4 flex items-center gap-3">
                  <span>Hành động</span>
                  <span className="h-px flex-1 bg-slate-100"></span>
                </p>
                <div className="grid grid-cols-4 gap-x-2 gap-y-5">
                  {Object.entries(BADGE_META).map(([key, meta]) => {
                    const isUnlocked = summary?.achievements?.some((a) => a.key === key);
                    const achieved   = summary?.achievements?.find((a) => a.key === key);
                    return (
                      <div key={key} className="flex flex-col items-center gap-2 group">
                        <div className={`relative p-2.5 rounded-2xl transition-all duration-300 ${
                          isUnlocked ? "bg-amber-50 hover:bg-amber-100 hover:-translate-y-1 shadow-sm" : "bg-slate-50"
                        }`}>
                          <img
                            src={meta.image}
                            alt={meta.label}
                            className={`h-12 w-12 object-contain transition-all duration-300 ${
                              !isUnlocked ? "grayscale opacity-25" : "drop-shadow-md group-hover:scale-110"
                            }`}
                          />
                          {isUnlocked && (
                            <div className="absolute -bottom-1 -right-1 bg-amber-400 rounded-full p-0.5 border-2 border-white shadow-sm">
                              <Check size={12} className="text-white" strokeWidth={4} />
                            </div>
                          )}
                        </div>
                        <span className={`text-[10px] text-center font-bold leading-tight px-1 ${
                          isUnlocked ? "text-amber-700" : "text-slate-400"
                        }`}>
                          {isUnlocked ? (achieved?.title ?? meta.label) : meta.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Level-based badges */}
              <div className="pt-2">
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-4 flex items-center gap-3">
                  <span>Cấp độ</span>
                  <span className="h-px flex-1 bg-slate-100"></span>
                </p>
                <div className="grid grid-cols-4 gap-x-2 gap-y-5">
                  {LEVEL_BADGE_META.map((badge) => {
                    const isUnlocked = totalPoints >= badge.minPoints;
                    return (
                      <div key={badge.key} className="flex flex-col items-center gap-2 group">
                        <div className={`relative h-16 w-16 rounded-2xl flex items-center justify-center text-[13px] font-black transition-all duration-300 ${
                          isUnlocked
                            ? "bg-gradient-to-br from-teal-400 to-emerald-600 text-white shadow-lg shadow-emerald-200/60 hover:-translate-y-1 hover:shadow-xl hover:shadow-emerald-300/50 border border-teal-300"
                            : "bg-slate-100 text-slate-300 border border-slate-200"
                        }`}>
                          {`Lv.${badge.key.replace("level_", "")}`}
                          {isUnlocked && (
                            <span className="absolute -top-1.5 -right-1.5 h-4 w-4 rounded-full bg-amber-400 border-2 border-white shadow-sm flex items-center justify-center">
                              <span className="w-1.5 h-1.5 rounded-full bg-white"></span>
                            </span>
                          )}
                        </div>
                        <span className={`text-[10px] text-center font-bold leading-tight px-1 ${
                          isUnlocked ? "text-teal-700" : "text-slate-400"
                        }`}>
                          {badge.label}
                        </span>
                        {!isUnlocked && (
                          <span className="text-[9px] font-bold text-slate-400 bg-slate-50 px-2 py-0.5 rounded-md border border-slate-100">{badge.minPoints} đ</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {!summary?.achievements?.length && totalPoints < 101 && (
                <div className="mt-4 bg-slate-50 rounded-2xl p-4 border border-slate-100">
                  <p className="text-xs font-semibold text-slate-500 text-center">
                    Thành tích sẽ được mở khóa khi bạn đạt cột mốc đầu tiên
                  </p>
                </div>
              )}
            </div>
          )}
        </article>
      </div>

      {/* ── 4. Encouragement ──────────────────────────────────────────── */}
      {encouragement && (
        <div className="flex items-center gap-3 rounded-2xl bg-gradient-to-r from-teal-50 to-emerald-50/30 p-5 border-l-4 border-teal-400 shadow-sm">
          <div className="p-2 bg-white rounded-full shadow-sm text-teal-500">
            <Sparkles size={20} strokeWidth={2.5} />
          </div>
          <p className="text-sm font-bold text-teal-800 leading-relaxed">{encouragement}</p>
        </div>
      )}

    </section>
  );
}

