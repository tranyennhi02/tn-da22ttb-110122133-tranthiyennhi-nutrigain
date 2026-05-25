export const SAFE_GAIN_MIN_KG_PER_MONTH = 0.5;
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
  const minMonths = Math.ceil(weightToGain / SAFE_GAIN_MAX_KG_PER_MONTH);
  const minWeeks = minMonths * WEEKS_PER_MONTH;

  result.durationMonths = durationMonths;
  result.weightToGain = weightToGain;
  result.requiredGainPerMonth = requiredGainPerMonth;
  result.minMonths = minMonths;
  result.minWeeks = minWeeks;

  if (requiredGainPerMonth > SAFE_GAIN_MAX_KG_PER_MONTH) {
    result.fieldErrors.target_duration_value = `Bạn cần tăng khoảng ${formatKgRate(requiredGainPerMonth)}kg/tháng, vượt mức khuyến nghị 0,5–1kg/tháng cho người trưởng thành. Vui lòng chọn thời gian dài hơn. Nên chọn tối thiểu khoảng ${minMonths} tháng hoặc ${minWeeks} tuần.`;
    return result;
  }

  result.ok = true;
  result.severity = requiredGainPerMonth < SAFE_GAIN_MIN_KG_PER_MONTH ? "info" : "success";
  result.suggestedSpeed = requiredGainPerMonth < SAFE_GAIN_MIN_KG_PER_MONTH ? "slow" : requiredGainPerMonth <= 0.75 ? "moderate" : "fast";
  result.message = requiredGainPerMonth >= SAFE_GAIN_MIN_KG_PER_MONTH
    ? "Tốc độ tăng cân này phù hợp với mức khuyến nghị 0,5–1kg/tháng."
    : "Tốc độ này khá chậm và an toàn, phù hợp nếu bạn muốn tăng cân bền vững.";
  return result;
}

export function buildWeightGainPlan(currentWeightKg, targetWeightKg, durationValue, durationUnit) {
  return validateWeightGoalTimeline({ currentWeightKg, targetWeightKg, durationValue, durationUnit });
}
