export const BMI_NOT_UNDERWEIGHT_REASON = "BMI_NOT_UNDERWEIGHT";
export const BMI_OVERWEIGHT_REASON = "BMI_OVERWEIGHT_NOT_SUPPORTED";
export const BMI_OBESE_REASON = "BMI_OBESE_NOT_SUPPORTED";

export const BMI_SEVERE_UNDERWEIGHT_WARNING =
  "BMI của bạn đang rất thấp. Thực đơn chỉ mang tính hỗ trợ, nên theo dõi cân nặng định kỳ và tham khảo chuyên gia dinh dưỡng khi cần.";

export const ASIAN_BMI_LABELS = {
  underweight: "Gầy / thiếu cân",
  normal: "Bình thường",
  overweight: "Thừa cân",
  obese: "Béo phì",
  unknown: "Đang theo dõi",
};

export function calculateAsianBmi(weightKg, heightCm) {
  const weight = Number(weightKg);
  const height = Number(heightCm);
  if (!Number.isFinite(weight) || !Number.isFinite(height) || weight <= 0 || height <= 0) return null;
  return weight / ((height / 100) ** 2);
}

export function classifyAsianBMI(bmi) {
  if (bmi === null || bmi === undefined || bmi === "") return "unknown";
  const raw = Number(bmi);
  if (!Number.isFinite(raw)) return "unknown";
  const value = Number(raw.toFixed(1));
  if (value < 18.5) return "underweight";
  if (value < 23) return "normal";
  if (value < 30) return "overweight";
  return "obese";
}

export function asianBmiLabel(value) {
  if (typeof value === "number") return ASIAN_BMI_LABELS[classifyAsianBMI(value)];
  const normalized = String(value || "").trim().toLowerCase();
  if (["gầy / thiếu cân", "gầy", "thiếu cân", "underweight", "severely_underweight"].includes(normalized)) {
    return ASIAN_BMI_LABELS.underweight;
  }
  if (["bình thường", "normal"].includes(normalized)) return ASIAN_BMI_LABELS.normal;
  if (["thừa cân", "overweight"].includes(normalized)) return ASIAN_BMI_LABELS.overweight;
  if (["béo phì", "obese"].includes(normalized)) return ASIAN_BMI_LABELS.obese;
  return ASIAN_BMI_LABELS[normalized] || ASIAN_BMI_LABELS.unknown;
}

export function bmiReasonForCategory(category) {
  const normalized = String(category || "").trim().toLowerCase();
  if (normalized === "overweight") return BMI_OVERWEIGHT_REASON;
  if (normalized === "obese") return BMI_OBESE_REASON;
  return BMI_NOT_UNDERWEIGHT_REASON;
}

export function bmiMessageForCategory(category) {
  const normalized = String(category || "").trim().toLowerCase();
  if (normalized === "underweight") {
    return "Gầy / thiếu cân – NutriGain có thể hỗ trợ tạo thực đơn tăng cân.";
  }
  if (normalized === "normal") {
    return "BMI của bạn đang ở mức bình thường. NutriGain vẫn hỗ trợ tạo thực đơn tăng cân lành mạnh nếu bạn muốn cải thiện thể trạng.";
  }
  if (normalized === "overweight") {
    return "BMI của bạn đang thuộc nhóm thừa cân. NutriGain hiện chưa hỗ trợ tạo thực đơn tăng cân cho nhóm này.";
  }
  if (normalized === "obese") {
    return "BMI của bạn đang thuộc nhóm béo phì. NutriGain hiện chưa hỗ trợ tạo thực đơn tăng cân cho nhóm này.";
  }
  return "NutriGain hỗ trợ tạo thực đơn tăng cân cho người có BMI dưới 23 (thiếu cân hoặc bình thường theo chuẩn Châu Á).";
}

export function bmiPreviewMessage(category) {
  const normalized = String(category || "").trim().toLowerCase();
  if (normalized === "underweight") {
    return "Gầy / thiếu cân – NutriGain có thể hỗ trợ tạo thực đơn tăng cân.";
  }
  if (normalized === "normal") {
    return "BMI của bạn đang ở mức bình thường – NutriGain vẫn hỗ trợ tạo thực đơn tăng cân lành mạnh nếu bạn muốn cải thiện thể trạng.";
  }
  if (normalized === "overweight") {
    return "BMI của bạn đang thuộc nhóm thừa cân. NutriGain hiện chưa hỗ trợ tạo thực đơn tăng cân cho nhóm này.";
  }
  if (normalized === "obese") {
    return "BMI của bạn đang thuộc nhóm béo phì. NutriGain hiện chưa hỗ trợ tạo thực đơn tăng cân cho nhóm này.";
  }
  return "Nhập chiều cao và cân nặng để xem BMI theo chuẩn Châu Á.";
}

export function buildAsianBmiOutOfScopeResult(profile) {
  const bmi = calculateAsianBmi(profile?.weight ?? profile?.weight_kg, profile?.height ?? profile?.height_cm);
  if (!Number.isFinite(bmi)) return null;

  const roundedBmi = Number(bmi.toFixed(1));
  const category = classifyAsianBMI(bmi);
  // Cho phép underweight và normal — chỉ block overweight/obese
  if (category === "underweight" || category === "normal") return null;
  const label = asianBmiLabel(category);
  const reason = bmiReasonForCategory(category);
  const message = bmiMessageForCategory(category);

  return {
    eligible: false,
    reason,
    bmi: roundedBmi,
    bmi_category: category,
    bmi_label: label,
    message,
    meal_plan: null,
    eligibility_check: {
      bmi: roundedBmi,
      weight_status: category,
      bmi_category: category,
      bmi_label: label,
      eligible: false,
      reason,
      message,
    },
  };
}

export function isOutOfScopeBmiReason(reason) {
  return [BMI_NOT_UNDERWEIGHT_REASON, BMI_OVERWEIGHT_REASON, BMI_OBESE_REASON].includes(reason);
}
