import { useState, useMemo, useEffect } from "react";
import { calculateNutritionTarget } from "../utils/nutritionTarget";
import { updateUserProfile, postRegenerateMealPlan, fetchCurrentUser } from "../services/apiService";
import { mapFormStateToBackendProfile } from "../App";
import { normalizePayload } from "../models/recommendationModel";
import NutriGainLogo from "../components/NutriGainLogo";
import { buildWeightGainPlan, formatKgRate } from "../utils/weightGainPlan.js";
import {
  asianBmiLabel,
  bmiPreviewMessage,
  buildAsianBmiOutOfScopeResult,
  calculateAsianBmi,
  classifyAsianBMI,
} from "../utils/bmi";
import { foodListToInput, parseFoodList } from "../utils/profileFormUtils.js";

// ─── helpers ────────────────────────────────────────────────────────────────
function safeNum(v) { const n = Number(v); return Number.isFinite(n) && n > 0 ? n : 0; }

function isValidNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function formatKg(value) {
  if (!Number.isFinite(value)) return "";
  const rounded = Math.round(value * 10) / 10;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

function buildWeightGoalPreview(data) {
  const currentWeight = Number(data.weight ?? data.weight_kg);
  const targetWeight = Number(data.target_weight ?? data.target_weight_kg);
  const durationValue = Number(data.target_duration_value ?? data.target_duration_months);
  const durationUnit = data.target_duration_unit || "months";
  const hasWeights = isValidNumber(currentWeight) && isValidNumber(targetWeight);
  const targetDiff = hasWeights ? targetWeight - currentWeight : null;
  const hasDuration = isValidNumber(durationValue) && durationValue > 0;
  const durationMonths = hasDuration ? (durationUnit === "weeks" ? durationValue / WEEKS_PER_MONTH : durationValue) : null;
  const monthlyGain = targetDiff != null && targetDiff > 0 && hasDuration && durationMonths > 0 ? targetDiff / durationMonths : null;

  return {
    currentWeight,
    targetWeight,
    targetDiff,
    durationValue: hasDuration ? durationValue : null,
    durationUnit,
    durationMonths,
    monthlyGain,
    hasWeights,
    hasDuration,
  };
}

// Mốc tham khảo từ Intermountain Health: 0.5–2.0 lb/tuần
// Quy đổi: 0.5 lb/tuần ≈ 0.23 kg/tuần ≈ 1 kg/tháng
//          2.0 lb/tuần ≈ 0.9 kg/tuần ≈ 3.6 kg/tháng
const SAFE_GAIN_MIN_KG_PER_MONTH = 1.0;
const SAFE_GAIN_MAX_KG_PER_MONTH = 3.6;
const WEEKS_PER_MONTH = 4;

const validateWeightGoalTimeline = ({
  currentWeightKg,
  targetWeightKg,
  durationValue,
  durationUnit,
}) => {
  const current = Number(currentWeightKg);
  const target = Number(targetWeightKg);
  const duration = Number(durationValue);

  if (!Number.isFinite(current) || current <= 0) {
    return {
      ok: false,
      severity: "error",
      error: "Vui lòng nhập cân nặng hiện tại hợp lệ.",
    };
  }

  if (!Number.isFinite(target) || target <= current) {
    return {
      ok: false,
      severity: "error",
      error: "Cân nặng mục tiêu phải lớn hơn cân nặng hiện tại.",
    };
  }

  if (!Number.isFinite(duration) || duration <= 0) {
    return {
      ok: false,
      severity: "error",
      error: "Vui lòng nhập thời gian mục tiêu hợp lệ.",
    };
  }

  const weightToGain = target - current;
  const durationMonths = durationUnit === "weeks" ? duration / WEEKS_PER_MONTH : duration;

  if (!Number.isFinite(durationMonths) || durationMonths <= 0) {
    return {
      ok: false,
      severity: "error",
      error: "Vui lòng nhập thời gian mục tiêu hợp lệ.",
    };
  }

  const gainPerMonth = weightToGain / durationMonths;
  const minMonths = Math.ceil(weightToGain / SAFE_GAIN_MAX_KG_PER_MONTH); // thời gian tối thiểu
  const maxMonths = Math.ceil(weightToGain / SAFE_GAIN_MIN_KG_PER_MONTH); // thời gian tối đa
  const minWeeks = minMonths * WEEKS_PER_MONTH;

  // Tốc độ quá nhanh (> 3.6 kg/tháng)
  if (gainPerMonth > SAFE_GAIN_MAX_KG_PER_MONTH) {
    return {
      ok: false,
      severity: "error",
      weightToGain,
      durationMonths,
      gainPerMonth,
      minMonths,
      maxMonths,
      minWeeks,
      error: `Bạn muốn tăng ${gainPerMonth.toFixed(1)}kg/tháng. Mốc tham khảo quy đổi từ Intermountain Health là khoảng 0.5–2.0 lb/tuần, tương đương khoảng 1–3.6 kg/tháng. Tốc độ bạn nhập đang cao hơn mốc này. Gợi ý: với mục tiêu tăng ${weightToGain.toFixed(1)}kg, bạn nên chọn khoảng ${minMonths}–${maxMonths} tháng.`,
    };
  }

  // Tốc độ quá chậm (< 1 kg/tháng)
  if (gainPerMonth < SAFE_GAIN_MIN_KG_PER_MONTH) {
    return {
      ok: true,
      severity: "info",
      weightToGain,
      durationMonths,
      gainPerMonth,
      minMonths,
      maxMonths,
      minWeeks,
      message: `Bạn muốn tăng ${weightToGain.toFixed(1)}kg trong ${duration} ${durationUnit === "weeks" ? "tuần" : "tháng"}, tương đương khoảng ${gainPerMonth.toFixed(1)}kg/tháng. Tốc độ này chậm hơn mốc tham khảo quy đổi từ Intermountain Health: khoảng 0.5–2.0 lb/tuần, tương đương khoảng 1–3.6 kg/tháng. Nếu bạn muốn tiến độ rõ hơn, có thể rút ngắn thời gian mục tiêu. Nếu bạn muốn đi chậm và dễ duy trì, lựa chọn này vẫn có thể phù hợp.`,
    };
  }

  // Tốc độ nằm trong mốc (1–3.6 kg/tháng)
  return {
    ok: true,
    severity: "success",
    weightToGain,
    durationMonths,
    gainPerMonth,
    minMonths,
    maxMonths,
    minWeeks,
    message: `Bạn muốn tăng ${weightToGain.toFixed(1)}kg trong ${duration} ${durationUnit === "weeks" ? "tuần" : "tháng"}, tương đương khoảng ${gainPerMonth.toFixed(1)}kg/tháng. Tốc độ này nằm trong mốc tham khảo quy đổi từ Intermountain Health: khoảng 0.5–2.0 lb/tuần, tương đương khoảng 1–3.6 kg/tháng. Hãy duy trì bữa ăn đều, thêm bữa phụ và theo dõi cơ thể trong quá trình tăng cân.`,
  };
};

function getVietnamDateString() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Ho_Chi_Minh",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

function mealComplexityFromItems(itemsPerMeal) {
  const count = Number(itemsPerMeal);
  if (count <= 3) return "simple";
  if (count >= 5) return "full";
  return "balanced";
}

function buildRegeneratePayload(formData, freshProfile = null) {
  const source = freshProfile
    ? {
      ...formData,
      weight: freshProfile.weight_kg ?? formData.weight,
      height: freshProfile.height_cm ?? formData.height,
      age: freshProfile.age ?? formData.age,
      sex: freshProfile.sex || freshProfile.gender || formData.sex,
      activity: freshProfile.activity_level || formData.activity,
      gain_speed: freshProfile.weight_gain_speed || formData.gain_speed,
      weight_gain_speed: freshProfile.weight_gain_speed || formData.weight_gain_speed,
      target_weight: freshProfile.target_weight_kg ?? formData.target_weight,
      target_duration_value: freshProfile.target_duration_value ?? freshProfile.target_duration_months ?? formData.target_duration_value,
      target_duration_unit: freshProfile.target_duration_unit || formData.target_duration_unit,
      target_duration_months: freshProfile.target_duration_months ?? formData.target_duration_months,
      target_gain_rate_kg_per_month: freshProfile.target_gain_rate_kg_per_month ?? formData.target_gain_rate_kg_per_month,
      diet_style: freshProfile.diet_type || formData.diet_style,
      diet_type: freshProfile.diet_type || formData.diet_type,
      budget_level: freshProfile.budget_level || formData.budget_level,
      items_per_meal: freshProfile.items_per_meal ?? formData.items_per_meal,
      meal_complexity: mealComplexityFromItems(freshProfile.items_per_meal ?? formData.items_per_meal),
      favorite_foods: freshProfile.favorite_foods ?? formData.favorite_foods,
      disliked_foods: freshProfile.disliked_foods ?? formData.disliked_foods,
      unfavorite_foods: freshProfile.disliked_foods ?? formData.unfavorite_foods,
      disliked_food_groups: freshProfile.disliked_food_groups ?? formData.disliked_food_groups,
    }
    : formData;
  const payload = normalizePayload({ ...source, save_user_data: true });
  return {
    ...payload,
    date: getVietnamDateString(),
    excludePreviousItems: true,
    randomSeed: Date.now(),
    force_regenerate: true,
    profile: freshProfile || undefined,
    favorite_foods: parseFoodList(source.favorite_foods),
    disliked_foods: parseFoodList(source.unfavorite_foods || source.disliked_foods),
    disliked_food_groups: parseFoodList(source.disliked_food_groups),
  };
}
function fmt(n) { return Number.isFinite(n) ? Math.round(n) : "—"; }

function getMealPlanItems(mealPlan) {
  if (!mealPlan) return [];
  if (Array.isArray(mealPlan.meals)) {
    return mealPlan.meals.flatMap((meal) => (Array.isArray(meal.items) ? meal.items : []));
  }
  if (Array.isArray(mealPlan)) {
    return mealPlan.flatMap((meal) => (Array.isArray(meal.items) ? meal.items : []));
  }
  return Object.values(mealPlan).flatMap((items) => (Array.isArray(items) ? items : []));
}

function getMealPlanKcal(mealPlan) {
  if (!mealPlan) return 0;
  const explicit = Number(mealPlan.total_kcal ?? mealPlan.totalKcal ?? mealPlan.total_calories ?? 0);
  if (Number.isFinite(explicit) && explicit > 0) return explicit;
  const items = getMealPlanItems(mealPlan);
  return items.reduce((sum, item) => sum + Number(item?.calories ?? item?.kcal ?? 0), 0);
}

function ensureValidMealPlanResult(result) {
  if (!result || result.eligible === false) return result;
  const items = getMealPlanItems(result.meal_plan);
  const totalKcal = getMealPlanKcal(result.meal_plan);
  if (!items.length || totalKcal <= 0) {
    throw new Error("Không thể tạo thực đơn hợp lệ. Meal plan đang rỗng hoặc kcal bằng 0.");
  }
  return result;
}



const STEPS = ["welcome","gender","body","activity","goal","diet","foods","summary"];

const INIT = {
  sex: "", weight: "", height: "", age: "",
  activity: "moderate", goal_type: "gain", gain_speed: "slow",
  target_weight: "", meal_complexity: "balanced", items_per_meal: 4,
  target_duration_value: "", target_duration_unit: "months",
  target_duration_months: "", target_gain_rate_kg_per_month: "",
  diet_style: "balanced", budget_level: "standard",
  favorite_foods: "", unfavorite_foods: "",
  meal_reminder_enabled: false,
  breakfast_time: "07:00",
  lunch_time: "12:00",
  dinner_time: "18:30",
  save_user_data: true,
};

// ─── OptionCard ──────────────────────────────────────────────────────────────
function OptionCard({ selected, onClick, title, desc, icon }) {
  return (
    <button type="button" onClick={onClick}
      className={`w-full rounded-2xl border-2 p-4 text-left transition-all hover:shadow-md ${
        selected
          ? "border-[#10B981] bg-[#ECFDF5] ring-2 ring-[#10B981]/20"
          : "border-[#E2E8F0] bg-white hover:border-[#10B981]/50 hover:bg-[#ECFDF5]/40"
      }`}>
      {icon && <div className="mb-2 text-2xl">{icon}</div>}
      <div className="text-sm font-bold text-[#0F172A]">{title}</div>
      {desc && <div className="mt-1 text-xs text-[#64748B]">{desc}</div>}
    </button>
  );
}

// ─── NumberField ─────────────────────────────────────────────────────────────
function NumberField({ label, name, value, onChange, placeholder, unit, error }) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-bold text-[#0F172A]">{label}</label>
      <div className="relative">
        <input type="number" name={name} value={value} onChange={onChange} placeholder={placeholder}
          className={`h-[52px] w-full rounded-2xl border-2 bg-white px-4 pr-12 text-base font-semibold text-[#0F172A] outline-none transition placeholder:text-[#64748B] focus:border-[#10B981] focus:ring-4 focus:ring-[#10B981]/10 ${error ? "border-[#EF4444]" : "border-[#E2E8F0]"}`} />
        {unit && <span className="absolute right-4 top-1/2 -translate-y-1/2 text-sm text-[#64748B]">{unit}</span>}
      </div>
      {error && <p className="mt-1 text-xs font-semibold text-[#EF4444]">{error}</p>}
    </div>
  );
}

