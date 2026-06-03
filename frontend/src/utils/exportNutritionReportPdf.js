import jsPDF from "jspdf";

/**
 * Sanitize số về giá trị an toàn
 */
function safeNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

/**
 * Sanitize số dương
 */
function safePositiveNumber(value, fallback = 1) {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : fallback;
}

/**
 * Normalize rect style to valid jsPDF values
 */
function normalizeRectStyle(style) {
  if (style === undefined || style === null || style === "") return undefined;
  const normalized = String(style).toUpperCase();
  // jsPDF rect chỉ nhận: "S", "F", "DF", "FD"
  if (["S", "F", "DF", "FD"].includes(normalized)) {
    return normalized;
  }
  console.warn("[PDF RECT INVALID STYLE FALLBACK]", { style });
  return undefined;
}

/**
 * Wrapper an toàn cho jsPDF.rect
 */
function safeRect(doc, x, y, width, height, style) {
  const safeX = safeNumber(x, NaN);
  const safeY = safeNumber(y, NaN);
  const safeWidth = safePositiveNumber(width, NaN);
  const safeHeight = safePositiveNumber(height, NaN);
  const safeStyle = normalizeRectStyle(style);
  
  const isValid = 
    doc &&
    Number.isFinite(safeX) &&
    Number.isFinite(safeY) &&
    Number.isFinite(safeWidth) &&
    Number.isFinite(safeHeight) &&
    safeWidth > 0 &&
    safeHeight > 0;
  
  if (!isValid) {
    console.warn("[PDF RECT SKIPPED INVALID ARGS]", {
      raw: { x, y, width, height, style },
      safe: { safeX, safeY, safeWidth, safeHeight, safeStyle },
    });
    return false;
  }
  
  try {
    if (safeStyle) {
      doc.rect(safeX, safeY, safeWidth, safeHeight, safeStyle);
    } else {
      doc.rect(safeX, safeY, safeWidth, safeHeight);
    }
    return true;
  } catch (error) {
    console.warn("[PDF RECT FAILED BUT SKIPPED]", {
      error,
      raw: { x, y, width, height, style },
      safe: { safeX, safeY, safeWidth, safeHeight, safeStyle },
    });
    return false;
  }
}

/**
 * Wrapper an toàn cho jsPDF.roundedRect
 */
function safeRoundedRect(doc, x, y, width, height, rx = 2, ry = 2, style) {
  const safeX = safeNumber(x, NaN);
  const safeY = safeNumber(y, NaN);
  const safeWidth = safePositiveNumber(width, NaN);
  const safeHeight = safePositiveNumber(height, NaN);
  const safeRx = safePositiveNumber(rx, 1);
  const safeRy = safePositiveNumber(ry, 1);
  const safeStyle = normalizeRectStyle(style);
  
  const isValid = 
    doc &&
    Number.isFinite(safeX) &&
    Number.isFinite(safeY) &&
    Number.isFinite(safeWidth) &&
    Number.isFinite(safeHeight) &&
    Number.isFinite(safeRx) &&
    Number.isFinite(safeRy) &&
    safeWidth > 0 &&
    safeHeight > 0;
  
  if (!isValid) {
    console.warn("[PDF ROUNDED RECT SKIPPED INVALID ARGS]", {
      raw: { x, y, width, height, rx, ry, style },
      safe: { safeX, safeY, safeWidth, safeHeight, safeRx, safeRy, safeStyle },
    });
    return false;
  }
  
  try {
    if (safeStyle) {
      doc.roundedRect(safeX, safeY, safeWidth, safeHeight, safeRx, safeRy, safeStyle);
    } else {
      doc.roundedRect(safeX, safeY, safeWidth, safeHeight, safeRx, safeRy);
    }
    return true;
  } catch (error) {
    console.warn("[PDF ROUNDED RECT FAILED BUT SKIPPED]", {
      error,
      raw: { x, y, width, height, rx, ry, style },
      safe: { safeX, safeY, safeWidth, safeHeight, safeRx, safeRy, safeStyle },
    });
    return false;
  }
}

/**
 * Wrapper an toàn cho jsPDF.line
 */
