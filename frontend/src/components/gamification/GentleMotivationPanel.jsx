import { useEffect, useState } from "react";
import { Check, Flame, Heart, Leaf, Sparkles, Star, Target, Trophy } from "lucide-react";
import { getGamificationSummary, completeGamificationChallenge } from "../../services/apiService";

export default function GentleMotivationPanel({ onAction }) {
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
  }, []);

  async function handleCompleteChallenge() {
    if (!summary?.today_challenge) return;
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
  const encouragement = summary?.encouragement || "Ăn đều hơn một chút cũng là tiến bộ.";

  return (
    <section className="gentle-motivation-section">
      <div className="gentle-motivation-header">
        <div className="motivation-title-group">
          <div className="motivation-icon-badge" aria-hidden="true">
            <Sparkles size={28} strokeWidth={2.4} />
          </div>
          <div>
            <h2>Động lực nhẹ nhàng</h2>
            <p>Những ghi nhận nhỏ để bạn duy trì thói quen, không áp lực.</p>
          </div>
        </div>

        <div className="motivation-trophy-illustration" aria-hidden="true">
          <span className="trophy-glow">
            <Trophy size={42} strokeWidth={2.2} />
          </span>
          <Sparkles className="trophy-spark trophy-spark-one" size={18} />
          <Star className="trophy-spark trophy-spark-two" size={16} />
        </div>
      </div>

      <div className="motivation-grid">
        <article className="motivation-card streak-card">
          <div className="streak-top">
            <div className="streak-orb" aria-hidden="true">
              <span><Flame size={36} fill="currentColor" /></span>
            </div>

            <div className="streak-content">
              <div className="streak-title-row">
                <h3>Chuỗi ăn đều</h3>
                <span className="soft-badge">{streakDays > 0 ? "Tuyệt vời!" : "Bắt đầu nhé"}</span>
              </div>

              <div className="streak-number">
                <strong>{streakDays}</strong>
                <span>ngày</span>
              </div>

              <p>{streakDays > 0 ? "Cố gắng duy trì mỗi ngày nhé!" : "Bắt đầu bằng một bữa ăn đều hôm nay nhé."}</p>
            </div>
          </div>

          <div className="streak-progress" aria-hidden="true">
            <div className="streak-progress-fill" style={{ width: `${weeklyProgress}%` }} />
          </div>

          <div className="streak-progress-label">
            <strong>{Math.min(streakDays, weeklyGoalDays)} / {weeklyGoalDays} ngày</strong>
            <span>mục tiêu tuần này</span>
          </div>

          <div className="streak-days" aria-label={`${Math.min(streakDays, weeklyGoalDays)} trên ${weeklyGoalDays} ngày mục tiêu tuần này`}>
            {Array.from({ length: weeklyGoalDays }).map((_, index) => {
              const done = index < Math.min(streakDays, weeklyGoalDays);
              return (
                <span key={index} className={`streak-day ${done ? "done" : ""}`}>
                  {done ? <Check size={17} strokeWidth={3} /> : index + 1}
                </span>
              );
            })}
          </div>
        </article>

        <article className="motivation-card achievement-card">
          <h3>Ghi nhận gần đây</h3>
          <div className="achievement-list">
            {loading ? (
              <>
                <div className="achievement-skeleton" />
                <div className="achievement-skeleton" />
                <div className="achievement-skeleton" />
              </>
            ) : (
              recentAchievements.map((achievement, index) => (
                <div key={achievement.key || achievement.title} className="achievement-item">
                  <span className="achievement-icon" aria-hidden="true">
                    {index === 0 ? <Leaf size={20} /> : index === 1 ? <Sparkles size={20} /> : <Target size={20} />}
                  </span>
                  <span className="achievement-label">{achievement.title}</span>
                  <span className="achievement-check" aria-hidden="true">
                    <Check size={16} strokeWidth={3} />
                  </span>
                </div>
              ))
            )}
          </div>
          {!loading ? <p className="achievement-updated">Cập nhật gần nhất hôm nay</p> : null}
        </article>

        <article className="motivation-card challenge-card">
          <div className="challenge-decoration" aria-hidden="true">
            <Trophy size={64} />
            <Sparkles size={22} />
          </div>
          <span className="challenge-kicker">
            <Star size={18} fill="currentColor" />
            Thử thách hôm nay
          </span>
          {loading ? (
            <div className="challenge-skeleton" />
          ) : summary?.today_challenge ? (
            <>
              <h3>{summary.today_challenge.title || "Một bước nhỏ hôm nay"}</h3>
              <p>{summary.today_challenge.description || "Chọn một việc nhỏ bạn muốn làm để chăm sóc bản thân."}</p>
              {challengeDone ? (
                <button className="challenge-button is-done" type="button">
                  Đã hoàn thành
                </button>
              ) : (
                <button
                  onClick={handleCompleteChallenge}
                  disabled={completing}
                  className="challenge-button"
                  type="button"
                >
                  {completing ? "Đang..." : "Thử ngay"}
                </button>
              )}
            </>
          ) : (
            <>
              <h3>Một bước nhỏ hôm nay</h3>
              <p>Chọn một việc nhỏ bạn muốn làm để chăm sóc bản thân.</p>
              <button className="challenge-button is-done" type="button">Để sau cũng được</button>
            </>
          )}
        </article>
      </div>

      <div className="motivation-message-banner">
        <div className="motivation-message-left">
          <span className="message-icon" aria-hidden="true">
            <Heart size={24} fill="currentColor" />
          </span>
          <div>
            <div className="message-title">{encouragement}</div>
            <div className="message-subtitle">Bạn đang làm rất tốt. Tiếp tục nhé!</div>
          </div>
        </div>
        <div className="message-leaf-line" aria-hidden="true">
          <Leaf size={28} />
        </div>
      </div>
    </section>
  );
}
