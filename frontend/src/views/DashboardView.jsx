import { useMemo, useState, useEffect } from "react";

import { saveUserProfile, submitRecommendation } from "../controllers/recommendationController";
import AccountPanel from "../components/AccountPanel";
import CaloriesChart from "../components/CaloriesChart";
import EnergyChart from "../components/EnergyChart";
import Header from "../components/Header";
import MacroChart from "../components/MacroChart";
import Sidebar from "../components/Sidebar";
import StatCard from "../components/StatCard";
import { defaultFormState } from "../models/recommendationModel";
import { calculateNutritionTarget } from "../utils/nutritionTarget";
import { validateMealPlan } from "../utils/mealPlanValidation";

const fallbackSummary = {
  targetCalories: 2203,
  eatenCalories: 0,
  bmr: 1260,
  tdee: 1953,
  bmi: 18.2,
  bmiStatus: "Gầy",
  medicalWarning: "",
  protein: 95,
  fat: 61,
  carbs: 318,
};

const pageTitles = {
  overview: "Tổng quan dinh dưỡng",
  journal: "Nhật ký ăn uống",
  charts: "Biểu đồ dinh dưỡng",
  "meal-plan": "Kế hoạch bữa ăn",
  account: "Tài khoản",
  system: "Cài đặt hệ thống",
  notifications: "Thông báo",
  help: "Hỗ trợ",
};

const mealLabels = {
  breakfast: "Bữa sáng",
  lunch: "Bữa trưa",
  dinner: "Bữa tối",
  snack: "Bữa phụ",
};

const mealKeysByLabel = Object.fromEntries(Object.entries(mealLabels).map(([key, label]) => [label, key]));

const mealAccents = {
  breakfast: "green",
  lunch: "blue",
  dinner: "orange",
  snack: "green",
};

const defaultFoodImage = "/images/placeholders/food-default.svg";
const dislikedFoodsStorageKey = "nutrigain_disliked_foods";
const dislikedFoodGroupsStorageKey = "nutrigain_disliked_food_groups";

