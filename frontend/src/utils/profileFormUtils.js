export function normalizeFoodList(value) {
  if (Array.isArray(value)) {
    return value.map((item) => String(item).trim()).filter(Boolean);
  }

  if (typeof value === "string") {
    return value
      .split(/[,\n;]+/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  return [];
}

export function parseFoodList(value) {
  return normalizeFoodList(value);
}

export function foodListToInput(value) {
  if (Array.isArray(value)) {
    return value.join(", ");
  }

  if (typeof value === "string") {
    return value;
  }

  return "";
}

// Mốc tham khảo từ Intermountain Health: 0.5–2.0 lb/tuần
// Quy đổi: 0.5 lb/tuần ≈ 0.23 kg/tuần ≈ 1 kg/tháng
//          2.0 lb/tuần ≈ 0.9 kg/tuần ≈ 3.6 kg/tháng
const SAFE_GAIN_MIN_KG_PER_MONTH = 1.0;
const SAFE_GAIN_MAX_KG_PER_MONTH = 3.6;
const WEEKS_PER_MONTH = 4;

export const buildWeightGainPlan = ({
  currentWeightKg,
  targetWeightKg,
  durationValue,
  durationUnit,
}) => {
  const current = Number(currentWeightKg);
  const target = Number(targetWeightKg);
  const duration = Number(durationValue);

  if (
    !Number.isFinite(current) ||
    current <= 0 ||
    !Number.isFinite(target) ||
    target <= current ||
    !Number.isFinite(duration) ||
    duration <= 0
  ) {
    return {
      valid: false,
      target_duration_value: null,
      target_duration_unit: null,
      target_duration_months: null,
      target_gain_rate_kg_per_month: null,
      weight_gain_speed: null,
    };
  }

  const weightToGain = target - current;
  const durationMonths = durationUnit === "weeks" ? duration / WEEKS_PER_MONTH : duration;
  const gainPerMonth = weightToGain / durationMonths;

  let weightGainSpeed = "slow";
  if (gainPerMonth >= 1.0 && gainPerMonth <= 2.0) {
    weightGainSpeed = "moderate";
  } else if (gainPerMonth > 2.0 && gainPerMonth <= 3.6) {
    weightGainSpeed = "fast";
  }

  return {
    valid: gainPerMonth <= SAFE_GAIN_MAX_KG_PER_MONTH,
    weight_to_gain_kg: weightToGain,
    target_duration_value: duration,
    target_duration_unit: durationUnit || "months",
    target_duration_months: durationMonths,
    target_gain_rate_kg_per_month: gainPerMonth,
    weight_gain_speed: weightGainSpeed,
    min_recommended_months: Math.ceil(weightToGain / SAFE_GAIN_MAX_KG_PER_MONTH),
    max_recommended_months: Math.ceil(weightToGain / SAFE_GAIN_MIN_KG_PER_MONTH),
    min_recommended_weeks:
      Math.ceil(weightToGain / SAFE_GAIN_MAX_KG_PER_MONTH) * WEEKS_PER_MONTH,
  };
};

function canonicalBudget(value) {
  const normalized = String(value || "").toLowerCase();
  if (normalized === "saving" || normalized === "low" || normalized === "tiết kiệm") return "low";
  if (normalized === "flexible" || normalized === "high" || normalized === "linh hoạt") return "high";
  if (normalized === "standard" || normalized === "tiêu chuẩn") return "standard";
  return normalized || "standard";
}

export function normalizeProfilePayload(form) {
  // Prefer editable text inputs from form to avoid resurrecting stale array state.
  const rawFav = Object.prototype.hasOwnProperty.call(form, "favorite_foods")
    ? form.favorite_foods
    : "";
  const rawDisliked = Object.prototype.hasOwnProperty.call(form, "unfavorite_foods")
    ? form.unfavorite_foods
    : form.disliked_foods;

  const hasMealReminderFields =
    Object.prototype.hasOwnProperty.call(form, "meal_reminder_enabled") ||
    Object.prototype.hasOwnProperty.call(form, "breakfast_time") ||
    Object.prototype.hasOwnProperty.call(form, "lunch_time") ||
    Object.prototype.hasOwnProperty.call(form, "dinner_time");
  const mealReminderEnabled = Boolean(form.meal_reminder_enabled);

  const payload = {
    age: form.age ? Number(form.age) : null,
    gender: form.gender || form.sex || null,
    height_cm: form.height_cm ? Number(form.height_cm) : (form.height ? Number(form.height) : null),
    weight_kg: form.weight_kg ? Number(form.weight_kg) : (form.weight ? Number(form.weight) : null),
    target_weight_kg: form.target_weight_kg
      ? Number(form.target_weight_kg)
      : (form.target_weight ? Number(form.target_weight) : null),
    target_duration_value: form.target_duration_value ? Number(form.target_duration_value) : (form.target_duration_months ? Number(form.target_duration_months) : null),
    target_duration_unit: form.target_duration_unit || null,
    target_duration_months: form.target_duration_months ? Number(form.target_duration_months) : null,
    target_gain_rate_kg_per_month: form.target_gain_rate_kg_per_month ? Number(form.target_gain_rate_kg_per_month) : null,
    weight_gain_speed: form.weight_gain_speed || form.gain_speed || null,
    activity_level: form.activity_level || form.activity || null,
    diet_type: form.diet_style || form.diet_type || "balanced",
    diet_style: form.diet_style || form.diet_type || "balanced",
    budget_level: canonicalBudget(form.budget_level),
    items_per_meal: form.items_per_meal ? Number(form.items_per_meal) : (form.meal_complexity === "simple" ? 3 : form.meal_complexity === "full" ? 5 : 4),
    favorite_foods: normalizeFoodList(rawFav),
    disliked_foods: normalizeFoodList(rawDisliked),
    disliked_food_groups: normalizeFoodList(form.disliked_food_groups),
  };

  if (hasMealReminderFields) {
    payload.meal_reminder_enabled = mealReminderEnabled;
    payload.breakfast_time = mealReminderEnabled ? (form.breakfast_time || "07:00") : (form.breakfast_time || null);
    payload.lunch_time = mealReminderEnabled ? (form.lunch_time || "12:00") : (form.lunch_time || null);
    payload.dinner_time = mealReminderEnabled ? (form.dinner_time || "18:30") : (form.dinner_time || null);
  }

  const weightGainPlan = buildWeightGainPlan({
    currentWeightKg:
      payload.weight_kg ??
      payload.weight ??
      form.weight_kg ??
      form.weight,
    targetWeightKg:
      payload.target_weight_kg ??
      payload.targetWeight ??
      form.target_weight_kg ??
      form.targetWeight,
    durationValue:
      payload.target_duration_value ??
      form.target_duration_value,
    durationUnit:
      payload.target_duration_unit ??
      form.target_duration_unit ??
      "months",
  });
  if (weightGainPlan.valid && weightGainPlan.weight_gain_speed) {
    payload.weight_gain_speed = weightGainPlan.weight_gain_speed;
  }
  if (weightGainPlan.target_duration_months !== null) {
    payload.target_duration_months = weightGainPlan.target_duration_months;
  }
  if (weightGainPlan.target_gain_rate_kg_per_month !== null) {
    payload.target_gain_rate_kg_per_month = weightGainPlan.target_gain_rate_kg_per_month;
  }

  return payload;
}
