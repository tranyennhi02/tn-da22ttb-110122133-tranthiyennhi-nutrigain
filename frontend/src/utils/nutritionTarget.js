const ACTIVITY_FACTORS = {
  default: 1.3,
  sedentary: 1.2,
  light: 1.375,
  moderate: 1.55,
  active: 1.725,
  very_active: 1.9,
};

function numberOrFallback(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : fallback;
}

function normalizeGoal(goal) {
  const value = String(goal || "gain").toLowerCase();
  if (["lose", "loss", "cut", "Giảm cân"].includes(value)) return "lose";
  if (["maintain", "maintenance", "keep", "Giữ cân"].includes(value)) return "maintain";
  return "gain";
}

export function calculateBMR(user) {
  const weight = numberOrFallback(user?.weight ?? user?.weight_kg, 50);
  const height = numberOrFallback(user?.height ?? user?.height_cm, 165);
  const age = numberOrFallback(user?.age, 25);
  const sex = String(user?.sex ?? user?.gender ?? "").toLowerCase();

  if (sex === "female" || sex === "f" || sex === "nữ" || sex === "nu") {
    return 10 * weight + 6.25 * height - 5 * age - 161;
  }

  return 10 * weight + 6.25 * height - 5 * age + 5;
}

export function calculateTDEE(user) {
  const activityKey = String(user?.activity ?? user?.activityLevel ?? user?.activity_level ?? "default").toLowerCase();
  const activityFactor = ACTIVITY_FACTORS[activityKey] || Number(activityKey) || ACTIVITY_FACTORS.default;
  return calculateBMR(user) * activityFactor;
}

export function calculateNutritionTarget(user) {
  const weight = numberOrFallback(user?.weight ?? user?.weight_kg, 50);
  const height = numberOrFallback(user?.height ?? user?.height_cm, 165);
  const age = numberOrFallback(user?.age, 25);
  const goal = normalizeGoal(user?.goal_type ?? user?.goal);
  const gainSpeed = String(user?.weight_gain_speed ?? user?.gain_speed ?? "slow").toLowerCase();
  const bmr = calculateBMR(user);
  const tdee = calculateTDEE(user);
  const bmi = weight / ((height / 100) ** 2);
  const surplusBySpeed = {
    slow: 300,
    medium: 400,
    moderate: 400,
    fast: 500,
  };
  const surplus = Number(user?.surplus_kcal) || surplusBySpeed[gainSpeed] || 300;

  let targetCalories = tdee;
  if (goal === "gain") targetCalories = Math.max(tdee + Math.abs(surplus), tdee);
  if (goal === "lose") targetCalories = tdee - 350;

  if (goal !== "gain" && age >= 18) targetCalories = Math.max(targetCalories, 1200);

  const proteinPerKg = bmi < 17.5 ? 1.8 : 1.7;
  const proteinTarget = Math.min(Math.max(weight * 1.6, weight * proteinPerKg), weight * 2.2);
  const fatTarget = Math.max(weight * 0.9, (targetCalories * 0.30) / 9);
  const carbTarget = Math.max((targetCalories - proteinTarget * 4 - fatTarget * 9) / 4, 0);

  return {
    bmi: Number(bmi.toFixed(1)),
    bmr: Math.round(bmr),
    tdee: Math.round(tdee),
    targetCalories: Math.round(targetCalories),
    proteinTarget: Math.round(proteinTarget),
    fatTarget: Math.round(fatTarget),
    carbTarget: Math.round(carbTarget),
    minCalories: Math.round(targetCalories * 0.95),
    maxCalories: Math.round(targetCalories * 1.05),
  };
}