export default function DashboardView({ userEmail, onLogout }) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [activeSection, setActiveSection] = useState("overview");

  useEffect(() => {
    if (activeSection === "system" || activeSection === "settings") {
      setActiveSection("overview");
    }
  }, [activeSection]);
  const [formState, setFormState] = useState(() => ({
    ...defaultFormState,
    disliked_foods: loadStoredList(dislikedFoodsStorageKey),
    disliked_food_groups: loadStoredList(dislikedFoodGroupsStorageKey),
  }));
  const [result, setResult] = useState(null);
  const [formErrors, setFormErrors] = useState({});
  const [submitError, setSubmitError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [favoriteMeals, setFavoriteMeals] = useState(() => new Set());
  const [ratings, setRatings] = useState({});
  const [mealLog, setMealLog] = useState({ entries: {}, manualItems: [] });
  const [addToMealRequest, setAddToMealRequest] = useState(null);
  const [dislikeRequest, setDislikeRequest] = useState(null);

  const hasRecommendation = Boolean(result);
  const meals = useMemo(() => buildMeals(result, formState.diet_style, formState), [result, formState]);
  const consumedNutrition = useMemo(() => calculateConsumedNutrition(meals, mealLog), [meals, mealLog]);
  const summary = useMemo(() => buildSummary(result, consumedNutrition), [result, consumedNutrition]);
  const weeklyCalories = useMemo(() => buildWeeklyCalories(result, summary), [result, summary]);
  const calorieProgress = Math.round((summary.eatenCalories / Math.max(summary.targetCalories, 1)) * 100);
  const nutritionTarget = useMemo(() => calculateNutritionTarget(formState), [formState]);
  const effectiveTarget = useMemo(
    () => buildEffectiveTarget(result, nutritionTarget),
    [result, nutritionTarget],
  );
  const mealPlanValidation = useMemo(
    () => validateMealPlan(result?.meal_plan || {}, formState, effectiveTarget),
    [result, formState, effectiveTarget],
  );
  const macroData = useMemo(
    () => ({
      protein: consumedNutrition.protein,
      fat: consumedNutrition.fat,
      carbs: consumedNutrition.carbs,
    }),
    [consumedNutrition],
  );
  const eligibility = useMemo(() => buildEligibilityStatus(formState, summary), [formState, summary]);
  const dataWarnings = useMemo(
    () => buildDataWarnings(formState, summary, mealPlanValidation, effectiveTarget),
    [formState, summary, mealPlanValidation, effectiveTarget],
  );
  const foodCatalog = useMemo(() => buildFoodCatalog(result, meals), [result, meals]);
  const datasetStats = useMemo(() => buildDatasetStats(result, foodCatalog), [result, foodCatalog]);

  function handleProfileChange(event) {
    const { name, value, type, checked } = event.target;
    setFormState((current) => ({
      ...current,
      [name]: type === "checkbox" ? checked : value,
    }));
    setSubmitError("");
    setFormErrors((current) => ({ ...current, [name]: "" }));
  }

  async function requestRecommendation() {
    const nextErrors = validateProfile(formState);
    setFormErrors(nextErrors);
    setSubmitError("");

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setIsSubmitting(true);
    try {
      const data = await submitRecommendation(formState);
      setResult(data);
      setFavoriteMeals(new Set());
      setRatings({});
      setMealLog({ entries: {}, manualItems: [] });
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setSubmitError(err.message || "Không thể tạo thực đơn. Vui lòng kiểm tra backend và thử lại.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleProfileSubmit(event) {
    event.preventDefault();
    await requestRecommendation();
  }

  function handleEditProfile() {
    setResult(null);
    setSubmitError("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handleSidebarNavigate(sectionId) {
    setActiveSection(sectionId);
    setDrawerOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function toggleFavorite(mealId) {
    setFavoriteMeals((current) => {
      const next = new Set(current);
      if (next.has(mealId)) {
        next.delete(mealId);
      } else {
        next.add(mealId);
      }
      return next;
    });
  }

  function rateMeal(mealId, value) {
    setRatings((current) => ({ ...current, [mealId]: value }));
  }

  function handleAddToMeal(food, mealKeyOrLabel, options = {}) {
    const mealKey = mealLabels[mealKeyOrLabel] ? mealKeyOrLabel : mealKeysByLabel[mealKeyOrLabel] || mealKeyOrLabel;
    if (!mealKey || !result?.meal_plan?.[mealKey]) {
      return { status: "missing_meal" };
    }

    const currentItems = result.meal_plan[mealKey] || [];
    const expectedCount = expectedItemsPerMeal(formState.meal_complexity);
    if (currentItems.length >= expectedCount && options.replaceIndex == null && !options.allowExtra) {
      setAddToMealRequest({ food, mealKey });
      return { status: "needs_choice" };
    }

    const payload = toMealPlanPayload(food, options.allowExtra ? "extra" : "suggested");
    setResult((current) => {
      if (!current?.meal_plan?.[mealKey]) return current;
      const nextMealPlan = { ...current.meal_plan };
      const nextItems = [...(nextMealPlan[mealKey] || [])];
      if (options.replaceIndex != null && nextItems[options.replaceIndex]) {
        nextItems[options.replaceIndex] = payload;
      } else {
        nextItems.push(payload);
      }
      nextMealPlan[mealKey] = nextItems;
      return { ...current, meal_plan: nextMealPlan };
    });
    setAddToMealRequest(null);
    return { status: "added" };
  }

  function handleDislikeFood(food, dislikeType = "food") {
    const foodKey = String(food?.foodId || food?.id || food?.name || "").trim();
    const groupKey = String(food?.technicalCategory || food?.subCategory || food?.foodGroup || food?.category || "").trim();
    const nextDislikedFoods = dislikeType === "group" ? formState.disliked_foods : uniqueValues([...(formState.disliked_foods || []), foodKey || food?.name]);
    const nextDislikedGroups = dislikeType === "group" ? uniqueValues([...(formState.disliked_food_groups || []), groupKey]) : formState.disliked_food_groups || [];

    setFormState((current) => ({
      ...current,
      disliked_foods: nextDislikedFoods.filter(Boolean),
      disliked_food_groups: nextDislikedGroups.filter(Boolean),
    }));
    persistDislikedProfile(nextDislikedFoods, nextDislikedGroups);
    setResult((current) => removeDislikedFromResult(current, food, dislikeType));
    setDislikeRequest(null);
  }

  function handleExportReport() {
    if (!hasRecommendation) return;
    const rows = [
      ["Metric", "Value", "Unit"],
      ["Calories mục tiêu", summary.targetCalories, "kcal"],
      ["Calories hiện tại", mealPlanValidation.totalCalories, "kcal"],
      ["BMI", summary.bmi, ""],
      ["BMR", summary.bmr, "kcal"],
      ["TDEE", summary.tdee, "kcal"],
      ["Protein hiện tại", mealPlanValidation.totalProtein, "g"],
      ["Fat hiện tại", mealPlanValidation.totalFat, "g"],
      ["Carbs hiện tại", mealPlanValidation.totalCarbs, "g"],
    ];
    const csv = rows.map((row) => row.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "nutrigain-report.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="min-h-screen overflow-x-hidden bg-dashboard text-slate-900">
      <Sidebar
        isOpen={drawerOpen}
        activeSection={activeSection}
        userEmail={userEmail}
        onClose={() => setDrawerOpen(false)}
        onNavigate={handleSidebarNavigate}
        onLogout={onLogout}
      />
      {drawerOpen ? (
        <button
          className="drawer-overlay fixed inset-0 z-30 lg:hidden"
          aria-label="Đóng menu"
          onClick={() => setDrawerOpen(false)}
        />
      ) : null}

      <div className="lg:pl-72">
        <Header
          title={hasRecommendation ? pageTitles[activeSection] || pageTitles.overview : "Thiết lập hồ sơ dinh dưỡng"}
          onToggleMenu={() => setDrawerOpen(true)}
          onEditProfile={handleEditProfile}
          onExport={handleExportReport}
        />

        {!hasRecommendation ? (
          <ProfileSetup
            formState={formState}
            errors={formErrors}
            submitError={submitError}
            isSubmitting={isSubmitting}
            onChange={handleProfileChange}
            onSubmit={handleProfileSubmit}
          />
        ) : (
          <DashboardContent
            result={result}
            userEmail={userEmail}
            profileSettings={formState}
            summary={summary}
            meals={meals}
            foodCatalog={foodCatalog}
            datasetStats={datasetStats}
            weeklyCalories={weeklyCalories}
            calorieProgress={calorieProgress}
            macroData={macroData}
            nutritionTarget={effectiveTarget}
            eligibility={eligibility}
            dataWarnings={dataWarnings}
            validation={mealPlanValidation}
            activeSection={activeSection}
            favoriteMeals={favoriteMeals}
            ratings={ratings}
            mealLog={mealLog}
            consumedNutrition={consumedNutrition}
            onFavorite={toggleFavorite}
            onRate={rateMeal}
            onMealLogChange={setMealLog}
            onProfileChange={handleProfileChange}
            onRegenerate={requestRecommendation}
            onOpenAddToMeal={(food) => setAddToMealRequest({ food, mealKey: null })}
            onOpenDislikeFood={(food) => setDislikeRequest(food)}
            isSubmitting={isSubmitting}
            handleSidebarNavigate={handleSidebarNavigate}
          />
        )}
      </div>
      <AddToMealModal
        request={addToMealRequest}
        meals={meals}
        expectedCount={expectedItemsPerMeal(formState.meal_complexity)}
        onAdd={handleAddToMeal}
        onClose={() => setAddToMealRequest(null)}
      />
      <DislikeFoodModal
        food={dislikeRequest}
        onDislike={handleDislikeFood}
        onClose={() => setDislikeRequest(null)}
      />
    </div>
  );
}

function ProfileSetup({ formState, errors, submitError, isSubmitting, onChange, onSubmit }) {
  const previewTarget = useMemo(() => calculateNutritionTarget(formState), [formState]);
  const macroTotal = previewTarget.proteinTarget + previewTarget.fatTarget + previewTarget.carbTarget;
  const bmiStatus = bmiStatusLabel(previewTarget.bmi);

  return (
    <main className="px-4 pb-10 pt-6 sm:px-6 xl:px-8">
      <section className="grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(360px,0.9fr)] lg:items-start">
        <form
          id="profile-setup-form"
          className="rounded-[28px] border border-emerald-100/80 bg-white p-6 shadow-xl shadow-emerald-900/10 sm:p-7"
          onSubmit={onSubmit}
          noValidate
        >
          <div>
            <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">Thiết lập hồ sơ</p>
            <h2 className="mt-2 text-3xl font-black text-slate-950">Thiết lập hồ sơ dinh dưỡng</h2>
            <p className="mt-2 text-sm font700 leading-6 text-slate-500">
              Điền thông tin cơ thể và mục tiêu để NutriGain dự báo BMI, calories và macro cá nhân hóa.
            </p>
          </div>

          <div className="mt-6 grid gap-6">
            <section className="rounded-3xl border border-slate-100 bg-white/95 p-5 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font900 uppercase tracking-[0.16em] text-emerald-700">01 · Thông tin cơ thể</p>
                  <h3 className="mt-1 text-lg font-black text-slate-950">Thông tin cơ thể</h3>
                </div>
                <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font900 text-emerald-700">Bắt buộc</span>
              </div>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <ProfileField
                  label="Cân nặng (kg)"
                  name="weight"
                  type="number"
                  min="20"
                  max="250"
                  value={formState.weight}
                  error={errors.weight}
                  onChange={onChange}
                />
                <ProfileField
                  label="Chiều cao (cm)"
                  name="height"
                  type="number"
                  min="100"
                  max="230"
                  value={formState.height}
                  error={errors.height}
                  onChange={onChange}
                />
                <ProfileField
                  label="Tuổi"
                  name="age"
                  type="number"
                  min="1"
                  max="120"
                  placeholder="Tùy chọn"
                  value={formState.age}
                  error={errors.age}
                  onChange={onChange}
                />
                <ProfileSelect
                  label="Giới tính"
                  name="sex"
                  value={formState.sex}
                  error={errors.sex}
                  onChange={onChange}
                  options={[
                    { value: "", label: "Không chọn" },
                    { value: "male", label: "Nam" },
                    { value: "female", label: "Nữ" },
                  ]}
                />
                <div className="sm:col-span-2">
                  <ProfileSelect
                    label="Mức độ hoạt động"
                    name="activity"
                    value={formState.activity}
                    error={errors.activity}
                    onChange={onChange}
                    options={[
                      { value: "default", label: "Mặc định" },
                      { value: "sedentary", label: "Ít vận động" },
                      { value: "light", label: "Nhẹ" },
                      { value: "moderate", label: "Vừa phải" },
                      { value: "active", label: "Năng động" },
                      { value: "very_active", label: "Rất năng động" },
                    ]}
                  />
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-100 bg-white/95 p-5 shadow-sm">
              <div>
                <p className="text-xs font900 uppercase tracking-[0.16em] text-emerald-700">02 · Mục tiêu dinh dưỡng</p>
                <h3 className="mt-1 text-lg font-black text-slate-950">Mục tiêu dinh dưỡng</h3>
              </div>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <ProfileSelect
                  label="Mục tiêu cá nhân"
                  name="goal_type"
                  value={formState.goal_type}
                  error={errors.goal_type}
                  onChange={onChange}
                  options={[
                    { value: "gain", label: "Tăng cân lành mạnh" },
                    { value: "muscle_gain", label: "Tăng cơ" },
                  ]}
                />
                <ProfileSelect
                  label="Mức calories"
                  name="gain_speed"
                  value={formState.gain_speed}
                  error={errors.gain_speed}
                  onChange={onChange}
                  options={[
                    { value: "slow", label: "Nhẹ, ổn định" },
                    { value: "medium", label: "Vừa phải" },
                    { value: "fast", label: "Mạnh hơn" },
                  ]}
                />
                <ProfileSelect
                  label="Số món mỗi bữa"
                  name="meal_complexity"
                  value={formState.meal_complexity}
                  error={errors.meal_complexity}
                  onChange={onChange}
                  options={[
                    { value: "simple", label: "Đơn giản - 3 món/bữa" },
                    { value: "balanced", label: "Cân bằng - 4 món/bữa" },
                    { value: "full", label: "Đầy đủ - 5 món/bữa" },
                  ]}
                />
                <ProfileSelect
                  label="Chế độ ăn"
                  name="diet_style"
                  value={formState.diet_style}
                  error={errors.diet_style}
                  onChange={onChange}
                  options={[
                    { value: "balanced", label: "Cân bằng / eat clean" },
                    { value: "vegetarian", label: "Chay" },
                    { value: "low_carb", label: "Low-carb" },
                  ]}
                />
                <div className="sm:col-span-2">
                  <ProfileSelect
                    label="Ngân sách"
                    name="budget_level"
                    value={formState.budget_level}
                    error={errors.budget_level}
                    onChange={onChange}
                    options={[
                      { value: "standard", label: "Tiêu chuẩn" },
                      { value: "low", label: "Tiết kiệm" },
                      { value: "high", label: "Linh hoạt" },
                    ]}
                  />
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-100 bg-white/95 p-5 shadow-sm">
              <div>
                <p className="text-xs font900 uppercase tracking-[0.16em] text-emerald-700">03 · Món yêu thích</p>
                <h3 className="mt-1 text-lg font-black text-slate-950">Món yêu thích</h3>
                <p className="mt-2 text-sm font700 text-slate-500">Thêm món hoặc nguyên liệu bạn muốn ưu tiên.</p>
              </div>
              <div className="mt-4">
                <TagInput
                  label="Danh sách món yêu thích"
                  name="favorite_foods"
                  placeholder="Ví dụ: ức gà, yến mạch, chuối"
                  helperText="Nhấn Enter để thêm tag, dùng dấu phẩy để ngăn cách."
                  value={formState.favorite_foods}
                  error={errors.favorite_foods}
                  onChange={onChange}
                />
              </div>
            </section>

            <section className="rounded-3xl border border-slate-100 bg-white/95 p-5 shadow-sm">
              <div>
                <p className="text-xs font900 uppercase tracking-[0.16em] text-emerald-700">04 · Dị ứng / món không thích</p>
                <h3 className="mt-1 text-lg font-black text-slate-950">Dị ứng / món không thích</h3>
                <p className="mt-2 text-sm font700 text-slate-500">Loại bỏ món không phù hợp với bạn.</p>
              </div>
              <div className="mt-4">
                <TagInput
                  label="Danh sách cần tránh"
                  name="unfavorite_foods"
                  placeholder="Ví dụ: hải sản, đậu phộng"
                  helperText="NutriGain sẽ loại bỏ các món trùng tag này khỏi gợi ý."
                  value={formState.unfavorite_foods}
                  error={errors.unfavorite_foods}
                  onChange={onChange}
                />
              </div>
            </section>
          </div>

          <label className="mt-6 flex items-start gap-3 rounded-2xl bg-emerald-50/70 p-4 text-sm font800 text-slate-700">
            <input
              type="checkbox"
              name="save_user_data"
              checked={formState.save_user_data}
              onChange={onChange}
              className="mt-1 h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
            />
            Lưu hồ sơ để lần sau hệ thống cá nhân hóa tốt hơn.
          </label>

          {submitError ? (
            <div className="mt-5 rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm font800 text-red-600" role="alert">
              {submitError}
            </div>
          ) : null}

          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-6 flex min-h-[52px] w-full items-center justify-center rounded-3xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-base font900 text-emerald-800 shadow-sm transition hover:-translate-y-0.5 hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Đang tạo thực đơn..." : "Tạo thực đơn hôm nay"}
          </button>
        </form>

        <aside className="space-y-5">
          <section className="rounded-[28px] border border-emerald-100/80 bg-white p-6 shadow-xl shadow-emerald-900/10">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">Tóm tắt hồ sơ</p>
                <h3 className="mt-2 text-2xl font-black text-slate-950">Chỉ số dự kiến hôm nay</h3>
                <p className="mt-2 text-sm font700 leading-6 text-slate-500">
                  Tính theo dữ liệu bạn nhập. Hệ thống sẽ tinh chỉnh thêm sau khi tạo thực đơn.
                </p>
              </div>
              <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-2xl bg-emerald-50 ring-1 ring-emerald-100">
                <img src="/images/hero-food.png" alt="Minh họa dinh dưỡng" className="h-full w-full object-cover" />
                <div className="absolute inset-0 bg-gradient-to-t from-white/70 via-white/10 to-transparent" />
              </div>
            </div>

            <div className="mt-6 grid gap-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl bg-emerald-50 p-4">
                  <p className="text-xs font900 uppercase tracking-[0.12em] text-emerald-700">BMI</p>
                  <div className="mt-2 flex items-end gap-2">
                    <span className="text-3xl font-black text-slate-950">{previewTarget.bmi}</span>
                    <span className="pb-1 text-xs font900 text-emerald-700">{bmiStatus}</span>
                  </div>
                  <p className="mt-2 text-xs font800 text-emerald-700">Theo cân nặng & chiều cao</p>
                </div>
                <div className="rounded-2xl bg-orange-50 p-4">
                  <p className="text-xs font900 uppercase tracking-[0.12em] text-orange-700">Kcal mục tiêu</p>
                  <div className="mt-2 text-3xl font-black text-slate-950">
                    {previewTarget.targetCalories.toLocaleString("vi-VN")}
                  </div>
                  <p className="mt-2 text-xs font800 text-orange-700">kcal / ngày</p>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-100 bg-slate-50/80 p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs font900 uppercase tracking-[0.12em] text-slate-500">Macro mục tiêu</p>
                  <span className="rounded-full bg-white px-3 py-1 text-xs font900 text-slate-600 ring-1 ring-slate-100">
                    {macroTotal}g
                  </span>
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs font900">
                  <div className="rounded-2xl bg-white p-3 ring-1 ring-slate-100">
                    <span className="mx-auto block h-2 w-10 rounded-full bg-sky-500" />
                    <div className="mt-2 text-lg font-black text-slate-950">{previewTarget.proteinTarget}g</div>
                    <div className="text-[11px] font900 uppercase tracking-[0.12em] text-slate-500">Protein</div>
                  </div>
                  <div className="rounded-2xl bg-white p-3 ring-1 ring-slate-100">
                    <span className="mx-auto block h-2 w-10 rounded-full bg-orange-400" />
                    <div className="mt-2 text-lg font-black text-slate-950">{previewTarget.fatTarget}g</div>
                    <div className="text-[11px] font900 uppercase tracking-[0.12em] text-slate-500">Fat</div>
                  </div>
                  <div className="rounded-2xl bg-white p-3 ring-1 ring-slate-100">
                    <span className="mx-auto block h-2 w-10 rounded-full bg-emerald-500" />
                    <div className="mt-2 text-lg font-black text-slate-950">{previewTarget.carbTarget}g</div>
                    <div className="text-[11px] font900 uppercase tracking-[0.12em] text-slate-500">Carbs</div>
                  </div>
                </div>
              </div>

              <button
                type="submit"
                form="profile-setup-form"
                disabled={isSubmitting}
                className="mt-2 flex h-12 w-full items-center justify-center rounded-3xl bg-gradient-to-r from-emerald-500 to-orange-400 px-5 text-base font900 text-white shadow-lg shadow-orange-500/20 transition hover:-translate-y-0.5 hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSubmitting ? "Đang tạo thực đơn..." : "Tạo thực đơn hôm nay"}
              </button>
              <p className="text-xs font800 text-slate-500">
                Bạn có thể chỉnh lại thông tin trước khi gửi yêu cầu tạo thực đơn.
              </p>
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}

function DashboardContent({
  result,
  userEmail,
  profileSettings,
  summary,
  meals,
  foodCatalog,
  datasetStats,
  weeklyCalories,
  calorieProgress,
  macroData,
  nutritionTarget,
  eligibility,
  dataWarnings,
  validation,
  activeSection,
  favoriteMeals,
  ratings,
  mealLog,
  consumedNutrition,
  onFavorite,
  onRate,
  onMealLogChange,
  onProfileChange,
  onRegenerate,
  onOpenAddToMeal,
  onOpenDislikeFood,
  isSubmitting,
  handleSidebarNavigate,
}) {
  return (
    <main className="px-4 pb-8 pt-4 sm:px-6 xl:px-8">
      {activeSection === "overview" ? (
        <OverviewPage
          summary={summary}
          validation={validation}
          nutritionTarget={nutritionTarget}
          calorieProgress={calorieProgress}
          eligibility={eligibility}
          dataWarnings={dataWarnings}
          weeklyCalories={weeklyCalories}
          meals={meals}
          consumedNutrition={consumedNutrition}
          onRegenerate={onRegenerate}
          isSubmitting={isSubmitting}
        />
      ) : null}

      {activeSection === "journal" ? (
        <JournalPage
          meals={meals}
          validation={validation}
          nutritionTarget={nutritionTarget}
          mealLog={mealLog}
          onMealLogChange={onMealLogChange}
        />
      ) : null}

      {activeSection === "meal-plan" ? (
        <MealsPage
          summary={summary}
          meals={meals}
          validation={validation}
          profileSettings={profileSettings}
          favoriteMeals={favoriteMeals}
          ratings={ratings}
          onFavorite={onFavorite}
          onRate={onRate}
          onRegenerate={onRegenerate}
          onOpenDislikeFood={onOpenDislikeFood}
          isSubmitting={isSubmitting}
        />
      ) : null}

      {activeSection === "foods" ? <FoodsPage foods={foodCatalog} meals={meals} profileSettings={profileSettings} onOpenAddToMeal={onOpenAddToMeal} onOpenDislikeFood={onOpenDislikeFood} /> : null}

      {activeSection === "charts" ? (
        <ChartsPage
          weeklyCalories={weeklyCalories}
          macroData={macroData}
          summary={summary}
          meals={meals}
          validation={validation}
          consumedNutrition={consumedNutrition}
        />
      ) : null}

      {activeSection === "account" ? (
        <AccountSettingsPage
          email={userEmail}
          profile={profileSettings}
          eligibility={eligibility}
          errors={buildProfileSoftErrors(profileSettings)}
          onChange={onProfileChange}
          onRegenerate={onRegenerate}
          isSubmitting={isSubmitting}
        />
      ) : null}

      {activeSection === "system" ? (
        <SystemSettingsPage
          result={result}
          datasetStats={datasetStats}
          progress={calorieProgress}
          summary={summary}
          validation={validation}
        />
      ) : null}
      {activeSection === "notifications" ? (
        <EnhancedNotificationPanel
          progress={calorieProgress}
          summary={summary}
          validation={validation}
          dataWarnings={dataWarnings}
          onNavigate={handleSidebarNavigate}
        />
      ) : null}
      {activeSection === "help" ? <EnhancedHelpPanel foods={foodCatalog} /> : null}
    </main>
  );
}

function OverviewPage({
  summary,
  validation,
  nutritionTarget,
  calorieProgress,
  eligibility,
  dataWarnings,
  weeklyCalories,
  meals,
  consumedNutrition,
  onRegenerate,
  isSubmitting,
}) {
  const remainingCalories = Math.max(nutritionTarget.targetCalories - consumedNutrition.calories, 0);
  const actionFood = findEnergySupportFood(meals);
  return (
    <div className="space-y-5">
      <DailyNutritionSummary
        validation={validation}
        consumedNutrition={consumedNutrition}
        nutritionTarget={nutritionTarget}
        onRegenerate={onRegenerate}
        isSubmitting={isSubmitting}
      />

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Kcal mục tiêu" value={summary.targetCalories} unit="kcal" tone="green" />
        <StatCard label="Kcal đã ăn" value={consumedNutrition.calories} unit="kcal" tone="navy" />
        <StatCard label="BMI" value={summary.bmi} unit={summary.bmiStatus} tone="mint" />
        <StatCard label="Hoàn thành" value={calorieProgress} unit="%" tone="orange" />
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <EligibilityCard eligibility={eligibility} />
        <ProgressCard profile={eligibility.profile} />
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,0.95fr)_minmax(360px,1.05fr)]">
        <ActionSuggestionCard remainingCalories={remainingCalories} actionFood={actionFood} validation={validation} />
        <MiniTrendCard data={weeklyCalories} metricLabel="kcal" />
      </section>

      {dataWarnings.length ? (
        <section className="grid gap-3 md:grid-cols-2">
          {dataWarnings.map((warning) => (
            <WarningCard key={warning} text={warning} />
          ))}
        </section>
      ) : null}

      <section className="glass-panel p-5">
          <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">Năng lượng</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <InfoRow label="BMR" value={`${summary.bmr} kcal`} />
            <InfoRow label="TDEE" value={`${summary.tdee} kcal`} />
            <InfoRow label="Ngưỡng thấp" value={`${nutritionTarget.minCalories} kcal`} />
            <InfoRow label="Ngưỡng cao" value={`${nutritionTarget.maxCalories} kcal`} />
          </div>
      </section>
    </div>
  );
}

function JournalPage({ meals, validation, nutritionTarget, mealLog, onMealLogChange }) {
  const entries = mealLog?.entries || {};
  const manualItems = mealLog?.manualItems || [];
  const [manualDraft, setManualDraft] = useState({
    mealTitle: meals[0]?.title || "",
    name: "",
    calories: "",
    protein: "",
    fat: "",
    carbs: "",
  });
  const mealRows = meals.map((meal) => buildJournalMealRow(meal, entries, manualItems));
  const actualTotals = sumJournalRows(mealRows);

  function updateEntry(key, patch) {
    onMealLogChange((current) => ({
      ...current,
      entries: {
        ...(current.entries || {}),
        [key]: {
          ...(current.entries?.[key] || {}),
          ...patch,
        },
      },
    }));
  }

  function addManualItem(event) {
    event.preventDefault();
    const name = manualDraft.name.trim();
    const mealTitle = manualDraft.mealTitle || meals[0]?.title;
    const calories = Number(manualDraft.calories);
    if (!name || !mealTitle || !Number.isFinite(calories) || calories < 0) return;

    onMealLogChange((current) => ({
      ...current,
      manualItems: [
        ...(current.manualItems || []),
        {
          id: `manual-${Date.now()}`,
          status: "manual",
          mealTitle,
          name,
          calories: round(calories),
          protein: round(manualDraft.protein),
          fat: round(manualDraft.fat),
          carbs: round(manualDraft.carbs),
        },
      ],
    }));
    setManualDraft((current) => ({ ...current, name: "", calories: "", protein: "", fat: "", carbs: "" }));
  }

  return (
    <div className="space-y-5">
      <section className="glass-panel p-5 sm:p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">Nhật ký ăn uống</p>
            <h2 className="mt-2 text-2xl font-black text-slate-950">Theo dõi từng bữa trong ngày</h2>
          </div>
          <span className="w-fit rounded-full bg-slate-950 px-4 py-2 text-sm font900 text-white">
            {round(actualTotals.calories).toLocaleString("vi-VN")} / {validation.totalCalories.toLocaleString("vi-VN")} kcal
          </span>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-4">
          <InfoTile label="Kcal gợi ý" value={`${validation.totalCalories.toLocaleString("vi-VN")} kcal`} />
          <InfoTile label="Kcal đã ăn" value={`${round(actualTotals.calories).toLocaleString("vi-VN")} kcal`} />
          <InfoTile label="Protein đã ăn" value={`${round(actualTotals.protein)}g / ${nutritionTarget.proteinTarget}g`} />
          <InfoTile label="Macro thực tế" value={`F ${round(actualTotals.fat)}g · C ${round(actualTotals.carbs)}g`} />
        </div>

        <form className="mt-5 rounded-2xl bg-white/80 p-4 ring-1 ring-slate-100" onSubmit={addManualItem}>
          <div className="grid gap-3 md:grid-cols-[1fr_1.4fr_repeat(4,minmax(86px,0.7fr))_auto]">
            <select
              className="h-11 rounded-2xl border border-slate-200 bg-white px-3 text-sm font800 outline-none focus:border-emerald-500"
              value={manualDraft.mealTitle || meals[0]?.title || ""}
              onChange={(event) => setManualDraft((current) => ({ ...current, mealTitle: event.target.value }))}
              aria-label="Chọn bữa"
            >
              {meals.map((meal) => (
                <option key={meal.title} value={meal.title}>{meal.title}</option>
              ))}
            </select>
            <input
              className="h-11 rounded-2xl border border-slate-200 bg-white px-3 text-sm font800 outline-none focus:border-emerald-500"
              placeholder="Thêm món thủ công"
              value={manualDraft.name}
              onChange={(event) => setManualDraft((current) => ({ ...current, name: event.target.value }))}
            />
            {["calories", "protein", "fat", "carbs"].map((field) => (
              <input
                key={field}
                type="number"
                min="0"
                className="h-11 rounded-2xl border border-slate-200 bg-white px-3 text-sm font800 outline-none focus:border-emerald-500"
                placeholder={field === "calories" ? "kcal" : field}
                value={manualDraft[field]}
                onChange={(event) => setManualDraft((current) => ({ ...current, [field]: event.target.value }))}
              />
            ))}
            <button type="submit" className="h-11 rounded-2xl bg-emerald-600 px-4 text-sm font900 text-white">
              Thêm
            </button>
          </div>
        </form>

        <div className="mt-5 grid gap-3">
          {mealRows.map((meal) => (
            <article key={meal.title} className="rounded-2xl bg-white/85 p-4 ring-1 ring-slate-100">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h3 className="text-lg font-black text-slate-950">{meal.title}</h3>
                  <p className="mt-1 text-sm font800 text-slate-500">
                    {meal.items.length} món · gợi ý {meal.suggested.calories} kcal · đã ăn {meal.actual.calories} kcal
                  </p>
                  <MealStatusPill status={meal.status} />
                </div>
                <div className="grid grid-cols-3 gap-2 sm:min-w-[320px]">
                  <MacroMini label="Protein" value={meal.actual.protein} color="bg-sky-500" />
                  <MacroMini label="Fat" value={meal.actual.fat} color="bg-orange-400" />
                  <MacroMini label="Carbs" value={meal.actual.carbs} color="bg-emerald-500" />
                </div>
              </div>

              <div className="mt-4 grid gap-3">
                {meal.items.map((item) => {
                  const entryKey = `${meal.title}-${item.id}`;
                  const entry = entries[entryKey] || {};
                  const baseGrams = Number(item.servingGrams || 100) || 100;
                  const entryStatus = entry.status || "suggested";
                  return (
                    <div key={entryKey} className="grid gap-3 rounded-2xl bg-slate-50 p-3 ring-1 ring-slate-100 lg:grid-cols-[minmax(0,1fr)_150px_120px_110px] lg:items-center">
                      <div className="flex min-w-0 items-start gap-3">
                        <span className={`mt-1 h-3 w-3 rounded-full ${entryStatus === "suggested" ? "bg-slate-300" : entryStatus === "skipped" ? "bg-orange-300" : "bg-emerald-500"}`} />
                        <span className="min-w-0">
                          <span className="block truncate text-sm font900 text-slate-950">{item.name}</span>
                          <span className="mt-1 block text-xs font800 text-slate-500">
                            Gợi ý {item.calories} kcal · {item.servingDisplay || `${baseGrams}g`}
                          </span>
                        </span>
                      </div>
                      <select
                        className="h-10 rounded-2xl border border-slate-200 bg-white px-3 text-sm font800 outline-none focus:border-emerald-500"
                        value={entryStatus}
                        onChange={(event) => updateEntry(entryKey, { status: event.target.value })}
                        aria-label={`Trạng thái ${item.name}`}
                      >
                        <option value="suggested">Gợi ý</option>
                        <option value="eaten">Đã ăn</option>
                        <option value="partial">Ăn một phần</option>
                        <option value="skipped">Bỏ qua</option>
                      </select>
                      <input
                        type="number"
                        min="1"
                        className="h-10 rounded-2xl border border-slate-200 bg-white px-3 text-sm font800 outline-none focus:border-emerald-500"
                        value={entry.grams ?? baseGrams}
                        onChange={(event) => updateEntry(entryKey, { grams: event.target.value, status: entryStatus === "suggested" ? "partial" : entryStatus })}
                        aria-label={`Khẩu phần gram ${item.name}`}
                      />
                      <span className="rounded-2xl bg-white px-3 py-2 text-center text-sm font900 text-slate-700 ring-1 ring-slate-100">
                        {round(scaleItemByPortion(item, entry).calories)} kcal
                      </span>
                    </div>
                  );
                })}
                {meal.manualItems.map((item) => (
                  <div key={item.id} className="rounded-2xl bg-emerald-50 p-3 text-sm font800 text-emerald-900 ring-1 ring-emerald-100">
                    Đã thêm thủ công: <strong>{item.name}</strong> · {item.calories} kcal
                  </div>
                ))}
              </div>

              <textarea
                className="mt-4 min-h-20 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font800 text-slate-800 outline-none focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
                placeholder={`Ghi chú ${meal.title.toLowerCase()}`}
                value={entries[`${meal.title}-note`]?.note || ""}
                onChange={(event) => updateEntry(`${meal.title}-note`, { note: event.target.value })}
              />
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function MealsPage({
  summary,
  meals,
  validation,
  profileSettings,
  favoriteMeals,
  ratings,
  onFavorite,
  onRate,
  onRegenerate,
  onOpenDislikeFood,
  isSubmitting,
}) {
  const [detailFood, setDetailFood] = useState(null);
  const expectedCount = expectedItemsPerMeal(profileSettings?.meal_complexity);

  return (
    <div className="space-y-5">
      {summary.medicalWarning ? (
        <section className="rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm font800 leading-6 text-amber-900">
          {summary.medicalWarning}
        </section>
      ) : null}
      <section className="glass-panel p-5 sm:p-6">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">Kế hoạch bữa ăn</p>
            <h2 className="mt-2 text-2xl font-black text-slate-950">Thực đơn tăng cân lành mạnh hôm nay</h2>
            <p className="mt-2 text-sm font700 text-slate-500">
              Mỗi bữa ưu tiên cân bằng tinh bột, đạm, rau/trái cây và món phụ tăng năng lượng khi đủ số món.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="h-11 rounded-2xl bg-slate-950 px-4 text-sm font900 text-white disabled:cursor-not-allowed disabled:opacity-60"
              onClick={onRegenerate}
              disabled={isSubmitting}
            >
              {isSubmitting ? "Đang tạo..." : "Tạo lại thực đơn"}
            </button>
            <span className="rounded-2xl bg-emerald-50 px-4 py-2 text-sm font900 text-emerald-800">
              {validation.totalCalories.toLocaleString("vi-VN")} kcal
            </span>
          </div>
        </div>
      </section>

      <div className="space-y-5">
        {meals.map((meal) => {
          const totals = sumItems(meal.items);
          const balance = analyzeMealBalance(meal.items, expectedCount);
          return (
            <section key={meal.title} className="glass-panel overflow-hidden p-0">
              <div className="flex flex-col gap-3 border-b border-slate-100 bg-white/75 p-5 lg:flex-row lg:items-start lg:justify-between">
                <div className="flex items-start gap-3">
                  <span className={`mt-1 h-12 w-2 rounded-full ${accentClass(meal.accent)}`} />
                  <div>
                    <h3 className="text-xl font-black text-slate-950">{meal.title}</h3>
                    <p className="mt-1 text-sm font800 text-slate-500">
                      {meal.items.length}/{expectedCount} món · {totals.calories} kcal · P {totals.protein}g · F {totals.fat}g · C {totals.carbs}g
                    </p>
                    <MealBalanceChips balance={balance} />
                  </div>
                </div>
                {balance.warnings.length ? (
                  <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font800 leading-6 text-amber-900">
                    {balance.warnings.join(" ")}
                  </div>
                ) : (
                  <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font900 text-emerald-900">
                    Bữa ăn cân bằng nhóm món.
                  </div>
                )}
              </div>

              <div className="grid gap-4 p-4 sm:p-5 lg:grid-cols-2 2xl:grid-cols-3">
                {meal.items.map((item) => (
                  <article key={item.id} className="overflow-hidden rounded-3xl border border-white bg-white shadow-xl shadow-slate-900/7">
                    <div className="relative aspect-[16/10] overflow-hidden bg-emerald-50">
                      <img
                        src={item.image}
                        alt={item.imageAlt || item.name}
                        className="h-full w-full object-cover"
                        onError={(event) => {
                          const image = event.currentTarget;
                          if (image.dataset.usedFallback === "true") return;
                          image.dataset.usedFallback = "true";
                          image.src = item.fallbackImage || defaultFoodImage;
                        }}
                      />
                      {item.imageBadge ? (
                        <span className="absolute left-4 top-4 rounded-full bg-amber-50 px-3 py-1.5 text-xs font900 text-amber-800 ring-1 ring-amber-100">
                          {item.imageBadge}
                        </span>
                      ) : null}
                      <span className="absolute bottom-4 right-4 rounded-2xl bg-accent px-3 py-2 text-sm font-black text-white">
                        {item.calories} kcal
                      </span>
                    </div>
                    <div className="space-y-4 p-4">
                      <div>
                        <h4 className="text-lg font-black leading-snug text-slate-950">{item.name}</h4>
                        <p className="mt-1 text-sm font800 text-slate-600">{item.foodGroup || item.category}</p>
                        <p className="mt-1 text-sm font700 text-slate-500">{item.servingDisplay || `${item.servingGrams}g`}</p>
                      </div>
                      <p className="rounded-2xl bg-emerald-50 p-3 text-sm font800 leading-6 text-emerald-900">
                        {item.reason || buildSuggestionReason(item)}
                      </p>
                      <div className="grid grid-cols-3 gap-2 text-center text-xs font900">
                        <span className="rounded-xl bg-sky-50 px-2 py-2 text-sky-700">P {item.protein}g</span>
                        <span className="rounded-xl bg-orange-50 px-2 py-2 text-orange-700">F {item.fat}g</span>
                        <span className="rounded-xl bg-emerald-50 px-2 py-2 text-emerald-700">C {item.carbs}g</span>
                      </div>
                      <div className="grid gap-2 sm:grid-cols-2">
                        <button type="button" className="h-10 rounded-2xl bg-slate-100 px-3 text-sm font900 text-slate-700" onClick={() => setDetailFood(item)}>
                          Xem chi tiết
                        </button>
                        <button type="button" className="h-10 rounded-2xl bg-emerald-50 px-3 text-sm font900 text-emerald-800 disabled:cursor-not-allowed disabled:opacity-60" onClick={onRegenerate} disabled={isSubmitting}>
                          Đổi món
                        </button>
                        <button type="button" className={`h-10 rounded-2xl px-3 text-sm font900 ${favoriteMeals.has(item.id) ? "bg-rose-50 text-rose-600" : "bg-slate-100 text-slate-700"}`} onClick={() => onFavorite(item.id)}>
                          Yêu thích
                        </button>
                        <button type="button" className={`h-10 rounded-2xl px-3 text-sm font900 ${isFoodDisliked(item, profileSettings) ? "bg-orange-50 text-orange-700" : "bg-slate-100 text-slate-700"}`} onClick={() => onOpenDislikeFood(item)}>
                          Không thích
                        </button>
                      </div>
                      <label className="flex h-10 items-center justify-center gap-2 rounded-2xl bg-white px-3 text-sm font900 text-slate-700 ring-1 ring-slate-100">
                        Đánh giá
                        <select
                          className="bg-transparent text-sm font900 outline-none"
                          value={ratings[item.id] || ""}
                          onChange={(event) => onRate(item.id, Number(event.target.value))}
                          aria-label={`Đánh giá ${item.name}`}
                        >
                          <option value="">--</option>
                          <option value="5">5</option>
                          <option value="4">4</option>
                          <option value="3">3</option>
                        </select>
                      </label>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          );
        })}
      </div>
      <FoodDetailModal food={detailFood} onClose={() => setDetailFood(null)} />
    </div>
  );
}

function FoodsPage({ foods, meals, profileSettings, onOpenAddToMeal, onOpenDislikeFood }) {
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState("all");
  const [kcalRange, setKcalRange] = useState("all");
  const [mealFilter, setMealFilter] = useState("all");
  const [validity, setValidity] = useState("eligible");
  const [detailFood, setDetailFood] = useState(null);
  
  const groups = uniqueValues(foods.map((item) => item.foodGroup || item.category).filter(Boolean));
  const mealTitles = uniqueValues(meals.map((meal) => meal.title));
  
  const filteredFoods = foods.filter((item) => {
    const text = stripAccents(`${item.name} ${item.foodGroup} ${item.category}`).toLowerCase();
    const matchesQuery = !query.trim() || text.includes(stripAccents(query).toLowerCase().trim());
    const matchesGroup = group === "all" || (item.foodGroup || item.category) === group;
    const matchesMeal = mealFilter === "all" || item.mealTitle === mealFilter || item.mealTitles?.includes(mealFilter);
    const matchesValidity = validity === "all" || (validity === "eligible" ? item.menuEligible !== false : item.qualityFlags);
    
    const calories = Number(item.calories || 0);
    const matchesKcal =
      kcalRange === "all" ||
      (kcalRange === "low" && calories < 250) ||
      (kcalRange === "medium" && calories >= 250 && calories <= 450) ||
      (kcalRange === "high" && calories > 450);
      
    // Force showing only eligible foods as a baseline if not explicitly filtered for flagged foods.
    const isBaselineEligible = item.menuEligible !== false;
    
    return matchesQuery && matchesGroup && matchesMeal && matchesValidity && matchesKcal && (validity !== "all" || isBaselineEligible);
  });
  
  const categoryCounts = filteredFoods.reduce((acc, item) => {
    const category = item.foodGroup || item.category || "Khác";
    acc[category] = (acc[category] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {/* 1. Header trang */}
      <section className="glass-panel p-6 shadow-sm border border-slate-200/60 rounded-3xl">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="inline-flex items-center gap-2 mb-2">
              <span className="flex h-6 flex-shrink-0 items-center justify-center rounded-md bg-orange-100 px-2.5 text-[11px] font-bold uppercase tracking-wider text-orange-800">
                THƯ VIỆN
              </span>
            </div>
            <h2 className="text-3xl font-black text-slate-900 tracking-tight hidden">Thư viện món ăn</h2>
            <p className="mt-1.5 text-sm font-semibold text-slate-500 max-w-2xl leading-relaxed">
              Khám phá món ăn phù hợp với hồ sơ dinh dưỡng và mục tiêu tăng cân của bạn.
            </p>
          </div>
          <div className="flex align-bottom">
            <span className="inline-flex items-center justify-center h-10 px-5 rounded-xl bg-emerald-50 text-sm font-bold text-emerald-700 ring-1 ring-emerald-200">
              {filteredFoods.length} món phù hợp
            </span>
          </div>
        </div>

        <div className="mt-8 flex flex-wrap gap-2">
          {Object.entries(categoryCounts).map(([category, count]) => (
            <span key={category} className="rounded-full bg-white px-3 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-200 shadow-sm border border-slate-50">
              {category}: {count}
            </span>
          ))}
        </div>
      </section>

      <section className="bg-white rounded-3xl shadow-sm border border-slate-200 p-3 sm:p-5">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5 items-end">
          <div className="lg:col-span-2">
            <label className="block text-[11px] font-extrabold uppercase tracking-widest text-slate-400 mb-2">Tìm món ăn</label>
            <div className="relative">
              <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 pl-11 pr-4 text-sm font-bold outline-none focus:bg-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
                placeholder="Gõ tên món..."
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
            </div>
          </div>
          <FilterSelectX label="Nhóm món" value={group} onChange={setGroup} options={[["all", "Tất cả nhóm"], ...groups.map((item) => [item, item])]} />
          <FilterSelectX
            label="Mức kcal"
            value={kcalRange}
            onChange={setKcalRange}
            options={[
              ["all", "Tất cả kcal"],
              ["low", "< 250 kcal"],
              ["medium", "250-450 kcal"],
              ["high", "> 450 kcal"],
            ]}
          />
          <FilterSelectX
            label="Phù hợp thực đơn"
            value={validity}
            onChange={setValidity}
            options={[
              ["eligible", "Đang khuyên dùng"],
              ["all", "Tất cả thư viện"],
            ]}
          />
        </div>
      </section>

      <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {filteredFoods.map((item) => (
          <FoodLibraryCard
            key={`${item.mealTitle || "catalog"}-${item.id}`}
            item={item}
            disliked={isFoodDisliked(item, profileSettings)}
            onDetail={() => setDetailFood(item)}
            onAdd={() => onOpenAddToMeal(item)}
            onDislike={() => onOpenDislikeFood(item)}
          />
        ))}
      </section>
      
      {!filteredFoods.length ? (
        <EmptyChartState 
          title="Không tìm thấy món ăn phù hợp" 
          desc="Thử điều chỉnh lại bộ lọc hoặc từ khóa tìm kiếm để khám phá nhiều món ăn ngon hơn." 
          actionLabel="Xóa các bộ lọc"
          onAction={() => {
            setQuery("");
            setGroup("all");
            setKcalRange("all");
            setValidity("eligible");
          }}
        />
      ) : null}
      
      <FoodDetailModal food={detailFood} onClose={() => setDetailFood(null)} />
    </div>
  );
}

function FilterSelectX({ label, value, onChange, options }) {
  return (
    <div>
      <label className="block text-[11px] font-extrabold uppercase tracking-widest text-slate-400 mb-2">{label}</label>
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="h-11 w-full appearance-none rounded-xl border border-slate-200 bg-slate-50 px-4 pr-10 text-sm font-bold text-slate-700 outline-none focus:bg-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
        >
          {options.map(([val, label]) => (
            <option key={val} value={val}>{label}</option>
          ))}
        </select>
        <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </div>
  );
}

function FoodLibraryCard({ item, disliked, onDetail, onAdd, onDislike }) {
  return (
    <article className="rounded-3xl bg-white p-5 shadow-sm border border-slate-200 hover:shadow-md transition-all flex flex-col justify-between">
      <div className="flex gap-4">
        <div className="h-28 w-28 shrink-0 overflow-hidden rounded-2xl bg-slate-100 shadow-inner">
          <img
            src={item.image}
            alt={item.imageAlt || item.name}
            className="h-full w-full object-cover"
            onError={(event) => {
              const image = event.currentTarget;
              if (image.dataset.usedFallback === "true") return;
              image.dataset.usedFallback = "true";
              image.src = item.fallbackImage || defaultFoodImage;
            }}
          />
        </div>
        <div className="min-w-0 flex flex-col justify-center">
          <div className="inline-flex mb-1.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-100">
              {item.mealTitle || "Đề xuất"}
            </span>
          </div>
          <h3 className="truncate text-base font-black text-slate-900">{item.name}</h3>
          <p className="mt-0.5 truncate text-sm font-semibold text-slate-500">{item.foodGroup || item.category || "Chưa phân loại"}</p>
          <div className="mt-2 text-[13px] font-bold text-slate-700 bg-slate-50 w-fit px-2 py-1 rounded truncate max-w-full inline-flex items-center gap-1.5">
            <span className="text-orange-500">🔥 {item.calories} kcal</span>
            <span className="text-slate-300">|</span>
            <span className="truncate">{item.servingDisplay ? `${item.servingDisplay}` : item.servingGrams ? `~${item.servingGrams}g` : "1 phần"}</span>
          </div>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-3 gap-2 text-center text-xs font-bold">
        <div className="rounded-xl bg-sky-50/50 border border-sky-100 py-2.5 flex flex-col">
          <span className="text-slate-400 text-[10px] uppercase mb-0.5">Protein</span>
          <span className="text-sky-700">{item.protein}g</span>
        </div>
        <div className="rounded-xl bg-orange-50/50 border border-orange-100 py-2.5 flex flex-col">
          <span className="text-slate-400 text-[10px] uppercase mb-0.5">Fat</span>
          <span className="text-orange-700">{item.fat}g</span>
        </div>
        <div className="rounded-xl bg-emerald-50/50 border border-emerald-100 py-2.5 flex flex-col">
          <span className="text-slate-400 text-[10px] uppercase mb-0.5">Carbs</span>
          <span className="text-emerald-700">{item.carbs}g</span>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-[1fr_1fr_40px] gap-2">
        <button type="button" className="h-10 rounded-xl bg-slate-50 text-slate-600 text-sm font-bold hover:bg-slate-100 transition-all border border-slate-200" onClick={onDetail}>
          Chi tiết
        </button>
        <button type="button" className="h-10 rounded-xl bg-emerald-600 text-white text-sm font-bold hover:bg-emerald-700 transition-all shadow-sm" onClick={onAdd}>
          Nhật ký
        </button>
        <button 
          title={disliked ? "Đã nằm trong danh sách Không thích" : "Đánh dấu Không thích món này"}
          type="button" 
          className={`h-10 w-10 flex items-center justify-center rounded-xl text-lg transition-all border ${disliked ? "bg-orange-50 text-orange-600 border-orange-200" : "bg-white text-slate-300 hover:text-orange-500 border-slate-200 hover:bg-slate-50"}`} 
          onClick={onDislike}
        >
          <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            {disliked ? (
              <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.84 3h.32A2 2 0 0111 4.79v3.053l2.844-.949A2 2 0 0116.5 8.718V11m-6 3v5a2 2 0 002 2h3.454a2 2 0 001.96-1.558l.75-3.75A2 2 0 0017.703 14H10z" />
            )}
          </svg>
        </button>
      </div>
    </article>
  );
}

function ChartsPage({ weeklyCalories, macroData, summary, meals, validation }) {
  const [activeTab, setActiveTab] = useState("calories");
  const [range, setRange] = useState("7");
  const visibleCalories = weeklyCalories.slice(-Number(range));
  const groupCounts = buildFoodGroupCounts(meals);
  const compliance = buildComplianceRows(validation);
  const hasHistory = visibleCalories.length > 1;
  const tabs = [
    { id: "calories", label: "Calories", icon: "🔥" },
    { id: "macro", label: "Macro", icon: "🥑" },
    { id: "weight", label: "Cân nặng", icon: "⚖️" },
    { id: "compliance", label: "Tuân thủ thực đơn", icon: "✅" },
    { id: "groups", label: "Nhóm thực phẩm", icon: "🥗" },
  ];

  const avgCalories = visibleCalories.length
    ? Math.round(visibleCalories.reduce((sum, item) => sum + item.calories, 0) / visibleCalories.length)
    : summary.eatenCalories || 0;
    
  const compliancePercent = summary.targetCalories ? Math.min(100, Math.round((summary.eatenCalories / summary.targetCalories) * 100)) : 0;

  return (
    <div className="space-y-6">
      {/* 1. Header trang */}
      <section className="glass-panel p-6 shadow-sm border border-slate-200/60 rounded-3xl">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="inline-flex items-center gap-2 mb-2">
              <span className="flex h-6 items-center rounded-md bg-emerald-100 px-2.5 text-[11px] font-bold uppercase tracking-wider text-emerald-800">
                NutriGain Dashboard
              </span>
            </div>
            <h2 className="text-3xl font-black text-slate-900 tracking-tight">Biểu đồ dinh dưỡng</h2>
            <p className="mt-1.5 text-sm font-semibold text-slate-500">
              Theo dõi xu hướng calories, macro, cân nặng và mức tuân thủ thực đơn.
            </p>
          </div>
          
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex bg-slate-100/80 p-1 rounded-xl border border-slate-200">
              {["7", "14", "30"].map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`h-9 px-4 text-sm font-bold rounded-lg transition-all ${
                    range === item 
                      ? "bg-white text-emerald-600 shadow-sm ring-1 ring-black/5" 
                      : "text-slate-500 hover:text-slate-900 hover:bg-slate-200/50"
                  }`}
                  onClick={() => setRange(item)}
                >
                  {item} ngày
                </button>
              ))}
            </div>
            <button className="h-11 px-5 rounded-xl bg-white border border-slate-200 text-sm font-bold text-slate-700 shadow-sm hover:bg-slate-50 hover:border-slate-300 transition-all flex items-center gap-2">
              <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} className="text-slate-400">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
              Chỉnh hồ sơ
            </button>
            <button className="h-11 px-5 rounded-xl bg-emerald-600 text-sm font-bold text-white shadow-sm hover:bg-emerald-700 transition-all flex items-center gap-2">
              <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Xuất báo cáo
            </button>
          </div>
        </div>
      </section>

      {/* 2. KPI Cards */}
      <section className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
        {[
          { label: "Calories Kì Vọng/Ngày", value: `${avgCalories} kcal`, desc: "Mức trung bình", icon: "🔥", color: "text-orange-500", bg: "bg-orange-50" },
          { label: "Protein Mục Tiêu", value: `${macroData.protein}g`, desc: "Hôm nay", icon: "🥩", color: "text-rose-500", bg: "bg-rose-50" },
          { label: "Mức Tuân Thủ", value: `${compliancePercent}%`, desc: "Mục tiêu calo", icon: "🎯", color: "text-emerald-500", bg: "bg-emerald-50" },
          { label: "Ngày Ghi Nhận", value: `${weeklyCalories.length}`, desc: "Tổng cộng", icon: "📅", color: "text-blue-500", bg: "bg-blue-50" },
          { label: "Xu Hướng", value: summary.bmiStatus || "N/A", desc: "Dựa trên BMI", icon: "📈", color: "text-indigo-500", bg: "bg-indigo-50" }
        ].map((kpi, idx) => (
          <div key={idx} className="bg-white rounded-3xl p-5 shadow-sm border border-slate-200 flex flex-col justify-between">
            <div className="flex justify-between items-start mb-4">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center text-lg ${kpi.bg}`}>
                {kpi.icon}
              </div>
            </div>
            <div>
              <p className="text-xs font-extrabold text-slate-500 uppercase tracking-widest">{kpi.label}</p>
              <h3 className="text-2xl font-black text-slate-900 mt-1">{kpi.value}</h3>
              <p className="text-xs font-semibold text-slate-400 mt-2">{kpi.desc}</p>
            </div>
          </div>
        ))}
      </section>

      {/* 3. Tabs */}
      <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-none snap-x">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`shrink-0 snap-start flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-bold transition-all shadow-sm ${
              activeTab === tab.id 
                ? "bg-emerald-600 text-white border border-emerald-600" 
                : "bg-white text-slate-600 border border-slate-200 hover:border-slate-300 hover:text-slate-900"
            }`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* 4 & 5. Main Chart Card & Empty State */}
      <div className="bg-white rounded-[24px] shadow-sm border border-slate-200 relative overflow-hidden">
        {activeTab === "calories" ? (
          hasHistory ? (
            <div className="p-6">
              <div className="mb-6">
                <h3 className="text-lg font-black text-slate-900">Biểu đồ Calories</h3>
                <p className="text-sm font-medium text-slate-500 mt-1">Xu hướng nạp năng lượng trong khoảng {range} ngày gần đây.</p>
              </div>
              <CaloriesChart data={visibleCalories} />
            </div>
          ) : (
            <EmptyChartState 
              title="Chưa đủ dữ liệu lịch sử Calories" 
              desc="Hệ thống cần ít nhất 2 ngày ghi nhận để vẽ xu hướng. Bạn hãy tạo lịch sử bằng cách sử dụng ứng dụng mỗi ngày."
              actionLabel="Ghi nhận ngay"
            />
          )
        ) : null}

        {activeTab === "macro" ? (
          <div className="grid gap-6 lg:grid-cols-[minmax(0,0.7fr)_minmax(320px,0.3fr)] p-6">
            <div className="flex flex-col">
              <div className="mb-6">
                <h3 className="text-lg font-black text-slate-900">Tỷ lệ Macronutrients</h3>
                <p className="text-sm font-medium text-slate-500 mt-1">Phân bổ Protein, Fat, Carbs trong bữa ăn hôm nay.</p>
              </div>
              <div className="flex-1 flex justify-center items-center min-h-[300px]">
                <MacroChart data={macroData} />
              </div>
            </div>
            <div className="bg-slate-50 rounded-2xl p-6 border border-slate-100 flex flex-col justify-center">
              <div className="inline-flex mb-4">
                <span className="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2 py-1 uppercase rounded-md tracking-wider">AI Insight</span>
              </div>
              <h3 className="text-lg font-black text-slate-900">Phân tích nhanh</h3>
              <p className="mt-3 text-sm font-semibold leading-relaxed text-slate-600 border-b border-slate-200 pb-5">{buildMacroComment(macroData)}</p>
              <div className="mt-5 grid gap-4">
                <InfoRow label="🥩 Protein" value={`${macroData.protein}g`} />
                <InfoRow label="🥑 Fat" value={`${macroData.fat}g`} />
                <InfoRow label="🍚 Carbs" value={`${macroData.carbs}g`} />
              </div>
            </div>
          </div>
        ) : null}

        {activeTab === "weight" ? (
          <EmptyChartState 
            title="Chưa có lịch sử Cân Nặng" 
            desc={`Chỉ số BMI hiện tại của bạn là ${summary.bmi}. Cập nhật cân nặng định kỳ ở trang Tài khoản để ứng dụng theo dõi tiến trình tăng/giảm cân của bạn.`}
            actionLabel="Cập nhật hồ sơ"
          />
        ) : null}

        {activeTab === "compliance" ? (
          <div className="p-6">
            <div className="mb-6 border-b border-slate-100 pb-5">
              <h3 className="text-lg font-black text-slate-900">Chi tiết mức tuân thủ</h3>
              <p className="text-sm font-medium text-slate-500 mt-1">So sánh thực tế đạt được so với mục tiêu đề ra.</p>
            </div>
            <div className="grid gap-5 md:grid-cols-3">
              {compliance.map((item) => (
                <ProgressMetric key={item.label} label={item.label} value={item.value} target={item.target} unit={item.unit} />
              ))}
            </div>
          </div>
        ) : null}

        {activeTab === "groups" ? (
          <div className="p-6">
            <div className="mb-6">
              <h3 className="text-lg font-black text-slate-900">Tần suất nhóm món ăn</h3>
              <p className="text-sm font-medium text-slate-500 mt-1">Sự đa dạng của các nhóm thực phẩm trong thực đơn hiện tại.</p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              {groupCounts.map((item) => (
                <div key={item.label} className="rounded-2xl border border-slate-200 bg-slate-50/50 p-5 hover:shadow-sm transition-all hover:bg-white">
                  <div className="flex items-center justify-between gap-3 mb-4">
                    <strong className="text-sm font-extrabold text-slate-800">{item.label}</strong>
                    <span className="text-xs font-bold text-emerald-700 bg-emerald-100 px-2 py-1 rounded-md">{item.count} món</span>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-full bg-slate-200">
                    <div className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-emerald-600 transition-all duration-1000" style={{ width: `${item.percent}%` }} />
                  </div>
                  <p className="text-[11px] font-bold text-slate-400 text-right mt-2 uppercase">{item.percent}% tổng số</p>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </div>

      {/* 6. Khu vực biểu đồ BMR & TDEE */}
      <EnergyChart bmr={summary.bmr} tdee={summary.tdee} />
    </div>
  );
}

function EmptyChartState({ title, desc, actionLabel }) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center py-20">
      <div className="w-20 h-20 bg-slate-50 border border-slate-100 rounded-full flex items-center justify-center mb-6 shadow-sm">
        <svg width="32" height="32" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} className="text-slate-300">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 13h2.667c.7 0 1.349.447 1.583 1.107l1.056 2.955a1.678 1.678 0 003.165 0l2.056-5.748a1.678 1.678 0 013.165 0l1.056 2.955c.234.66.883 1.107 1.583 1.107H21" />
        </svg>
      </div>
      <h3 className="text-xl font-black text-slate-800 mb-2">{title}</h3>
      <p className="max-w-md text-sm font-semibold text-slate-500 leading-relaxed mb-8">{desc}</p>
      <button className="h-10 px-5 rounded-xl bg-emerald-50 text-sm font-bold text-emerald-700 hover:bg-emerald-100 transition-all">
        {actionLabel}
      </button>
    </div>
  );
}

function EligibilityCard({ eligibility }) {
  const tone = eligibility.eligible ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-amber-200 bg-amber-50 text-amber-900";
  return (
    <section className={`rounded-3xl border p-5 ${tone}`}>
      <p className="text-xs font900 uppercase tracking-[0.18em] opacity-80">Trạng thái đủ điều kiện</p>
      <div className="mt-3 flex flex-wrap items-end gap-3">
        <h3 className="text-4xl font-black">{eligibility.bmi ?? "N/A"}</h3>
        <span className="pb-1 text-sm font900">{eligibility.statusLabel}</span>
      </div>
      <p className="mt-3 text-sm font800 leading-6">{eligibility.reason}</p>
    </section>
  );
}

function ProgressCard({ profile }) {
  const hasTarget = Number.isFinite(profile.targetWeight) && profile.targetWeight > 0;
  const percent = hasTarget ? Math.min(100, Math.round((profile.weight / profile.targetWeight) * 100)) : null;
  return (
    <section className="glass-panel p-5">
      <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">Tiến độ tăng cân</p>
      <h3 className="mt-2 text-xl font-black text-slate-950">
        {hasTarget ? `${profile.weight}kg / ${profile.targetWeight}kg` : "Chưa đặt cân nặng mục tiêu"}
      </h3>
      {hasTarget ? (
        <>
          <div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-emerald-500" style={{ width: `${percent}%` }} />
          </div>
          <p className="mt-3 text-sm font800 text-slate-500">Đạt {percent}% so với cân nặng mục tiêu đã nhập.</p>
        </>
      ) : (
        <p className="mt-3 text-sm font800 leading-6 text-slate-500">
          Có thể cập nhật mục tiêu ở trang Tài khoản để theo dõi tiến độ rõ hơn.
        </p>
      )}
    </section>
  );
}

function ActionSuggestionCard({ remainingCalories, actionFood, validation }) {
  const suggestion = actionFood
    ? `Nên thêm hoặc ưu tiên ${actionFood.name} (${actionFood.calories} kcal, ${actionFood.servingDisplay || `${actionFood.servingGrams}g`}).`
    : "Không đủ dữ liệu món phụ từ backend để gợi ý món cụ thể.";
  return (
    <section className="glass-panel p-5">
      <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">Hành động hôm nay</p>
      <h3 className="mt-2 text-xl font-black text-slate-950">
        {remainingCalories > 0 ? `Còn thiếu ${remainingCalories.toLocaleString("vi-VN")} kcal` : "Đã đạt mốc kcal gợi ý"}
      </h3>
      <p className="mt-3 text-sm font800 leading-6 text-slate-600">{remainingCalories > 0 ? suggestion : validation.messages?.[0]}</p>
    </section>
  );
}

function MiniTrendCard({ data, metricLabel }) {
  const maxValue = Math.max(...data.map((item) => Number(item.calories || 0)), 1);
  const hasHistory = data.length > 1;
  return (
    <section className="glass-panel p-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">Mini chart</p>
          <h3 className="mt-2 text-xl font-black text-slate-950">Xu hướng {metricLabel}</h3>
        </div>
        {!hasHistory ? <span className="rounded-full bg-amber-50 px-3 py-1.5 text-xs font900 text-amber-800">Thiếu lịch sử</span> : null}
      </div>
      <div className="mt-5 flex h-28 items-end gap-2">
        {data.map((item) => (
          <div key={item.day} className="flex flex-1 flex-col items-center gap-2">
            <div className="w-full rounded-t-xl bg-emerald-500" style={{ height: `${Math.max((Number(item.calories || 0) / maxValue) * 100, 8)}%` }} />
            <span className="text-xs font900 text-slate-500">{item.day}</span>
          </div>
        ))}
      </div>
      {!hasHistory ? <p className="mt-3 text-sm font800 text-slate-500">Chỉ có dữ liệu hôm nay, chưa vẽ đủ 7 ngày.</p> : null}
    </section>
  );
}

function WarningCard({ text }) {
  return (
    <article className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font800 leading-6 text-amber-900">
      {text}
    </article>
  );
}

function EmptyState({ title, text }) {
  return (
    <section className="glass-panel p-6 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-xl font-black text-emerald-700">i</div>
      <h3 className="mt-4 text-xl font-black text-slate-950">{title}</h3>
      <p className="mx-auto mt-2 max-w-2xl text-sm font800 leading-6 text-slate-500">{text}</p>
    </section>
  );
}

function InfoTile({ label, value }) {
  return (
    <div className="rounded-2xl bg-white/85 p-4 ring-1 ring-slate-100">
      <p className="text-xs font900 uppercase tracking-[0.1em] text-slate-500">{label}</p>
      <p className="mt-2 text-lg font-black text-slate-950">{value}</p>
    </div>
  );
}

function FilterBar({ children }) {
  return (
    <section className="glass-panel flex flex-col gap-3 p-4 lg:flex-row lg:items-center">
      {children}
    </section>
  );
}

function FilterSelect({ label, value, options, onChange }) {
  return (
    <label className="min-w-[150px] text-xs font900 uppercase tracking-[0.08em] text-slate-500">
      {label}
      <select
        className="mt-1 h-11 w-full rounded-2xl border border-slate-200 bg-white px-3 text-sm font800 normal-case tracking-normal text-slate-800 outline-none focus:border-emerald-500"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>{optionLabel}</option>
        ))}
      </select>
    </label>
  );
}

function FoodCard({ item, disliked, onDetail, onAdd, onDislike }) {
  return (
    <article className="rounded-2xl bg-white p-3 shadow-lg shadow-slate-900/5 ring-1 ring-slate-100">
      <div className="grid grid-cols-[92px_minmax(0,1fr)] gap-3">
        <img
          src={item.image}
          alt={item.imageAlt || item.name}
          className="h-24 w-full rounded-2xl object-cover"
          onError={(event) => {
            const image = event.currentTarget;
            if (image.dataset.usedFallback === "true") return;
            image.dataset.usedFallback = "true";
            image.src = item.fallbackImage || defaultFoodImage;
          }}
        />
        <div className="min-w-0">
          <p className="text-xs font900 uppercase tracking-[0.12em] text-emerald-700">{item.mealTitle || "Kho món"}</p>
          <h3 className="mt-1 truncate text-base font-black text-slate-950">{item.name}</h3>
          <p className="mt-1 text-sm font800 leading-5 text-slate-600">{item.foodGroup || item.category}</p>
          <p className="mt-1 text-sm font800 text-slate-500">
            {item.calories} kcal{item.servingDisplay ? ` · ${item.servingDisplay}` : item.servingGrams ? ` · ~${item.servingGrams}g` : ""}
          </p>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs font900 text-slate-600">
        <span className="rounded-xl bg-sky-50 px-2 py-2 text-sky-700">P {item.protein}g</span>
        <span className="rounded-xl bg-orange-50 px-2 py-2 text-orange-700">F {item.fat}g</span>
        <span className="rounded-xl bg-emerald-50 px-2 py-2 text-emerald-700">C {item.carbs}g</span>
      </div>

      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        <button type="button" className="h-10 rounded-2xl bg-slate-100 px-3 text-sm font900 text-slate-700" onClick={onDetail}>Chi tiết</button>
        <button type="button" className="h-10 rounded-2xl bg-emerald-50 px-3 text-sm font900 text-emerald-800" onClick={onAdd}>Thêm vào bữa</button>
        <button type="button" className={`h-10 rounded-2xl px-3 text-sm font900 ${disliked ? "bg-orange-50 text-orange-700" : "bg-slate-100 text-slate-700"}`} onClick={onDislike}>
          Không thích
        </button>
      </div>
    </article>
  );
}

function AddToMealModal({ request, meals, expectedCount, onAdd, onClose }) {
  if (!request?.food) return null;
  const mealOptions = ["breakfast", "lunch", "dinner"];
  const selectedMeal = request.mealKey
    ? meals.find((meal) => meal.title === mealLabels[request.mealKey])
    : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-sm" role="dialog" aria-modal="true">
      <article className="w-full max-w-xl rounded-3xl bg-white p-5 shadow-2xl shadow-slate-950/20">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">Thêm vào bữa</p>
            <h3 className="mt-2 text-xl font-black text-slate-950">{request.food.name}</h3>
          </div>
          <button type="button" className="h-10 rounded-2xl bg-slate-100 px-4 text-sm font900 text-slate-700" onClick={onClose}>
            Đóng
          </button>
        </div>

        {!request.mealKey ? (
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            {mealOptions.map((mealKey) => (
              <button
                key={mealKey}
                type="button"
                className="rounded-2xl bg-emerald-50 px-4 py-4 text-sm font900 text-emerald-900 ring-1 ring-emerald-100"
                onClick={() => onAdd(request.food, mealKey)}
              >
                {mealLabels[mealKey]}
              </button>
            ))}
          </div>
        ) : (
          <div className="mt-5 space-y-4">
            <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font800 leading-6 text-amber-900">
              {mealLabels[request.mealKey]} đã đủ {expectedCount} món. Chọn món muốn thay hoặc thêm ngoài kế hoạch.
            </div>
            <div className="grid gap-2">
              {(selectedMeal?.items || []).map((item, index) => (
                <button
                  key={`${item.id}-${index}`}
                  type="button"
                  className="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3 text-left text-sm font900 text-slate-800 ring-1 ring-slate-100"
                  onClick={() => onAdd(request.food, request.mealKey, { replaceIndex: index })}
                >
                  <span className="min-w-0 truncate">{item.name}</span>
                  <span className="shrink-0 text-emerald-700">Thay</span>
                </button>
              ))}
            </div>
            <button
              type="button"
              className="h-11 w-full rounded-2xl bg-slate-950 px-4 text-sm font900 text-white"
              onClick={() => onAdd(request.food, request.mealKey, { allowExtra: true })}
            >
              Thêm ngoài kế hoạch
            </button>
          </div>
        )}
      </article>
    </div>
  );
}

function DislikeFoodModal({ food, onDislike, onClose }) {
  if (!food) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-sm" role="dialog" aria-modal="true">
      <article className="w-full max-w-md rounded-3xl bg-white p-5 shadow-2xl shadow-slate-950/20">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font900 uppercase tracking-[0.18em] text-orange-700">Không thích</p>
            <h3 className="mt-2 text-xl font-black text-slate-950">{food.name}</h3>
          </div>
          <button type="button" className="h-10 rounded-2xl bg-slate-100 px-4 text-sm font900 text-slate-700" onClick={onClose}>
            Đóng
          </button>
        </div>
        <div className="mt-5 grid gap-3">
          <button
            type="button"
            className="rounded-2xl bg-orange-50 px-4 py-4 text-left text-sm font900 text-orange-800 ring-1 ring-orange-100"
            onClick={() => onDislike(food, "food")}
          >
            Không thích món này
          </button>
          <button
            type="button"
            className="rounded-2xl bg-slate-50 px-4 py-4 text-left text-sm font900 text-slate-800 ring-1 ring-slate-100"
            onClick={() => onDislike(food, "group")}
          >
            Không thích nhóm món tương tự
          </button>
        </div>
      </article>
    </div>
  );
}

function FoodDetailModal({ food, onClose }) {
  if (!food) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-sm" role="dialog" aria-modal="true">
      <article className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-3xl bg-white shadow-2xl shadow-slate-950/20">
        <div className="relative aspect-[16/8] bg-emerald-50">
          <img
            src={food.image}
            alt={food.imageAlt || food.name}
            className="h-full w-full rounded-t-3xl object-cover"
            onError={(event) => {
              const image = event.currentTarget;
              if (image.dataset.usedFallback === "true") return;
              image.dataset.usedFallback = "true";
              image.src = food.fallbackImage || defaultFoodImage;
            }}
          />
          {food.imageBadge ? (
            <span className="absolute left-4 top-4 rounded-full bg-amber-50 px-3 py-1.5 text-xs font900 text-amber-800 ring-1 ring-amber-100">
              {food.imageBadge}
            </span>
          ) : null}
          <button type="button" className="absolute right-4 top-4 h-10 rounded-2xl bg-white/95 px-4 text-sm font900 text-slate-900" onClick={onClose}>
            Đóng
          </button>
        </div>
        <div className="space-y-4 p-5">
          <div>
            <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">{food.foodGroup || food.category}</p>
            <h3 className="mt-2 text-2xl font-black text-slate-950">{food.name}</h3>
            <p className="mt-2 text-sm font800 text-slate-500">{food.servingDisplay || `${food.servingGrams}g`} · {food.calories} kcal</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-4">
            <InfoTile label="Kcal" value={food.calories} />
            <InfoTile label="Protein" value={`${food.protein}g`} />
            <InfoTile label="Fat" value={`${food.fat}g`} />
            <InfoTile label="Carbs" value={`${food.carbs}g`} />
          </div>
          <div className="rounded-2xl bg-emerald-50 p-4 text-sm font800 leading-6 text-emerald-900">
            {food.reason || buildSuggestionReason(food)}
          </div>
          <InfoRow label="Yêu cầu ảnh" value={food.imageRequirement || "Không đủ dữ liệu"} />
          <InfoRow label="Quality flags" value={food.qualityFlags || "Không có"} />
        </div>
      </article>
    </div>
  );
}

function AccountSettingsPage({ email, profile, eligibility, errors, onChange, onRegenerate, isSubmitting }) {
  const [activeTab, setActiveTab] = useState("profile");

  const tabs = [
    { id: 'profile', label: 'Hồ sơ cá nhân', icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z' },
    { id: 'nutrition', label: 'Mục tiêu dinh dưỡng', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
    { id: 'security', label: 'Bảo mật', icon: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z' },
    { id: 'preferences', label: 'Tuỳ chỉnh', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z' }
  ];

  const handleMockSave = () => {
    alert("Tính năng đang phát triển. API chưa hỗ trợ lưu trữ thay đổi này.");
  };

  return (
    <section className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
      <div className="space-y-5">
        <AccountPanel email={email} />
        <div className="glass-panel p-2">
          <nav className="flex flex-col gap-1">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font900 transition-colors ${
                  activeTab === tab.id ? 'bg-emerald-50 text-emerald-700' : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                <svg className="w-5 h-5 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={tab.icon} />
                </svg>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      <div className="space-y-5">
        {activeTab === 'profile' && (
          <section className="glass-panel p-5 sm:p-6 animate-fade-in">
            <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">Hồ sơ cá nhân</p>
            <h2 className="mt-2 text-2xl font-black text-slate-950">Chỉnh thông tin gợi ý thực đơn</h2>
            <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <ProfileField label="Tuổi" name="age" type="number" min="1" max="120" value={profile.age} error={errors.age} onChange={onChange} />
              <ProfileSelect label="Giới tính" name="sex" value={profile.sex} error={errors.sex} onChange={onChange} options={[{ value: "", label: "Không chọn" }, { value: "male", label: "Nam" }, { value: "female", label: "Nữ" }]} />
              <ProfileField label="Chiều cao (cm)" name="height" type="number" min="100" max="230" value={profile.height} error={errors.height} onChange={onChange} />
              <ProfileField label="Cân nặng hiện tại (kg)" name="weight" type="number" min="20" max="250" value={profile.weight} error={errors.weight} onChange={onChange} />
              <ProfileField label="Cân nặng mục tiêu (kg)" name="target_weight" type="number" min="20" max="250" value={profile.target_weight || ""} error={errors.target_weight} onChange={onChange} />
              <ProfileSelect label="Tốc độ tăng cân" name="gain_speed" value={profile.gain_speed} error={errors.gain_speed} onChange={onChange} options={[{ value: "slow", label: "Nhẹ, ổn định" }, { value: "medium", label: "Vừa phải" }, { value: "fast", label: "Mạnh hơn" }]} />
              <ProfileSelect label="Mức độ vận động" name="activity" value={profile.activity} error={errors.activity} onChange={onChange} options={[{ value: "default", label: "Mặc định" }, { value: "sedentary", label: "Ít vận động" }, { value: "light", label: "Nhẹ" }, { value: "moderate", label: "Vừa phải" }, { value: "active", label: "Năng động" }, { value: "very_active", label: "Rất năng động" }]} />
              <ProfileSelect label="Chế độ ăn" name="diet_style" value={profile.diet_style} error={errors.diet_style} onChange={onChange} options={[{ value: "balanced", label: "Cân bằng / eat clean" }, { value: "vegetarian", label: "Chay" }, { value: "low_carb", label: "Low-carb" }]} />
              <ProfileSelect label="Ngân sách" name="budget_level" value={profile.budget_level} error={errors.budget_level} onChange={onChange} options={[{ value: "standard", label: "Tiêu chuẩn" }, { value: "low", label: "Tiết kiệm" }, { value: "high", label: "Linh hoạt" }]} />
              <ProfileSelect label="Số món mỗi bữa" name="meal_complexity" value={profile.meal_complexity} error={errors.meal_complexity} onChange={onChange} options={[{ value: "simple", label: "3 món/bữa" }, { value: "balanced", label: "4 món/bữa" }, { value: "full", label: "5 món/bữa" }]} />
              <ProfileField label="Món yêu thích" name="favorite_foods" value={profile.favorite_foods} error={errors.favorite_foods} onChange={onChange} />
              <ProfileField label="Danh sách loại trừ" name="unfavorite_foods" value={profile.unfavorite_foods} error={errors.unfavorite_foods} onChange={onChange} />
            </div>
            <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-slate-100 pt-5">
              <button
                type="button"
                className="h-12 rounded-2xl bg-emerald-600 px-6 text-sm font900 text-white disabled:cursor-not-allowed disabled:opacity-60 hover:bg-emerald-700 transition"
                onClick={onRegenerate}
                disabled={isSubmitting || !eligibility.eligible}
              >
                {isSubmitting ? "Đang cập nhật..." : "Cập nhật và tạo lại thực đơn"}
              </button>
            </div>
          </section>
        )}

        {activeTab === 'nutrition' && (
          <div className="animate-fade-in space-y-5">
             <EligibilityCard eligibility={eligibility} />
          </div>
        )}

        {activeTab === 'security' && (
          <section className="glass-panel p-5 sm:p-6 animate-fade-in">
            <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">Bảo mật</p>
            <h2 className="mt-2 text-2xl font-black text-slate-950">Thay đổi mật khẩu</h2>
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <ProfileField label="Mật khẩu hiện tại" name="currentPassword" type="password" />
              <div className="hidden sm:block"></div>
              <ProfileField label="Mật khẩu mới" name="newPassword" type="password" />
              <ProfileField label="Xác nhận mật khẩu mới" name="confirmPassword" type="password" />
            </div>
            <div className="mt-5 border-t border-slate-100 pt-5">
              <button
                type="button"
                onClick={handleMockSave}
                className="h-12 rounded-2xl bg-slate-950 px-6 text-sm font900 text-white hover:bg-slate-800 transition"
              >
                Lưu mật khẩu
              </button>
            </div>
          </section>
        )}

        {activeTab === 'preferences' && (
          <section className="glass-panel p-5 sm:p-6 animate-fade-in">
            <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">Tuỳ chỉnh</p>
            <h2 className="mt-2 text-2xl font-black text-slate-950">Giao diện và thông báo</h2>
            <div className="mt-7 space-y-6">
              
              <div>
                <h3 className="text-sm font900 text-slate-900 mb-3">Chủ đề (Theme)</h3>
                <div className="flex gap-3">
                  <button className="flex-1 rounded-2xl border-2 border-emerald-500 bg-emerald-50 p-4 text-center font800 text-emerald-700">Sáng (Light)</button>
                  <button onClick={handleMockSave} className="flex-1 rounded-2xl border-2 border-transparent bg-slate-50 p-4 text-center font800 text-slate-500 hover:bg-slate-100 transition">Tối (Dark)</button>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100">
                <h3 className="text-sm font900 text-slate-900 mb-3 mt-4">Thông báo Email</h3>
                <div className="space-y-3">
                  <label className="flex items-center justify-between gap-3 rounded-2xl bg-white/85 p-4 text-sm font900 text-slate-800 ring-1 ring-slate-100">
                    Báo cáo dinh dưỡng hàng tuần
                    <input type="checkbox" defaultChecked className="h-5 w-5 rounded border-slate-300 text-emerald-600" onChange={handleMockSave} />
                  </label>
                  <label className="flex items-center justify-between gap-3 rounded-2xl bg-white/85 p-4 text-sm font900 text-slate-800 ring-1 ring-slate-100">
                    Nhắc nhở cập nhật cân nặng
                    <input type="checkbox" defaultChecked className="h-5 w-5 rounded border-slate-300 text-emerald-600" onChange={handleMockSave} />
                  </label>
                </div>
              </div>

            </div>
          </section>
        )}
      </div>
    </section>
  );
}

function SettingsMetricCard({ icon: Icon, label, value, subtext, colorClass }) {
  return (
    <div className="glass-panel p-5 flex flex-col justify-between h-full hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <p className="text-sm font800 text-slate-500">{label}</p>
        <div className={`p-2.5 rounded-xl ${colorClass}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <div className="mt-4">
        <h3 className="text-3xl font-black text-slate-900">{value}</h3>
        <p className="text-xs font800 text-slate-400 mt-1">{subtext}</p>
      </div>
    </div>
  );
}

function ValidationRuleItem({ id, label, description, checked, onChange, required = false }) {
  return (
    <div className="flex items-center justify-between gap-4 p-4 rounded-2xl bg-white border border-slate-100 hover:border-emerald-100 transition-colors shadow-sm">
      <div className="flex items-start gap-4">
        <div className="mt-0.5">
          <div className="w-8 h-8 rounded-full bg-slate-50 text-slate-400 flex items-center justify-center">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          </div>
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h4 className="text-sm font900 text-slate-900">{label}</h4>
            {required && <span className="px-2 py-0.5 rounded-md bg-orange-100 text-orange-700 text-[10px] font900 uppercase tracking-widest">Bắt buộc</span>}
          </div>
          <p className="text-xs font800 text-slate-500 mt-1">{description}</p>
        </div>
      </div>
      
      <button 
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(id)}
        className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${checked ? 'bg-emerald-500' : 'bg-slate-200'}`}
      >
        <span aria-hidden="true" className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${checked ? 'translate-x-5' : 'translate-x-0'}`}></span>
      </button>
    </div>
  );
}

function ReportSummaryCard({ datasetStats, progress, summary, validation }) {
  const isOverTarget = progress >= 100;
  return (
    <div className="glass-panel p-6 sticky top-28">
      <div className="flex items-center gap-2 mb-6">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 text-emerald-600"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/><path d="M8 14h.01"/><path d="M12 14h.01"/><path d="M16 14h.01"/><path d="M8 18h.01"/><path d="M12 18h.01"/><path d="M16 18h.01"/></svg>
        <h2 className="text-lg font-black text-slate-900">Báo cáo & Tổng quan</h2>
      </div>

      <div className="space-y-5">
        
        <div>
          <div className="flex justify-between text-sm mb-1.5">
            <span className="font900 text-slate-700">Tiến độ Calories</span>
            <span className={`font-black ${isOverTarget ? 'text-orange-600' : 'text-emerald-600'}`}>{progress}%</span>
          </div>
          <div className="h-2.5 w-full bg-slate-100 rounded-full overflow-hidden">
            <div 
              className={`h-full rounded-full transition-all duration-500 ${isOverTarget ? 'bg-orange-500' : 'bg-emerald-500'}`}
              style={{ width: `${Math.min(progress, 100)}%` }}
            ></div>
          </div>
        </div>

        <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 space-y-3">
          <div className="flex justify-between">
            <span className="text-sm font800 text-slate-500">Cập nhật dataset</span>
            <span className="text-sm font900 text-slate-900">{datasetStats.updatedAt || "Không rõ"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm font800 text-slate-500">BMR / TDEE</span>
            <span className="text-sm font900 text-slate-900">{summary.bmr} / {summary.tdee} kcal</span>
          </div>
          <div className="flex justify-between border-t border-slate-200 pt-2.5">
            <span className="text-sm font800 text-slate-500">Tổng Calories thực đơn</span>
            <span className="text-sm font900 text-emerald-700">{validation.totalCalories} kcal</span>
          </div>
        </div>

        <div className="pt-2 gap-3 flex flex-col">
          <button type="button" className="flex items-center justify-center gap-2 h-12 rounded-xl bg-emerald-600 px-4 text-sm font900 text-white shadow-sm hover:bg-emerald-700 transition">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
            Xuất file CSV
          </button>
          <button type="button" className="flex items-center justify-center gap-2 h-12 rounded-xl bg-slate-100 px-4 text-sm font900 text-slate-400 cursor-not-allowed" disabled>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><path d="M10 13v6"/><path d="M10 13h2.5"/><path d="M10 16h1.5"/><path d="M16 13v6"/><path d="M16 13h2.5"/><path d="M16 19h2.5"/></svg>
            Xuất PDF (Chưa hỗ trợ)
          </button>
        </div>

        <p className="text-center text-xs font800 text-slate-400 mt-2">Dữ liệu được cập nhật theo kết quả tính toán gần nhất</p>
      </div>
    </div>
  );
}

function SystemSettingsPage({ datasetStats, progress, summary, validation }) {
  const [rules, setRules] = useState({
    bmi: true,
    macro: true,
    duplicateGroup: true,
    placeholder: true,
  });

  const [saving, setSaving] = useState(false);

  function toggleRule(key) {
    setRules((current) => ({ ...current, [key]: !current[key] }));
  }

  const handleSave = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      alert("Cài đặt đã được lưu thành công.");
    }, 800);
  };

  const handleRestore = () => {
    setRules({ bmi: true, macro: true, duplicateGroup: true, placeholder: true });
  };

  return (
    <div className="space-y-6">
      
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-black text-slate-950">Cài đặt hệ thống</h1>
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font900 text-slate-600">Admin</span>
        </div>
        <p className="mt-1 text-sm font800 text-slate-500">Quản lý rule kiểm định, dữ liệu món ăn và xuất báo cáo hệ thống.</p>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SettingsMetricCard 
          icon={(props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M4 22h14a2 2 0 0 0 2-2V7.5L14.5 2H6a2 2 0 0 0-2 2v4"/><polyline points="14 2 14 8 20 8"/><path d="M2 15h10"/><path d="m9 18 3-3-3-3"/></svg>}
          label="Tổng món Dataset" 
          value={formatStat(datasetStats.total)} 
          subtext="Số lượng món gốc từ CSV"
          colorClass="bg-blue-50 text-blue-600"
        />
        <SettingsMetricCard 
          icon={(props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>}
          label="Menu Eligible" 
          value={formatStat(datasetStats.eligible)} 
          subtext="Món được phép đưa vào thực đơn"
          colorClass="bg-emerald-50 text-emerald-600"
        />
        <SettingsMetricCard 
          icon={(props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>}
          label="Món bị loại" 
          value={formatStat(datasetStats.excluded)} 
          subtext="Vi phạm macro hoặc rule"
          colorClass="bg-orange-50 text-orange-600"
        />
        <SettingsMetricCard 
          icon={(props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>}
          label="Món đang hiển thị" 
          value={datasetStats.visible} 
          subtext="Hiện diện trong kế hoạch ăn"
          colorClass="bg-indigo-50 text-indigo-600"
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px] items-start">
        
        {/* Left Column: Validation Rules */}
        <div className="glass-panel p-6 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-xs font900 uppercase tracking-wider text-emerald-700">Rules</p>
              <h2 className="mt-1 text-xl font-black text-slate-900">Cài đặt kiểm định thuật toán</h2>
            </div>
            <div className="p-2 bg-slate-50 rounded-xl">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 text-slate-400"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="9" y1="3" x2="9" y2="21"/><path d="M17 16v-6a2 2 0 0 0-2-2h-2"/></svg>
            </div>
          </div>
          
          <div className="space-y-3">
            <ValidationRuleItem 
              id="bmi" 
              label="Kiểm tra BMI < 18.5" 
              description="Từ chối sinh thực đơn đối với người có BMI bình thường hoặc béo phì." 
              checked={rules.bmi} 
              onChange={toggleRule} 
              required 
            />
            <ValidationRuleItem 
              id="macro" 
              label="Kiểm tra macro bất thường" 
              description="Loại bỏ các món ăn có chỉ số Đạm/Béo/Tinh bột vi phạm logic hoặc không cân đối." 
              checked={rules.macro} 
              onChange={toggleRule} 
            />
            <ValidationRuleItem 
              id="duplicateGroup" 
              label="Kiểm tra trùng nhóm món" 
              description="Ngăn chặn việc xuất hiện nhiều món cùng nhóm (VD: 2 món xào, 2 món canh) trong 1 bữa." 
              checked={rules.duplicateGroup} 
              onChange={toggleRule} 
              required
            />
            <ValidationRuleItem 
              id="placeholder" 
              label="Dùng placeholder khi thiếu ảnh" 
              description="Tự động thay thế bằng ảnh minh họa đối với các món ăn chưa có ảnh thật trong dataset." 
              checked={rules.placeholder} 
              onChange={toggleRule} 
            />
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-3 pt-6 border-t border-slate-100">
            <button 
              type="button" 
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 h-11 rounded-xl bg-slate-900 px-6 text-sm font900 text-white hover:bg-slate-800 transition"
            >
              {saving ? 'Đang lưu...' : 'Lưu thay đổi'}
            </button>
            <button 
              type="button" 
              onClick={handleRestore}
              className="h-11 rounded-xl bg-white border border-slate-200 px-5 text-sm font900 text-slate-600 hover:bg-slate-50 transition"
            >
              Khôi phục mặc định
            </button>
          </div>
        </div>

        {/* Right Column: Report Summary */}
        <ReportSummaryCard 
          datasetStats={datasetStats} 
          progress={progress} 
          summary={summary} 
          validation={validation} 
        />
        
      </section>
    </div>
  );
}

function DailyNutritionSummary({ validation, consumedNutrition, nutritionTarget, onRegenerate, isSubmitting }) {
  const consumed = consumedNutrition || { calories: 0, protein: 0, fat: 0, carbs: 0 };
  return (
    <section className="glass-panel p-5 sm:p-6">
      <div className="grid gap-5 xl:grid-cols-[minmax(0,0.9fr)_minmax(360px,1.1fr)] xl:items-center">
        <div>
          <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">Hôm nay</p>
          <div className="mt-2 flex flex-wrap items-end gap-3">
            <h2 className="text-4xl font-black leading-none text-slate-950">
              {consumed.calories.toLocaleString("vi-VN")}
              <span className="ml-2 text-lg font900 text-slate-500">/ {nutritionTarget.targetCalories} kcal</span>
            </h2>
          </div>
          <div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-100">
            <div
              className={`h-full rounded-full ${validation.level === "error" ? "bg-orange-400" : "bg-emerald-500"}`}
              style={{
                width: `${Math.min((consumed.calories / Math.max(nutritionTarget.targetCalories, 1)) * 100, 100)}%`,
              }}
            />
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <MacroTarget label="Protein" value={consumed.protein} target={nutritionTarget.proteinTarget} tone="sky" />
          <MacroTarget label="Fat" value={consumed.fat} target={nutritionTarget.fatTarget} tone="orange" />
          <MacroTarget label="Carbs" value={consumed.carbs} target={nutritionTarget.carbTarget} tone="emerald" />
        </div>
      </div>

      <div className="mt-5">
        <PlanAlert validation={validation} onRegenerate={onRegenerate} isSubmitting={isSubmitting} compact />
      </div>
    </section>
  );
}

function MacroTarget({ label, value, target, tone }) {
  const color = {
    sky: "bg-sky-500",
    orange: "bg-orange-400",
    emerald: "bg-emerald-500",
  }[tone];

  return (
    <div className="rounded-2xl bg-white/85 p-4 ring-1 ring-slate-100">
      <div className={`h-2 w-10 rounded-full ${color}`} />
      <div className="mt-3 text-2xl font-black text-slate-950">
        {value}<span className="text-sm font900 text-slate-500"> / {target}g</span>
      </div>
      <div className="mt-1 text-xs font900 uppercase tracking-[0.1em] text-slate-500">{label}</div>
    </div>
  );
}

function PlanAlert({ validation, onRegenerate, isSubmitting, compact = false }) {
  const isError = validation.level === "error";
  const isWarning = validation.level === "warning";
  const shellClass = isError
    ? "border-orange-200 bg-orange-50 text-orange-900"
    : isWarning
      ? "border-amber-200 bg-amber-50 text-amber-900"
      : "border-emerald-200 bg-emerald-50 text-emerald-900";

  return (
    <section className={`rounded-2xl border px-5 py-4 ${shellClass}`}>
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h3 className="text-base font-black">
            {validation.isValid ? "Thực đơn phù hợp với mục tiêu hôm nay." : "Thực đơn chưa phù hợp mục tiêu cá nhân hóa."}
          </h3>
          <ul className={`mt-2 space-y-1 text-sm font800 leading-6 ${compact ? "max-h-24 overflow-y-auto pr-1" : ""}`}>
            {validation.messages.slice(0, compact ? 3 : 6).map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </div>
        {!validation.isValid ? (
          <button
            type="button"
            className="min-h-11 shrink-0 rounded-2xl bg-slate-950 px-4 text-sm font900 text-white transition hover:bg-navy disabled:cursor-not-allowed disabled:opacity-60"
            onClick={onRegenerate}
            disabled={isSubmitting}
          >
            {isSubmitting ? "Đang tạo lại..." : "Tạo lại thực đơn phù hợp hơn"}
          </button>
        ) : null}
      </div>
    </section>
  );
}

function parseTagValue(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatTagValue(tags) {
  return tags.filter(Boolean).join(", ");
}

function bmiStatusLabel(bmi) {
  if (!Number.isFinite(bmi)) return "Đang theo dõi";
  if (bmi < 18.5) return "Thiếu cân";
  if (bmi < 23) return "Bình thường";
  if (bmi < 25) return "Thừa cân";
  return "Béo phì";
}

function ProfileField({ label, name, type = "text", value, error, onChange, ...props }) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font900 text-slate-800">{label}</span>
      <input
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        className={`h-12 w-full rounded-3xl border bg-white px-4 text-sm font800 text-slate-950 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100 ${
          error ? "border-red-400" : "border-slate-200"
        }`}
        {...props}
      />
      {error ? <span className="mt-2 block text-sm font800 text-red-500">{error}</span> : null}
    </label>
  );
}

function ProfileSelect({ label, name, value, error, options, onChange }) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font900 text-slate-800">{label}</span>
      <select
        name={name}
        value={value}
        onChange={onChange}
        className={`h-12 w-full rounded-3xl border bg-white px-4 text-sm font800 text-slate-950 shadow-sm outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100 ${
          error ? "border-red-400" : "border-slate-200"
        }`}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error ? <span className="mt-2 block text-sm font800 text-red-500">{error}</span> : null}
    </label>
  );
}

function TagInput({ label, name, value, error, placeholder, helperText, onChange }) {
  const [draft, setDraft] = useState("");
  const tags = useMemo(() => parseTagValue(value), [value]);

  function emitChange(nextTags) {
    if (!onChange) return;
    onChange({ target: { name, value: formatTagValue(nextTags), type: "text" } });
  }

  function commitTag(rawValue) {
    const items = parseTagValue(rawValue);
    if (!items.length) return;
    const normalized = tags.map((tag) => tag.toLowerCase());
    const nextTags = [...tags];
    items.forEach((item) => {
      if (!normalized.includes(item.toLowerCase())) {
        nextTags.push(item);
        normalized.push(item.toLowerCase());
      }
    });
    emitChange(nextTags);
    setDraft("");
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      commitTag(draft);
      return;
    }

    if (event.key === "Backspace" && !draft && tags.length) {
      emitChange(tags.slice(0, -1));
    }
  }

  return (
    <label className="block">
      <span className="mb-2 block text-sm font900 text-slate-800">{label}</span>
      <div
        className={`flex min-h-[52px] flex-wrap items-center gap-2 rounded-3xl border bg-white px-3 py-2 shadow-sm transition focus-within:border-emerald-500 focus-within:ring-4 focus-within:ring-emerald-100 ${
          error ? "border-red-400" : "border-slate-200"
        }`}
      >
        {tags.map((tag) => (
          <span key={tag} className="flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font900 text-emerald-800">
            {tag}
            <button
              type="button"
              className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font900 text-emerald-800 transition hover:bg-emerald-200"
              onClick={() => emitChange(tags.filter((item) => item !== tag))}
              aria-label={`Xóa ${tag}`}
            >
              x
            </button>
          </span>
        ))}
        <input
          type="text"
          name={name}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={() => commitTag(draft)}
          placeholder={tags.length ? "" : placeholder}
          className="min-w-[160px] flex-1 bg-transparent px-2 py-1 text-sm font800 text-slate-800 outline-none placeholder:text-slate-400"
        />
      </div>
      {helperText ? <span className="mt-2 block text-xs font800 text-slate-500">{helperText}</span> : null}
      {error ? <span className="mt-2 block text-sm font800 text-red-500">{error}</span> : null}
    </label>
  );
}

function SetupBenefit({ title, text }) {
  return (
    <div className="rounded-3xl border border-white/15 bg-white/12 p-4 text-white backdrop-blur-xl">
      <div className="text-base font900">{title}</div>
      <div className="mt-2 text-sm font700 leading-6 text-slate-200">{text}</div>
    </div>
  );
}

function PersonalizationPanel({ profile }) {
  return (
    <section className="glass-panel p-5">
      <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">
        Cá nhân hóa
      </p>
      <h2 className="mt-2 text-xl font-black text-slate-950">Căn cứ gợi ý</h2>
      <div className="mt-5 space-y-3">
        <InfoRow label="Mục tiêu" value={goalLabel(profile.goal_type)} />
        <InfoRow label="Hồ sơ" value={`${profile.weight}kg · ${profile.height}cm${profile.age ? ` · ${profile.age} tuổi` : ""}`} />
        <InfoRow label="Giới tính" value={sexLabel(profile.sex)} />
        <InfoRow label="Chế độ" value={dietLabel(profile.diet_style)} />
        <InfoRow label="Số món" value={complexityLabel(profile.meal_complexity)} />
        <InfoRow label="Ngân sách" value={budgetLabel(profile.budget_level)} />
        <InfoRow label="Loại trừ" value={profile.unfavorite_foods?.trim() || "Chưa có"} />
      </div>
    </section>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-2xl bg-white/80 px-4 py-3 ring-1 ring-slate-100">
      <span className="text-sm font800 text-slate-500">{label}</span>
      <strong className="max-w-[12rem] text-right text-sm font900 leading-5 text-slate-950">{value}</strong>
    </div>
  );
}

function goalLabel(value) {
  return {
    gain: "Tăng cân",
    muscle_gain: "Tăng cơ",
    maintain: "Giữ cân",
    lose: "Giảm cân nhẹ",
  }[value] || "Tăng cân";
}

function sexLabel(value) {
  return {
    male: "Nam",
    female: "Nữ",
  }[value] || "Chưa chọn";
}

function dietLabel(value) {
  return {
    balanced: "Cân bằng",
    vegetarian: "Chay",
    low_carb: "Low-carb",
  }[value] || "Cân bằng";
}

function complexityLabel(value) {
  return {
    simple: "3 món/bữa",
    balanced: "4 món/bữa",
    full: "5 món/bữa",
  }[value] || "4 món/bữa";
}

function budgetLabel(value) {
  return {
    standard: "Tiêu chuẩn",
    low: "Tiết kiệm",
    high: "Linh hoạt",
  }[value] || "Tiêu chuẩn";
}

const notificationFilters = [
  { id: "all", label: "Tất cả" },
  { id: "unread", label: "Chưa đọc" },
  { id: "reminder", label: "Nhắc nhở" },
  { id: "warning", label: "Cảnh báo" },
  { id: "profile", label: "Hồ sơ" },
  { id: "read", label: "Đã đọc" },
];

function EnhancedNotificationPanel({ progress, summary, validation, dataWarnings = [], onNavigate }) {
  const [readMap, setReadMap] = useState({});
  const [activeFilter, setActiveFilter] = useState("all");
  const [showFilters, setShowFilters] = useState(true);
  const safeProgress = Number.isFinite(Number(progress)) ? Number(progress) : 0;
  const safeSummary = summary || fallbackSummary;
  const safeValidation = validation || { totalProtein: 0, totalCalories: 0, messages: [], isValid: false };
  const safeWarnings = Array.isArray(dataWarnings) ? dataWarnings : [];
  const notifications = buildNotifications(safeProgress, safeSummary, safeValidation, safeWarnings) || [];
  const safeNotifications = Array.isArray(notifications) ? notifications : [];
  const unreadCount = safeNotifications.filter((item) => !readMap[item.id]).length;
  const warningCount = safeNotifications.filter((item) => item.category === "warning").length;
  const handledCount = Math.max(safeNotifications.length - unreadCount, 0);
  const filteredNotifications = useMemo(
    () => filterNotifications(safeNotifications, readMap, activeFilter),
    [safeNotifications, readMap, activeFilter],
  );

  function markAllRead() {
    setReadMap((current) => ({
      ...current,
      ...Object.fromEntries(safeNotifications.map((item) => [item.id, true])),
    }));
  }

  function markRead(notificationId) {
    setReadMap((current) => ({ ...current, [notificationId]: true }));
  }

  function handleAction(item) {
    markRead(item.id);
    if (item.actionTarget && onNavigate) {
      onNavigate(item.actionTarget);
    }
  }

  return (
    <section
      id="notifications-panel"
      className="scroll-mt-28 rounded-[28px] border border-emerald-100/70 bg-[#F7FAF8] p-6 shadow-sm"
    >
      <NotificationPageHeader
        unreadCount={unreadCount}
        onMarkAllRead={markAllRead}
        onToggleFilters={() => setShowFilters((current) => !current)}
      />

      <NotificationStats
        total={safeNotifications.length}
        unread={unreadCount}
        warning={warningCount}
        handled={handledCount}
      />

      <NotificationFilterBar
        items={notificationFilters}
        activeFilter={activeFilter}
        onChange={setActiveFilter}
        showFilters={showFilters}
      />

      <div className="mt-5 grid gap-4">
        {filteredNotifications.length ? (
          filteredNotifications.map((item) => (
            <NotificationCard
              key={item.id}
              item={item}
              isRead={Boolean(readMap[item.id])}
              onMarkRead={() => markRead(item.id)}
              onAction={() => handleAction(item)}
            />
          ))
        ) : (
          <NotificationEmptyState isFiltered={safeNotifications.length > 0} />
        )}
      </div>
    </section>
  );
}

function NotificationPageHeader({ unreadCount, onMarkAllRead, onToggleFilters }) {
  const todayLabel = useMemo(
    () => new Date().toLocaleDateString("vi-VN", { weekday: "long", day: "2-digit", month: "long", year: "numeric" }),
    [],
  );

  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">Thông báo</p>
        <h2 className="mt-2 text-2xl font-black text-slate-950">Trung tâm thông báo</h2>
        <p className="mt-2 text-sm font700 leading-6 text-slate-500">
          Theo dõi nhắc bữa ăn, cảnh báo dinh dưỡng và cập nhật hồ sơ hằng ngày.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <span className="rounded-2xl border border-emerald-100 bg-white px-4 py-2 text-sm font900 text-emerald-700">
          {todayLabel}
        </span>
        <button
          type="button"
          className="h-11 rounded-2xl bg-slate-950 px-4 text-sm font900 text-white shadow-sm"
          onClick={onMarkAllRead}
        >
          Đánh dấu tất cả đã đọc ({unreadCount})
        </button>
        <button
          type="button"
          className="h-11 rounded-2xl border border-slate-200 bg-white px-4 text-sm font900 text-slate-700 shadow-sm transition hover:border-emerald-200"
          onClick={onToggleFilters}
        >
          <span className="inline-flex items-center gap-2">
            <IconFilter className="h-4 w-4" />
            Lọc
          </span>
        </button>
      </div>
    </div>
  );
}

function NotificationStats({ total, unread, warning, handled }) {
  const stats = [
    { id: "total", label: "Tổng thông báo", value: total, tone: "green", icon: "bell" },
    { id: "unread", label: "Chưa đọc", value: unread, tone: "blue", icon: "clock" },
    { id: "warning", label: "Cảnh báo", value: warning, tone: "orange", icon: "alert" },
    { id: "handled", label: "Đã xử lý", value: handled, tone: "green", icon: "check" },
  ];

  return (
    <section className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {stats.map((item) => (
        <NotificationStatCard key={item.id} {...item} />
      ))}
    </section>
  );
}

function NotificationStatCard({ label, value, tone, icon }) {
  const toneStyles = notificationToneStyles(tone);

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-xs font900 uppercase tracking-[0.16em] text-slate-500">{label}</span>
        <span className={`grid h-10 w-10 place-items-center rounded-2xl ${toneStyles.icon}`}>
          <NotificationIcon name={icon} className="h-5 w-5" />
        </span>
      </div>
      <div className="mt-3 text-3xl font-black text-slate-950">{value}</div>
    </article>
  );
}

function NotificationFilterBar({ items, activeFilter, onChange, showFilters }) {
  return (
    <div className={`mt-5 ${showFilters ? "block" : "hidden"} lg:block`}>
      <div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
        <div className="flex flex-wrap gap-2">
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onChange(item.id)}
              className={`rounded-full px-4 py-2 text-xs font900 uppercase tracking-[0.14em] transition ${
                activeFilter === item.id
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "bg-slate-100 text-slate-600 hover:bg-emerald-50 hover:text-emerald-700"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function NotificationCard({ item, isRead, onMarkRead, onAction }) {
  const toneStyles = notificationToneStyles(item.tone);
  const timeLabel = item.timeLabel || "Hôm nay";

  return (
    <article
      className={`rounded-3xl border bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md ${
        isRead ? "border-slate-200 text-slate-500" : "border-emerald-100 text-slate-900"
      }`}
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex gap-4">
          <div className={`grid h-12 w-12 shrink-0 place-items-center rounded-2xl ${toneStyles.icon}`}>
            <NotificationIcon name={item.icon} className="h-5 w-5" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className={`rounded-full px-2.5 py-1 text-xs font900 uppercase tracking-[0.08em] ${toneStyles.badge}`}>
                {item.type}
              </span>
              {isRead ? (
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font900 text-slate-500">Đã đọc</span>
              ) : (
                <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font900 text-emerald-800">Chưa đọc</span>
              )}
            </div>
            <h3 className="mt-3 text-base font-black text-slate-950">{item.title}</h3>
            <p className="mt-2 text-sm font700 leading-6 text-slate-600">{item.text}</p>
            <div className="mt-3 flex items-center gap-2 text-xs font800 text-slate-500">
              <IconClock className="h-4 w-4" />
              {timeLabel}
            </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 sm:flex-col sm:items-end">
          {item.actionLabel ? (
            <button
              type="button"
              className={`h-10 rounded-2xl px-4 text-sm font900 transition ${toneStyles.action}`}
              onClick={onAction}
            >
              {item.actionLabel}
            </button>
          ) : null}
          <button
            type="button"
            className={`h-10 rounded-2xl border px-4 text-sm font900 transition ${
              isRead ? "border-slate-200 bg-slate-50 text-slate-400" : "border-slate-200 bg-white text-slate-700 hover:border-emerald-200"
            }`}
            onClick={onMarkRead}
            disabled={isRead}
          >
            {isRead ? "Đã đọc" : "Đánh dấu đã đọc"}
          </button>
        </div>
      </div>
    </article>
  );
}

function NotificationEmptyState({ isFiltered }) {
  const title = isFiltered ? "Không có thông báo phù hợp bộ lọc" : "Bạn chưa có thông báo mới";
  const description = isFiltered
    ? "Hãy thử đổi bộ lọc để xem các nhắc nhở khác trong ngày."
    : "NutriGain sẽ nhắc bữa ăn, cảnh báo kcal và cập nhật hồ sơ tại đây.";

  return (
    <div className="rounded-3xl border border-dashed border-emerald-100 bg-white p-8 text-center shadow-sm">
      <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-emerald-50 text-emerald-700">
        <IconBell className="h-6 w-6" />
      </div>
      <h3 className="mt-4 text-lg font-black text-slate-950">{title}</h3>
      <p className="mt-2 text-sm font700 text-slate-500">{description}</p>
    </div>
  );
}

function NotificationIcon({ name, className }) {
  switch (name) {
    case "utensils":
      return <IconUtensils className={className} />;
    case "scale":
      return <IconScale className={className} />;
    case "flame":
      return <IconFlame className={className} />;
    case "alert":
      return <IconAlertTriangle className={className} />;
    case "check":
      return <IconCheckCircle className={className} />;
    case "clock":
      return <IconClock className={className} />;
    default:
      return <IconBell className={className} />;
  }
}

function notificationToneStyles(tone) {
  const palette = {
    green: {
      icon: "bg-emerald-50 text-emerald-700",
      badge: "bg-emerald-50 text-emerald-700",
      action: "bg-emerald-600 text-white hover:bg-emerald-700",
    },
    blue: {
      icon: "bg-sky-50 text-sky-700",
      badge: "bg-sky-50 text-sky-700",
      action: "bg-sky-600 text-white hover:bg-sky-700",
    },
    orange: {
      icon: "bg-orange-50 text-orange-700",
      badge: "bg-orange-50 text-orange-700",
      action: "bg-orange-500 text-white hover:bg-orange-600",
    },
    red: {
      icon: "bg-rose-50 text-rose-700",
      badge: "bg-rose-50 text-rose-700",
      action: "bg-rose-600 text-white hover:bg-rose-700",
    },
  };

  return palette[tone] || palette.green;
}

function IconBell({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 7h18s-3 0-3-7" />
      <path d="M13.7 21a2 2 0 0 1-3.4 0" />
    </svg>
  );
}

function IconUtensils({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 3v8a3 3 0 0 0 6 0V3" />
      <path d="M7 3v8" />
      <path d="M14 3v8a3 3 0 0 0 6 0V3" />
      <path d="M17 3v18" />
    </svg>
  );
}

function IconScale({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="10" r="7" />
      <path d="M12 10l3-3" />
      <path d="M7 20h10" />
    </svg>
  );
}

function IconFlame({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 2c3 3 4.5 6 4.5 9a4.5 4.5 0 1 1-9 0c0-3 1.5-6 4.5-9z" />
      <path d="M12 12c1.3 1 1.8 2.1 1.8 3.2a1.8 1.8 0 1 1-3.6 0c0-1.1.5-2.2 1.8-3.2z" />
    </svg>
  );
}

function IconAlertTriangle({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M10.3 4.3 2.8 18.6a2 2 0 0 0 1.8 3h15a2 2 0 0 0 1.8-3L13.7 4.3a2 2 0 0 0-3.4 0z" />
      <path d="M12 9v4" />
      <path d="M12 17h.01" />
    </svg>
  );
}

function IconCheckCircle({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

function IconClock({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  );
}

function IconFilter({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 5h16" />
      <path d="M7 12h10" />
      <path d="M10 19h4" />
    </svg>
  );
}

const HelpIcons = {
  Search: (props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>,
  ChevronDown: (props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="m6 9 6 6 6-6"/></svg>,
  ChevronUp: (props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="m18 15-6-6-6 6"/></svg>,
  MessageSquare: (props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="m3 21 1.9-5.7a8.5 8.5 0 1 1 3.8 3.8z"/></svg>,
  BookOpen: (props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>,
  LifeBuoy: (props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><path d="m4.9 4.9 4.2 4.2"/><path d="m14.9 14.9 4.2 4.2"/><path d="m14.9 9.1 4.2-4.2"/><path d="m4.9 19.1 4.2-4.2"/></svg>,
  Activity: (props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>,
  AlertCircle: (props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>,
  Lightbulb: (props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/></svg>,
  HelpCircle: (props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>,
  CheckCircle: (props) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="12" cy="12" r="9"/><path d="m9 12 2 2 4-4"/></svg>
};

function EnhancedHelpPanel({ foods }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");
  const [expandedFaq, setExpandedFaq] = useState("faq-0");
  
  const [report, setReport] = useState({ item: "", type: "wrong_image", description: "" });
  const [submitted, setSubmitted] = useState(false);

  const categories = [
    { id: "all", label: "Tất cả" },
    { id: "system", label: "Hệ thống" },
    { id: "profile", label: "Hồ sơ & BMI" },
    { id: "menu", label: "Thực đơn" },
    { id: "data", label: "Dữ liệu & Ảnh" },
    { id: "account", label: "Tài khoản" },
  ];

  const faqs = [
    { id: 'faq-0', category: 'system', group: 'Hệ thống hoạt động thế nào?', title: 'Hệ thống dành cho ai?', answer: 'NutriGain chỉ phục vụ người thiếu cân hoặc BMI dưới 18.5 có nhu cầu tăng cân lành mạnh.' },
    { id: 'faq-1', category: 'profile', group: 'Hồ sơ & BMI', title: 'Vì sao cần BMI < 18.5?', answer: 'Đây là ràng buộc phạm vi hệ thống. Chúng tôi thiết kế thuật toán dành riêng cho người thiếu cân, không áp dụng cho người bình thường, thừa cân hoặc béo phì.' },
    { id: 'faq-2', category: 'profile', group: 'Hồ sơ & BMI', title: 'BMR/TDEE là gì?', answer: 'BMR là năng lượng nền (năng lượng cơ thể cần để duy trì sự sống). TDEE là tổng năng lượng tiêu hao ước tính theo mức độ vận động hàng ngày của bạn.' },
    { id: 'faq-3', category: 'system', group: 'Hệ thống hoạt động thế nào?', title: 'Vì sao hệ thống không sinh thực đơn cho người BMI bình thường?', answer: 'Thuật toán tăng cân yêu cầu thặng dư calo cụ thể, nếu áp dụng cho người bình thường sẽ gây nguy cơ thừa cân béo phì. Hệ thống sẽ khóa tính năng sinh thực đơn nếu BMI ≥ 18.5.' },
    { id: 'faq-4', category: 'menu', group: 'Thực đơn & món ăn', title: 'Cách đổi món trong kế hoạch bữa ăn?', answer: 'Bạn nhấn nút "Đổi món" ở góc thẻ món ăn trong Kế hoạch. Hệ thống sẽ đề xuất một nhóm món khác có giá trị dinh dưỡng tương đương.' },
    { id: 'faq-5', category: 'account', group: 'Tài khoản', title: 'Cách cập nhật cân nặng và tạo lại thực đơn?', answer: 'Vào phần "Tài khoản", cập nhật cân nặng hiện tại và nhấn "Cập nhật và tạo lại thực đơn". Lượng calories bắt buộc sẽ được tính toán lại theo cân nặng mới.' },
    { id: 'faq-6', category: 'data', group: 'Ảnh và dữ liệu', title: 'Vì sao ảnh món ăn có thể là ảnh minh họa?', answer: 'Hệ thống tối ưu hiệu suất và tốc độ load bằng cách dùng bộ dataset tĩnh. Một số món ăn chưa có ảnh thật sẽ được thay thế bằng placeholder hoặc ảnh minh họa chung.' },
    { id: 'faq-7', category: 'menu', group: 'Thực đơn & món ăn', title: 'Nếu thực đơn chưa hiện thì phải làm gì?', answer: 'Đảm bảo bạn đã nhập đầy đủ Chiều cao, Cân nặng và hệ thống xác nhận bạn đủ điều kiện (BMI < 18.5). Sau đó nhấn Tạo thực đơn.' },
    { id: 'faq-8', category: 'system', group: 'Hệ thống hoạt động thế nào?', title: 'Khi nào dữ liệu biểu đồ được hiển thị?', answer: 'Biểu đồ sẽ xuất hiện sau khi bạn có ít nhất một thao tác đánh dấu "Đã ăn" hoặc có dòng dữ liệu báo cáo dinh dưỡng trong ngày được ghi nhận.' },
    { id: 'faq-9', category: 'menu', group: 'Thực đơn & món ăn', title: 'Làm sao đánh dấu “Đã ăn”?', answer: 'Vào mục "Kế hoạch món ăn" hoặc Dashboard, click vào thẻ món ăn hoặc nút tick để xác nhận bạn đã tiêu thụ món đó. Hệ thống sẽ cộng dồn calories trong ngày.' }
  ];

  const filteredFaqs = faqs.filter(faq => {
    const matchesSearch = faq.title.toLowerCase().includes(searchQuery.toLowerCase()) || faq.answer.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = activeCategory === "all" || faq.category === activeCategory;
    return matchesSearch && matchesCategory;
  });

  const groupedFaqs = filteredFaqs.reduce((acc, faq) => {
    if (!acc[faq.group]) acc[faq.group] = [];
    acc[faq.group].push(faq);
    return acc;
  }, {});

  function submitReport(event) {
    event.preventDefault();
    if (!report.item.trim() || !report.description.trim()) return;
    setSubmitted(true);
    setTimeout(() => setSubmitted(false), 5000);
  }

  const handleScrollTo = (id) => {
    const el = document.getElementById(id);
    if(el) el.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div id="help-panel" className="space-y-6">
      
      {/* Top Header Section */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black text-slate-950">Hỗ trợ</h1>
            <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font900 text-emerald-800">Support Center</span>
          </div>
          <p className="mt-1 text-sm font800 text-slate-500">Tìm câu trả lời nhanh, xem hướng dẫn sử dụng và gửi phản hồi cho hệ thống.</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => handleScrollTo('quick-guide')} className="flex items-center gap-2 rounded-2xl bg-white px-4 py-2.5 text-sm font900 text-slate-700 shadow-sm ring-1 ring-slate-200 hover:bg-slate-50 transition">
            <HelpIcons.BookOpen className="h-4 w-4 text-emerald-600" /> Xem hướng dẫn
          </button>
          <button onClick={() => handleScrollTo('feedback-form')} className="flex items-center gap-2 rounded-2xl bg-emerald-600 px-4 py-2.5 text-sm font900 text-white shadow-sm hover:bg-emerald-700 transition">
            <HelpIcons.MessageSquare className="h-4 w-4" /> Gửi phản hồi
          </button>
        </div>
      </div>

      {/* Hero Support Card */}
      <section className="glass-panel relative overflow-hidden bg-gradient-to-br from-emerald-600 to-teal-800 p-8 sm:p-10 shadow-lg text-center">
        <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-10 mix-blend-overlay"></div>
        <div className="relative z-10 mx-auto max-w-2xl">
          <h2 className="text-2xl sm:text-3xl font-black text-white">Chúng tôi có thể giúp gì cho bạn?</h2>
          
          <div className="mt-6 relative">
            <HelpIcons.Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
            <input 
              type="text" 
              placeholder="Tìm câu hỏi, ví dụ: BMI là gì, cách đổi món, cập nhật cân nặng..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-14 w-full rounded-full border-0 bg-white pl-12 pr-4 text-base font800 text-slate-900 shadow-lg outline-none ring-4 ring-emerald-500/20 placeholder:text-slate-400 focus:ring-emerald-500/40 transition-all"
            />
          </div>

          <div className="mt-6 flex flex-wrap justify-center gap-2">
            {["Hồ sơ dinh dưỡng", "Tạo thực đơn", "Đổi món", "Nhật ký ăn uống", "Biểu đồ", "Tài khoản", "Thông báo"].map(chip => (
              <button key={chip} onClick={() => setSearchQuery(chip)} className="rounded-full bg-white/10 px-4 py-1.5 text-sm font800 text-white hover:bg-white/20 transition whitespace-nowrap">
                {chip}
              </button>
            ))}
          </div>

          <div className="mt-8 flex justify-center gap-6 text-emerald-50">
             <div className="flex items-center gap-2"><HelpIcons.HelpCircle className="h-5 w-5" /><span className="text-sm font900">10+ FAQ</span></div>
             <div className="flex items-center gap-2"><HelpIcons.BookOpen className="h-5 w-5" /><span className="text-sm font900">Hướng dẫn 5 bước</span></div>
             <div className="flex items-center gap-2"><HelpIcons.LifeBuoy className="h-5 w-5" /><span className="text-sm font900">Phản hồi 24/7</span></div>
          </div>
        </div>
      </section>

      {/* Main Content 2 Columns */}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(340px,0.8fr)] items-start">
        
        {/* Left Column: Knowledge */}
        <div className="space-y-6">
          
          {/* FAQ Section */}
          <section className="glass-panel p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-6">
              <HelpIcons.HelpCircle className="h-5 w-5 text-emerald-600" />
              <h2 className="text-xl font-black text-slate-900">Câu hỏi thường gặp</h2>
            </div>
            
            {Object.keys(groupedFaqs).length === 0 ? (
              <div className="text-center py-10">
                <HelpIcons.Search className="mx-auto h-12 w-12 text-slate-300 mb-3" />
                <p className="text-base font900 text-slate-600">Không tìm thấy nội dung phù hợp.</p>
                <p className="text-sm font800 text-slate-500 mt-1">Hãy thử từ khóa khác hoặc gửi phản hồi phía dưới.</p>
              </div>
            ) : (
              <div className="space-y-6">
                {Object.entries(groupedFaqs).map(([groupName, groupItems]) => (
                  <div key={groupName}>
                    <h3 className="text-xs font900 uppercase tracking-wider text-emerald-700 mb-3">{groupName}</h3>
                    <div className="space-y-2">
                       {groupItems.map(faq => {
                          const isExpanded = expandedFaq === faq.id;
                          return (
                            <div key={faq.id} className={`rounded-2xl border transition-colors ${isExpanded ? 'border-emerald-200 bg-emerald-50/50' : 'border-slate-100 bg-white hover:border-emerald-100'}`}>
                              <button 
                                onClick={() => setExpandedFaq(isExpanded ? null : faq.id)}
                                className="w-full flex items-center justify-between p-4 text-left focus:outline-none"
                              >
                                <span className="font900 text-sm text-slate-800 pr-4">{faq.title}</span>
                                <span className={`flex-shrink-0 text-emerald-600 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}>
                                  <HelpIcons.ChevronDown className="h-4 w-4" />
                                </span>
                              </button>
                              {isExpanded && (
                                <div className="px-4 pb-4 animate-fade-in text-sm font800 text-slate-600 leading-relaxed">
                                  {faq.answer}
                                </div>
                              )}
                            </div>
                          )
                       })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Quick Guide Section */}
          <section id="quick-guide" className="glass-panel p-6 shadow-sm">
             <div className="flex items-center gap-2 mb-6">
              <HelpIcons.BookOpen className="h-5 w-5 text-emerald-600" />
              <h2 className="text-xl font-black text-slate-900">Hướng dẫn nhanh</h2>
            </div>
            
            <div className="relative space-y-4 before:absolute before:inset-0 before:ml-[1.4rem] before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-200 before:to-transparent">
              {[
                { title: "Nhập hồ sơ", desc: "Cập nhật chiều cao, cân nặng, tuổi và mức độ vận động." },
                { title: "Tính toán chỉ số", desc: "Hệ thống tự động tính ra BMI, BMR, TDEE và lượng calories cần thiết." },
                { title: "Tạo thực đơn", desc: "Dựa vào thông tin của bạn để sinh thực đơn tăng cân thích hợp." },
                { title: "Kế hoạch & Nhật ký", desc: "Theo dõi, đổi món nếu cần và đánh dấu 'Đã ăn' hàng ngày." },
                { title: "Cập nhật định kỳ", desc: "Thay đổi cân nặng hàng tuần để tiếp tục lộ trình tăng cân hoàn hảo." }
              ].map((step, idx) => (
                <div key={idx} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                  <div className="flex items-center justify-center w-12 h-12 rounded-full border-4 border-white bg-emerald-100 text-emerald-600 font-black shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10">
                    {idx + 1}
                  </div>
                  <div className="w-[calc(100%-4rem)] md:w-[calc(50%-3rem)] rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-100 group-hover:ring-emerald-200 transition">
                    <h3 className="font900 text-slate-900 text-sm">{step.title}</h3>
                    <p className="font800 text-slate-500 text-xs mt-1 leading-relaxed">{step.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Quick Tips */}
          <section className="grid sm:grid-cols-2 gap-4">
             <div className="glass-panel p-5 bg-gradient-to-br from-amber-50 to-orange-50 border-orange-100">
                <div className="flex items-center gap-2 mb-2 text-orange-600">
                  <HelpIcons.Lightbulb className="h-5 w-5" />
                  <h3 className="font900 text-sm">Mẹo: Cập nhật cân nặng</h3>
                </div>
                <p className="text-xs font800 text-orange-800/80 leading-relaxed">Luôn nhớ cập nhật cân nặng của bạn định kỳ (ví dụ mỗi chủ nhật) để hệ thống điều chỉnh calories chính xác nhất.</p>
             </div>
             <div className="glass-panel p-5 bg-gradient-to-br from-blue-50 to-sky-50 border-blue-100">
                <div className="flex items-center gap-2 mb-2 text-blue-600">
                  <HelpIcons.Activity className="h-5 w-5" />
                  <h3 className="font900 text-sm">Mẹo: Nhật ký chính xác</h3>
                </div>
                <p className="text-xs font800 text-blue-800/80 leading-relaxed">Đánh dấu những món bạn đã ăn thực tế. Bạn có thể sửa khẩu phần nếu có thay đổi để biểu đồ luôn sát với thực tế nhất.</p>
             </div>
          </section>

        </div>

        {/* Right Column: Support Utilities */}
        <div className="space-y-6">
          
          {/* Categories Filter */}
          <div className="glass-panel p-5 shadow-sm">
             <p className="text-xs font900 uppercase tracking-wider text-emerald-700 mb-4">Danh mục hỗ trợ</p>
             <div className="flex flex-col gap-1.5">
               {categories.map(cat => (
                 <button
                    key={cat.id}
                    onClick={() => setActiveCategory(cat.id)}
                    className={`flex items-center justify-between px-4 py-2.5 rounded-xl text-sm font900 transition-colors ${activeCategory === cat.id ? 'bg-emerald-50 text-emerald-700' : 'text-slate-600 hover:bg-slate-50'}`}
                 >
                   {cat.label}
                   {activeCategory === cat.id && <HelpIcons.CheckCircle className="h-4 w-4 opacity-70" />}
                 </button>
               ))}
             </div>
          </div>

          {/* Feedback Form */}
          <div id="feedback-form" className="glass-panel p-5 shadow-sm relative overflow-hidden">
             <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/10 rounded-full blur-2xl -mr-10 -mt-10"></div>
             <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">Phản hồi / Báo lỗi</p>
             <h3 className="mt-2 text-lg font-black text-slate-950">Gặp vấn đề? Hãy cho chúng tôi biết.</h3>
             
             <form className="mt-5 space-y-4 relative z-10" onSubmit={submitReport}>
                <div>
                  <label className="block text-xs font900 text-slate-700 mb-1.5">Loại vấn đề</label>
                  <select
                    className="h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font800 text-slate-800 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition"
                    value={report.type}
                    onChange={(event) => setReport((current) => ({ ...current, type: event.target.value }))}
                  >
                    <option value="wrong_image">Ảnh món ăn sai</option>
                    <option value="abnormal_macro">Dữ liệu Macro sai</option>
                    <option value="not_working">Lỗi không sinh được thực đơn</option>
                    <option value="ui_glitch">Giao diện lỗi/Hỏng</option>
                    <option value="other">Vấn đề khác</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-xs font900 text-slate-700 mb-1.5">Vị trí / Tên món (nếu có)</label>
                  <input
                    className="h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font800 text-slate-800 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition"
                    list="food-report-options"
                    placeholder="VD: Phở bò, hoặc trang Tài khoản"
                    value={report.item}
                    onChange={(event) => setReport((current) => ({ ...current, item: event.target.value }))}
                  />
                  <datalist id="food-report-options">
                    {foods?.slice(0, 80).map((food) => (
                      <option key={food.id} value={food.name} />
                    ))}
                  </datalist>
                </div>

                <div>
                  <label className="block text-xs font900 text-slate-700 mb-1.5">Mô tả chi tiết</label>
                  <textarea
                    className="min-h-24 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font800 text-slate-800 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition resize-none"
                    placeholder="Vui lòng cung cấp chi tiết..."
                    value={report.description}
                    onChange={(event) => setReport((current) => ({ ...current, description: event.target.value }))}
                  />
                </div>

                <button type="submit" className="flex w-full items-center justify-center gap-2 h-11 rounded-xl bg-slate-950 px-4 text-sm font900 text-white hover:bg-slate-800 transition">
                  <HelpIcons.MessageSquare className="h-4 w-4" /> Gửi phản hồi
                </button>

                {submitted && (
                  <div className="rounded-xl bg-emerald-50 p-3 border border-emerald-100 animate-fade-in flex items-start gap-2">
                    <HelpIcons.CheckCircle className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" />
                    <p className="text-xs font900 text-emerald-800 leading-tight">Đã ghi nhận phản hồi cục bộ. Cảm ơn bạn!</p>
                  </div>
                )}
             </form>
          </div>

          {/* Quick Contacts */}
          <div className="grid gap-3">
             <button onClick={() => handleScrollTo('quick-guide')} className="flex items-center p-4 glass-panel hover:bg-slate-50 transition group shadow-sm text-left">
                <div className="flex bg-emerald-50 text-emerald-600 p-2.5 rounded-xl mr-3 group-hover:scale-110 transition-transform">
                  <HelpIcons.BookOpen className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="text-sm font900 text-slate-900">Xem nhanh hướng dẫn</h4>
                  <p className="text-xs font800 text-slate-500">Các bước chuẩn để bắt đầu</p>
                </div>
             </button>
             <button onClick={() => { setActiveCategory("profile"); handleScrollTo("help-panel"); }} className="flex items-center p-4 glass-panel hover:bg-slate-50 transition group shadow-sm text-left">
                <div className="flex bg-orange-50 text-orange-600 p-2.5 rounded-xl mr-3 group-hover:scale-110 transition-transform">
                  <HelpIcons.AlertCircle className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="text-sm font900 text-slate-900">Kiểm tra Hồ sơ & BMI</h4>
                  <p className="text-xs font800 text-slate-500">Sửa lỗi không nhận thực đơn</p>
                </div>
             </button>
          </div>

          {/* System Status Mock */}
          <div className="glass-panel p-5 shadow-sm">
             <div className="flex items-center gap-2 mb-4">
                <HelpIcons.Activity className="h-5 w-5 text-slate-900" />
                <h3 className="text-sm font900 text-slate-900">Tình trạng hệ thống</h3>
             </div>
             <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font800 text-slate-600">Dữ liệu món ăn</span>
                  <span className="flex items-center gap-1.5 text-xs font900 text-emerald-700 bg-emerald-50 px-2 py-1 rounded-md"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>Sẵn sàng</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font800 text-slate-600">Thuật toán sinh menu</span>
                  <span className="flex items-center gap-1.5 text-xs font900 text-emerald-700 bg-emerald-50 px-2 py-1 rounded-md"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>Hoạt động</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font800 text-slate-600">Đồng bộ Nhật ký</span>
                  <span className="flex items-center gap-1.5 text-xs font900 text-emerald-700 bg-emerald-50 px-2 py-1 rounded-md"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>Hoạt động</span>
                </div>
             </div>
          </div>

        </div>
      </div>
    </div>
  );
}

function NotificationPanel({ progress, summary, validation }) {
  const isOverTarget = progress >= 100;
  return (
    <section id="notifications-panel" className="glass-panel scroll-mt-28 p-5">
      <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">
        Thông báo
      </p>
      <h2 className="mt-2 text-xl font-black text-slate-950">Nhắc nhở hôm nay</h2>
      <div className="mt-5 space-y-3">
        <NoticeRow
          tone={isOverTarget ? "orange" : "green"}
          title={validation?.isValid ? "Thực đơn đạt mục tiêu" : "Cần điều chỉnh thực đơn"}
          text={
            validation?.isValid
              ? "Thực đơn phù hợp với mục tiêu hôm nay."
              : validation?.messages?.[0] || `Bạn đang đạt ${progress}%, nên tăng khẩu phần hoặc tạo lại thực đơn.`
          }
        />
        <NoticeRow
          tone="blue"
          title={`BMI ${summary.bmi} - ${summary.bmiStatus}`}
          text="Theo dõi cân nặng hằng tuần để điều chỉnh mức tăng phù hợp."
        />
      </div>
    </section>
  );
}

function HelpPanel() {
  return (
    <section id="help-panel" className="glass-panel scroll-mt-28 p-5">
      <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">
        Hỗ trợ
      </p>
      <h2 className="mt-2 text-xl font-black text-slate-950">Trợ giúp nhanh</h2>
      <div className="mt-5 space-y-3">
        <NoticeRow
          tone="green"
          title="Cập nhật hồ sơ"
          text="Dùng nút Chỉnh hồ sơ để nhập lại cân nặng, chiều cao hoặc mục tiêu."
        />
        <NoticeRow
          tone="blue"
          title="Xuất báo cáo"
          text="Tải CSV để lưu calories, BMI, BMR, TDEE và macro mục tiêu."
        />
      </div>
    </section>
  );
}

function NoticeRow({ tone, title, text }) {
  const toneClass = {
    green: "bg-emerald-500",
    blue: "bg-sky-500",
    orange: "bg-orange-400",
  }[tone] || "bg-emerald-500";

  return (
    <div className="rounded-2xl bg-white/80 p-4 ring-1 ring-slate-100">
      <div className="flex items-center gap-3">
        <span className={`h-2.5 w-2.5 rounded-full ${toneClass}`} />
        <strong className="text-sm font900 text-slate-950">{title}</strong>
      </div>
      <p className="mt-2 text-sm font700 leading-6 text-slate-500">{text}</p>
    </div>
  );
}

function MacroMini({ label, value, color }) {
  return (
    <div className="rounded-2xl bg-slate-50 p-3 text-center ring-1 ring-slate-100">
      <div className={`mx-auto h-2 w-10 rounded-full ${color}`} />
      <div className="mt-3 text-2xl font-black text-slate-950">{value}g</div>
      <div className="mt-1 text-xs font800 uppercase tracking-[0.12em] text-slate-500">
        {label}
      </div>
    </div>
  );
}

function MealStatusPill({ status }) {
  const classes = {
    unconfirmed: "bg-slate-100 text-slate-600",
    complete: "bg-emerald-50 text-emerald-800",
    lowProtein: "bg-sky-50 text-sky-800",
    lowCalories: "bg-amber-50 text-amber-800",
    overTarget: "bg-orange-50 text-orange-800",
  };
  const labels = {
    unconfirmed: "Chưa xác nhận",
    complete: "Hoàn thành",
    lowProtein: "Thiếu đạm",
    lowCalories: "Thiếu kcal",
    overTarget: "Vượt mục tiêu",
  };
  return (
    <span className={`mt-2 inline-flex rounded-full px-3 py-1 text-xs font900 ${classes[status] || classes.unconfirmed}`}>
      {labels[status] || labels.unconfirmed}
    </span>
  );
}

function MealBalanceChips({ balance }) {
  const labels = {
    starch: "Tinh bột",
    protein: "Đạm",
    produce: "Rau/trái cây",
    energy: "Món phụ năng lượng",
  };
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {Object.entries(labels).map(([role, label]) => (
        <span
          key={role}
          className={`rounded-full px-3 py-1.5 text-xs font900 ${balance.roles[role] ? "bg-emerald-50 text-emerald-800" : "bg-slate-100 text-slate-500"}`}
        >
          {label}
        </span>
      ))}
    </div>
  );
}

function ProgressMetric({ label, value, target, unit }) {
  const percent = Math.min(100, Math.round((Number(value || 0) / Math.max(Number(target || 1), 1)) * 100));
  return (
    <article className="glass-panel p-5">
      <p className="text-xs font900 uppercase tracking-[0.18em] text-emerald-700">{label}</p>
      <div className="mt-3 text-2xl font-black text-slate-950">
        {value}<span className="text-sm font900 text-slate-500"> / {target}{unit}</span>
      </div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-emerald-500" style={{ width: `${percent}%` }} />
      </div>
    </article>
  );
}

function buildEligibilityStatus(profile, summary) {
  const weight = Number(profile.weight);
  const height = Number(profile.height);
  const targetWeight = profile.target_weight === "" || profile.target_weight == null ? null : Number(profile.target_weight);
  const validWeight = Number.isFinite(weight) && weight >= 20 && weight <= 250;
  const validHeight = Number.isFinite(height) && height >= 100 && height <= 230;
  if (!validWeight || !validHeight) {
    return {
      bmi: null,
      status: "unknown",
      statusLabel: "Dữ liệu không hợp lệ",
      eligible: false,
      reason: "Không đủ dữ liệu chiều cao/cân nặng hợp lệ để sinh thực đơn.",
      profile: { weight: validWeight ? weight : 0, height: validHeight ? height : 0, targetWeight },
    };
  }

  const bmi = round(weight / ((height / 100) ** 2), 1);
  const status = bmi < 18.5 ? "underweight" : bmi < 25 ? "normal" : bmi < 30 ? "overweight" : "obese";
  const labels = {
    underweight: "Thiếu cân",
    normal: "Bình thường",
    overweight: "Thừa cân",
    obese: "Béo phì",
  };
  return {
    bmi,
    status,
    statusLabel: labels[status],
    eligible: bmi < 18.5,
    reason: bmi < 18.5 ? "Được phép sinh thực đơn tăng cân lành mạnh." : "Không thuộc phạm vi hệ thống dành riêng cho người thiếu cân.",
    profile: { weight, height, targetWeight: Number.isFinite(targetWeight) ? targetWeight : null, bmiStatus: summary.bmiStatus },
  };
}

function buildDataWarnings(profile, summary, validation, target) {
  const warnings = [];
  const weight = Number(profile.weight);
  const height = Number(profile.height);
  if (!Number.isFinite(weight) || weight < 20 || weight > 250) warnings.push("Cân nặng nằm ngoài ngưỡng hợp lý (20-250kg), cần kiểm tra lại hồ sơ.");
  if (!Number.isFinite(height) || height < 100 || height > 230) warnings.push("Chiều cao nằm ngoài ngưỡng hợp lý (100-230cm), cần kiểm tra lại hồ sơ.");
  if (Number.isFinite(summary.bmi) && (summary.bmi < 10 || summary.bmi > 60)) warnings.push(`BMI ${summary.bmi} bất thường, có thể do nhập sai chiều cao/cân nặng.`);
  if (validation.totalCalories > Math.max(target.maxCalories * 1.4, 5000)) warnings.push("Tổng kcal thực đơn đang vượt ngưỡng hợp lý, cần kiểm tra dữ liệu khẩu phần hoặc macro.");
  if (validation.totalProtein > Math.max(target.proteinTarget * 1.8, 220)) warnings.push("Protein đang rất cao so với mục tiêu, cần kiểm tra món đạm hoặc khẩu phần.");
  if (validation.totalFat > Math.max(target.fatTarget * 1.8, 180)) warnings.push("Fat đang rất cao so với mục tiêu, cần kiểm tra món nhiều dầu/hạt/bơ.");
  if (validation.totalCarbs > Math.max(target.carbTarget * 1.8, 700)) warnings.push("Carbs đang rất cao so với mục tiêu, cần kiểm tra nhóm tinh bột.");
  return warnings;
}

function buildProfileSoftErrors(profile) {
  const errors = {};
  const weight = Number(profile.weight);
  const height = Number(profile.height);
  const targetWeight = profile.target_weight === "" || profile.target_weight == null ? null : Number(profile.target_weight);
  if (!Number.isFinite(weight) || weight < 20 || weight > 250) errors.weight = "Cân nặng nên trong khoảng 20-250kg";
  if (!Number.isFinite(height) || height < 100 || height > 230) errors.height = "Chiều cao nên trong khoảng 100-230cm";
  if (targetWeight !== null && (!Number.isFinite(targetWeight) || targetWeight < 20 || targetWeight > 250)) errors.target_weight = "Mục tiêu cân nặng không hợp lệ";
  if (Number.isFinite(targetWeight) && Number.isFinite(weight) && targetWeight <= weight) errors.target_weight = "Mục tiêu nên lớn hơn cân nặng hiện tại";
  return errors;
}

function buildJournalMealRow(meal, entries, manualItems) {
  const suggested = sumItems(meal.items);
  const actual = meal.items.reduce((acc, item) => {
    const entry = entries[`${meal.title}-${item.id}`] || {};
    const status = entry.status || "suggested";
    if (!["eaten", "partial"].includes(status)) return acc;
    const scaled = scaleItemByPortion(item, entry);
    return addTotals(acc, scaled);
  }, { calories: 0, protein: 0, fat: 0, carbs: 0 });
  const mealManualItems = manualItems.filter((item) => item.mealTitle === meal.title);
  mealManualItems.forEach((item) => addTotals(actual, item));
  const roundedActual = roundTotals(actual);
  const confirmedCount = meal.items.filter((item) => ["eaten", "partial"].includes(entries[`${meal.title}-${item.id}`]?.status)).length + mealManualItems.length;
  const status = getMealLogStatus(roundedActual, suggested, confirmedCount);
  return {
    ...meal,
    suggested,
    actual: roundedActual,
    status,
    manualItems: mealManualItems,
  };
}

function calculateConsumedNutrition(meals, mealLog) {
  const rows = (meals || []).map((meal) => buildJournalMealRow(meal, mealLog?.entries || {}, mealLog?.manualItems || []));
  return sumJournalRows(rows);
}

function getMealLogStatus(actual, suggested, confirmedCount) {
  if (!confirmedCount) return "unconfirmed";
  if (actual.calories > suggested.calories * 1.15) return "overTarget";
  if (actual.calories >= suggested.calories * 0.9) return "complete";
  if (actual.protein < suggested.protein * 0.65) return "lowProtein";
  return "lowCalories";
}

function sumJournalRows(rows) {
  return roundTotals(rows.reduce((acc, meal) => addTotals(acc, meal.actual), { calories: 0, protein: 0, fat: 0, carbs: 0 }));
}

function scaleItemByPortion(item, entry) {
  const baseGrams = Number(item.servingGrams || 100) || 100;
  const grams = Number(entry.grams || baseGrams);
  const ratio = Number.isFinite(grams) && grams > 0 ? grams / baseGrams : 1;
  return {
    calories: Number(item.calories || 0) * ratio,
    protein: Number(item.protein || 0) * ratio,
    fat: Number(item.fat || 0) * ratio,
    carbs: Number(item.carbs || 0) * ratio,
  };
}

function sumItems(items) {
  return roundTotals((items || []).reduce((acc, item) => addTotals(acc, item), { calories: 0, protein: 0, fat: 0, carbs: 0 }));
}

function addTotals(acc, item) {
  acc.calories += Number(item.calories || item.kcal || 0);
  acc.protein += Number(item.protein || 0);
  acc.fat += Number(item.fat || 0);
  acc.carbs += Number(item.carbs || 0);
  return acc;
}

function roundTotals(totals) {
  return {
    calories: round(totals.calories),
    protein: round(totals.protein),
    fat: round(totals.fat),
    carbs: round(totals.carbs),
  };
}

function expectedItemsPerMeal(value) {
  return { simple: 3, balanced: 4, full: 5 }[value] || 4;
}

function analyzeMealBalance(items, expectedCount) {
  const roles = { starch: false, protein: false, produce: false, energy: false };
  items.forEach((item) => {
    roles[getFoodRole(item)] = true;
  });
  const warnings = [];
  if (!roles.starch) warnings.push("Thiếu nhóm tinh bột.");
  if (!roles.protein) warnings.push("Thiếu nhóm đạm.");
  if (!roles.produce) warnings.push("Thiếu rau/củ hoặc trái cây.");
  if (expectedCount >= 4 && !roles.energy) warnings.push("Có thể thêm món phụ tăng năng lượng.");
  if (items.length !== expectedCount) warnings.push(`Số món hiện là ${items.length}/${expectedCount}.`);
  const roleCounts = items.reduce((acc, item) => {
    const role = getFoodRole(item);
    acc[role] = (acc[role] || 0) + 1;
    return acc;
  }, {});
  Object.entries(roleCounts).forEach(([role, count]) => {
    if (count > 2) warnings.push(`Nhóm ${roleLabel(role)} xuất hiện ${count} lần trong bữa.`);
  });
  return { roles, warnings };
}

function getFoodRole(item) {
  const text = stripAccents(`${item.category || ""} ${item.subCategory || ""} ${item.foodGroup || ""} ${item.name || ""}`).toLowerCase();
  if (/(starch|grain|tinh bot|ngu coc|rice|com|bread|banh mi|oat|potato|khoai|noodle|pasta)/.test(text)) return "starch";
  if (/(protein|meat|seafood|plant_protein|dam|thit|ca |hai san|trung|egg|tofu|dau phu|dau hu|soy|bean)/.test(text)) return "protein";
  if (/(vegetable|fruit|rau|cu|trai cay|banana|chuoi|apple|tao|salad)/.test(text)) return "produce";
  if (/(drink_natural|do uong|nuoc dua|healthy_fat|fat|nuts|hat|peanut|dau phong|butter|bo dau phong|avocado|bo |milk|sua|yogurt|sua chua)/.test(text)) return "energy";
  return "energy";
}

function roleLabel(role) {
  return { starch: "tinh bột", protein: "đạm", produce: "rau/trái cây", energy: "món phụ năng lượng" }[role] || role;
}

function buildSuggestionReason(item) {
  const role = getFoodRole(item);
  const categoryKey = String(item.technicalCategory || item.subCategory || "").toLowerCase();
  if (categoryKey === "drink_natural") {
    return "Bổ sung năng lượng/nước, không thay thế hoàn toàn trái cây tươi.";
  }
  if (categoryKey === "dessert_sweets" || categoryKey === "sweet_spread") {
    return "Bổ sung năng lượng nhanh, nên dùng lượng vừa phải.";
  }
  const reasons = {
    starch: "Cung cấp tinh bột để tăng năng lượng đều trong ngày, phù hợp mục tiêu tăng cân lành mạnh.",
    protein: "Bổ sung đạm giúp hỗ trợ tăng cân có chất lượng và duy trì khối cơ.",
    produce: "Bổ sung rau/củ hoặc trái cây để cân bằng vi chất và chất xơ trong bữa.",
    energy: "Là món phụ tăng năng lượng, nên dùng khẩu phần vừa phải để tránh dồn quá nhiều kcal.",
  };
  return reasons[role] || "Món được backend chọn từ dataset hợp lệ cho thực đơn hiện tại.";
}

function findEnergySupportFood(meals) {
  const allItems = meals.flatMap((meal) => meal.items);
  return allItems.find((item) => getFoodRole(item) === "energy") || allItems.find((item) => item.calories >= 250) || null;
}

function buildFoodGroupCounts(meals) {
  const foods = meals.flatMap((meal) => meal.items);
  const counts = foods.reduce((acc, item) => {
    const group = item.foodGroup || item.category || "Khác";
    acc[group] = (acc[group] || 0) + 1;
    return acc;
  }, {});
  const max = Math.max(...Object.values(counts), 1);
  return Object.entries(counts).map(([label, count]) => ({ label, count, percent: Math.round((count / max) * 100) }));
}

function buildComplianceRows(validation) {
  return [
    { label: "Calories", value: validation.totalCalories, target: Math.max(validation.totalCalories, 1), unit: "kcal" },
    { label: "Protein", value: validation.totalProtein, target: Math.max(validation.totalProtein, 1), unit: "g" },
    { label: "Số cảnh báo", value: validation.isValid ? 0 : validation.messages.length, target: Math.max(validation.messages.length, 1), unit: "" },
  ];
}

function buildMacroComment(macroData) {
  const values = [
    ["protein", macroData.protein],
    ["fat", macroData.fat],
    ["carbs", macroData.carbs],
  ].sort((a, b) => b[1] - a[1]);
  return `Macro cao nhất hiện là ${values[0][0]} (${values[0][1]}g). Nên đối chiếu với mục tiêu cá nhân để tránh thực đơn lệch quá nhiều về một nhóm.`;
}

function uniqueValues(values) {
  return Array.from(new Set(values.filter(Boolean)));
}

function formatStat(value) {
  return value == null ? "Không đủ dữ liệu" : value.toLocaleString("vi-VN");
}

function noticeToneClass(tone) {
  return {
    green: "bg-emerald-500",
    blue: "bg-sky-500",
    orange: "bg-orange-400",
    amber: "bg-amber-400",
    red: "bg-rose-500",
  }[tone] || "bg-emerald-500";
}

function filterNotifications(notifications, readMap, activeFilter) {
  if (!Array.isArray(notifications)) return [];
  if (activeFilter === "unread") return notifications.filter((item) => !readMap[item.id]);
  if (activeFilter === "read") return notifications.filter((item) => readMap[item.id]);
  if (activeFilter === "reminder") return notifications.filter((item) => item.category === "reminder");
  if (activeFilter === "warning") return notifications.filter((item) => item.category === "warning");
  if (activeFilter === "profile") return notifications.filter((item) => item.category === "profile");
  return notifications;
}

function buildNotifications(progress, summary, validation, dataWarnings) {
  const safeProgress = Number.isFinite(Number(progress)) ? Number(progress) : 0;
  const safeSummary = summary || fallbackSummary;
  const safeValidation = validation || { totalProtein: 0, totalCalories: 0, messages: [], isValid: false };
  const safeWarnings = Array.isArray(dataWarnings) ? dataWarnings : [];
  const notices = [
    {
      id: "meal-reminder",
      type: "nhắc bữa ăn",
      tone: "green",
      category: "reminder",
      icon: "utensils",
      title: "Theo dõi bữa ăn hôm nay",
      text: "Vào Nhật ký ăn uống để đánh dấu món đã ăn và chỉnh khẩu phần thực tế.",
      actionLabel: "Mở nhật ký",
      actionTarget: "journal",
      timeLabel: "Hôm nay",
    },
    {
      id: "weight-update",
      type: "nhắc cập nhật cân nặng",
      tone: "blue",
      category: "profile",
      icon: "scale",
      title: `BMI ${safeSummary.bmi} - ${safeSummary.bmiStatus}`,
      text: "Cập nhật cân nặng định kỳ để hệ thống tính lại nhu cầu năng lượng.",
      actionLabel: "Cập nhật hồ sơ",
      actionTarget: "account",
      timeLabel: "Hôm nay",
    },
  ];
  if (safeProgress > 0 && safeProgress < 90) {
    notices.push({
      id: "low-calorie",
      type: "cảnh báo kcal",
      tone: "orange",
      category: "warning",
      icon: "flame",
      title: "Kcal đang thấp hơn mục tiêu",
      text: safeValidation?.messages?.[0] || `Bạn đang đạt khoảng ${safeProgress}% mục tiêu kcal.`,
      actionLabel: "Xem thực đơn",
      actionTarget: "meal-plan",
      timeLabel: "Hôm nay",
    });
  }
  if (safeProgress > 0 && safeValidation.totalProtein < 60) {
    notices.push({
      id: "low-protein",
      type: "cảnh báo protein",
      tone: "orange",
      category: "warning",
      icon: "alert",
      title: "Protein cần được theo dõi",
      text: "Nếu bữa ăn thiếu đạm, hãy ưu tiên món đạm phù hợp từ backend.",
      actionLabel: "Xem thực đơn",
      actionTarget: "meal-plan",
      timeLabel: "Hôm nay",
    });
  }
  safeWarnings.forEach((warning, index) => {
    const tone = /nghiem|nguy hiem|critical|error|bad/i.test(warning) ? "red" : "orange";
    notices.push({
      id: `data-warning-${index}`,
      type: "cảnh báo dữ liệu bất thường",
      tone,
      category: "warning",
      icon: "alert",
      title: "Kiểm tra dữ liệu đầu vào",
      text: warning,
      actionLabel: "Xem thực đơn",
      actionTarget: "meal-plan",
      timeLabel: "Hôm nay",
    });
  });
  if (safeValidation.isValid && safeProgress >= 95) {
    notices.push({
      id: "goal-achievement",
      type: "thành tích đạt mục tiêu",
      tone: "green",
      category: "success",
      icon: "check",
      title: "Thực đơn đạt mục tiêu hôm nay",
      text: "Kcal và macro đang phù hợp với mục tiêu tăng cân lành mạnh.",
      actionLabel: "Xem tổng quan",
      actionTarget: "overview",
      timeLabel: "Hôm nay",
    });
  }
  return notices;
}

function buildSummary(result, consumedNutrition = { calories: 0 }) {
  if (!result?.target) return fallbackSummary;
  return {
    targetCalories: round(result.target.calories),
    eatenCalories: round(consumedNutrition.calories),
    bmr: round(result.target.bmr),
    tdee: round(result.target.tdee),
    bmi: round(result.target.bmi, 1),
    bmiStatus: result.target.bmi_status || "Đang theo dõi",
    medicalWarning: result.target.medical_warning || "",
    protein: round(result.target.protein),
    fat: round(result.target.fat),
    carbs: round(result.target.carbs),
  };
}

function buildEffectiveTarget(result, fallbackTarget) {
  if (!result?.target) return fallbackTarget;
  const targetCalories = round(result.target.calories || fallbackTarget.targetCalories);
  const proteinTarget = round(result.target.protein || fallbackTarget.proteinTarget);
  const fatTarget = round(result.target.fat || fallbackTarget.fatTarget);
  const carbTarget = round(result.target.carbs || fallbackTarget.carbTarget);

  return {
    ...fallbackTarget,
    bmr: round(result.target.bmr || fallbackTarget.bmr),
    tdee: round(result.target.tdee || fallbackTarget.tdee),
    targetCalories,
    proteinTarget,
    fatTarget,
    carbTarget,
    minCalories: round(result.evaluation?.validation?.min_calories || targetCalories * 0.85),
    maxCalories: round(targetCalories * 1.15),
  };
}

function buildWeeklyCalories(result, summary) {
  const source = result?.calorie_history || result?.weekly_calories || result?.history?.calories || [];
  if (Array.isArray(source) && source.length) {
    return source.map((item, index) => ({
      day: item.day || item.date || `D${index + 1}`,
      calories: round(item.calories ?? item.kcal ?? item.value),
      target: round(item.target ?? summary.targetCalories),
    }));
  }

  return [
    {
      day: "Hôm nay",
      calories: round(summary.eatenCalories),
      target: round(summary.targetCalories),
    },
  ];
}

function buildMeals(result, dietType = "balanced", profileSettings = {}) {
  if (!result?.meal_plan) return [];
  return Object.entries(result.meal_plan).map(([mealKey, items]) => ({
    title: mealLabels[mealKey] || mealKey,
    accent: mealAccents[mealKey] || "green",
    items: filterFoodsByDietType(
      (items || [])
      .filter(isUiMenuEligible)
      .map((item, index) => mapFoodPayload(item, `${mealKey}-${index}`, mealLabels[mealKey] || mealKey)),
      dietType,
    ).filter((item) => !isFoodDisliked(item, profileSettings)),
  }));
}

function buildFoodCatalog(result, meals) {
  const byId = new Map();
  meals.forEach((meal) => {
    meal.items.forEach((item) => {
      const current = byId.get(item.id);
      if (current) {
        byId.set(item.id, {
          ...current,
          mealTitles: uniqueValues([...(current.mealTitles || []), meal.title]),
        });
      } else {
        byId.set(item.id, { ...item, mealTitle: meal.title, mealTitles: [meal.title] });
      }
    });
  });

  return Array.from(byId.values());
}

function buildDatasetStats(result, foodCatalog) {
  const stats = result?.dataset_stats || result?.evaluation?.dataset_stats || {};
  return {
    total: stats.total_items ?? stats.total ?? null,
    eligible: stats.menu_eligible ?? stats.eligible ?? null,
    excluded: stats.excluded ?? stats.rejected ?? null,
    updatedAt: stats.updated_at || stats.last_updated || "Không đủ dữ liệu",
    visible: foodCatalog.length,
  };
}

function normalizeFoodCategory(category, name = "") {
  const current = String(category || "").trim().toLowerCase() || "other";
  const original = String(name || "").toLowerCase();
  const text = stripAccents(name).toLowerCase();
  if (original.includes("mứt") || text.startsWith("mut") || text.includes(" mut ")) return "dessert_sweets";
  if (/(nuoc cam|nuoc dua|nuoc ep|nuoc trai cay|orange juice|juice)/.test(text)) return "drink_natural";
  if (text.includes("kem lua mi") || text.includes("cream of wheat")) return "starch_grain";
  if (text.includes("do an nhanh") || text.includes("fast food")) return "other";
  if (text.includes("bac ha")) return "vegetable_herb";
  if (text.includes("khoai tay")) return "starch_tuber";
  if (text.includes("ngu coc")) return "starch_grain";
  if (text.includes("banh")) {
    if (text.includes("banh mi") || current === "starch_grain" || current === "grain") return "starch_grain";
    return "dessert_sweets";
  }
  return current;
}

function mapCategoryLabel(category, fallback = "") {
  const normalized = String(category || "").trim().toLowerCase();
  const labels = {
    starch_grain: "Tinh bột · Ngũ cốc",
    starch_tuber: "Tinh bột · Củ",
    protein_seafood: "Đạm · Hải sản",
    protein_meat: "Đạm · Thịt",
    protein_plant: "Đạm thực vật",
    plant_protein: "Đạm thực vật",
    vegetable: "Rau củ",
    vegetable_herb: "Rau củ · Rau gia vị",
    fruit: "Trái cây",
    dairy: "Sữa",
    drink_natural: "Đồ uống tự nhiên",
    dessert_sweets: "Bánh/ngọt",
    sweet_spread: "Bánh/ngọt",
    fats_good: "Chất béo tốt",
    healthy_fat: "Chất béo tốt",
    healthy_fat_nuts: "Chất béo tốt",
    egg: "Đạm · Trứng",
    grain: "Tinh bột · Ngũ cốc",
    meat: "Đạm · Thịt",
  };
  return labels[normalized] || fallback || "Khác";
}

function accentClass(accent) {
  if (accent === "blue") return "bg-sky-500";
  if (accent === "orange") return "bg-orange-400";
  return "bg-emerald-500";
}

function mapFoodPayload(item, fallbackId, mealTitle = "") {
  const name = item.dish_name_vi || item.name || "Món ăn";
  const cleanCategory = normalizeFoodCategory(
    item.clean_category || item.category || item.normalized_category || "",
    name,
  );
  const displayCategory = mapCategoryLabel(cleanCategory, item.food_group || item.foodGroup);
  const imageUrl = typeof item.image_url === "string" ? item.image_url.trim() : "";
  const id = item.food_id || item.id || fallbackId;
  const imageSourceType = item.image_source_type
    || (imageUrl.includes("/images/placeholders/") ? "placeholder" : imageUrl ? "real_food_photo" : "placeholder");
  const imageBadge = item.image_badge || (imageSourceType === "placeholder" ? "Ảnh minh họa" : null);
  const imageVerified = item.image_verified === true || item.image_verified === "true";
  return {
    id,
    foodId: id,
    name,
    type: displayCategory,
    category: displayCategory,
    subCategory: cleanCategory,
    technicalCategory: cleanCategory,
    mealRole: item.meal_role || item.culinary_role || "",
    reason: item.reason || "",
    status: item.status || "suggested",
    image: imageUrl || defaultFoodImage,
    fallbackImage: defaultFoodImage,
    imageAlt: item.image_alt || `Ảnh món ${name}`,
    imageSourceType,
    imageVerified,
    imageBadge,
    imageMissing: imageSourceType === "placeholder",
    calories: round(item.kcal ?? item.calories ?? item.kcal_per_serving_clean),
    protein: round(item.protein ?? item.protein_per_serving_clean),
    fat: round(item.fat ?? item.fat_per_serving_clean),
    carbs: round(item.carbs ?? item.carbs_per_serving_clean),
    servingGrams: round(item.quantity_g ?? item.serving_grams ?? item.recommended_serving_g),
    servingDisplay: item.serving_display || item.portion_display || "",
    foodGroup: displayCategory,
    imageQuery: item.image_query || item.image_search_query_vi || "",
    imageRequirement: item.image_requirement || "",
    qualityFlags: item.quality_flags || "",
    menuEligible: item.menu_eligible !== false && item.menu_eligible !== "false",
    mealTitle,
  };
}

function filterFoodsByDietType(foods, dietType, minItems = 0) {
  if (!isEatCleanDiet(dietType)) return foods;
  const preferred = foods.filter((item) => !isBlockedByEatClean(item));
  if (preferred.length >= minItems) return preferred;
  return [
    ...preferred,
    ...foods
      .filter(isBlockedByEatClean)
      .map((item) => ({ ...item, dietFallback: true, score: Number(item.score || 0) - 1 })),
  ];
}

function isEatCleanDiet(dietType) {
  const normalized = stripAccents(dietType || "balanced").toLowerCase().replace(/[_/]+/g, " ");
  return ["eat clean", "clean", "balanced", "can bang"].some((term) => normalized.includes(term));
}

function isBlockedByEatClean(item) {
  const text = stripAccents(`${item.name || ""} ${item.original_name || ""} ${item.category || ""} ${item.foodGroup || ""}`).toLowerCase();
  const blockedTerms = [
    "xuc xich",
    "sausage",
    "hun khoi",
    "smoked",
    "do an nhanh",
    "fast food",
    "processed",
    "chien ran nhieu dau",
    "fried",
    "mut",
    "jam",
    "jelly",
    "nuoc ngot",
    "soft drink",
    "soda",
    "banh keo ngot",
    "mon ngot nhieu duong",
    "sugary",
    "candy",
  ];
  return blockedTerms.some((term) => text.includes(term));
}

function toMealPlanPayload(item, status = "suggested") {
  return {
    food_id: String(item.foodId || item.id || item.name),
    original_name: item.originalName || item.name,
    name: item.name,
    image_url: item.image || defaultFoodImage,
    image_alt: item.imageAlt || `Ảnh món ${item.name}`,
    image_source_type: item.imageSourceType || (item.imageMissing ? "placeholder" : "real_food_photo"),
    image_verified: Boolean(item.imageVerified),
    image_badge: item.imageBadge || (item.imageMissing ? "Ảnh minh họa" : null),
    category: item.technicalCategory || item.subCategory || item.category,
    normalized_category: item.technicalCategory || item.subCategory || item.category,
    food_group: item.foodGroup || item.category,
    meal_role: item.mealRole || "",
    culinary_role: item.mealRole || "",
    quantity_g: item.servingGrams || null,
    serving_grams: item.servingGrams || null,
    serving_display: item.servingDisplay || "",
    portion_display: item.servingDisplay || "",
    kcal: item.calories,
    calories: item.calories,
    protein: item.protein,
    fat: item.fat,
    carbs: item.carbs,
    reason: item.reason || buildSuggestionReason(item),
    status,
    quality_flags: item.qualityFlags || "",
    score: Number(item.score || 0),
    menu_eligible: item.menuEligible !== false,
  };
}

function isFoodDisliked(item, profileSettings = {}) {
  const dislikedFoods = profileSettings.disliked_foods || [];
  const dislikedGroups = profileSettings.disliked_food_groups || [];
  return (
    dislikedFoods.some((term) => foodMatchesTerm(item, term))
    || dislikedGroups.some((term) => foodMatchesGroup(item, term))
  );
}

function foodMatchesTerm(item, term) {
  const normalizedTerm = stripAccents(term || "").toLowerCase().trim();
  if (!normalizedTerm) return false;
  const text = stripAccents(`${item.foodId || item.food_id || item.id || ""} ${item.name || ""} ${item.dish_name_vi || ""}`).toLowerCase();
  return text.includes(normalizedTerm);
}

function foodMatchesGroup(item, term) {
  const normalizedTerm = stripAccents(term || "").toLowerCase().trim();
  if (!normalizedTerm) return false;
  const text = stripAccents(`${item.technicalCategory || ""} ${item.subCategory || ""} ${item.normalized_category || ""} ${item.category || ""} ${item.foodGroup || ""} ${item.food_group || ""}`).toLowerCase();
  const compactText = text.trim();
  return Boolean(compactText) && (compactText.includes(normalizedTerm) || normalizedTerm.includes(compactText));
}

function removeDislikedFromResult(current, food, dislikeType) {
  if (!current?.meal_plan) return current;
  const nextMealPlan = Object.fromEntries(
    Object.entries(current.meal_plan).map(([mealKey, items]) => [
      mealKey,
      (items || []).filter((item) => {
        const mapped = mapFoodPayload(item, item.food_id || item.id || item.name);
        return dislikeType === "group"
          ? !foodMatchesGroup(mapped, food.technicalCategory || food.subCategory || food.foodGroup || food.category)
          : !foodMatchesTerm(mapped, food.foodId || food.id || food.name);
      }),
    ]),
  );
  return { ...current, meal_plan: nextMealPlan };
}

function loadStoredList(storageKey) {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(storageKey);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter(Boolean) : [];
  } catch {
    return [];
  }
}

function persistDislikedProfile(dislikedFoods, dislikedFoodGroups) {
  const foods = uniqueValues((dislikedFoods || []).filter(Boolean));
  const groups = uniqueValues((dislikedFoodGroups || []).filter(Boolean));
  if (typeof window !== "undefined") {
    try {
      window.localStorage.setItem(dislikedFoodsStorageKey, JSON.stringify(foods));
      window.localStorage.setItem(dislikedFoodGroupsStorageKey, JSON.stringify(groups));
    } catch {
      // Local storage may be unavailable in locked-down browsers; backend save still runs.
    }
  }
  saveUserProfile({ disliked_foods: foods, disliked_food_groups: groups }).catch(() => {});
}

function isUiMenuEligible(item) {
  if (item?.menu_eligible === false || item?.menu_eligible === "false") return false;
  const flags = String(item?.quality_flags || "").toLowerCase();
  const severeFlags = ["abnormal_macro", "raw_ingredient", "invalid_name", "wrong_category", "generic_name"];
  return !severeFlags.some((flag) => flags.includes(flag));
}

function stripAccents(value) {
  return String(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D");
}

function sumMealPlan(mealPlan, key) {
  if (!mealPlan) return 0;
  return Object.values(mealPlan).reduce(
    (total, items) => total + items.reduce((sum, item) => sum + Number(item[key] || 0), 0),
    0,
  );
}

function validateProfile(formState) {
  const errors = {};
  const weight = Number(formState.weight);
  const height = Number(formState.height);
  const age = formState.age === "" ? null : Number(formState.age);

  if (!Number.isFinite(weight) || weight < 20 || weight > 250) errors.weight = "Vui lòng nhập cân nặng hợp lệ (20-250kg)";
  if (!Number.isFinite(height) || height < 100 || height > 230) errors.height = "Vui lòng nhập chiều cao hợp lệ (100-230cm)";
  if (!errors.weight && !errors.height && Number.isFinite(weight) && Number.isFinite(height)) {
    const bmi = weight / ((height / 100) ** 2);
    if (bmi >= 18.5) {
      errors.weight = `BMI hiện tại ${bmi.toFixed(1)}. Hệ thống chỉ tạo thực đơn cho người thiếu cân (BMI < 18.5).`;
    }
  }
  if (age !== null && (!Number.isFinite(age) || age < 1 || age > 120)) errors.age = "Tuổi không hợp lệ";
  if (!formState.activity) errors.activity = "Vui lòng chọn mức độ hoạt động";
  if (!formState.goal_type) errors.goal_type = "Vui lòng chọn mục tiêu";
  if (!formState.gain_speed) errors.gain_speed = "Vui lòng chọn mục tiêu tăng cân";
  if (!formState.meal_complexity) errors.meal_complexity = "Vui lòng chọn số món";
  if (!formState.diet_style) errors.diet_style = "Vui lòng chọn chế độ ăn";
  if (!formState.budget_level) errors.budget_level = "Vui lòng chọn ngân sách";

  return errors;
}

function round(value, digits = 0) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  const factor = 10 ** digits;
  return Math.round(number * factor) / factor;
}