function safeLine(doc, x1, y1, x2, y2) {
  const safeX1 = safeNumber(x1, NaN);
  const safeY1 = safeNumber(y1, NaN);
  const safeX2 = safeNumber(x2, NaN);
  const safeY2 = safeNumber(y2, NaN);
  
  const isValid = 
    doc &&
    Number.isFinite(safeX1) &&
    Number.isFinite(safeY1) &&
    Number.isFinite(safeX2) &&
    Number.isFinite(safeY2);
  
  if (!isValid) {
    console.warn("[PDF LINE SKIPPED INVALID ARGS]", { 
      raw: { x1, y1, x2, y2 },
      safe: { safeX1, safeY1, safeX2, safeY2 }
    });
    return false;
  }
  
  try {
    doc.line(safeX1, safeY1, safeX2, safeY2);
    return true;
  } catch (error) {
    console.warn("[PDF LINE FAILED BUT SKIPPED]", {
      error,
      raw: { x1, y1, x2, y2 },
      safe: { safeX1, safeY1, safeX2, safeY2 }
    });
    return false;
  }
}

/**
 * Wrapper an toàn cho jsPDF.text
 */
function safeText(doc, text, x, y, options = {}) {
  const safeX = safeNumber(x, NaN);
  const safeY = safeNumber(y, NaN);
  const safeTextValue = text === null || text === undefined || text === "" 
    ? "Chưa có dữ liệu" 
    : String(text);
  
  const isValid = 
    doc &&
    Number.isFinite(safeX) &&
    Number.isFinite(safeY);
  
  if (!isValid) {
    console.warn("[PDF TEXT SKIPPED INVALID ARGS]", { 
      text, 
      raw: { x, y },
      safe: { safeX, safeY },
      options 
    });
    return false;
  }
  
  try {
    doc.text(safeTextValue, safeX, safeY, options);
    return true;
  } catch (error) {
    console.warn("[PDF TEXT FAILED BUT SKIPPED]", {
      error,
      text,
      raw: { x, y },
      safe: { safeX, safeY },
      options
    });
    return false;
  }
}

/**
 * Format số với dấu phân cách và suffix
 */
function formatNumber(value, suffix = "") {
  if (value === null || value === undefined || isNaN(value)) {
    return "Chưa có dữ liệu";
  }
  const number = Number(value);
  if (!Number.isFinite(number)) return `0${suffix}`;
  return `${Math.round(number).toLocaleString("vi-VN")}${suffix}`;
}

/**
 * Format ngày tháng dd/mm/yyyy
 */
function formatDate(value) {
  const date = value ? new Date(value) : new Date();
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
}

/**
 * Export nutrition report to PDF with professional office format
 * @param {Object} data - Report data
 * @param {Object} data.userEmail - Email người dùng
 * @param {Object} data.summary - Tóm tắt dinh dưỡng
 * @param {Object} data.profileSettings - Thông tin hồ sơ
 * @param {Array} data.meals - Danh sách bữa ăn
 * @param {Object} data.consumedNutrition - Dinh dưỡng đã tiêu thụ
 * @param {Object} data.validation - Validation data
 * @param {Object} data.nutritionTarget - Mục tiêu dinh dưỡng
 */
