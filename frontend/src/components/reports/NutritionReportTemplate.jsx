function formatNumber(value, suffix = "") {
  const number = Number(value || 0);
  if (!Number.isFinite(number)) return `0${suffix}`;
  return `${Math.round(number).toLocaleString("vi-VN")}${suffix}`;
}

function formatDate(value) {
  const date = value ? new Date(value) : new Date();
  return date.toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function profileValue(value, fallback = "Chưa cập nhật") {
  return value === null || value === undefined || value === "" ? fallback : value;
}

function genderLabel(value) {
  return {
    male: "Nam",
    female: "Nữ",
    other: "Khác",
  }[value] || "Chưa chọn";
}

function mealRows(meals = []) {
  return (meals || []).flatMap((meal) =>
    (meal.items || []).map((item) => ({
      meal: meal.title || meal.name || "Bữa ăn",
      name: item.name || item.display_name || "Món ăn",
      calories: item.calories ?? item.kcal ?? 0,
      protein: item.protein ?? item.protein_g ?? 0,
      status: item.is_eaten || item.consumed || item.status === "eaten" ? "Đã ăn" : "Theo kế hoạch",
    })),
  );
}

export default function NutritionReportTemplate({
  currentUser,
  profile,
  summary,
  validation,
  nutritionTarget,
  meals,
  generatedAt,
  statusPoints = [],
}) {
  const rows = mealRows(meals);
  const targetWeight = profile?.target_weight || profile?.target_weight_kg;
  const currentWeight = profile?.weight || profile?.weight_kg;
  const targetGain = Number(targetWeight || 0) - Number(currentWeight || 0);
  const calories = validation?.totalCalories ?? summary?.targetCalories ?? nutritionTarget?.targetCalories;
  const protein = validation?.totalProtein ?? nutritionTarget?.proteinTarget;
  const targetCalories = summary?.targetCalories ?? nutritionTarget?.targetCalories;
  const targetProtein = nutritionTarget?.proteinTarget;
  const eatenCount = rows.filter((row) => row.status === "Đã ăn").length;
  const generatedDate = formatDate(generatedAt);
  const userEmail = currentUser?.email || currentUser || "Người dùng NutriGain";

  return (
    <article className="nutrition-report">
      <header className="report-header">
        <div>
          <div className="report-brand">
            <span className="report-brand-mark">NG</span>
            <span>NUTRIGAIN</span>
          </div>
          <h1 className="report-title">Báo cáo dinh dưỡng</h1>
          <p className="report-subtitle">Ngày xuất báo cáo: {generatedDate}</p>
        </div>
        <div className="report-user-box">
          <strong>{profileValue(currentUser?.full_name, "Người dùng NutriGain")}</strong>
          <span>{userEmail}</span>
        </div>
      </header>

      <section className="report-section">
        <h2 className="report-section-title">Thông tin hồ sơ</h2>
        <div className="report-grid">
          <ReportCard label="Tuổi" value={profileValue(profile?.age)} />
          <ReportCard label="Giới tính" value={genderLabel(profile?.sex)} />
          <ReportCard label="Chiều cao" value={`${profileValue(profile?.height || profile?.height_cm)} cm`} />
          <ReportCard label="Cân nặng hiện tại" value={`${profileValue(currentWeight)} kg`} />
          <ReportCard label="Cân nặng mục tiêu" value={`${profileValue(targetWeight)} kg`} />
          <ReportCard label="Mục tiêu tăng cân" value={targetGain > 0 ? `+${targetGain.toFixed(1)} kg` : "Chưa đặt"} />
        </div>
      </section>

      <section className="report-section">
        <h2 className="report-section-title">Tổng quan dinh dưỡng</h2>
        <div className="report-grid">
          <ReportCard label="Tổng kcal" value={formatNumber(calories, " kcal")} />
          <ReportCard label="Tổng protein" value={formatNumber(protein, " g")} />
          <ReportCard label="Món đã ăn" value={`${eatenCount}/${rows.length || 0} món`} />
          <ReportCard label="Kcal mục tiêu" value={formatNumber(targetCalories, " kcal")} />
          <ReportCard label="Protein mục tiêu" value={formatNumber(targetProtein, " g")} />
          <ReportCard label="Đánh giá" value={validation?.isValid === false ? "Cần điều chỉnh" : "Khá phù hợp"} />
        </div>
      </section>

      <section className="report-section">
        <h2 className="report-section-title">Danh sách bữa ăn</h2>
        <table className="report-table">
          <thead>
            <tr>
              <th>Bữa</th>
              <th>Món ăn</th>
              <th>Kcal</th>
              <th>Protein</th>
              <th>Trạng thái</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? rows.map((row, index) => (
              <tr key={`${row.meal}-${row.name}-${index}`}>
                <td>{row.meal}</td>
                <td>{row.name}</td>
                <td>{formatNumber(row.calories)}</td>
                <td>{formatNumber(row.protein, " g")}</td>
                <td>{row.status}</td>
              </tr>
            )) : (
              <tr>
                <td colSpan="5">Chưa có dữ liệu bữa ăn.</td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      <section className="report-section">
        <h2 className="report-section-title">Nhận xét hệ thống</h2>
        <div className="report-note">
          {(statusPoints.length ? statusPoints : ["Thực đơn hôm nay khá phù hợp với mục tiêu dinh dưỡng."]).map((point) => (
            <p key={point}>{point}</p>
          ))}
        </div>
      </section>

      <p className="report-disclaimer">
        Báo cáo chỉ mang tính tham khảo, không thay thế tư vấn từ chuyên gia dinh dưỡng.
      </p>
    </article>
  );
}

function ReportCard({ label, value }) {
  return (
    <div className="report-card">
      <div className="report-card-label">{label}</div>
      <div className="report-card-value">{value}</div>
    </div>
  );
}