// ─── StepWelcome ─────────────────────────────────────────────────────────────
function StepWelcome({ onNext }) {
  return (
    <div className="flex flex-col items-center text-center">
      <NutriGainLogo size="lg" />
      <h1 className="mt-6 text-3xl font-extrabold text-[#0F172A]">Thiết lập hồ sơ dinh dưỡng</h1>
      <p className="mt-3 max-w-md text-base text-[#64748B]">Trả lời vài câu hỏi ngắn để NutriGain tính calories, macro và tạo thực đơn phù hợp với bạn.</p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        {["Tính BMI / BMR / TDEE","Tạo thực đơn cá nhân hóa","Theo dõi calories & macro"].map(b=>(
          <span key={b} className="rounded-full border border-[#E2E8F0] bg-[#F8FAFC] px-4 py-2 text-sm font-semibold text-[#64748B]">{b}</span>
        ))}
      </div>
      <button onClick={onNext} className="mt-10 h-14 w-full max-w-sm rounded-2xl bg-[#10B981] text-base font-bold text-white shadow-lg shadow-[#10B981]/25 transition hover:bg-[#047857]">
        Bắt đầu →
      </button>
    </div>
  );
}

// ─── StepGender ──────────────────────────────────────────────────────────────
function StepGender({ data, update }) {
  const opts = [
    { v:"male", title:"Nam giới", icon:"👨" },
    { v:"female", title:"Nữ giới", icon:"👩" },
    { v:"undisclosed", title:"Tôi không muốn nói", icon:"🙂" },
  ];
  return (
    <div>
      <p className="mb-6 text-sm text-[#64748B]">Thông tin này giúp hệ thống ước lượng nhu cầu năng lượng chính xác hơn.</p>
      <div className="grid gap-3">
        {opts.map(o=>(
          <OptionCard key={o.v} selected={data.sex===o.v} onClick={()=>update("sex",o.v)} icon={o.icon} title={o.title} />
        ))}
      </div>
    </div>
  );
}

