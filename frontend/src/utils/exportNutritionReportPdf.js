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
 * Export nutrition report to PDF - Black & White Office Format
 * Similar to Vietnamese administrative report form
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

    // CRITICAL: Ensure no character spacing (fix Vietnamese text spacing)
    doc.setCharSpace(0);

    // A4 dimensions in points (1 pt = 1/72 inch)
    const pageWidth = safePositiveNumber(doc.internal.pageSize.getWidth(), 595); // 595pt
    const pageHeight = safePositiveNumber(doc.internal.pageSize.getHeight(), 842); // 842pt
    const margin = 40;
    const contentWidth = safePositiveNumber(pageWidth - 2 * margin, 515);
    let yPos = margin;

    console.log("[PDF EXPORT] Page dimensions:", { pageWidth, pageHeight, margin, contentWidth });

    // === HEADER - TWO COLUMN ADMINISTRATIVE FORMAT ===
    // Left side: Organization
    doc.setFontSize(11);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0, 0, 0);
    doc.setCharSpace(0);
    safeText(doc, "NUTRIGAIN", margin, yPos);
    
    yPos += 14;
    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.setCharSpace(0);
    safeText(doc, "BAO CAO DINH DUONG", margin, yPos);

    // Right side: National motto
    const rightX = pageWidth - margin;
    yPos = margin;
    doc.setFontSize(10);
    doc.setFont("helvetica", "bold");
    doc.setCharSpace(0);
    safeText(doc, "CONG HOA XA HOI CHU NGHIA VIET NAM", rightX, yPos, { align: "right" });
    
    yPos += 14;
    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    doc.setCharSpace(0);
    safeText(doc, "Doc lap - Tu do - Hanh phuc", rightX, yPos, { align: "right" });
    
    yPos += 3;
    doc.setCharSpace(0);
    safeText(doc, "-------------------", rightX, yPos, { align: "right" });

    // Date line
    yPos += 15;
    const today = new Date();
    const dateStr = formatDate(today);
    const dateParts = dateStr.split("/");
    const dateText = `TP. Ho Chi Minh, ngay ${dateParts[0]} thang ${dateParts[1]} nam ${dateParts[2]}`;
    doc.setFontSize(9);
    doc.setCharSpace(0);
    safeText(doc, dateText, rightX, yPos, { align: "right" });

    yPos += 25;

    // === MAIN TITLE - CENTERED ===
    doc.setFontSize(16);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0, 0, 0);
    doc.setCharSpace(0);
    safeText(doc, "BAO CAO DINH DUONG HANG NGAY", pageWidth / 2, yPos, { align: "center" });
    
    yPos += 18;
    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.setCharSpace(0);
    safeText(doc, `Ngay bao cao: ${dateStr}`, pageWidth / 2, yPos, { align: "center" });

    yPos += 25;

    // === USER INFORMATION - TEXT WITH DOTS FORMAT ===
    doc.setFontSize(11);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0, 0, 0);
    doc.setCharSpace(0);
    safeText(doc, "I. THONG TIN NGUOI DUNG", margin, yPos);
    yPos += 18;

    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");

    const userName = profileSettings?.full_name || userEmail || "Chua co du lieu";
    const age = profileSettings?.age ? String(profileSettings.age) : "Chua co du lieu";
    const gender = profileSettings?.sex === "male" ? "Nam" : profileSettings?.sex === "female" ? "Nu" : "Khac";
    const height = profileSettings?.height || profileSettings?.height_cm ? formatNumber(profileSettings.height || profileSettings.height_cm) + " cm" : "Chua co du lieu";
    const currentWeight = profileSettings?.weight || profileSettings?.weight_kg ? formatNumber(profileSettings.weight || profileSettings.weight_kg) + " kg" : "Chua co du lieu";
    const targetWeight = profileSettings?.target_weight || profileSettings?.target_weight_kg ? formatNumber(profileSettings.target_weight || profileSettings.target_weight_kg) + " kg" : "Chua co du lieu";
    const bmi = summary?.bmi ? formatNumber(summary.bmi) : "Chua co du lieu";

    // User info lines with dots
    doc.setFont("helvetica", "normal");
    doc.setCharSpace(0);
    safeText(doc, `Ho va ten/Email: ${userName}`, margin + 5, yPos);
    yPos += 16;
    doc.setCharSpace(0);
    safeText(doc, `Tuoi: ${age}        Gioi tinh: ${gender}`, margin + 5, yPos);
    yPos += 16;
    doc.setCharSpace(0);
    safeText(doc, `Chieu cao: ${height}        Can nang hien tai: ${currentWeight}`, margin + 5, yPos);
    yPos += 16;
    doc.setCharSpace(0);
    safeText(doc, `Can nang muc tieu: ${targetWeight}        BMI: ${bmi}`, margin + 5, yPos);
    yPos += 25;

    // === TABLE 1: NUTRITION METRICS SUMMARY ===
    if (yPos + 100 > pageHeight - margin - 50) {
      doc.addPage();
      yPos = margin;
    }

    doc.setFontSize(11);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0, 0, 0);
    doc.setCharSpace(0);
    safeText(doc, "BANG 1. TONG HOP CHI SO DINH DUONG", margin, yPos);
    yPos += 18;

    const targetCal = summary?.targetCalories || nutritionTarget?.targetCalories || 0;
    const eatenCal = validation?.totalCalories || consumedNutrition?.calories || 0;
    const remainingCal = Math.max(0, targetCal - eatenCal);
    const progress = targetCal > 0 ? Math.round((eatenCal / targetCal) * 100) : 0;
    const protein = validation?.totalProtein || consumedNutrition?.protein || 0;
    const bmr = summary?.bmr || 0;
    const tdee = summary?.tdee || 0;

    const table1Data = [
      ["STT", "Noi dung", "Gia tri", "Don vi", "Ghi chu"],
      ["1", "BMR", formatNumber(bmr), "kcal", "Nang luong trao doi co ban"],
      ["2", "TDEE", formatNumber(tdee), "kcal", "Nang luong duy tri uoc tinh"],
      ["3", "Muc tieu nang luong", formatNumber(targetCal), "kcal/ngay", "Muc tieu hom nay"],
      ["4", "Da ghi nhan", formatNumber(eatenCal), "kcal", "Tong tu nhat ky an uong"],
      ["5", "Con lai", formatNumber(remainingCal), "kcal", "So voi muc tieu"],
      ["6", "Tien do", String(progress), "%", "Muc hoan thanh nang luong"],
      ["7", "Protein", formatNumber(protein), "g", "Da ghi nhan"],
    ];

    const table1ColWidths = [35, 140, 80, 80, 180];
    const table1RowHeight = 20;

    // Draw table
    table1Data.forEach((row, rowIndex) => {
      if (yPos + table1RowHeight > pageHeight - margin - 50) {
        doc.addPage();
        yPos = margin;
      }

      let xOffset = margin;

      // Draw row borders
      doc.setDrawColor(0, 0, 0);
      doc.setLineWidth(0.5);

      row.forEach((cell, colIndex) => {
        const cellWidth = table1ColWidths[colIndex];

        // Draw cell border
        safeRect(doc, xOffset, yPos, cellWidth, table1RowHeight, "S");

        // Header row background
        if (rowIndex === 0) {
          doc.setFillColor(245, 245, 245);
          safeRect(doc, xOffset, yPos, cellWidth, table1RowHeight, "F");
          safeRect(doc, xOffset, yPos, cellWidth, table1RowHeight, "S");
        }

        // Cell text
        doc.setFontSize(9);
        doc.setFont(rowIndex === 0 ? "helvetica" : "normal", rowIndex === 0 ? "bold" : "normal");
        doc.setTextColor(0, 0, 0);
        doc.setCharSpace(0);

        const cellText = String(cell || "");
        const textX = colIndex === 0 || colIndex === 2 ? xOffset + cellWidth / 2 : xOffset + 3;
        const textAlign = colIndex === 0 || colIndex === 2 ? "center" : "left";

        safeText(doc, cellText, textX, yPos + table1RowHeight / 2 + 3, { align: textAlign });

        xOffset += cellWidth;
      });

      yPos += table1RowHeight;
    });

    yPos += 20;

    // === TABLE 2: MACRONUTRIENT BREAKDOWN ===
    if (yPos + 80 > pageHeight - margin - 50) {
      doc.addPage();
      yPos = margin;
    }

    doc.setFontSize(11);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0, 0, 0);
    doc.setCharSpace(0);
    safeText(doc, "BANG 2. PHAN BO DINH DUONG", margin, yPos);
    yPos += 18;

    const carbs = consumedNutrition?.carbs || validation?.totalCarbs || 0;
    const fat = consumedNutrition?.fat || validation?.totalFat || 0;

    const table2Data = [
      ["STT", "Thanh phan", "Da ghi nhan", "Don vi", "Ghi chu"],
      ["1", "Protein", formatNumber(protein), "g", "-"],
      ["2", "Carbohydrate", formatNumber(carbs), "g", "-"],
      ["3", "Chat beo", formatNumber(fat), "g", "-"],
    ];

    const table2ColWidths = [35, 140, 120, 80, 140];
    const table2RowHeight = 20;

    table2Data.forEach((row, rowIndex) => {
      if (yPos + table2RowHeight > pageHeight - margin - 50) {
        doc.addPage();
        yPos = margin;
      }

      let xOffset = margin;

      doc.setDrawColor(0, 0, 0);
      doc.setLineWidth(0.5);

      row.forEach((cell, colIndex) => {
        const cellWidth = table2ColWidths[colIndex];

        safeRect(doc, xOffset, yPos, cellWidth, table2RowHeight, "S");

        if (rowIndex === 0) {
          doc.setFillColor(245, 245, 245);
          safeRect(doc, xOffset, yPos, cellWidth, table2RowHeight, "F");
          safeRect(doc, xOffset, yPos, cellWidth, table2RowHeight, "S");
        }

        doc.setFontSize(9);
        doc.setFont(rowIndex === 0 ? "helvetica" : "normal", rowIndex === 0 ? "bold" : "normal");
        doc.setTextColor(0, 0, 0);
        doc.setCharSpace(0);

        const cellText = String(cell || "");
        const textX = colIndex === 0 || colIndex === 2 ? xOffset + cellWidth / 2 : xOffset + 3;
        const textAlign = colIndex === 0 || colIndex === 2 ? "center" : "left";

        safeText(doc, cellText, textX, yPos + table2RowHeight / 2 + 3, { align: textAlign });

        xOffset += cellWidth;
      });

      yPos += table2RowHeight;
    });

    yPos += 20;

    // === TABLE 3: MEAL LOG ===
    if (yPos + 100 > pageHeight - margin - 50) {
      doc.addPage();
      yPos = margin;
    }

    doc.setFontSize(11);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0, 0, 0);
    doc.setCharSpace(0);
    safeText(doc, "BANG 3. NHAT KY BUA AN TRONG NGAY", margin, yPos);
    yPos += 18;

    // Table header - Wider columns for better readability
    const table3Headers = ["STT", "Bua an", "Ten mon", "Khau phan", "Kcal", "Protein", "Trang thai"];
    // Adjusted widths: STT=40, Meal=72, Food=175, Portion=82, Kcal=46, Protein=46, Status=54 (Total=515)
    const table3ColWidths = [40, 72, 175, 82, 46, 46, 54];
    const table3RowHeight = 22;

    // Draw header
    let xOffset = margin;
    doc.setDrawColor(0, 0, 0);
    doc.setLineWidth(0.5);

    table3Headers.forEach((header, colIndex) => {
      const cellWidth = table3ColWidths[colIndex];
      
      doc.setFillColor(245, 245, 245);
      safeRect(doc, xOffset, yPos, cellWidth, table3RowHeight, "FD");

      doc.setFontSize(9);
      doc.setFont("helvetica", "bold");
      doc.setTextColor(0, 0, 0);
      doc.setCharSpace(0);

      safeText(doc, header, xOffset + cellWidth / 2, yPos + table3RowHeight / 2 + 3, { align: "center" });

      xOffset += cellWidth;
    });

    yPos += table3RowHeight;

    // Table rows
    const mealLabels = {
      breakfast: "Bua sang",
      lunch: "Bua trua",
      dinner: "Bua toi",
      snacks: "Bua phu",
    };

    let rowNumber = 1;
    let hasData = false;

    if (meals && meals.length > 0) {
      meals.forEach((meal) => {
        const mealName = mealLabels[meal.meal_type] || meal.title || "Bua an";
        const items = meal.items || [];

        items.forEach((item) => {
          hasData = true;

          if (yPos + table3RowHeight > pageHeight - margin - 50) {
            doc.addPage();
            yPos = margin;

            // Repeat header on new page
            xOffset = margin;
            table3Headers.forEach((header, colIndex) => {
              const cellWidth = table3ColWidths[colIndex];
              doc.setFillColor(245, 245, 245);
              safeRect(doc, xOffset, yPos, cellWidth, table3RowHeight, "FD");
              doc.setFontSize(9);
              doc.setFont("helvetica", "bold");
              doc.setTextColor(0, 0, 0);
              doc.setCharSpace(0);
              safeText(doc, header, xOffset + cellWidth / 2, yPos + table3RowHeight / 2 + 3, { align: "center" });
              xOffset += cellWidth;
            });
            yPos += table3RowHeight;
          }

          // Row data
          const foodName = item.name || item.display_name || item.food_name || "Mon an";
          const portion = item.portion || "1 phan";
          const kcal = formatNumber(item.calories || item.kcal || 0);
          const proteinValue = formatNumber(item.protein || item.protein_g || 0) + "g";
          const isEaten = item.is_eaten || item.consumed || item.status === "eaten";
          const status = isEaten ? "Da an" : "Chua an";

          // Calculate row height based on food name length for wrapping
          const maxCharsPerLine = 30;
          const estimatedLines = Math.ceil(foodName.length / maxCharsPerLine);
          const dynamicRowHeight = Math.max(table3RowHeight, estimatedLines * 12 + 6);

          // Check if we need new page
          if (yPos + dynamicRowHeight > pageHeight - margin - 50) {
            doc.addPage();
            yPos = margin;

            // Repeat header on new page
            xOffset = margin;
            table3Headers.forEach((header, colIndex) => {
              const cellWidth = table3ColWidths[colIndex];
              doc.setFillColor(245, 245, 245);
              safeRect(doc, xOffset, yPos, cellWidth, table3RowHeight, "FD");
              doc.setFontSize(9);
              doc.setFont("helvetica", "bold");
              doc.setTextColor(0, 0, 0);
              doc.setCharSpace(0);
              safeText(doc, header, xOffset + cellWidth / 2, yPos + table3RowHeight / 2 + 3, { align: "center" });
              xOffset += cellWidth;
            });
            yPos += table3RowHeight;
          }

          xOffset = margin;

          // Column 0: STT
          let cellWidth = table3ColWidths[0];
          safeRect(doc, xOffset, yPos, cellWidth, dynamicRowHeight, "S");
          doc.setFontSize(9);
          doc.setFont("helvetica", "normal");
          doc.setTextColor(0, 0, 0);
          doc.setCharSpace(0);
          safeText(doc, String(rowNumber), xOffset + cellWidth / 2, yPos + dynamicRowHeight / 2 + 3, { align: "center" });
          xOffset += cellWidth;

          // Column 1: Bua an (Meal) - CRITICAL: No letter spacing
          cellWidth = table3ColWidths[1];
          safeRect(doc, xOffset, yPos, cellWidth, dynamicRowHeight, "S");
          doc.setCharSpace(0);
          safeText(doc, mealName, xOffset + 3, yPos + dynamicRowHeight / 2 + 3);
          xOffset += cellWidth;

          // Column 2: Ten mon (Food name) - Wrap long text
          cellWidth = table3ColWidths[2];
          safeRect(doc, xOffset, yPos, cellWidth, dynamicRowHeight, "S");
          doc.setCharSpace(0);
          const wrappedText = doc.splitTextToSize(foodName, cellWidth - 6);
          const textStartY = yPos + (dynamicRowHeight - (wrappedText.length * 10)) / 2 + 7;
          doc.text(wrappedText, xOffset + 3, textStartY);
          xOffset += cellWidth;

          // Column 3: Khau phan (Portion)
          cellWidth = table3ColWidths[3];
          safeRect(doc, xOffset, yPos, cellWidth, dynamicRowHeight, "S");
          doc.setCharSpace(0);
          safeText(doc, portion, xOffset + 3, yPos + dynamicRowHeight / 2 + 3);
          xOffset += cellWidth;

          // Column 4: Kcal
          cellWidth = table3ColWidths[4];
          safeRect(doc, xOffset, yPos, cellWidth, dynamicRowHeight, "S");
          doc.setFont("helvetica", "bold");
          doc.setCharSpace(0);
          safeText(doc, kcal, xOffset + cellWidth / 2, yPos + dynamicRowHeight / 2 + 3, { align: "center" });
          doc.setFont("helvetica", "normal");
          xOffset += cellWidth;

          // Column 5: Protein
          cellWidth = table3ColWidths[5];
          safeRect(doc, xOffset, yPos, cellWidth, dynamicRowHeight, "S");
          doc.setCharSpace(0);
          safeText(doc, proteinValue, xOffset + cellWidth / 2, yPos + dynamicRowHeight / 2 + 3, { align: "center" });
          xOffset += cellWidth;

          // Column 6: Trang thai (Status)
          cellWidth = table3ColWidths[6];
          safeRect(doc, xOffset, yPos, cellWidth, dynamicRowHeight, "S");
          doc.setFont("helvetica", "bold");
          doc.setCharSpace(0);
          safeText(doc, status, xOffset + cellWidth / 2, yPos + dynamicRowHeight / 2 + 3, { align: "center" });
          doc.setFont("helvetica", "normal");

          yPos += dynamicRowHeight;
          rowNumber++;
        });
      });
    }

    // No data message
    if (!hasData) {
      xOffset = margin;
      const totalWidth = table3ColWidths.reduce((sum, w) => sum + w, 0);
      
      safeRect(doc, xOffset, yPos, totalWidth, table3RowHeight, "S");

      doc.setFontSize(9);
      doc.setFont("helvetica", "normal");
      doc.setTextColor(0, 0, 0);
      doc.setCharSpace(0);

      safeText(doc, "Chua co du lieu nhat ky an uong", xOffset + totalWidth / 2, yPos + table3RowHeight / 2 + 3, { align: "center" });

      yPos += table3RowHeight;
    }

    yPos += 20;

    // === COMMENTS/CONCLUSION SECTION ===
    if (yPos + 80 > pageHeight - margin - 80) {
      doc.addPage();
      yPos = margin;
    }

    doc.setFontSize(11);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0, 0, 0);
    doc.setCharSpace(0);
    safeText(doc, "II. NHAN XET", margin, yPos);
    yPos += 18;

    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.setCharSpace(0);

    // Feedback based on progress
    let feedback = "";
    if (progress >= 90 && progress <= 110) {
      feedback = "Muc nang luong hom nay gan dat muc tieu.";
    } else if (progress < 90) {
      feedback = "Nang luong hom nay con thap hon muc tieu.";
    } else {
      feedback = "Nang luong hom nay vuot muc tieu, can theo doi o cac bua sau.";
    }

    doc.setCharSpace(0);
    safeText(doc, `- Tong nang luong da ghi nhan: ${formatNumber(eatenCal)} kcal`, margin + 5, yPos);
    yPos += 16;
    doc.setCharSpace(0);
    safeText(doc, `- Tien do so voi muc tieu: ${progress}%`, margin + 5, yPos);
    yPos += 16;
    doc.setCharSpace(0);
    safeText(doc, `- Nhan xet: ${feedback}`, margin + 5, yPos);
    yPos += 20;

    // Disclaimer
    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(80, 80, 80);
    doc.setCharSpace(0);
    safeText(doc, "Ghi chu: Bao cao chi mang tinh tham khao, khong thay the tu van y te hoac chi dinh", margin + 5, yPos);
    yPos += 12;
    doc.setCharSpace(0);
    safeText(doc, "cua chuyen gia dinh duong.", margin + 5, yPos);
    yPos += 30;

    // === SIGNATURE SECTION ===
    // Check if we need new page for signatures
    if (yPos + 100 > pageHeight - margin - 40) {
      doc.addPage();
      yPos = margin;
    }

    const sigLeftX = margin + 80;
    const sigRightX = pageWidth - margin - 120;

    doc.setFontSize(10);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0, 0, 0);
    doc.setCharSpace(0);

    // Left signature
    safeText(doc, "NGUOI LAP BAO CAO", sigLeftX, yPos, { align: "center" });
    
    // Right signature  
    safeText(doc, "NGUOI DUNG", sigRightX, yPos, { align: "center" });

    yPos += 50; // Space for signature

    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    
    safeText(doc, "(Ky, ghi ro ho ten)", sigLeftX, yPos, { align: "center" });
    safeText(doc, "(Ky, ghi ro ho ten)", sigRightX, yPos, { align: "center" });

    // === FOOTER - Black and white, simple ===
    const totalPages = doc.internal.pages.length - 1;
    for (let i = 1; i <= totalPages; i++) {
      doc.setPage(i);
      
      // Footer line
      doc.setDrawColor(0, 0, 0);
      doc.setLineWidth(0.3);
      safeLine(doc, margin, pageHeight - 30, pageWidth - margin, pageHeight - 30);

      doc.setFontSize(8);
      doc.setFont("helvetica", "normal");
      doc.setTextColor(80, 80, 80);
      doc.setCharSpace(0);
      
      safeText(doc, "NutriGain - Bao cao dinh duong", margin, pageHeight - 18);
      safeText(doc, `Trang ${i} / ${totalPages}`, pageWidth - margin, pageHeight - 18, { align: "right" });
    }

    // Save PDF
    const fileDate = new Date();
    const year = fileDate.getFullYear();
    const month = String(fileDate.getMonth() + 1).padStart(2, "0");
    const day = String(fileDate.getDate()).padStart(2, "0");
    const fileName = `nutrigain-bao-cao-dinh-duong-${year}-${month}-${day}.pdf`;
    doc.save(fileName);

    console.log(`[PDF Export] Successfully exported to ${fileName}`);
  } catch (error) {
    console.error("[PDF Export] Failed to generate PDF:", error);
    throw new Error("Không thể tạo PDF. Vui lòng thử lại.");
  }
}
