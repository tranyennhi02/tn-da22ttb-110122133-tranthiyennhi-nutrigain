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
  const recentAchievements = summary?.achievements?.length
    ? summary.achievements.slice(0, 3)
    : [
        { key: "meal-today", title: "Ăn đều hôm nay" },
        { key: "gentle-start", title: "Bắt đầu nhẹ nhàng" },
        { key: "weight-check", title: "Theo dõi cân nặng" },
      ];
  const challengeDone = String(summary?.today_challenge?.status || "").toLowerCase() === "completed";
  const pendingEatingStreak = summary?.today_challenge?.key === "first_complete_day" && !challengeDone;
  const safeStreakDays = Number(streakDays) || 0;
  const weeklyCycleDay = safeStreakDays > 0 ? ((safeStreakDays - 1) % weeklyGoalDays) + 1 : 0;
  const weeklyRemainingDays = Math.max(0, weeklyGoalDays - weeklyCycleDay);
  const isWeeklyComplete = safeStreakDays > 0 && weeklyCycleDay === weeklyGoalDays;
  const weeklyProgress = weeklyCycleDay > 0 ? (weeklyCycleDay / weeklyGoalDays) * 100 : 0;
  const monthCareDays = summary?.month?.days ?? summary?.monthly?.days ?? summary?.month?.care_days ?? null;
  const monthDuyTriRate = summary?.month?.rate ?? summary?.monthly?.rate ?? summary?.month?.retention_rate ?? null;
  const supportMessages = [
    summary?.encouragement,
    "Ăn đều hơn một chút cũng là tiến bộ.",
    "Bạn không cần hoàn hảo, chỉ cần quay lại nhẹ nhàng.",
    "Một ngày chưa tốt không xoá đi cả hành trình.",
    "Tăng cân lành mạnh cần thời gian, bạn đang đi đúng hướng.",
    "Bạn đang chăm sóc bản thân tốt hơn từng chút một.",
  ].filter(Boolean);
  const encouragement = supportMessages.length ? supportMessages[(new Date().getDate() + safeStreakDays + (recentAchievements?.length || 0)) % supportMessages.length] : "";
  const streakStatusPill =
    safeStreakDays === 0
      ? "Nghỉ nhẹ"
      : weeklyCycleDay === weeklyGoalDays
        ? "Tuần mới bắt đầu"
        : "Ngày linh hoạt";
  const streakSupportCopy =
    safeStreakDays === 0
      ? "Không sao, hôm nay mình bắt đầu lại nhẹ nhàng."
      : weeklyCycleDay === weeklyGoalDays
        ? "Bạn đã hoàn thành một vòng 7 ngày. Giữ nhịp nhẹ nhàng cho tuần mới nhé."
        : "Mỗi ngày quay lại đều tính. Tiến bộ nhỏ vẫn là tiến bộ.";
  const monthProgressText =
    monthCareDays != null
      ? `${monthCareDays} ngày chăm sóc bản thân`
      : "Đang ghi nhận thêm để hiển thị tiến trình tháng";
  const monthRateText =
    monthDuyTriRate != null
      ? `${Math.round(Number(monthDuyTriRate) * 100)}% nhịp duy trì`
      : "Tỷ lệ duy trì tháng sẽ hiện khi có dữ liệu";
  return (
    <section className="space-y-6">
      {/* Main Achievement Card */}
      <article className="rounded-2xl border border-emerald-100 bg-white p-6 shadow-md">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h3 className="text-lg font-bold text-slate-700">Chuỗi duy trì hiện tại</h3>
          </div>
          {isWeeklyComplete ? (
            <div className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1.5 text-sm font-semibold text-emerald-700 ring-1 ring-emerald-100">
              <Check size={14} />
              Hoàn thành tuần
            </div>
          ) : (
            <div className="inline-flex items-center gap-2 rounded-full bg-amber-50 px-3 py-1.5 text-sm font-semibold text-amber-700 ring-1 ring-amber-100">
              <Star size={14} />
              {streakStatusPill}
            </div>
          )}
        </div>

        <div className="flex items-center gap-6 mb-6">
          <div className="flex-shrink-0 flex items-center justify-center h-24 w-24 rounded-2xl bg-gradient-to-br from-amber-50 to-amber-100 text-amber-600 shadow-md">
            <Flame size={48} strokeWidth={2.5} />
          </div>
          <div>
            <div className="flex items-baseline gap-3">
              <strong className="text-7xl font-black text-slate-900 leading-none">{streakDays}</strong>
              <div className="text-lg font-semibold text-slate-600">ngày liên tiếp</div>
            </div>
            <p className="mt-3 text-sm text-slate-600">{streakSupportCopy}</p>
          </div>
        </div>

        {/* Weekly Progress */}
        <div className="mt-8 p-4 rounded-xl bg-gradient-to-br from-slate-50 to-emerald-50/30 border border-emerald-100/50">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-semibold text-slate-700">Tuần này: <span className="text-slate-900">{weeklyCycleDay}/{weeklyGoalDays} ngày</span></div>
            <div className="text-sm text-slate-500">
              {isWeeklyComplete ? "Tuần mới bắt đầu ngày mai" : `Còn ${weeklyRemainingDays} ngày để hoàn thành mục tiêu tuần`}
            </div>
          </div>
          <div className="h-2.5 rounded-full bg-slate-200 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-amber-400 via-amber-500 to-amber-600 transition-all duration-500"
              style={{ width: `${weeklyProgress}%` }}
            />
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          <div className="text-center p-4 rounded-xl bg-gradient-to-br from-slate-50 to-white border border-slate-100">
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">Tuần này</div>
            <div className="mt-2 text-2xl font-black text-slate-900">{weeklyCycleDay}/{weeklyGoalDays}</div>
            <div className="mt-1 text-xs text-slate-600">ngày</div>
          </div>
          <div className="text-center p-4 rounded-xl bg-gradient-to-br from-slate-50 to-white border border-slate-100">
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">Tháng này</div>
            <div className="mt-2 text-2xl font-black text-slate-900">
              {monthCareDays != null ? monthCareDays : "—"}
            </div>
            <div className="mt-1 text-xs text-slate-600">
              {monthCareDays != null ? "ngày chăm sóc" : "Đang ghi nhận"}
            </div>
          </div>
          <div className="text-center p-4 rounded-xl bg-gradient-to-br from-slate-50 to-white border border-slate-100">
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">Bữa chính hôm nay</div>
            <div className="mt-2 text-2xl font-black text-slate-900">
              {challengeDone ? "3/3" : "—"}
            </div>
            <div className="mt-1 text-xs text-slate-600">
              {challengeDone ? "Đã hoàn thành" : "Đang thực hiện"}
            </div>
          </div>
        </div>
      </article>

      {/* Two Column Layout for Secondary Content */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent Achievements */}
        <article className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
          <h3 className="text-base font-bold text-slate-900 mb-4">Ghi nhận gần đây</h3>

          <div className="space-y-3">
            {loading ? (
              <div className="space-y-3 animate-pulse">
                <div className="h-16 rounded-lg bg-slate-100" />
                <div className="h-16 rounded-lg bg-slate-100" />
                <div className="h-16 rounded-lg bg-slate-100" />
              </div>
            ) : (
              recentAchievements.slice(0, 3).map((achievement, index) => {
                const accentClass = index === 0 ? "text-emerald-600 bg-emerald-50" : index === 1 ? "text-amber-600 bg-amber-50" : "text-sky-600 bg-sky-50";
                const Icon = index === 0 ? Leaf : index === 1 ? Sparkles : Target;
                const description = achievement?.description || (
                  achievement?.title === "Bạn đồng hành 3 ngày"
                    ? "Bạn đã quay lại chăm sóc bản thân trong 3 ngày"
                    : achievement?.title === "Duy trì nhẹ nhàng"
                      ? "Có " + weeklyCycleDay + " ngày được ghi nhận trong tuần này"
                      : achievement?.title === "Ăn đều hôm nay"
                        ? "Đã hoàn thành đủ các bữa chính"
                        : "Tiến bộ nhỏ từng ngày"
                );
                return (
                  <div key={achievement.key || achievement.title} className="flex items-start gap-3 p-3 rounded-lg hover:bg-slate-50 transition">
                    <div className={`flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl ${accentClass}`}>
                      <Icon size={20} strokeWidth={2.5} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-bold text-slate-900">{achievement.title}</div>
                      <div className="mt-0.5 text-xs text-slate-600 leading-relaxed">{description}</div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </article>

        {/* Today's Challenge */}
        <article className="rounded-2xl border border-emerald-100 bg-gradient-to-br from-white to-emerald-50/30 p-5 shadow-sm">
          <h3 className="text-base font-bold text-slate-900 mb-4">Thử thách hôm nay</h3>

          <div className="flex items-start gap-4 mb-4">
            <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-600">
              <Target size={24} strokeWidth={2.5} />
            </div>
            <div className="flex-1">
              {(() => {
                const safeChallengeTitle = summary?.today_challenge?.title || summary?.today_challenge?.name || "Ăn đều hôm nay";
                const safeChallengeDescription = summary?.today_challenge?.description || "Hoàn thành đủ bữa sáng, trưa và tối";
                return (
                  <>
                    <div className="text-lg font-black text-slate-900">{safeChallengeTitle}</div>
                    <div className="mt-1 text-sm text-slate-600 leading-relaxed">{safeChallengeDescription}</div>
                  </>
                );
              })()}
            </div>
          </div>

          <div className="flex items-center justify-between pt-3 border-t border-emerald-100">
            <div className="text-sm font-semibold text-slate-600">
              {pendingEatingStreak ? "Bắt đầu lần đầu" : challengeDone ? "" : "Đang thực hiện"}
            </div>
            <button
              onClick={handleCompleteChallenge}
              disabled={completing || challengeDone}
              className={`inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-bold transition shadow-sm ${
                challengeDone
                  ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200"
                  : "bg-emerald-600 text-white hover:bg-emerald-700"
              }`}
            >
              {challengeDone ? (
                <>
                  <Check size={16} />
                  Đã hoàn thành
                </>
              ) : (
                <>{completing ? "Đang xử lý..." : "Hoàn thành"}</>
              )}
            </button>
          </div>
        </article>
      </div>

      {/* Encouragement Banner */}
      <div className="rounded-xl bg-gradient-to-r from-emerald-50 via-white to-emerald-50 border border-emerald-100 p-4 flex items-center gap-3 shadow-sm">
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-emerald-100 text-emerald-600">
          <Heart size={20} strokeWidth={2.5} />
        </div>
        <div className="flex-1">
          <div className="text-sm font-bold text-slate-900">Bạn đang làm rất tốt</div>
          <div className="mt-0.5 text-xs text-slate-600">Mỗi ngày quay lại đều được ghi nhận.</div>
        </div>
      </div>
    </section>
  );
}
