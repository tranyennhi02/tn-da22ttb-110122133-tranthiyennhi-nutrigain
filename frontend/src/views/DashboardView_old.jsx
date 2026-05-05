import { useRef, useState } from "react";

import { submitRecommendation } from "../controllers/recommendationController";
import NutriGainLogo from "../components/NutriGainLogo";
import { defaultFormState } from "../models/recommendationModel";

const mealLabels = {
  breakfast: "Bữa sáng",
  lunch: "Bữa trưa",
  dinner: "Bữa tối",
};

const mealOrder = ["breakfast", "lunch", "dinner"];

export default function DashboardView({ userEmail, onLogout }) {
  const [formState, setFormState] = useState(defaultFormState);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const submitLockRef = useRef(false);

  function handleChange(event) {
    const { name, value, type, checked } = event.target;
    setFormState((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitLockRef.current) {
      return;
    }
    submitLockRef.current = true;
    setLoading(true);
    setError("");
    try {
      const data = await submitRecommendation(formState);
      setResult(data);
    } catch (err) {
      setError(err.message || "Request failed");
    } finally {
      setLoading(false);
      submitLockRef.current = false;
    }
  }

  const mealPlanEntries = result ? Object.entries(result.meal_plan) : [];
  const mealCalories = mealPlanEntries.reduce((acc, [, items]) => {
    const sum = items.reduce((mealAcc, item) => mealAcc + item.calories, 0);
    return acc + sum;
  }, 0);

  const progressRatio = result && result.target.calories > 0 ? (mealCalories / result.target.calories) * 100 : 0;
  const progressFillPercent = Math.max(0, Math.min(100, progressRatio));
  const isOverTarget = result ? mealCalories > result.target.calories : false;
  const overCalories = isOverTarget && result ? mealCalories - result.target.calories : 0;

  const actualMacros = mealPlanEntries.reduce(
    (acc, [, items]) => {
      items.forEach((item) => {
        acc.protein += item.protein;
        acc.fat += item.fat;
        acc.carbs += item.carbs;
      });
      return acc;
    },
    { protein: 0, fat: 0, carbs: 0 }
  );

  const macroTargets = result
    ? [
      { label: "Protein", value: actualMacros.protein, target: result.target.protein, color: "var(--macro-protein)" },
      { label: "Fat", value: actualMacros.fat, target: result.target.fat, color: "var(--macro-fat)" },
      { label: "Carbs", value: actualMacros.carbs, target: result.target.carbs, color: "var(--macro-carbs)" },
    ]
    : [];

  const mealDistributionEntries = result
    ? mealOrder
      .map((meal) => [meal, result.evaluation.meal_macro_distribution?.[meal]])
      .filter(([, distribution]) => Boolean(distribution))
    : [];

  return (
    <main className="page app-shell">
      <header className="topbar">
        <div className="brand-wrap">
          <NutriGainLogo size="md" />
          <p className="brand-kicker">Nutrition Intelligence Platform</p>
          <h1>Nhật ký dinh dưỡng tăng cân</h1>
        </div>
        <div className="topbar-actions">
          <span className="live-pill">Live Tracking</span>
          <p className="topbar-note">{userEmail}</p>
          <button type="button" className="logout-btn" onClick={onLogout}>
            Đăng xuất
          </button>
        </div>
      </header>

      <section className="kpi-strip">
        <article className="kpi-card">
          <p className="kpi-label">Mục tiêu hôm nay</p>
          <p className="kpi-value">{result ? `${result.target.calories.toFixed(0)} kcal` : "-"}</p>
        </article>
        <article className="kpi-card">
          <p className="kpi-label">Đã gợi ý</p>
          <p className="kpi-value">{result ? `${mealCalories.toFixed(0)} kcal` : "-"}</p>
        </article>
        <article className="kpi-card">
          <p className="kpi-label">Tiến độ</p>
          <p className="kpi-value">{result ? `${progressRatio.toFixed(1)}%` : "-"}</p>
        </article>
      </section>

      <section className="grid">
        <article className="panel form-panel">
          <h2>Nhập thông tin cơ thể</h2>
          <p className="panel-subtitle">Điền nhanh hồ sơ để hệ thống tạo thực đơn 1 ngày</p>
          <form onSubmit={handleSubmit} className="form-grid">
            <label>
              Cân nặng (kg)
              <input name="weight" type="number" step="0.1" value={formState.weight} onChange={handleChange} required />
            </label>
            <label>
              Chiều cao (cm)
              <input name="height" type="number" step="0.1" value={formState.height} onChange={handleChange} required />
            </label>
            <label>
              Mức độ hoạt động
              <select name="activity" value={formState.activity} onChange={handleChange}>
                <option value="sedentary">Ít vận động</option>
                <option value="light">Nhẹ</option>
                <option value="moderate">Vừa</option>
                <option value="active">Năng động</option>
                <option value="very_active">Rất năng động</option>
              </select>
            </label>
            <label>
              Mục tiêu tăng cân
              <select name="gain_speed" value={formState.gain_speed} onChange={handleChange}>
                <option value="slow">Tăng cân chậm</option>
                <option value="fast">Tăng cân nhanh</option>
              </select>
            </label>
            <label>
              Tuổi
              <input name="age" type="number" value={formState.age} onChange={handleChange} />
            </label>
            <label>
              Giới tính
              <select name="sex" value={formState.sex} onChange={handleChange}>
                <option value="">-</option>
                <option value="male">Nam</option>
                <option value="female">Nữ</option>
              </select>
            </label>
            <label>
              Số món gợi ý
              <input name="top_n" type="number" min="1" max="50" value={formState.top_n} onChange={handleChange} />
            </label>
            <label>
              Món yêu thích
              <input
                name="favorite_foods"
                type="text"
                value={formState.favorite_foods}
                onChange={handleChange}

              />
            </label>
            <label>
              Món dị ứng
              <input
                name="unfavorite_foods"
                type="text"
                value={formState.unfavorite_foods}
                onChange={handleChange}

              />
            </label>
            <label className="checkbox-row">
              <input name="save_user_data" type="checkbox" checked={formState.save_user_data} onChange={handleChange} />
              Lưu vào lịch sử người dùng
            </label>
            <button type="submit" disabled={loading}>
              {loading ? "Đang tính toán..." : "Tạo thực đơn"}
            </button>
            {error ? <p className="error-text">Không thể tải kết quả</p> : null}
          </form>
        </article>

        <article className="panel result-panel">
          <h2>Tổng quan hôm nay</h2>
          <p className="panel-subtitle">Cập nhật theo dữ liệu từ FastAPI ngay sau mỗi lần chạy</p>
          {!result ? <p>Nhập thông tin bên trái và bấm Tạo thực đơn để xem kết quả.</p> : null}
          {result ? (
            <>
              <div className="summary-grid">
                <div className="summary-card">
                  <p className="summary-label">BMI</p>
                  <p className="summary-value">{result.target.bmi.toFixed(2)}</p>
                </div>
                <div className="summary-card">
                  <p className="summary-label">Duy trì</p>
                  <p className="summary-value">{result.target.maintenance_kcal.toFixed(0)} kcal</p>
                </div>
                <div className="summary-card">
                  <p className="summary-label">Sai số kcal</p>
                  <p className="summary-value">{result.evaluation.absolute_error.toFixed(0)}</p>
                </div>
                <div className="summary-card">
                  <p className="summary-label">Sai số macro TB</p>
                  <p className="summary-value">{result.evaluation.macro_mae_relative_pct.toFixed(1)}%</p>
                </div>
              </div>

              <div className={`progress-card${isOverTarget ? " over-target" : ""}`}>
                <div className="progress-row">
                  <span>Tiến độ calories mục tiêu</span>
                  <strong>{progressRatio.toFixed(1)}%</strong>
                </div>
                <div className="progress-track">
                  <div className={`progress-fill${isOverTarget ? " over-target" : ""}`} style={{ width: `${progressFillPercent}%` }} />
                </div>
                <p>
                  {mealCalories.toFixed(1)} / {result.target.calories.toFixed(1)} kcal
                  {isOverTarget ? ` | Vượt ${overCalories.toFixed(1)} kcal` : ""}
                </p>
              </div>

              <div className="macro-list">
                {macroTargets.map((macro) => (
                  <div key={macro.label} className="macro-row">
                    <span>{macro.label}</span>
                    <strong>{macro.value.toFixed(1)}g / {macro.target.toFixed(1)}g</strong>
                    <div className="macro-dot" style={{ backgroundColor: macro.color }} />
                  </div>
                ))}
              </div>

              <h3 className="section-title">Phân bổ macro theo từng bữa</h3>
              <div className="distribution-grid">
                {mealDistributionEntries.map(([meal, distribution]) => (
                  <article key={`distribution-${meal}`} className="distribution-card">
                    <div className="distribution-header">
                      <div>
                        <h4>{mealLabels[meal] || meal}</h4>
                        <p>{distribution.ratio_pct.toFixed(1)}% mục tiêu calories</p>
                      </div>
                      <strong>
                        {distribution.actual_calories.toFixed(1)} / {distribution.target_calories.toFixed(1)} kcal
                      </strong>
                    </div>

                    <div className="distribution-body">
                      <div className="distribution-row">
                        <span>Protein</span>
                        <strong>
                          {distribution.actual_protein.toFixed(1)}g / {distribution.target_protein.toFixed(1)}g
                        </strong>
                      </div>
                      <div className="distribution-row">
                        <span>Fat</span>
                        <strong>
                          {distribution.actual_fat.toFixed(1)}g / {distribution.target_fat.toFixed(1)}g
                        </strong>
                      </div>
                      <div className="distribution-row">
                        <span>Carbs</span>
                        <strong>
                          {distribution.actual_carbs.toFixed(1)}g / {distribution.target_carbs.toFixed(1)}g
                        </strong>
                      </div>
                    </div>
                  </article>
                ))}
              </div>

              <h3 className="section-title">Kế hoạch bữa ăn 1 ngày</h3>
              <div className="meal-columns">
                {mealPlanEntries.map(([meal, items]) => (
                  <div key={meal} className="meal-card">
                    <h4>{mealLabels[meal] || meal}</h4>
                    {items.length === 0 ? <p>Không có món phù hợp</p> : null}
                    {items.map((item) => (
                      <div key={`${meal}-${item.food_id}`} className="food-card">
                        <strong>{item.name}</strong>
                        <p>Nhóm: {item.category}</p>
                        <p>{item.calories.toFixed(1)} kcal</p>
                      </div>
                    ))}
                  </div>
                ))}
              </div>

              <h3 className="section-title">Top món được gợi ý</h3>
              <div className="recommend-list">
                {result.top_recommendations.map((item) => (
                  <div className="recommend-item" key={`top-${item.food_id}`}>
                    <div>
                      <strong>{item.name}</strong>
                      <p>Nhóm: {item.category}</p>
                    </div>
                    <span>{item.calories.toFixed(0)} kcal</span>
                  </div>
                ))}
              </div>
            </>
          ) : null}
        </article>
      </section>

      <section className="footer-note">
        <p>
          Đánh giá hiện tại: {result ? `${result.evaluation.relative_error_pct.toFixed(2)}% sai số calories | precision@${formState.top_n}: ${result.evaluation.preference_precision_pct === null ? "N/A" : `${result.evaluation.preference_precision_pct.toFixed(2)}%`}` : "Chưa có"}
        </p>
      </section>
    </main>
  );
}