export async function exportNutritionReportPdf(data) {
  const {
    userEmail = "",
    summary = {},
    profileSettings = {},
    meals = [],
    consumedNutrition = {},
    validation = {},
    nutritionTarget = {},
  } = data || {};

  console.log("[PDF EXPORT] Starting with data:", {
    userEmail,
    hasSummary: !!summary,
    hasProfileSettings: !!profileSettings,
    mealsCount: Array.isArray(meals) ? meals.length : 0,
    hasConsumedNutrition: !!consumedNutrition,
    hasValidation: !!validation,
    hasNutritionTarget: !!nutritionTarget,
  });

  try {
    // Initialize jsPDF with A4 portrait
    const doc = new jsPDF({
      orientation: "portrait",
      unit: "pt",
      format: "a4",
      compress: true,
    });

    // A4 dimensions in points (1 pt = 1/72 inch)
    const pageWidth = safePositiveNumber(doc.internal.pageSize.getWidth(), 595); // 595pt
    const pageHeight = safePositiveNumber(doc.internal.pageSize.getHeight(), 842); // 842pt
    const margin = 40;
    const contentWidth = safePositiveNumber(pageWidth - 2 * margin, 515);
    let yPos = margin;

    console.log("[PDF EXPORT] Page dimensions:", { pageWidth, pageHeight, margin, contentWidth });

    // === HEADER ===
    doc.setFillColor(236, 253, 245); // #ecfdf5
    safeRect(doc, margin, yPos, contentWidth, 80, "F");
    
    doc.setDrawColor(5, 150, 105); // #059669
    doc.setLineWidth(3);
    safeLine(doc, margin, yPos + 80, pageWidth - margin, yPos + 80);

    // Brand name
    doc.setFontSize(24);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(5, 150, 105);
    safeText(doc, "NutriGain", margin + 10, yPos + 25);

    // Subtitle
    doc.setFontSize(11);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(100, 116, 139);
    safeText(doc, "BÁO CÁO DINH DƯỠNG", margin + 10, yPos + 45);

    // Ngày xuất
    const dateText = `Ngày xuất: ${formatDate(new Date())}`;
    doc.setFontSize(9);
    safeText(doc, dateText, pageWidth - margin - 10, yPos + 25, { align: "right" });

    // User email
    if (userEmail) {
      doc.setFontSize(9);
      doc.setTextColor(71, 85, 105);
      safeText(doc, `Người dùng: ${userEmail}`, margin + 10, yPos + 65);
    }

    yPos += 100;

    // === THÔNG TIN HỒ SƠ ===
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(5, 150, 105);
    safeText(doc, "Thông tin hồ sơ", margin, yPos);
    yPos += 20;

    doc.setDrawColor(5, 150, 105);
    doc.setLineWidth(1);
    safeLine(doc, margin, yPos - 5, pageWidth - margin, yPos - 5);
    yPos += 5;

    // Profile info grid
    const profileInfo = [
      ["Tuổi", formatNumber(profileSettings?.age, ""), "Giới tính", profileSettings?.sex === "male" ? "Nam" : profileSettings?.sex === "female" ? "Nữ" : "Khác"],
      ["Chiều cao", formatNumber(profileSettings?.height || profileSettings?.height_cm, " cm"), "Cân nặng hiện tại", formatNumber(profileSettings?.weight || profileSettings?.weight_kg, " kg")],
      ["Cân nặng mục tiêu", formatNumber(profileSettings?.target_weight || profileSettings?.target_weight_kg, " kg"), "BMI", formatNumber(summary?.bmi, "")],
      ["BMR", formatNumber(summary?.bmr, " kcal"), "TDEE", formatNumber(summary?.tdee, " kcal")],
      ["Mục tiêu năng lượng", formatNumber(summary?.targetCalories || nutritionTarget?.targetCalories, " kcal/ngày"), "", ""],
    ];

    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    
    const colWidth = safePositiveNumber(contentWidth / 4, 100);
    const rowHeight = 20;

    console.log("[PDF EXPORT] Profile grid:", { colWidth, rowHeight, contentWidth });

    profileInfo.forEach((row, index) => {
      if (yPos + rowHeight > pageHeight - margin) {
        doc.addPage();
        yPos = margin;
      }

      // Only fill background for even rows
      if (index % 2 === 0) {
        doc.setFillColor(248, 250, 252);
        safeRect(doc, margin, yPos, contentWidth, rowHeight, "F");
      }

      doc.setTextColor(100, 116, 139);
      doc.setFont("helvetica", "bold");
      safeText(doc, row[0], margin + 5, yPos + 13);
      
      doc.setTextColor(15, 23, 42);
      doc.setFont("helvetica", "normal");
      safeText(doc, String(row[1] || ""), margin + colWidth - 5, yPos + 13, { align: "right" });

      if (row[2]) {
        doc.setTextColor(100, 116, 139);
        doc.setFont("helvetica", "bold");
        safeText(doc, row[2], margin + colWidth * 2 + 5, yPos + 13);
        
        doc.setTextColor(15, 23, 42);
        doc.setFont("helvetica", "normal");
        safeText(doc, String(row[3] || ""), margin + colWidth * 3 - 5, yPos + 13, { align: "right" });
      }

      yPos += rowHeight;
    });

    yPos += 15;

    // === TỔNG QUAN HÔM NAY ===
    if (yPos + 80 > pageHeight - margin) {
      doc.addPage();
      yPos = margin;
    }

    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(5, 150, 105);
    safeText(doc, "Tổng quan hôm nay", margin, yPos);
    yPos += 20;

    doc.setDrawColor(5, 150, 105);
    doc.setLineWidth(1);
    safeLine(doc, margin, yPos - 5, pageWidth - margin, yPos - 5);
    yPos += 5;

    const targetCal = summary?.targetCalories || nutritionTarget?.targetCalories || 0;
    const eatenCal = validation?.totalCalories || consumedNutrition?.calories || 0;
    const remainingCal = Math.max(0, targetCal - eatenCal);
    const progress = targetCal > 0 ? Math.round((eatenCal / targetCal) * 100) : 0;
    const protein = validation?.totalProtein || consumedNutrition?.protein || 0;

    const statsData = [
      { label: "Mục tiêu", value: formatNumber(targetCal, " kcal") },
      { label: "Đã ăn", value: formatNumber(eatenCal, " kcal") },
      { label: "Còn lại", value: formatNumber(remainingCal, " kcal") },
      { label: "Protein", value: formatNumber(protein, " g") },
    ];

    const statBoxWidth = safePositiveNumber((contentWidth / 4) - 5, 100);
    const statBoxHeight = 45;

    console.log("[PDF EXPORT] Summary stats boxes:", { 
      statBoxWidth, 
      statBoxHeight, 
      contentWidth,
      statsCount: statsData.length 
    });

    statsData.forEach((stat, index) => {
      const xOffset = safeNumber(margin + index * (statBoxWidth + 5), margin);
      
      console.log("[PDF EXPORT] Drawing stat box:", { index, xOffset, yPos, statBoxWidth, statBoxHeight, label: stat.label });
      
      doc.setFillColor(236, 253, 245);
      doc.setDrawColor(167, 243, 208);
      doc.setLineWidth(0.5);
      safeRoundedRect(doc, xOffset, yPos, statBoxWidth, statBoxHeight, 3, 3, "FD");

      doc.setFontSize(8);
      doc.setFont("helvetica", "bold");
      doc.setTextColor(5, 150, 105);
      safeText(doc, stat.label.toUpperCase(), xOffset + statBoxWidth / 2, yPos + 15, { align: "center" });

      doc.setFontSize(12);
      doc.setTextColor(15, 23, 42);
      safeText(doc, stat.value, xOffset + statBoxWidth / 2, yPos + 32, { align: "center" });
    });

    yPos += statBoxHeight + 10;

    // Progress
    doc.setFontSize(9);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(15, 23, 42);
    safeText(doc, `Tiến độ: ${progress}%`, margin, yPos);
    yPos += 5;

    // Progress bar
    doc.setFillColor(226, 232, 240);
    safeRoundedRect(doc, margin, yPos, contentWidth, 8, 2, 2, "F");

    const progressWidth = safePositiveNumber((Math.min(progress, 100) / 100) * contentWidth, 0);
    doc.setFillColor(5, 150, 105);
    if (progressWidth > 0) {
      safeRoundedRect(doc, margin, yPos, progressWidth, 8, 2, 2, "F");
    }

    yPos += 20;

    // Nhận xét
    let feedback = "";
    if (progress >= 90 && progress <= 110) {
      feedback = "Mức năng lượng hôm nay gần đạt mục tiêu.";
    } else if (progress < 90) {
      feedback = "Năng lượng hôm nay còn thấp hơn mục tiêu.";
    } else {
      feedback = "Năng lượng hôm nay vượt mục tiêu, nên theo dõi ở các bữa sau.";
    }

    doc.setFontSize(9);
    doc.setFont("helvetica", "italic");
    doc.setTextColor(71, 85, 105);
    safeText(doc, feedback, margin, yPos);
    yPos += 20;

    // === PHÂN BỔ DINH DƯỠNG ===
    if (yPos + 80 > pageHeight - margin) {
      doc.addPage();
      yPos = margin;
    }

    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(5, 150, 105);
    safeText(doc, "Phân bổ dinh dưỡng", margin, yPos);
    yPos += 20;

    doc.setDrawColor(5, 150, 105);
    doc.setLineWidth(1);
    safeLine(doc, margin, yPos - 5, pageWidth - margin, yPos - 5);
    yPos += 5;

    const macroData = [
      ["Protein", formatNumber(protein, " g")],
      ["Carbohydrate", formatNumber(consumedNutrition?.carbs || validation?.totalCarbs, " g")],
      ["Chất béo", formatNumber(consumedNutrition?.fat || validation?.totalFat, " g")],
    ];

    doc.setFontSize(9);
    macroData.forEach((row) => {
      if (yPos + 20 > pageHeight - margin) {
        doc.addPage();
        yPos = margin;
      }

      doc.setFont("helvetica", "bold");
      doc.setTextColor(100, 116, 139);
      safeText(doc, row[0], margin, yPos);

      doc.setFont("helvetica", "normal");
      doc.setTextColor(15, 23, 42);
      safeText(doc, row[1], pageWidth - margin, yPos, { align: "right" });

      yPos += 18;
    });

    yPos += 10;

    // === NHẬT KÝ BỮA ĂN ===
    if (yPos + 100 > pageHeight - margin) {
      doc.addPage();
      yPos = margin;
    }

    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(5, 150, 105);
    safeText(doc, "Nhật ký bữa ăn hôm nay", margin, yPos);
    yPos += 20;

    doc.setDrawColor(5, 150, 105);
    doc.setLineWidth(1);
    safeLine(doc, margin, yPos - 5, pageWidth - margin, yPos - 5);
    yPos += 10;

    // Table header
    const colWidths = [80, 200, 70, 60, 60, 60];
    const tableHeaders = ["Bữa", "Món ăn", "Khẩu phần", "Kcal", "Protein", "Trạng thái"];

    doc.setFillColor(236, 253, 245);
    safeRect(doc, margin, yPos, contentWidth, 20, "F");

    doc.setDrawColor(5, 150, 105);
    doc.setLineWidth(2);
    safeLine(doc, margin, yPos + 20, pageWidth - margin, yPos + 20);

    doc.setFontSize(9);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(5, 150, 105);

    let xOffset = margin;
    tableHeaders.forEach((header, index) => {
      safeText(doc, header, xOffset + 5, yPos + 13);
      xOffset += colWidths[index];
    });

    yPos += 22;

    // Table rows
    const mealLabels = {
      breakfast: "Bữa sáng",
      lunch: "Bữa trưa",
      dinner: "Bữa tối",
      snacks: "Bữa phụ",
    };

    doc.setFontSize(8);
    doc.setFont("helvetica", "normal");

    if (meals && meals.length > 0) {
      meals.forEach((meal) => {
        const mealName = mealLabels[meal.meal_type] || meal.title || "Bữa ăn";
        const items = meal.items || [];

        items.forEach((item, itemIndex) => {
          if (yPos + 18 > pageHeight - margin - 30) {
            doc.addPage();
            yPos = margin;

            // Repeat header
            doc.setFillColor(236, 253, 245);
            safeRect(doc, margin, yPos, contentWidth, 20, "F");
            doc.setDrawColor(5, 150, 105);
            doc.setLineWidth(2);
            safeLine(doc, margin, yPos + 20, pageWidth - margin, yPos + 20);
            doc.setFont("helvetica", "bold");
            doc.setTextColor(5, 150, 105);
            xOffset = margin;
            tableHeaders.forEach((header, index) => {
              safeText(doc, header, xOffset + 5, yPos + 13);
              xOffset += colWidths[index];
            });
            yPos += 22;
            doc.setFont("helvetica", "normal");
          }

          // Row background
          if (itemIndex % 2 === 1) {
            doc.setFillColor(248, 250, 252);
            safeRect(doc, margin, yPos, contentWidth, 18, "F");
          }

          doc.setTextColor(15, 23, 42);

          xOffset = margin;
          
          // Bữa
          safeText(doc, itemIndex === 0 ? mealName : "", xOffset + 5, yPos + 12);
          xOffset += colWidths[0];

          // Món ăn
          const foodName = item.name || item.display_name || "Món ăn";
          const truncatedName = foodName.length > 35 ? foodName.substring(0, 32) + "..." : foodName;
          safeText(doc, truncatedName, xOffset + 5, yPos + 12);
          xOffset += colWidths[1];

          // Khẩu phần
          safeText(doc, item.portion || "1 phần", xOffset + 5, yPos + 12);
          xOffset += colWidths[2];

          // Kcal
          doc.setFont("helvetica", "bold");
          safeText(doc, formatNumber(item.calories || item.kcal || 0), xOffset + colWidths[3] - 5, yPos + 12, { align: "right" });
          doc.setFont("helvetica", "normal");
          xOffset += colWidths[3];

          // Protein
          safeText(doc, formatNumber(item.protein || item.protein_g || 0) + " g", xOffset + colWidths[4] - 5, yPos + 12, { align: "right" });
          xOffset += colWidths[4];

          // Trạng thái
          const isEaten = item.is_eaten || item.consumed || item.status === "eaten";
          doc.setFont("helvetica", "bold");
          doc.setTextColor(isEaten ? 5 : 148, isEaten ? 150 : 163, isEaten ? 105 : 184);
          safeText(doc, isEaten ? "Đã ăn" : "Chưa ăn", xOffset + colWidths[5] / 2, yPos + 12, { align: "center" });
          doc.setFont("helvetica", "normal");
          doc.setTextColor(15, 23, 42);

          yPos += 18;
        });
      });
    } else {
      doc.setTextColor(148, 163, 184);
      safeText(doc, "Chưa có dữ liệu nhật ký ăn uống", margin + contentWidth / 2, yPos + 12, { align: "center" });
      yPos += 30;
    }

    yPos += 15;

    // === KẾT LUẬN ===
    if (yPos + 60 > pageHeight - margin) {
      doc.addPage();
      yPos = margin;
    }

    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(5, 150, 105);
    safeText(doc, "Kết luận", margin, yPos);
    yPos += 20;

    doc.setDrawColor(5, 150, 105);
    doc.setLineWidth(1);
    safeLine(doc, margin, yPos - 5, pageWidth - margin, yPos - 5);
    yPos += 10;

    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(15, 23, 42);
    safeText(doc, `• Tổng năng lượng đã ghi nhận: ${formatNumber(eatenCal, " kcal")}`, margin, yPos);
    yPos += 15;
    safeText(doc, `• Tiến độ so với mục tiêu: ${progress}%`, margin, yPos);
    yPos += 15;
    doc.setFont("helvetica", "italic");
    doc.setTextColor(100, 116, 139);
    safeText(doc, "• Ghi chú: Báo cáo chỉ mang tính tham khảo, không thay thế tư vấn y tế.", margin, yPos);

    // === FOOTER ===
    const totalPages = doc.internal.pages.length - 1; // Trừ 1 vì page đầu tiên là null
    for (let i = 1; i <= totalPages; i++) {
      doc.setPage(i);
      
      doc.setDrawColor(226, 232, 240);
      doc.setLineWidth(0.5);
      safeLine(doc, margin, pageHeight - 25, pageWidth - margin, pageHeight - 25);

      doc.setFontSize(8);
      doc.setFont("helvetica", "normal");
      doc.setTextColor(100, 116, 139);
      safeText(doc, "NutriGain - Báo cáo dinh dưỡng", margin, pageHeight - 15);
      safeText(doc, `Trang ${i} / ${totalPages}`, pageWidth - margin, pageHeight - 15, { align: "right" });
    }

    // Save PDF
    const fileName = `nutrigain-bao-cao-dinh-duong-${formatDate(new Date()).replace(/\//g, "-")}.pdf`;
    doc.save(fileName);

    console.log(`[PDF Export] Successfully exported to ${fileName}`);
  } catch (error) {
    console.error("[PDF Export] Failed to generate PDF:", error);
    throw new Error("Không thể tạo PDF. Vui lòng thử lại.");
  }
}
