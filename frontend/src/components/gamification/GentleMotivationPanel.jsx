import { useEffect, useState } from "react";
import { Check, Flame, Heart, Leaf, Sparkles, Star, Target, Trophy } from "lucide-react";
import { getGamificationSummary, completeGamificationChallenge } from "../../services/apiService";

export default function GentleMotivationPanel({ onAction, refreshKey = 0 }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [completing, setCompleting] = useState(false);

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

  const streakDays = summary?.streak?.current ?? 0;
  const weeklyGoalDays = 7;
  const weeklyProgress = Math.min(100, Math.max(0, (streakDays / weeklyGoalDays) * 100));
  const recentAchievements = summary?.achievements?.length
    ? summary.achievements.slice(0, 3)
    : [
        { key: "meal-today", title: "Ăn đều hôm nay" },
        { key: "gentle-start", title: "Bắt đầu nhẹ nhàng" },
        { key: "weight-check", title: "Theo dõi cân nặng" },
      ];
  const challengeDone = String(summary?.today_challenge?.status || "").toLowerCase() === "completed";
  const pendingEatingStreak = summary?.today_challenge?.key === "first_complete_day" && !challengeDone;
  const encouragement = summary?.encouragement || "Ăn đều hơn một chút cũng là tiến bộ.";

  return (
    <section className="mt-8 rounded-3xl border border-emerald-100 bg-gradient-to-br from-emerald-50/50 to-white p-6 shadow-sm sm:p-8">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-600">
            <Sparkles size={24} strokeWidth={2.4} />
          </div>
          <div>
            <h2 className="text-xl font-black text-slate-900">Động lực nhẹ nhàng</h2>
            <p className="text-sm font-semibold text-slate-500">Những ghi nhận nhỏ để bạn duy trì thói quen, không áp lực.</p>
          </div>
        </div>
      </div>

      {/* Grid */}
      <div className="mt-8 grid gap-6 md:grid-cols-3">
        {/* Streak Card */}
        <article className="flex flex-col justify-between rounded-2xl border border-orange-100 bg-orange-50/50 p-5">
          <div>
            <div className="flex items-center justify-between">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-orange-100 text-orange-500">
                <Flame size={24} fill="currentColor" />
              </div>
              <span className="rounded-full bg-orange-100 px-3 py-1 text-xs font-bold text-orange-700">
                {streakDays > 0 ? "Tuyệt vời!" : "Bắt đầu nhé"}
              </span>
            </div>
            <div className="mt-4">
              <h3 className="text-sm font-bold text-slate-700">Chuỗi ăn đều</h3>
              <div className="mt-1 flex items-baseline gap-1">
                <strong className="text-3xl font-black text-slate-900">{streakDays}</strong>
                <span className="text-sm font-semibold text-slate-500">ngày</span>
              </div>
            </div>
          </div>
          <div className="mt-6">
            <div className="flex justify-between text-xs font-bold text-slate-500 mb-2">
              <span>{Math.min(streakDays, weeklyGoalDays)} / {weeklyGoalDays} ngày</span>
              <span>mục tiêu tuần</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-orange-100">
              <div className="h-full rounded-full bg-orange-500 transition-all" style={{ width: `${weeklyProgress}%` }} />
            </div>
            <div className="mt-3 flex justify-between">
              {Array.from({ length: weeklyGoalDays }).map((_, index) => {
                const done = index < Math.min(streakDays, weeklyGoalDays);
                return (
                  <div key={index} className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${done ? "bg-orange-500 text-white" : "bg-orange-100 text-orange-300"}`}>
                    {done ? <Check size={14} strokeWidth={3} /> : index + 1}
                  </div>
                );
              })}
            </div>
          </div>
        </article>

        {/* Achievements Card */}
        <article className="rounded-2xl border border-sky-100 bg-sky-50/50 p-5">
          <h3 className="text-sm font-bold text-slate-700 mb-4">Ghi nhận gần đây</h3>
          <div className="space-y-3">
            {loading ? (
              <div className="space-y-3 animate-pulse">
                <div className="h-10 rounded-xl bg-sky-100/50" />
                <div className="h-10 rounded-xl bg-sky-100/50" />
                <div className="h-10 rounded-xl bg-sky-100/50" />
              </div>
            ) : (
              recentAchievements.map((achievement, index) => (
                <div key={achievement.key || achievement.title} className="flex items-center gap-3 rounded-xl bg-white p-2.5 shadow-sm">
                  <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${index === 0 ? "bg-emerald-100 text-emerald-600" : index === 1 ? "bg-amber-100 text-amber-600" : "bg-sky-100 text-sky-600"}`}>
                    {index === 0 ? <Leaf size={16} /> : index === 1 ? <Sparkles size={16} /> : <Target size={16} />}
                  </div>
                  <span className="flex-1 text-sm font-bold text-slate-700">{achievement.title}</span>
                  <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-white">
                    <Check size={12} strokeWidth={3} />
                  </div>
                </div>
              ))
            )}
          </div>
        </article>

        {/* Challenge Card */}
        <article className="flex flex-col justify-between rounded-2xl border border-indigo-100 bg-indigo-50/50 p-5 relative overflow-hidden">
          <div className="absolute -right-4 -top-4 text-indigo-100/50">
            <Trophy size={120} />
          </div>
          <div className="relative z-10">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-100 px-3 py-1 text-xs font-black text-indigo-700">
              <Star size={14} fill="currentColor" />
              Thử thách hôm nay
            </span>
            <div className="mt-4">
              <h3 className="text-lg font-black text-slate-900">
                {summary?.today_challenge?.title || "Một bước nhỏ hôm nay"}
              </h3>
              <p className="mt-1 text-sm font-semibold text-slate-600 line-clamp-2">
                {summary?.today_challenge?.description || "Chọn một việc nhỏ bạn muốn làm để chăm sóc bản thân."}
              </p>
            </div>
          </div>
          <div className="relative z-10 mt-6">
            {challengeDone ? (
              <button className="w-full rounded-xl bg-indigo-100 py-3 text-sm font-bold text-indigo-400 cursor-not-allowed" type="button" disabled>
                Đã hoàn thành
              </button>
            ) : pendingEatingStreak ? (
              <button
                onClick={onAction}
                className="w-full rounded-xl bg-indigo-600 py-3 text-sm font-black text-white shadow-md transition hover:bg-indigo-700"
                type="button"
              >
                Mở Nhật ký
              </button>
            ) : (
              <button
                onClick={handleCompleteChallenge}
                disabled={completing || loading}
                className="w-full rounded-xl bg-indigo-600 py-3 text-sm font-black text-white shadow-md transition hover:bg-indigo-700 disabled:opacity-60"
                type="button"
              >
                {completing ? "Đang xử lý..." : "Thử ngay"}
              </button>
            )}
          </div>
        </article>
      </div>

      {/* Banner */}
      <div className="mt-6 flex items-center justify-between rounded-2xl bg-emerald-600 p-5 text-white shadow-md">
        <div className="flex items-center gap-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/20">
            <Heart size={20} fill="currentColor" />
          </div>
          <div>
            <div className="text-base font-black">{encouragement}</div>
            <div className="text-sm font-semibold opacity-90">Bạn đang làm rất tốt. Tiếp tục nhé!</div>
          </div>
        </div>
      </div>
    </section>
  );
}