// ─── StepBody ────────────────────────────────────────────────────────────────
function StepBody({ data, update, errors, onLogout }) {
  function handle(e){ update(e.target.name, e.target.value); }
  const bmi = calculateAsianBmi(data.weight, data.height);
  const bmiCategory = classifyAsianBMI(bmi);
  const isOutOfScope = Number.isFinite(bmi) && bmi >= 18.5;

  let outOfScopeMessage = "";
  if (isOutOfScope) {
    if (bmiCategory === "normal") {
      outOfScopeMessage = "BMI của bạn hiện đang ở mức bình thường. NutriGain được thiết kế riêng cho người thiếu cân cần tăng cân lành mạnh, nên hiện chưa phù hợp để tạo thực đơn tăng cân cho hồ sơ này.";
    } else if (bmiCategory === "overweight") {
      outOfScopeMessage = "BMI của bạn hiện thuộc nhóm thừa cân. NutriGain được thiết kế riêng cho người thiếu cân cần tăng cân lành mạnh, nên hiện chưa phù hợp để tạo thực đơn tăng cân cho hồ sơ này.";
    } else if (bmiCategory === "obese") {
      outOfScopeMessage = "BMI của bạn hiện thuộc nhóm béo phì. NutriGain được thiết kế riêng cho người thiếu cân cần tăng cân lành mạnh, nên hiện chưa phù hợp để tạo thực đơn tăng cân cho hồ sơ này.";
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <NumberField label="Cân nặng hiện tại" name="weight" value={data.weight} onChange={handle} placeholder="60" unit="kg" error={errors.weight} />
        <NumberField label="Chiều cao" name="height" value={data.height} onChange={handle} placeholder="165" unit="cm" error={errors.height} />
        <div className="sm:col-span-2">
          <NumberField label="Tuổi" name="age" value={data.age} onChange={handle} placeholder="22" unit="tuổi" error={errors.age} />
        </div>
      </div>
      {Number.isFinite(bmi) && (
        isOutOfScope ? (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-[#92400E] animate-fade-in sm:col-span-2">
            <p className="text-xl font-black">BMI {bmi.toFixed(1)}</p>
            <p className="mt-3 text-sm font-semibold leading-relaxed">
              {outOfScopeMessage}
            </p>
            <p className="mt-3 text-sm font-semibold leading-relaxed">
              Bạn có thể đăng xuất khỏi hệ thống. Cảm ơn bạn đã quan tâm đến NutriGain.
            </p>
            <div className="mt-5">
              <button
                type="button"
                onClick={onLogout}
                className="h-11 rounded-xl bg-amber-600 px-6 text-sm font-black text-white shadow-md hover:bg-amber-700 transition"
              >
                Đăng xuất
              </button>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border border-[#D1FAE5] bg-[#ECFDF5] px-4 py-3 sm:col-span-2">
            <p className="text-xs font-bold uppercase tracking-widest text-[#047857]">BMI {bmi.toFixed(1)}</p>
            <p className="mt-1 text-sm font-bold leading-6 text-[#065F46]">{bmiPreviewMessage(bmiCategory)}</p>
          </div>
        )
      )}
    </div>
  );
}

// ─── StepActivity ────────────────────────────────────────────────────────────
function StepActivity({ data, update }) {
  const opts = [
    { v:"sedentary", title:"Ít vận động", desc:"Ngồi nhiều, ít vận động hoặc ít tập luyện.", icon:"🪑" },
    { v:"light", title:"Hoạt động nhẹ", desc:"Đi lại nhẹ hoặc tập 1–2 buổi/tuần.", icon:"🚶" },
    { v:"moderate", title:"Hoạt động vừa", desc:"Tập luyện 3–4 buổi/tuần.", icon:"🏃" },
    { v:"active", title:"Hoạt động cao", desc:"Vận động mạnh hoặc tập luyện thường xuyên.", icon:"💪" },
  ];
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {opts.map(o=>(
        <OptionCard key={o.v} selected={data.activity===o.v} onClick={()=>update("activity",o.v)} icon={o.icon} title={o.title} desc={o.desc} />
      ))}
    </div>
  );
}

// ─── StepGoal ────────────────────────────────────────────────────────────────
function StepGoal({ data, update, errors, validation }) {
  function handle(e){ update(e.target.name, e.target.value); }
  const weightGoalValidation = validation || validateWeightGoalTimeline({
    currentWeightKg: data.weight || data.weight_kg,
    targetWeightKg: data.target_weight || data.target_weight_kg,
    durationValue: data.target_duration_value || data.target_duration_months,
    durationUnit: data.target_duration_unit,
  });
  const goalPreview = buildWeightGoalPreview(data);
  const durationLabel = goalPreview.durationValue != null ? `${formatKg(goalPreview.durationValue)} ${goalPreview.durationUnit === "weeks" ? "tuần" : "tháng"}` : "";
  const targetDiffLabel = goalPreview.targetDiff != null ? formatKg(goalPreview.targetDiff) : "";
  const monthlyGainLabel = goalPreview.monthlyGain != null ? formatKg(goalPreview.monthlyGain) : "";
  const isBlocked = !weightGoalValidation.ok;
  const hasValidGoal = goalPreview.hasWeights && isValidNumber(goalPreview.currentWeight) && isValidNumber(goalPreview.targetWeight) && goalPreview.targetDiff > 0;
  const targetIsInvalid = goalPreview.hasWeights && isValidNumber(goalPreview.currentWeight) && isValidNumber(goalPreview.targetWeight) && goalPreview.targetWeight <= goalPreview.currentWeight;
  const hasFullTimeline = hasValidGoal && goalPreview.hasDuration && isValidNumber(goalPreview.monthlyGain);
  
  // Tính gợi ý thời gian dựa trên mốc Intermountain Health
  const recommendedMinMonths = hasValidGoal ? Math.ceil(goalPreview.targetDiff / SAFE_GAIN_MAX_KG_PER_MONTH) : null;
  const recommendedMaxMonths = hasValidGoal ? Math.ceil(goalPreview.targetDiff / SAFE_GAIN_MIN_KG_PER_MONTH) : null;
  
  const speedNote = hasFullTimeline
    ? (goalPreview.monthlyGain < SAFE_GAIN_MIN_KG_PER_MONTH
        ? `Tốc độ này chậm hơn mốc tham khảo quy đổi từ Intermountain Health: khoảng 0.5–2.0 lb/tuần, tương đương khoảng 1–3.6 kg/tháng. Nếu bạn muốn tiến độ rõ hơn, có thể rút ngắn thời gian mục tiêu. Nếu bạn muốn đi chậm và dễ duy trì, lựa chọn này vẫn có thể phù hợp.`
        : goalPreview.monthlyGain <= SAFE_GAIN_MAX_KG_PER_MONTH
          ? `Tốc độ này nằm trong mốc tham khảo quy đổi từ Intermountain Health: khoảng 0.5–2.0 lb/tuần, tương đương khoảng 1–3.6 kg/tháng. Hãy duy trì bữa ăn đều, thêm bữa phụ và theo dõi cơ thể trong quá trình tăng cân.`
          : `Tốc độ này cao hơn mốc tham khảo quy đổi từ Intermountain Health: khoảng 0.5–2.0 lb/tuần, tương đương khoảng 1–3.6 kg/tháng. Bạn nên theo dõi cơ thể và điều chỉnh nếu thấy khó duy trì.`)
    : `Khi có thời gian mục tiêu, NutriGain sẽ ước tính tốc độ tăng cân mỗi tháng cho bạn. NutriGain dùng mốc tham khảo từ Intermountain Health: 0.5–2.0 lb/tuần, tương đương khoảng 1–3.6 kg/tháng.`;
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <NumberField label="Cân nặng mục tiêu" name="target_weight" value={data.target_weight} onChange={handle} placeholder="65" unit="kg" error={errors.target_weight} />
        <NumberField label="Bạn muốn đạt mục tiêu trong bao lâu?" name="target_duration_value" value={data.target_duration_value} onChange={handle} placeholder="12" unit={data.target_duration_unit === "weeks" ? "tuần" : "tháng"} error={errors.target_duration_value} />
      </div>
      <div>
        <label className="mb-1.5 block text-sm font-bold text-[#0F172A]">Đơn vị thời gian</label>
        <select
          name="target_duration_unit"
          value={data.target_duration_unit || "months"}
          onChange={handle}
          className="h-[52px] w-full rounded-2xl border-2 border-[#E2E8F0] bg-white px-4 text-base font-semibold text-[#0F172A] outline-none transition focus:border-[#10B981] focus:ring-4 focus:ring-[#10B981]/10"
        >
          <option value="months">Tháng</option>
          <option value="weeks">Tuần</option>
        </select>
        {errors.target_duration_unit ? <p className="mt-1 text-xs font-semibold text-[#EF4444]">{errors.target_duration_unit}</p> : null}
      </div>
      <div className={`rounded-2xl border p-4 text-sm font-semibold ${isBlocked ? "border-rose-200 bg-rose-50/80 text-rose-800" : hasFullTimeline && goalPreview.monthlyGain >= SAFE_GAIN_MIN_KG_PER_MONTH && goalPreview.monthlyGain <= SAFE_GAIN_MAX_KG_PER_MONTH ? "border-[#D1FAE5] bg-[#ECFDF5] text-[#065F46]" : hasFullTimeline && goalPreview.monthlyGain < SAFE_GAIN_MIN_KG_PER_MONTH ? "border-blue-200 bg-blue-50 text-blue-800" : "border-[#D1FAE5] bg-[#ECFDF5] text-[#065F46]"}`}>
        {targetIsInvalid ? (
          <>
            <p className="text-rose-700">Mục tiêu cân nặng cần lớn hơn cân nặng hiện tại để NutriGain ước tính lộ trình tăng cân.</p>
            <p className="mt-2 text-rose-700">Vui lòng chọn cân nặng mục tiêu cao hơn cân nặng hiện tại.</p>
          </>
        ) : hasFullTimeline ? (
          <>
            <p className={isBlocked ? "text-rose-700" : ""}>Bạn muốn tăng {targetDiffLabel}kg trong {durationLabel}, tương đương khoảng {monthlyGainLabel}kg/tháng.</p>
            <p className="mt-2">{speedNote}</p>
            {isBlocked && weightGoalValidation.minMonths && weightGoalValidation.maxMonths && (
              <p className="mt-2 text-rose-700">Gợi ý: với mục tiêu tăng {targetDiffLabel}kg, bạn nên chọn khoảng {weightGoalValidation.minMonths}–{weightGoalValidation.maxMonths} tháng.</p>
            )}
          </>
        ) : hasValidGoal ? (
          <>
            <p className={isBlocked ? "text-rose-700" : ""}>Bạn muốn tăng {targetDiffLabel}kg so với cân nặng hiện tại.</p>
            <p className="mt-2">Vui lòng bổ sung thời gian mục tiêu để NutriGain ước tính tốc độ tăng cân mỗi tháng.</p>
            <p className="mt-2">{speedNote}</p>
            {recommendedMinMonths && recommendedMaxMonths && (
              <p className="mt-2">Gợi ý: với mục tiêu tăng {targetDiffLabel}kg, bạn có thể chọn khoảng {recommendedMinMonths}–{recommendedMaxMonths} tháng.</p>
            )}
          </>
        ) : (
          <>
            <p className={isBlocked ? "text-rose-700" : ""}>Hãy nhập cân nặng hiện tại và cân nặng mục tiêu để NutriGain ước tính lộ trình tăng cân.</p>
            <p className="mt-2">Khi có đủ dữ liệu, NutriGain sẽ tính giúp bạn tốc độ tăng cân mỗi tháng.</p>
          </>
        )}
        <p className={`mt-2 text-xs font-medium ${isBlocked ? "text-rose-700" : ""}`}>NutriGain chỉ hỗ trợ ước tính tham khảo, không thay thế tư vấn từ chuyên gia dinh dưỡng.</p>
      </div>
    </div>
  );
}

// ─── StepDiet ────────────────────────────────────────────────────────────────
function StepDiet({ data, update }) {
  const diets = [
    { v:"balanced", title:"Cân bằng", icon:"⚖️" },
    { v:"eat_clean", title:"Eat Clean", icon:"🥬" },
    { v:"high_protein", title:"Giàu Protein", icon:"🥩" },
    { v:"vegetarian", title:"Ăn chay", icon:"🌱" },
  ];
  const budgets = [
    { v:"low", title:"Tiết kiệm" },
    { v:"standard", title:"Tiêu chuẩn" },
    { v:"high", title:"Linh hoạt" },
  ];
  const complexities = [
    { v:"simple", title:"3 món/bữa" },
    { v:"balanced", title:"4 món/bữa" },
    { v:"full", title:"5 món/bữa" },
  ];
  return (
    <div className="space-y-6">
      <div>
        <p className="mb-3 text-sm font-bold text-[#0F172A]">Phong cách ăn uống</p>
        <div className="grid gap-3 sm:grid-cols-2">
          {diets.map(d=>(
            <OptionCard key={d.v} selected={data.diet_style===d.v} onClick={()=>update("diet_style",d.v)} icon={d.icon} title={d.title} />
          ))}
        </div>
      </div>
      <div>
        <p className="mb-3 text-sm font-bold text-[#0F172A]">Ngân sách</p>
        <div className="grid gap-3 grid-cols-3">
          {budgets.map(b=>(
            <OptionCard key={b.v} selected={data.budget_level===b.v} onClick={()=>update("budget_level",b.v)} title={b.title} />
          ))}
        </div>
      </div>
      <div>
        <p className="mb-3 text-sm font-bold text-[#0F172A]">Số món mỗi bữa</p>
        <div className="grid gap-3 grid-cols-3">
          {complexities.map(c=>(
            <OptionCard key={c.v} selected={data.meal_complexity===c.v} onClick={()=>update("meal_complexity",c.v)} title={c.title} />
          ))}
        </div>
      </div>
      <div className="rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-bold text-[#0F172A]">Nhắc giờ ăn</p>
            <p className="mt-1 text-sm text-[#64748B]">NutriGain sẽ gửi email nhắc bạn khi đến giờ ăn.</p>
          </div>
          <label className="flex items-center gap-2 text-sm font-bold text-[#0F172A]">
            <input
              type="checkbox"
              checked={Boolean(data.meal_reminder_enabled)}
              onChange={(event)=>update("meal_reminder_enabled", event.target.checked)}
              className="h-5 w-5 rounded border-[#CBD5E1] text-[#10B981] focus:ring-[#10B981]"
            />
            Bật nhắc giờ ăn qua email
          </label>
        </div>
        {data.meal_reminder_enabled && (
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            {[
              ["breakfast_time", "Giờ ăn sáng", "07:00"],
              ["lunch_time", "Giờ ăn trưa", "12:00"],
              ["dinner_time", "Giờ ăn tối", "18:30"],
            ].map(([name, label, fallback]) => (
              <label key={name} className="block">
                <span className="mb-1.5 block text-sm font-bold text-[#0F172A]">{label}</span>
                <input
                  type="time"
                  value={data[name] || fallback}
                  onChange={(event)=>update(name, event.target.value || fallback)}
                  className="h-[46px] w-full rounded-2xl border-2 border-[#E2E8F0] bg-white px-3 text-sm font-semibold text-[#0F172A] outline-none transition focus:border-[#10B981] focus:ring-4 focus:ring-[#10B981]/10"
                />
              </label>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── TagChip ─────────────────────────────────────────────────────────────────
function TagInput({ label, name, value, onChange, placeholder }) {
  const [draft, setDraft] = useState("");
  const tags = value ? String(value).split(",").map(t=>t.trim()).filter(Boolean) : [];
  function addTag(e){
    if((e.key==="Enter"||e.key===",") && draft.trim()){
      e.preventDefault();
      const next=[...tags,draft.trim()].join(", ");
      onChange({ target:{ name, value:next } });
      setDraft("");
    }
  }
  function removeTag(tag){
    const next=tags.filter(t=>t!==tag).join(", ");
    onChange({ target:{ name, value:next } });
  }
  return (
    <div>
      <label className="mb-1.5 block text-sm font-bold text-[#0F172A]">{label}</label>
      <div className="min-h-[52px] rounded-2xl border-2 border-[#E2E8F0] bg-white p-2 focus-within:border-[#10B981]">
        <div className="flex flex-wrap gap-1.5 mb-1">
          {tags.map(t=>(
            <span key={t} className="flex items-center gap-1 rounded-full bg-[#ECFDF5] px-3 py-1 text-xs font-bold text-[#10B981]">
              {t}
              <button type="button" onClick={()=>removeTag(t)} className="text-[#10B981]/60 hover:text-[#EF4444]">×</button>
            </span>
          ))}
        </div>
        <input value={draft} onChange={e=>setDraft(e.target.value)} onKeyDown={addTag}
          placeholder={tags.length===0 ? placeholder : "Nhấn Enter để thêm..."}
          className="w-full bg-transparent px-2 text-sm text-[#0F172A] outline-none placeholder:text-[#64748B]" />
      </div>
      <p className="mt-1 text-xs text-[#64748B]">Nhấn Enter để thêm tag.</p>
    </div>
  );
}

// ─── StepFoods ────────────────────────────────────────────────────────────────
function StepFoods({ data, update }) {
  function handle(e){ update(e.target.name, e.target.value); }
  return (
    <div className="space-y-6">
      <TagInput label="Món yêu thích" name="favorite_foods" value={data.favorite_foods} onChange={handle} placeholder="Ví dụ: chuối, sữa, cơm, trứng" />
      <TagInput label="Món không thích / dị ứng" name="unfavorite_foods" value={data.unfavorite_foods} onChange={handle} placeholder="Ví dụ: tôm, đậu phộng, trứng" />
    </div>
  );
}

// ─── StepSummary ─────────────────────────────────────────────────────────────
function StepSummary({ data, onFinish, onBack, isSaving, finishError, step, isExistingUser }) {
  const preview = useMemo(()=>calculateNutritionTarget({
    weight: data.weight, height: data.height, age: data.age,
    sex: data.sex, activity: data.activity,
    goal_type: data.goal_type, gain_speed: data.gain_speed,
  }),[data]);

  const bmiCategory = classifyAsianBMI(preview.bmi);
  const bmiLabel = asianBmiLabel(bmiCategory);
  const bmiMessage = bmiPreviewMessage(bmiCategory);
  const stats = [
    { label:"BMI", value:fmt(preview.bmi), sub: bmiLabel, color:"text-[#10B981]" },
    { label:"Mục tiêu", value:`${fmt(preview.targetCalories)} kcal`, sub:"mỗi ngày", color:"text-[#FB923C]" },
    { label:"Protein", value:`${fmt(preview.proteinTarget)}g`, sub:"mỗi ngày", color:"text-[#3B82F6]" },
    { label:"Carbs", value:`${fmt(preview.carbTarget)}g`, sub:"mỗi ngày", color:"text-[#10B981]" },
    { label:"Fat", value:`${fmt(preview.fatTarget)}g`, sub:"mỗi ngày", color:"text-[#FB923C]" },
    { label:"BMR", value:`${fmt(preview.bmr)} kcal`, sub:"năng lượng nền", color:"text-[#64748B]" },
  ];
  return (
    <div>
      <p className="mb-6 text-sm text-[#64748B]">Dựa trên thông tin bạn nhập, đây là chỉ số dinh dưỡng dự kiến:</p>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {stats.map(s=>(
          <div key={s.label} className="rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] p-4">
            <p className="text-xs font-bold uppercase tracking-widest text-[#64748B]">{s.label}</p>
            <p className={`mt-1 text-xl font-black ${s.color}`}>{s.value}</p>
            <p className="text-xs text-[#64748B]">{s.sub}</p>
          </div>
        ))}
      </div>
      <div className="mt-4 rounded-2xl border border-[#D1FAE5] bg-[#ECFDF5] px-4 py-3 text-sm font-bold leading-6 text-[#065F46]">
        {bmiMessage}
      </div>
      <div className="mt-8">
        {finishError && (
          <div className="mb-4 rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-bold leading-6 text-red-600">
            {finishError}
          </div>
        )}
        <div className="flex items-center justify-between gap-4">
          {((isExistingUser && step > 0) || (!isExistingUser && step > 1)) && (
            <button onClick={onBack}
              className="flex h-12 items-center gap-2 rounded-2xl border-2 border-[#E2E8F0] px-6 text-sm font-bold text-[#64748B] transition hover:border-[#10B981] hover:text-[#10B981] flex-none">
              ← Quay lại
            </button>
          )}
          <button onClick={onFinish} disabled={isSaving}
            className="flex h-12 flex-1 items-center justify-center gap-2 rounded-2xl bg-[#10B981] text-sm font-bold text-white shadow-md shadow-[#10B981]/25 transition hover:bg-[#047857] disabled:opacity-60">
            {isSaving ? "Đang cập nhật..." : isExistingUser ? "Cập nhật và tạo thực đơn" : "Hoàn tất và tạo thực đơn"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── validate per step ───────────────────────────────────────────────────────
function validateStep(stepName, data) {
  const errs = {};
  if (stepName==="gender" && !data.sex) errs._step="Vui lòng chọn giới tính";
  if (stepName==="body") {
    if (!safeNum(data.weight)) errs.weight="Vui lòng nhập cân nặng hợp lệ";
    if (!safeNum(data.height)) errs.height="Vui lòng nhập chiều cao hợp lệ";
    if (!safeNum(data.age)) errs.age="Vui lòng nhập tuổi hợp lệ";
  }
  if (stepName==="activity" && !data.activity) errs._step="Vui lòng chọn mức độ hoạt động";
  if (stepName === "goal") {
    const target = safeNum(data.target_weight || data.target_weight_kg);
    const weight = safeNum(data.weight || data.weight_kg);
    const height = safeNum(data.height || data.height_cm);
    if (!target) {
      errs.target_weight = "Vui lòng nhập cân nặng mục tiêu hợp lệ";
    } else if (target <= weight) {
      errs.target_weight = "Mục tiêu nên lớn hơn cân nặng hiện tại";
    } else if (height > 0) {
      const targetBmi = target / ((height / 100) ** 2);
      if (targetBmi >= 23.0) {
        const minNormal = (18.5 * ((height / 100) ** 2)).toFixed(1);
        const maxNormal = (22.9 * ((height / 100) ** 2)).toFixed(1);
        errs.target_weight = `Cân nặng mục tiêu vượt vùng BMI bình thường theo chuẩn Châu Á. Vui lòng chọn mục tiêu trong khoảng ${minNormal}kg–${maxNormal}kg.`;
      }
    }
  }
  return errs;
}

function validateProfile(data) {
  const errs = {};
  if (!data.sex) errs.sex = "Vui lòng chọn giới tính";
  const weight = safeNum(data.weight || data.weight_kg);
  const height = safeNum(data.height || data.height_cm);
  if (!weight) errs.weight = "Vui lòng nhập cân nặng hợp lệ";
  if (!height) errs.height = "Vui lòng nhập chiều cao hợp lệ";
  if (!safeNum(data.age)) errs.age = "Vui lòng nhập tuổi hợp lệ";
  if (!data.activity && !data.activity_level) errs.activity = "Vui lòng chọn mức độ vận động";
  if (!data.diet_style && !data.diet_type) errs.diet_style = "Vui lòng chọn chế độ ăn";
  if (!data.budget_level) errs.budget_level = "Vui lòng chọn ngân sách";
  if (!data.meal_complexity && !data.items_per_meal) errs.meal_complexity = "Vui lòng chọn số món mỗi bữa";

  const target = safeNum(data.target_weight || data.target_weight_kg);
  const durationValue = data.target_duration_value === "" || data.target_duration_value == null
    ? (data.target_duration_months === "" || data.target_duration_months == null ? null : Number(data.target_duration_months))
    : Number(data.target_duration_value);
  const durationUnit = data.target_duration_unit || "months";
  const weightGainPlan = buildWeightGainPlan(weight, target, durationValue, durationUnit);
  if (!target) {
    errs.target_weight = "Vui lòng nhập cân nặng mục tiêu hợp lệ";
  } else if (weight && target <= weight) {
    errs.target_weight = "Cân nặng mục tiêu phải lớn hơn cân nặng hiện tại.";
  } else if (height > 0) {
    const targetBmi = target / ((height / 100) ** 2);
    if (targetBmi >= 23.0) {
      const minNormal = (18.5 * ((height / 100) ** 2)).toFixed(1);
      const maxNormal = (22.9 * ((height / 100) ** 2)).toFixed(1);
      errs.target_weight = `Cân nặng mục tiêu vượt vùng BMI bình thường theo chuẩn Châu Á. Vui lòng chọn mục tiêu trong khoảng ${minNormal}kg–${maxNormal}kg.`;
    }
  }
  if (!data.target_duration_value && !data.target_duration_months) {
    errs.target_duration_value = "Vui lòng nhập thời gian hợp lệ.";
  } else if (weightGainPlan.fieldErrors.target_duration_value) {
    errs.target_duration_value = weightGainPlan.fieldErrors.target_duration_value;
  }
  if (!data.target_duration_unit) {
    errs.target_duration_unit = "Vui lòng chọn đơn vị thời gian.";
  }
  if (!errs.target_weight && weightGainPlan.fieldErrors.target_weight) {
    errs.target_weight = weightGainPlan.fieldErrors.target_weight;
  }
  return errs;
}

function isProfileDataComplete(data) {
  return Boolean(
    data?.age &&
    (data.sex || data.gender) &&
    (data.height || data.height_cm) &&
    (data.weight || data.weight_kg) &&
    (data.activity || data.activity_level) &&
    (data.gain_speed || data.weight_gain_speed) &&
    (data.diet_style || data.diet_type) &&
    data.budget_level &&
    (data.meal_complexity || data.items_per_meal)
  );
}

export default function OnboardingView({ userEmail, onComplete, initialData, user, onLogout, profileFormMode = "register_onboarding" }) {
  const [step, setStep] = useState(0);
  const [data, setData] = useState(() => ({ ...INIT, ...(initialData || {}) }));
  const [errors, setErrors] = useState({});
  const [isSaving, setIsSaving] = useState(false);
  const [finishError, setFinishError] = useState("");
  const [profileSaveNotice, setProfileSaveNotice] = useState("");
  const [regenerateFailed, setRegenerateFailed] = useState(false);
  const [regenerateErrorMsg, setRegenerateErrorMsg] = useState("");

  // Load existing profile from `user` prop when editing or when initialData absent
  useEffect(() => {
    const profile = user?.profile || user || null;
    if (!profile) return;
    setData((prev) => ({
      ...prev,
      weight: profile.weight_kg ?? prev.weight,
      weight_kg: profile.weight_kg ?? prev.weight_kg,
      height: profile.height_cm ?? prev.height,
      height_cm: profile.height_cm ?? prev.height_cm,
      age: profile.age ?? prev.age,
      sex: profile.sex ?? profile.gender ?? prev.sex,
      activity: profile.activity_level ?? prev.activity,
      gain_speed: profile.weight_gain_speed ?? prev.gain_speed,
      weight_gain_speed: profile.weight_gain_speed ?? prev.weight_gain_speed,
      target_weight: profile.target_weight_kg ?? prev.target_weight,
      target_weight_kg: profile.target_weight_kg ?? prev.target_weight_kg,
      target_duration_value: profile.target_duration_value ?? profile.target_duration_months ?? prev.target_duration_value,
      target_duration_unit: profile.target_duration_unit ?? prev.target_duration_unit ?? "months",
      target_duration_months: profile.target_duration_months ?? prev.target_duration_months,
      target_gain_rate_kg_per_month: profile.target_gain_rate_kg_per_month ?? prev.target_gain_rate_kg_per_month,
      meal_complexity: profile.items_per_meal === 3 ? "simple" : profile.items_per_meal === 5 ? "full" : prev.meal_complexity,
      diet_style: profile.diet_type === "low_carb" ? "high_protein" : profile.diet_type ?? prev.diet_style,
      budget_level: profile.budget_level ?? prev.budget_level,
      favorite_foods: profile.favorite_foods !== undefined && profile.favorite_foods !== null ? foodListToInput(profile.favorite_foods) : prev.favorite_foods,
      unfavorite_foods: profile.disliked_foods !== undefined && profile.disliked_foods !== null ? foodListToInput(profile.disliked_foods) : prev.unfavorite_foods,
      disliked_foods: profile.disliked_foods !== undefined && profile.disliked_foods !== null ? parseFoodList(profile.disliked_foods) : prev.disliked_foods,
      meal_reminder_enabled: Boolean(profile.meal_reminder_enabled),
      breakfast_time: profile.breakfast_time || prev.breakfast_time || "07:00",
      lunch_time: profile.lunch_time || prev.lunch_time || "12:00",
      dinner_time: profile.dinner_time || prev.dinner_time || "18:30",
    }));
  }, [user]);

  const isLoggedIn = Boolean(user);
  const hasExistingProfile = Boolean(
    user?.profile || 
    user?.onboarding_completed || 
    (user?.weight_kg || user?.height_cm || user?.age)
  );
  const isExistingUser = (isLoggedIn && hasExistingProfile) || profileFormMode === "edit_after_auth" || profileFormMode === "edit_after_login";

  const isOnboardingMode = !isExistingUser;
  const isEditProfileMode = isExistingUser;
  const isEditingExistingProfile = isEditProfileMode;
  const stepsToShow = isEditProfileMode ? STEPS.filter(s => s !== "welcome") : STEPS;
  const stepName = stepsToShow[step] || "";
  const isLastStep = stepName === "summary";
  const isSummary = stepName === "summary";
  const profileComplete = isProfileDataComplete(data);
  const totalVisible = stepsToShow.length;
  const progressStep = Math.max(0, step);
  const progressPct = totalVisible > 1 ? Math.round((progressStep / (totalVisible - 1)) * 100) : 0;
  const currentBmi = calculateAsianBmi(data.weight || data.weight_kg, data.height || data.height_cm);
  const canGenerateMealPlan = classifyAsianBMI(currentBmi) === "underweight";
  const weightGoalValidation = useMemo(
    () => validateWeightGoalTimeline({
      currentWeightKg: data.weight || data.weight_kg,
      targetWeightKg: data.target_weight || data.target_weight_kg,
      durationValue: data.target_duration_value || data.target_duration_months,
      durationUnit: data.target_duration_unit,
    }),
    [data.weight, data.weight_kg, data.target_weight, data.target_weight_kg, data.target_duration_value, data.target_duration_months, data.target_duration_unit]
  );

  const stepTitles = {
    welcome: "Chào mừng đến NutriGain",
    gender: "Giới tính của bạn là gì?",
    body: "Thông tin cơ thể của bạn",
    activity: "Mức độ hoạt động hằng ngày",
    goal: "Mục tiêu tăng cân của bạn",
    diet: "Phong cách ăn uống",
    foods: "Sở thích và loại trừ",
    summary: isEditProfileMode ? "Xác nhận cập nhật hồ sơ" : "Hồ sơ của bạn đã sẵn sàng 🎉",
  };

  function update(field, value) {
    setData(p => {
      const next = { ...p, [field]: value };
      if (field === "weight") next.weight_kg = value;
      if (field === "weight_kg") next.weight = value;
      if (field === "height") next.height_cm = value;
      if (field === "height_cm") next.height = value;
      if (field === "target_weight") next.target_weight_kg = value;
      if (field === "target_weight_kg") next.target_weight = value;
      if (field === "target_duration_value") next.target_duration_months = value;
      if (field === "target_duration_months") next.target_duration_value = value;
      const weightGainPlan = buildWeightGainPlan(
        next.weight || next.weight_kg,
        next.target_weight || next.target_weight_kg,
        next.target_duration_value || next.target_duration_months,
        next.target_duration_unit,
      );
      if (weightGainPlan.durationMonths !== null) next.target_duration_months = weightGainPlan.durationMonths;
      if (weightGainPlan.requiredGainPerMonth !== null) next.target_gain_rate_kg_per_month = weightGainPlan.requiredGainPerMonth;
      if (weightGainPlan.suggestedSpeed) {
        next.gain_speed = weightGainPlan.suggestedSpeed;
        next.weight_gain_speed = weightGainPlan.suggestedSpeed;
      }
      if (field === "meal_reminder_enabled" && value) {
        next.breakfast_time = next.breakfast_time || "07:00";
        next.lunch_time = next.lunch_time || "12:00";
        next.dinner_time = next.dinner_time || "18:30";
      }
      return next;
    });
    setErrors(p => ({ ...p, [field]: "", _step: "" }));
  }

  function handleChange(e){ update(e.target.name, e.target.value); }

  function goNext() {
    const errs = validateStep(stepName, data);
    if (Object.keys(errs).length > 0) { setErrors(errs); return; }

    if (stepName === "goal") {
      console.log("[WEIGHT GOAL VALIDATION]", weightGoalValidation);
      if (!weightGoalValidation.ok) {
        console.warn("[WEIGHT GOAL BLOCKED]", weightGoalValidation);
        setErrors((current) => ({
          ...current,
          target_weight: weightGoalValidation.error || current.target_weight,
          target_duration_value: weightGoalValidation.error || current.target_duration_value,
          target_duration_unit: weightGoalValidation.error || current.target_duration_unit,
        }));
        return;
      }
    }
    
    if (stepName === "body") {
      const currentBmi = calculateAsianBmi(data.weight || data.weight_kg, data.height || data.height_cm);
      if (Number.isFinite(currentBmi) && currentBmi >= 18.5) {
        return;
      }
    }

    setErrors({});
    setStep(s=>Math.min(s+1, stepsToShow.length-1));
    window.scrollTo({top:0,behavior:"smooth"});
  }

  function goBack() {
    setErrors({});
    setStep(s=>Math.max(s-1,0));
    window.scrollTo({top:0,behavior:"smooth"});
  }

  async function handleFinish() {
    const stepErrors = validateStep(stepName, data);
    if (Object.keys(stepErrors).length > 0) {
      setErrors(stepErrors);
      setFinishError("Vui lòng hoàn thành thông tin của bước hiện tại.");
      return;
    }

    const finalWeightGoalValidation = validateWeightGoalTimeline({
      currentWeightKg: data.weight || data.weight_kg,
      targetWeightKg: data.target_weight || data.target_weight_kg,
      durationValue: data.target_duration_value || data.target_duration_months,
      durationUnit: data.target_duration_unit,
    });
    if (!finalWeightGoalValidation.ok) {
      console.warn("[WEIGHT GOAL BLOCKED]", finalWeightGoalValidation);
      setErrors((current) => ({
        ...current,
        target_weight: finalWeightGoalValidation.error || current.target_weight,
        target_duration_value: finalWeightGoalValidation.error || current.target_duration_value,
        target_duration_unit: finalWeightGoalValidation.error || current.target_duration_unit,
      }));
      setFinishError(finalWeightGoalValidation.error || "Vui lòng chọn thời gian dài hơn.");
      return;
    }

    const validationErrors = validateProfile(data);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      setFinishError("Vui lòng hoàn thiện các thông tin bắt buộc trước khi tạo thực đơn.");
      return;
    }

    setIsSaving(true);
    setFinishError("");
    setProfileSaveNotice("");
    setRegenerateFailed(false);
    setRegenerateErrorMsg("");
    try {
      // Convert form data to backend profile format
      const backendProfile = mapFormStateToBackendProfile(data);
      console.log("[PROFILE SUBMIT WEIGHT DEBUG]", {
        form_weight_kg: data.weight_kg ?? data.weight,
        payload_weight_kg: backendProfile.weight_kg,
        currentUser_weight_kg: user?.profile?.weight_kg,
        payload: backendProfile,
      });
      console.log("[PROFILE SUBMIT PAYLOAD CHECK]", {
        weight_kg: backendProfile.weight_kg,
        target_weight_kg: backendProfile.target_weight_kg,
        height_cm: backendProfile.height_cm,
        diet_type: backendProfile.diet_type,
        items_per_meal: backendProfile.items_per_meal,
        payload: backendProfile,
      });
      
      // Update user profile via API
      const result = await updateUserProfile(backendProfile);
      if (backendProfile.meal_reminder_enabled) {
        setProfileSaveNotice("Đã lưu giờ nhắc bữa ăn.");
      }
      console.log("[PROFILE PUT RESULT] =", result);
      const updatedUser = await fetchCurrentUser();
      console.log("[PROFILE REFRESH /users/me] =", updatedUser);
      console.log("[PROFILE STATE AFTER SAVE]", {
        weight_kg: updatedUser?.profile?.weight_kg,
        target_weight_kg: updatedUser?.profile?.target_weight_kg,
        height_cm: updatedUser?.profile?.height_cm,
        diet_type: updatedUser?.profile?.diet_type,
        items_per_meal: updatedUser?.profile?.items_per_meal,
        favorite_foods: updatedUser?.profile?.favorite_foods,
        disliked_foods: updatedUser?.profile?.disliked_foods,
      });
      const freshProfile = updatedUser?.profile;

      const outOfScopeResult = buildAsianBmiOutOfScopeResult(data);
      if (outOfScopeResult) {
        if (onComplete) {
          onComplete({
            ...data,
            _mealPlanResult: outOfScopeResult,
            _updatedUser: updatedUser
          }, false);
        }
        setIsSaving(false);
        return;
      }

      // Regenerate meal plan (may fail) — handle regeneration errors separately
      let mealPlanResult = null;
      try {
        console.log("[REGENERATE USING FRESH PROFILE]", {
          user_id: updatedUser?.id,
          email: updatedUser?.email,
          weight_kg: freshProfile?.weight_kg,
          target_weight_kg: freshProfile?.target_weight_kg,
          height_cm: freshProfile?.height_cm,
          diet_type: freshProfile?.diet_type,
          items_per_meal: freshProfile?.items_per_meal,
        });
        mealPlanResult = ensureValidMealPlanResult(
          await postRegenerateMealPlan(buildRegeneratePayload(data, freshProfile))
        );
      } catch (err) {
        console.error("Regenerate failed after profile save:", err);
        const msg = err?.message || String(err) || "Không thể tạo thực đơn";
        setFinishError(`Hồ sơ đã lưu, nhưng chưa tạo được thực đơn: ${msg}`);
        setRegenerateFailed(true);
        setRegenerateErrorMsg(msg);
        setIsSaving(false);
        return;
      }
      // Call the onComplete callback with regenerated data
      if (onComplete) {
        onComplete({
          ...data,
          _mealPlanResult: mealPlanResult,
          _updatedUser: updatedUser
        }, false);
      }
    } catch (error) {
      console.error("Onboarding error:", error);
      setProfileSaveNotice("");
      setFinishError(error?.message || "Không thể lưu hồ sơ. Vui lòng kiểm tra thông tin và thử lại.");
      setIsSaving(false);
    }
  }

  async function retryRegenerate() {
    const outOfScopeResult = buildAsianBmiOutOfScopeResult(data);
    if (outOfScopeResult) {
      const updatedUser = await fetchCurrentUser();
      onComplete?.({ ...data, _mealPlanResult: outOfScopeResult, _updatedUser: updatedUser }, false);
      return;
    }
    setIsSaving(true);
    setFinishError("");
    setRegenerateFailed(false);
    try {
      const updatedUser = await fetchCurrentUser();
      const freshProfile = updatedUser?.profile;
      console.log("[REGENERATE USING FRESH PROFILE]", {
        user_id: updatedUser?.id,
        email: updatedUser?.email,
        weight_kg: freshProfile?.weight_kg,
        target_weight_kg: freshProfile?.target_weight_kg,
        height_cm: freshProfile?.height_cm,
        diet_type: freshProfile?.diet_type,
        items_per_meal: freshProfile?.items_per_meal,
      });
      const mealPlanResult = ensureValidMealPlanResult(
        await postRegenerateMealPlan(buildRegeneratePayload(data, freshProfile))
      );
      if (onComplete) {
        onComplete({ ...data, _mealPlanResult: mealPlanResult, _updatedUser: updatedUser }, false);
      }
    } catch (err) {
      console.error("Retry regenerate failed:", err);
      const msg = err?.message || String(err) || "Không thể tạo thực đơn";
      setFinishError(`Vẫn chưa tạo được thực đơn: ${msg}`);
      setRegenerateFailed(true);
      setRegenerateErrorMsg(msg);
      setIsSaving(false);
    }
  }

  async function gotoDashboard() {
    setIsSaving(true);
    try {
      const updatedUser = await fetchCurrentUser();
      if (onComplete) {
        onComplete({ ...data, _updatedUser: updatedUser }, false);
      }
    } catch (err) {
      console.error("Goto dashboard failed (fetch user):", err);
      setFinishError(err?.message || "Không thể chuyển đến Dashboard");
    } finally {
      setIsSaving(false);
    }
  }

  console.log({
    user,
    profile: user?.profile,
    isLoggedIn,
    hasExistingProfile,
    isExistingUser,
    isLastStep,
    currentStep: step
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#ECFDF5] via-[#F8FAFC] to-[#FFF7ED] px-4 py-8 sm:px-6">
      {/* Top bar */}
      <div className="mx-auto flex max-w-3xl items-center justify-between">
        <NutriGainLogo size="sm" />
        <div className="flex items-center gap-4">
          {userEmail && <span className="text-sm text-[#64748B]">{userEmail}</span>}
          {onLogout && (
            <button onClick={onLogout} className="text-sm font-semibold text-[#64748B] hover:text-[#10B981] transition">
              Đăng xuất
            </button>
          )}
        </div>
      </div>

      {/* Progress bar (hidden on welcome) */}
      {stepName !== "welcome" && (
        <div className="mx-auto mt-6 max-w-3xl">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-[#64748B]">Bước {progressStep + 1} / {totalVisible}</span>
            <span className="text-xs font-bold text-[#10B981]">{progressPct}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-[#E2E8F0]">
            <div className="h-full rounded-full bg-[#10B981] transition-all duration-500" style={{width:`${progressPct}%`}} />
          </div>
        </div>
      )}

      {/* Card */}
      <div className="mx-auto mt-6 max-w-3xl rounded-[28px] border border-[#E2E8F0] bg-white p-6 shadow-xl sm:p-10">
        {stepName !== "welcome" && (
          <div className="mb-6">
            <h2 className="text-2xl font-extrabold text-[#0F172A] sm:text-3xl">{stepTitles[stepName]}</h2>
          </div>
        )}

        {/* Step error */}
        {errors._step && (
          <div className="mb-4 rounded-2xl border border-[#EF4444]/20 bg-red-50 px-4 py-3 text-sm font-semibold text-[#EF4444]">
            {errors._step}
          </div>
        )}
        {profileSaveNotice && (
          <div className="mb-4 rounded-2xl border border-[#A7F3D0] bg-[#ECFDF5] px-4 py-3 text-sm font-semibold text-[#047857]">
            {profileSaveNotice}
          </div>
        )}

        {/* Step content */}
        {stepName==="welcome" && <StepWelcome onNext={goNext} />}
        {stepName==="gender" && <StepGender data={data} update={update} />}
        {stepName==="body" && <StepBody data={data} update={update} errors={errors} onLogout={onLogout} />}
        {stepName==="activity" && <StepActivity data={data} update={update} />}
        {stepName==="goal" && <StepGoal data={data} update={update} errors={errors} validation={weightGoalValidation} onChange={handleChange} />}
        {stepName==="diet" && <StepDiet data={data} update={update} />}
        {stepName==="foods" && <StepFoods data={data} update={update} onChange={handleChange} />}
        {stepName==="summary" && (
          <StepSummary data={data} isSaving={isSaving} finishError={finishError}
            onFinish={handleFinish} onBack={goBack} step={step} isExistingUser={isExistingUser} />
        )}
        {stepName !== "welcome" && !isSummary && !(stepName === "body" && currentBmi >= 18.5) && (
          <div className="mt-8 flex items-center justify-between gap-4">
            {/* 1. Back Button */}
            {((isOnboardingMode && step > 1) || (isEditProfileMode && step > 0)) && (
              <button onClick={goBack}
                className="flex h-12 items-center gap-2 rounded-2xl border-2 border-[#E2E8F0] px-6 text-sm font-bold text-[#64748B] transition hover:border-[#10B981] hover:text-[#10B981] flex-none">
                ← Quay lại
              </button>
            )}

            {/* 2. Middle "Cập nhật và tạo thực đơn" if existing user */}
            {isExistingUser && (
              <button onClick={handleFinish} disabled={isSaving}
                className="flex h-12 flex-1 items-center justify-center gap-2 rounded-2xl border-2 border-[#10B981] text-[#10B981] bg-emerald-50/30 hover:bg-emerald-50 text-sm font-bold transition disabled:opacity-60">
                {isSaving ? "Đang lưu..." : "Cập nhật và tạo thực đơn"}
              </button>
            )}

            {/* 3. Primary Next Button */}
            <button
              onClick={goNext}
              disabled={stepName === "goal" && !weightGoalValidation.ok}
              className={`flex h-12 flex-1 items-center justify-center gap-2 rounded-2xl text-sm font-bold text-white shadow-md shadow-[#10B981]/25 transition ${stepName === "goal" && !weightGoalValidation.ok ? "cursor-not-allowed bg-slate-300 shadow-none" : "bg-[#10B981] hover:bg-[#047857]"}`}>
              Tiếp tục →
            </button>
          </div>
        )}
        {regenerateFailed && (
          <div className="mt-6 flex gap-3">
            <button onClick={retryRegenerate} disabled={isSaving}
              className="flex-1 h-12 rounded-2xl bg-[#059669] text-sm font-bold text-white shadow-md transition hover:bg-[#047857] disabled:opacity-60">
              {isSaving ? "Đang thử tạo lại..." : "Thử tạo lại thực đơn"}
            </button>
            <button onClick={gotoDashboard} disabled={isSaving}
              className="h-12 rounded-2xl border-2 border-[#E2E8F0] px-6 text-sm font-bold text-[#64748B] transition hover:border-[#10B981] hover:text-[#10B981] disabled:opacity-60">
              Vào Dashboard
            </button>
          </div>
        )}
      </div>

    </div>
  );
}
