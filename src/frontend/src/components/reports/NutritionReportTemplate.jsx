// ============================================
// HELPER FUNCTIONS
// ============================================

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
  if (value === null || value === undefined || value === "") return fallback;
  return value;
}

function genderLabel(value) {
  const labels = {
    male: "Nam",
    female: "Nữ",
    other: "Khác",
  };
  return labels[value] || "Chưa chọn";
}

function mealRows(meals = []) {
  return (meals || []).flatMap((meal) =>
    (meal.items || []).map((item) => ({
      meal: meal.title || meal.name || "Bữa ăn",
      name: item.name || item.display_name || "Món ăn",
      portion: item.portion || "1 phần",
      calories: item.calories ?? item.kcal ?? 0,
      protein: item.protein ?? item.protein_g ?? 0,
      status: item.is_eaten || item.consumed || item.status === "eaten" ? "Đã ăn" : "Chưa ăn",
    })),
  );
}

function generateNutritionInsights(rows, calories, targetCalories, protein, targetProtein) {
  const insights = [];
  
  if (!rows || rows.length === 0) {
    return ["Chưa đủ dữ liệu để đưa ra nhận xét chi tiết."];
  }

  // Kiểm tra năng lượng
  const caloriePercent = targetCalories > 0 ? (calories / targetCalories) * 100 : 0;
  if (caloriePercent >= 80 && caloriePercent <= 110) {
    insights.push("Mức năng lượng hôm nay khá phù hợp với mục tiêu.");
  } else if (caloriePercent < 80) {
    insights.push("Bạn còn thiếu năng lượng so với mục tiêu, nên bổ sung thêm bữa phụ giàu năng lượng.");
  } else if (caloriePercent > 110) {
    insights.push("Năng lượng hôm nay vượt mục tiêu, nên điều chỉnh khẩu phần cho phù hợp.");
  }

  // Kiểm tra protein
  const proteinPercent = targetProtein > 0 ? (protein / targetProtein) * 100 : 0;
  if (proteinPercent < 70) {
    insights.push("Protein hôm nay còn thấp, nên thêm trứng, sữa, thịt, cá hoặc đậu phụ.");
  } else if (proteinPercent >= 70 && proteinPercent <= 100) {
    insights.push("Lượng protein đạt mức tốt.");
  }

  // Kiểm tra số món đã ăn
  const eatenCount = rows.filter((row) => row.status === "Đã ăn").length;
  if (eatenCount === 0) {
    insights.push("Chưa có món ăn nào được đánh dấu là đã ăn.");
  } else if (eatenCount < rows.length / 2) {
    insights.push("Bạn đã ăn ít hơn một nửa thực đơn hôm nay.");
  }

  return insights.length > 0 ? insights : ["Thực đơn hôm nay khá phù hợp với mục tiêu dinh dưỡng."];
}

