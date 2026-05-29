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
    <section className="relative mt-8 rounded-2xl border border-emerald-50/60 bg-gradient-to-b from-white to-emerald-50/60 p-6 shadow-lg sm:p-8">
      <div className="flex items-start gap-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white text-emerald-600 shadow-sm">
          <Sparkles size={20} strokeWidth={2} />
        </div>
        <div>
          <h2 className="text-2xl font-extrabold leading-tight text-slate-900">Động lực nhẹ nhàng</h2>
          <p className="mt-1 text-sm text-slate-600">Những ghi nhận nhỏ để bạn duy trì thói quen, không áp lực.</p>
        </div>
      </div>

      <div className="mt-6 grid gap-6 md:grid-cols-3">
        {/* Hero streak card - left (spans 2 cols) */}
        <article className="md:col-span-2 rounded-2xl border border-emerald-100 bg-white p-6 shadow-sm">
          <div className="flex items-start gap-6">
            <div className="flex-shrink-0 flex items-center justify-center h-20 w-20 rounded-2xl bg-gradient-to-br from-amber-50 to-amber-100 text-amber-600 shadow-md">
              <Flame size={32} />
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-slate-500">Chuỗi hiện tại</div>
                  <div className="mt-2 flex items-end gap-4">
                    <strong className="text-6xl font-extrabold text-slate-900 leading-none">{streakDays}</strong>
                    <div className="text-sm text-slate-600">ngày duy trì liên tiếp</div>
                  </div>
                </div>
                <div className="ml-4">
                  {isWeeklyComplete ? (
                    <div className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700 ring-1 ring-emerald-100">
                      <Check size={14} />
                      Đã hoàn thành mục tiêu tuần
                    </div>
                  ) : (
                    <div className="inline-flex items-center gap-2 rounded-full bg-amber-50 px-3 py-1 text-sm font-medium text-amber-700 ring-1 ring-amber-100">
                      <Star size={14} />
                      {streakStatusPill}
                    </div>
                  )}
                </div>
              </div>

              <div className="mt-4 flex items-center justify-between">
                <div className="text-sm text-slate-600">Tuần này: <span className="font-semibold text-slate-900">{weeklyCycleDay}/{weeklyGoalDays} ngày</span></div>
                <div className="text-sm text-slate-500">{weeklyCycleDay === weeklyGoalDays ? "Ngày mai sẽ bắt đầu vòng tuần mới" : "Tiếp tục duy trì đều đặn"}</div>
              </div>

              <div className="mt-4">
                <div className="h-3 rounded-full bg-amber-100 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-amber-400 via-amber-500 to-amber-600 transition-all"
                    style={{ width: `${weeklyProgress}%` }}
                  />
                </div>
              </div>

              <div className="mt-6 grid gap-3 sm:grid-cols-3">
                <div className="rounded-lg border border-emerald-50 bg-white p-3">
                  <div className="text-xs text-slate-500">Chuỗi hiện tại</div>
                  <div className="mt-1 text-lg font-semibold text-slate-900">{streakDays} ngày</div>
                  <div className="mt-1 text-xs text-slate-500">Mỗi lần quay lại đều được ghi nhận</div>
                </div>
                <div className="rounded-lg border border-emerald-50 bg-white p-3">
                  <div className="text-xs text-slate-500">Tuần này</div>
                  <div className="mt-1 text-lg font-semibold text-slate-900">{weeklyCycleDay}/{weeklyGoalDays} ngày</div>
                  <div className="mt-1 text-xs text-slate-500">{isWeeklyComplete ? "Bạn đã hoàn thành mục tiêu tuần" : `Còn ${weeklyRemainingDays} ngày để hoàn thành`}</div>
                </div>
                <div className="rounded-lg border border-emerald-50 bg-white p-3">
                  <div className="text-xs text-slate-500">Tiến trình tháng</div>
                  <div className="mt-1 text-lg font-semibold text-slate-900">{monthCareDays != null ? `${monthCareDays} ngày` : monthProgressText}</div>
                  <div className="mt-1 text-xs text-slate-500">{monthDuyTriRate != null ? monthRateText : "Sẽ hiển thị khi có đủ dữ liệu"}</div>
                </div>
              </div>

              <div className="mt-4 px-4 py-3 rounded-lg bg-emerald-50 text-sm text-slate-700">{streakSupportCopy}</div>
            </div>
          </div>
        </article>

        {/* Right column: two stacked cards */}
        <div className="flex flex-col gap-6">
          <article className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-900">Ghi nhận gần đây</h3>
              <span className="text-sm font-medium text-slate-500">Đã ghi nhận</span>
            </div>

            <div className="mt-4 space-y-3">
              {loading ? (
                <div className="space-y-3 animate-pulse">
                  <div className="h-14 rounded-lg bg-slate-100" />
                  <div className="h-14 rounded-lg bg-slate-100" />
                </div>
              ) : (
                recentAchievements.map((achievement, index) => {
                  const accentClass = index === 0 ? "text-emerald-600" : index === 1 ? "text-amber-600" : "text-sky-600";
                  const Icon = index === 0 ? Leaf : index === 1 ? Sparkles : Target;
                  const description = achievement?.description || (
                    achievement?.title === "Bạn đồng hành 3 ngày"
                      ? "Bạn đã quay lại chăm sóc bản thân"
                      : achievement?.title === "Duy trì nhẹ nhàng"
                        ? "Mỗi ngày đều có giá trị"
                        : achievement?.title === "Ăn đều hôm nay"
                          ? "Một bước nhỏ nhưng rất đáng quý"
                          : "Bạn đang xây dựng nhịp sinh hoạt tốt hơn"
                  );
                  return (
                    <div key={achievement.key || achievement.title} className="flex items-center gap-3 rounded-lg p-2">
                      <div className={`flex h-10 w-10 items-center justify-center rounded-lg bg-slate-50 ${accentClass}`}>
                        <Icon size={18} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-semibold text-slate-900">{achievement.title}</div>
                        <div className="mt-0.5 text-xs text-slate-500">{description}</div>
                      </div>
                      <div className="flex-shrink-0 text-sm font-medium text-emerald-700">Đã ghi nhận</div>
                    </div>
                  );
                })
              )}
            </div>
          </article>

          <article className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between">
                <div className="text-sm font-medium text-slate-600">Thử thách hôm nay</div>
                <div className="text-xs text-slate-400">Hôm nay</div>
              </div>
                  {/* minimal safe fallbacks for challenge title/description to avoid ReferenceError */}
                  {(() => {
                    const safeChallengeTitle = typeof challengeTitle !== "undefined"
                      ? challengeTitle
                      : summary?.today_challenge?.title || summary?.today_challenge?.name || "Thử thách hôm nay";
                    const safeChallengeDescription = typeof challengeDescription !== "undefined"
                      ? challengeDescription
                      : summary?.today_challenge?.description || "";
                    return (
                      <>
                        <div className="mt-2 text-lg font-semibold text-slate-900">{safeChallengeTitle}</div>
                        <div className="mt-1 text-sm text-slate-600">{safeChallengeDescription}</div>
                      </>
                    );
                  })()}
              <div className="mt-3 text-xs text-slate-500">Không cần hoàn hảo. Làm được một chút cũng tính.</div>
            </div>

            <div className="mt-4 flex items-center justify-between">
              <div className="text-sm text-slate-500">{pendingEatingStreak ? "Bắt đầu lần đầu" : challengeDone ? "Đã hoàn thành" : "Chưa hoàn thành"}</div>
              <button
                onClick={handleCompleteChallenge}
                disabled={completing || challengeDone}
                className={`inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-semibold transition ${
                  challengeDone ? "bg-emerald-50 text-emerald-700" : "bg-emerald-600 text-white"
                }`}
              >
                {challengeDone ? (
                  <>
                    <Check size={16} />Đã hoàn thành
                  </>
                ) : (
                  <>{completing ? "Đang xử lý..." : "Hoàn thành"}</>
                )}
              </button>
            </div>
          </article>
        </div>
      </div>

      {/* Encouragement banner */}
      <div className="mt-6 rounded-2xl bg-gradient-to-r from-emerald-50 to-emerald-100 border border-emerald-50 p-4 flex items-center justify-between shadow-sm">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white text-emerald-600 shadow-sm">
            <Trophy size={18} />
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-900">Bạn đang làm rất tốt</div>
            <div className="mt-0.5 text-xs text-slate-600">Một chút tiến bộ mỗi ngày sẽ tạo nên thay đổi lớn trong dài hạn.</div>
          </div>
        </div>
        <div className="text-sm text-slate-500">Tiếp tục duy trì nhịp nhẹ nhàng</div>
      </div>
    </section>
  );
}
