// Mốc tham khảo từ Intermountain Health: 0.5–2.0 lb/tuần
// Quy đổi: 0.5 lb/tuần ≈ 0.23 kg/tuần ≈ 1 kg/tháng
//          2.0 lb/tuần ≈ 0.9 kg/tuần ≈ 3.6 kg/tháng
// Backend sử dụng giới hạn an toàn: 1.0 kg/tháng
export const SAFE_GAIN_MIN_KG_PER_MONTH = 1.0;
export const SAFE_GAIN_MAX_KG_PER_MONTH = 1.0;
export const WEEKS_PER_MONTH = 4;
export const SAFE_GAIN_MAX_KG_PER_WEEK = SAFE_GAIN_MAX_KG_PER_MONTH / WEEKS_PER_MONTH;

export function normalizeDurationUnit(value) {
  const unit = String(value || "months").toLowerCase().trim();
  if (unit === "week" || unit === "weeks" || unit === "tuần" || unit === "tuan") {
    return "weeks";
  }
  return "months";
}

export function formatKgRate(value) {
  if (!Number.isFinite(value)) return "";
  const rounded = Math.round(value * 10) / 10;
  return String(rounded).replace(/\.0$/, "");
}

export function validateWeightGoalTimeline({ currentWeightKg, targetWeightKg, durationValue, durationUnit }) {
  const currentWeight = Number(currentWeightKg);
  const targetWeight = Number(targetWeightKg);
  const durationNumber = Number(durationValue);
  const normalizedUnit = normalizeDurationUnit(durationUnit);

  const result = {
    ok: false,
    severity: "error",
    currentWeightKg: Number.isFinite(currentWeight) ? currentWeight : null,
    targetWeightKg: Number.isFinite(targetWeight) ? targetWeight : null,
    durationValue: Number.isFinite(durationNumber) ? durationNumber : null,
    durationUnit: normalizedUnit,
    durationMonths: null,
    weightToGain: null,
    requiredGainPerMonth: null,
    minMonths: null,
    maxMonths: null,
    minWeeks: null,
    suggestedSpeed: null,
    message: "",
    fieldErrors: {},
  };

  if (!Number.isFinite(currentWeight) || !Number.isFinite(targetWeight) || targetWeight <= currentWeight) {
    result.fieldErrors.target_weight = "Cân nặng mục tiêu phải lớn hơn cân nặng hiện tại.";
    return result;
  }

  if (!Number.isFinite(durationNumber) || durationNumber <= 0) {
    result.fieldErrors.target_duration_value = "Vui lòng nhập thời gian hợp lệ.";
    return result;
  }

  const durationMonths = normalizedUnit === "weeks" ? durationNumber / WEEKS_PER_MONTH : durationNumber;
  const weightToGain = targetWeight - currentWeight;
  const requiredGainPerMonth = weightToGain / durationMonths;
  // Gợi ý thời gian dựa trên mốc Intermountain Health
  const minMonths = Math.ceil(weightToGain / SAFE_GAIN_MAX_KG_PER_MONTH); // thời gian tối thiểu (tốc độ nhanh nhất)
  const maxMonths = Math.ceil(weightToGain / SAFE_GAIN_MIN_KG_PER_MONTH); // thời gian tối đa (tốc độ chậm nhất)
  const minWeeks = minMonths * WEEKS_PER_MONTH;

  result.durationMonths = durationMonths;
  result.weightToGain = weightToGain;
  result.requiredGainPerMonth = requiredGainPerMonth;
  result.minMonths = minMonths;
  result.maxMonths = maxMonths;
  result.minWeeks = minWeeks;

  // Tốc độ quá nhanh (> 1.0 kg/tháng)
  if (requiredGainPerMonth > SAFE_GAIN_MAX_KG_PER_MONTH) {
    result.fieldErrors.target_duration_value = `Mục tiêu này tăng quá nhanh để NutriGain gợi ý thực đơn an toàn. Vui lòng tăng thời gian mục tiêu hoặc giảm cân nặng mục tiêu. Với mục tiêu tăng ${formatKgRate(weightToGain)}kg, bạn nên chọn ít nhất ${minMonths} tháng.`;
    return result;
  }

  result.ok = true;

  // Tốc độ quá chậm (< 1 kg/tháng)
  if (requiredGainPerMonth < SAFE_GAIN_MIN_KG_PER_MONTH) {
    result.severity = "info";
    result.suggestedSpeed = "slow";
    result.message = `Bạn muốn tăng ${formatKgRate(weightToGain)}kg trong ${durationNumber} ${normalizedUnit === "weeks" ? "tuần" : "tháng"}, tương đương khoảng ${formatKgRate(requiredGainPerMonth)}kg/tháng. Tốc độ này chậm hơn mốc tham khảo an toàn 1kg/tháng. Nếu bạn muốn tiến độ rõ hơn, có thể rút ngắn thời gian mục tiêu. Nếu bạn muốn đi chậm và dễ duy trì, lựa chọn này vẫn có thể phù hợp.`;
  } 
  // Tốc độ nằm trong mốc (1.0 kg/tháng)
  else {
    result.severity = "success";
    result.suggestedSpeed = "moderate";
    result.message = `Bạn muốn tăng ${formatKgRate(weightToGain)}kg trong ${durationNumber} ${normalizedUnit === "weeks" ? "tuần" : "tháng"}, tương đương khoảng ${formatKgRate(requiredGainPerMonth)}kg/tháng. Tốc độ này phù hợp với mốc an toàn 1kg/tháng. Hãy duy trì bữa ăn đều, thêm bữa phụ và theo dõi cơ thể trong quá trình tăng cân.`;
  }

  return result;
}

export function buildWeightGainPlan(currentWeightKg, targetWeightKg, durationValue, durationUnit) {
  return validateWeightGoalTimeline({ currentWeightKg, targetWeightKg, durationValue, durationUnit });
}