// ============================================
// MAIN COMPONENT
// ============================================

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
  
  const calories = validation?.totalCalories ?? summary?.targetCalories ?? nutritionTarget?.targetCalories ?? 0;
  const protein = validation?.totalProtein ?? nutritionTarget?.proteinTarget ?? 0;
  const targetCalories = summary?.targetCalories ?? nutritionTarget?.targetCalories ?? 0;
  const targetProtein = nutritionTarget?.proteinTarget ?? 0;
  const remainingCalories = Math.max(0, targetCalories - calories);
  
  const eatenCount = rows.filter((row) => row.status === "Đã ăn").length;
  const totalCount = rows.length;
  const caloriePercent = targetCalories > 0 ? Math.round((calories / targetCalories) * 100) : 0;
  
  const generatedDate = formatDate(generatedAt);
  const userName = profileValue(currentUser?.full_name, "Người dùng NutriGain");
  const userEmail = currentUser?.email || "";
  
  // Generate insights
  const insights = statusPoints.length > 0 
    ? statusPoints 
    : generateNutritionInsights(rows, calories, targetCalories, protein, targetProtein);

  // ============================================
  // INLINE STYLES
  // ============================================

  const styles = {
    page: {
      width: "210mm",
      minHeight: "297mm",
      padding: "14mm 16mm",
      background: "#ffffff",
      fontFamily: "'Segoe UI', 'Roboto', 'Arial', sans-serif",
      fontSize: "10pt",
      lineHeight: "1.5",
      color: "#0f172a",
      boxSizing: "border-box",
    },
    header: {
      borderBottom: "3px solid #059669",
      paddingBottom: "12px",
      marginBottom: "18px",
      background: "linear-gradient(to bottom, #ecfdf5 0%, #ffffff 100%)",
      padding: "12px 14px",
      borderRadius: "8px",
    },
    brandRow: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      marginBottom: "6px",
    },
    brandName: {
      fontSize: "22pt",
      fontWeight: "800",
      color: "#059669",
      letterSpacing: "-0.5px",
      margin: "0",
    },
    subtitle: {
      fontSize: "11pt",
      color: "#64748b",
      margin: "0",
      fontWeight: "600",
    },
    dateText: {
      fontSize: "9pt",
      color: "#64748b",
      textAlign: "right",
      margin: "0",
    },
    userBox: {
      background: "#f8fafc",
      border: "1px solid #e2e8f0",
      borderRadius: "6px",
      padding: "8px 12px",
      marginTop: "8px",
      display: "flex",
      flexDirection: "column",
      gap: "2px",
    },
    userName: {
      fontSize: "11pt",
      fontWeight: "700",
      color: "#0f172a",
      margin: "0",
    },
    userEmail: {
      fontSize: "9pt",
      color: "#64748b",
      margin: "0",
    },
    section: {
      marginBottom: "18px",
      pageBreakInside: "avoid",
    },
    sectionTitle: {
      fontSize: "14pt",
      fontWeight: "700",
      color: "#059669",
      marginBottom: "10px",
      borderBottom: "2px solid #ecfdf5",
      paddingBottom: "6px",
    },
    infoGrid: {
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: "10px",
      marginBottom: "12px",
    },
    infoCard: {
      background: "#f8fafc",
      border: "1px solid #e2e8f0",
      borderRadius: "6px",
      padding: "8px 10px",
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
    },
    infoLabel: {
      fontSize: "9pt",
      color: "#64748b",
      fontWeight: "600",
    },
    infoValue: {
      fontSize: "10pt",
      color: "#0f172a",
      fontWeight: "700",
    },
    statsGrid: {
      display: "grid",
      gridTemplateColumns: "repeat(4, 1fr)",
      gap: "8px",
      marginBottom: "14px",
    },
    statBox: {
      background: "#ecfdf5",
      border: "1px solid #a7f3d0",
      borderRadius: "6px",
      padding: "10px",
      textAlign: "center",
    },
    statLabel: {
      fontSize: "8pt",
      color: "#059669",
      fontWeight: "700",
      textTransform: "uppercase",
      letterSpacing: "0.5px",
      marginBottom: "4px",
    },
    statValue: {
      fontSize: "13pt",
      fontWeight: "800",
      color: "#0f172a",
    },
    progressBar: {
      background: "#e2e8f0",
      borderRadius: "4px",
      height: "8px",
      overflow: "hidden",
      marginTop: "6px",
    },
    progressFill: {
      background: "linear-gradient(90deg, #059669 0%, #10b981 100%)",
      height: "100%",
      borderRadius: "4px",
      transition: "width 0.3s ease",
    },
    table: {
      width: "100%",
      borderCollapse: "collapse",
      marginTop: "10px",
      fontSize: "9pt",
    },
    tableHeader: {
      background: "#ecfdf5",
      fontWeight: "700",
      color: "#059669",
      textAlign: "left",
      padding: "8px 6px",
      borderBottom: "2px solid #059669",
    },
    tableRow: {
      borderBottom: "1px solid #e2e8f0",
    },
    tableRowAlt: {
      background: "#f8fafc",
      borderBottom: "1px solid #e2e8f0",
    },
    tableCell: {
      padding: "7px 6px",
      color: "#0f172a",
    },
    insightBox: {
      background: "#fffbeb",
      border: "1px solid #fcd34d",
      borderRadius: "6px",
      padding: "12px 14px",
      marginTop: "10px",
    },
    insightItem: {
      fontSize: "9.5pt",
      color: "#0f172a",
      marginBottom: "6px",
      paddingLeft: "14px",
      position: "relative",
      lineHeight: "1.6",
    },
    insightBullet: {
      position: "absolute",
      left: "0",
      top: "0",
      color: "#f59e0b",
      fontWeight: "bold",
    },
    footer: {
      marginTop: "20px",
      paddingTop: "12px",
      borderTop: "1px solid #e2e8f0",
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      fontSize: "8pt",
      color: "#64748b",
    },
    disclaimer: {
      marginTop: "16px",
      fontSize: "8pt",
      color: "#94a3b8",
      fontStyle: "italic",
      textAlign: "center",
      lineHeight: "1.4",
    },
  };

  return (
    <div style={styles.page}>
      {/* HEADER */}
      <div style={styles.header}>
        <div style={styles.brandRow}>
          <div>
            <h1 style={styles.brandName}>NutriGain</h1>
            <p style={styles.subtitle}>Báo cáo dinh dưỡng cá nhân</p>
          </div>
          <p style={styles.dateText}>Ngày xuất: {generatedDate}</p>
        </div>
        <div style={styles.userBox}>
          <div style={styles.userName}>{userName}</div>
          {userEmail && <div style={styles.userEmail}>{userEmail}</div>}
        </div>
      </div>

      {/* THÔNG TIN HỒ SƠ */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>Thông tin hồ sơ</h2>
        <div style={styles.infoGrid}>
          <div style={styles.infoCard}>
            <span style={styles.infoLabel}>Tuổi</span>
            <span style={styles.infoValue}>{profileValue(profile?.age)}</span>
          </div>
          <div style={styles.infoCard}>
            <span style={styles.infoLabel}>Giới tính</span>
            <span style={styles.infoValue}>{genderLabel(profile?.sex)}</span>
          </div>
          <div style={styles.infoCard}>
            <span style={styles.infoLabel}>Chiều cao</span>
            <span style={styles.infoValue}>{profileValue(profile?.height || profile?.height_cm)} cm</span>
          </div>
          <div style={styles.infoCard}>
            <span style={styles.infoLabel}>Cân nặng hiện tại</span>
            <span style={styles.infoValue}>{profileValue(currentWeight)} kg</span>
          </div>
          <div style={styles.infoCard}>
            <span style={styles.infoLabel}>Cân nặng mục tiêu</span>
            <span style={styles.infoValue}>{profileValue(targetWeight)} kg</span>
          </div>
          <div style={styles.infoCard}>
            <span style={styles.infoLabel}>Mục tiêu tăng cân</span>
            <span style={styles.infoValue}>
              {targetGain > 0 ? `+${targetGain.toFixed(1)} kg` : "Chưa đặt"}
            </span>
          </div>
        </div>
      </div>

      {/* TỔNG QUAN HÔM NAY */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>Tổng quan dinh dưỡng hôm nay</h2>
        <div style={styles.statsGrid}>
          <div style={styles.statBox}>
            <div style={styles.statLabel}>Mục tiêu</div>
            <div style={styles.statValue}>{formatNumber(targetCalories)} kcal</div>
          </div>
          <div style={styles.statBox}>
            <div style={styles.statLabel}>Đã ăn</div>
            <div style={styles.statValue}>{formatNumber(calories)} kcal</div>
          </div>
          <div style={styles.statBox}>
            <div style={styles.statLabel}>Còn lại</div>
            <div style={styles.statValue}>{formatNumber(remainingCalories)} kcal</div>
          </div>
          <div style={styles.statBox}>
            <div style={styles.statLabel}>Protein</div>
            <div style={styles.statValue}>{formatNumber(protein)} g</div>
          </div>
        </div>
        <div style={{ fontSize: "9pt", color: "#0f172a", fontWeight: "600", marginTop: "8px" }}>
          Tiến độ: {caloriePercent}% hoàn thành • {eatenCount}/{totalCount} món
          <div style={{ ...styles.progressBar, width: "100%" }}>
            <div style={{ ...styles.progressFill, width: `${Math.min(caloriePercent, 100)}%` }}></div>
          </div>
        </div>
      </div>

      {/* THỰC ĐƠN / NHẬT KÝ MÓN ĂN */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>Nhật ký món ăn</h2>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={{ ...styles.tableHeader, width: "15%" }}>Bữa</th>
              <th style={{ ...styles.tableHeader, width: "35%" }}>Món ăn</th>
              <th style={{ ...styles.tableHeader, width: "15%", textAlign: "center" }}>Khẩu phần</th>
              <th style={{ ...styles.tableHeader, width: "12%", textAlign: "center" }}>Kcal</th>
              <th style={{ ...styles.tableHeader, width: "11%", textAlign: "center" }}>Protein</th>
              <th style={{ ...styles.tableHeader, width: "12%", textAlign: "center" }}>Trạng thái</th>
            </tr>
          </thead>
          <tbody>
            {rows.length > 0 ? (
              rows.map((row, index) => (
                <tr key={`${row.meal}-${row.name}-${index}`} style={index % 2 === 0 ? styles.tableRow : styles.tableRowAlt}>
                  <td style={styles.tableCell}>{row.meal}</td>
                  <td style={styles.tableCell}>{row.name}</td>
                  <td style={{ ...styles.tableCell, textAlign: "center" }}>{row.portion}</td>
                  <td style={{ ...styles.tableCell, textAlign: "center", fontWeight: "700" }}>{formatNumber(row.calories)}</td>
                  <td style={{ ...styles.tableCell, textAlign: "center" }}>{formatNumber(row.protein)} g</td>
                  <td style={{ ...styles.tableCell, textAlign: "center", fontWeight: "600", color: row.status === "Đã ăn" ? "#059669" : "#94a3b8" }}>
                    {row.status}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="6" style={{ ...styles.tableCell, textAlign: "center", color: "#94a3b8", padding: "16px" }}>
                  Chưa có dữ liệu bữa ăn
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* NHẬN XÉT DINH DƯỠNG */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>Nhận xét nhanh</h2>
        <div style={styles.insightBox}>
          {insights.map((insight, idx) => (
            <div key={idx} style={styles.insightItem}>
              <span style={styles.insightBullet}>•</span>
              {insight}
            </div>
          ))}
        </div>
      </div>

      {/* DISCLAIMER */}
      <p style={styles.disclaimer}>
        Báo cáo này chỉ mang tính tham khảo, không thay thế tư vấn từ chuyên gia dinh dưỡng hoặc bác sĩ.
      </p>

      {/* FOOTER */}
      <div style={styles.footer}>
        <span>NutriGain • Build healthy calories</span>
        <span>Trang 1</span>
      </div>
    </div>
  );
}
