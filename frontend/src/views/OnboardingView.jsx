import { useState, useMemo, useEffect } from "react";
import { calculateNutritionTarget } from "../utils/nutritionTarget";
import { updateUserProfile, postRegenerateMealPlan, fetchCurrentUser } from "../services/apiService";
import { mapFormStateToBackendProfile } from "../App";
import { normalizePayload } from "../models/recommendationModel";
import NutriGainLogo from "../components/NutriGainLogo";
import { formatFoodListInput, parseFoodList } from "../utils/foodList.js";

// ─── helpers ────────────────────────────────────────────────────────────────
function safeNum(v) { const n = Number(v); return Number.isFinite(n) && n > 0 ? n : 0; }

function buildRegeneratePayload(formData) {
  const payload = normalizePayload({ ...formData, save_user_data: true });
  return {
    ...payload,
    date: new Date().toISOString().slice(0, 10),
    excludePreviousItems: true,
    randomSeed: Date.now(),
    favorite_foods: parseFoodList(formData.favorite_foods),
    disliked_foods: parseFoodList(formData.unfavorite_foods || formData.disliked_foods),
    disliked_food_groups: parseFoodList(formData.disliked_food_groups),
  };
}
function fmt(n) { return Number.isFinite(n) ? Math.round(n) : "—"; }



const STEPS = ["welcome","gender","body","activity","goal","diet","foods","summary"];

const INIT = {
  sex: "", weight: "", height: "", age: "",
  activity: "moderate", goal_type: "gain", gain_speed: "slow",
  target_weight: "", meal_complexity: "balanced", items_per_meal: 4,
  diet_style: "balanced", budget_level: "standard",
  favorite_foods: "", unfavorite_foods: "",
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
function StepBody({ data, update, errors }) {
  function handle(e){ update(e.target.name, e.target.value); }
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <NumberField label="Cân nặng hiện tại" name="weight" value={data.weight} onChange={handle} placeholder="60" unit="kg" error={errors.weight} />
      <NumberField label="Chiều cao" name="height" value={data.height} onChange={handle} placeholder="165" unit="cm" error={errors.height} />
      <div className="sm:col-span-2">
        <NumberField label="Tuổi" name="age" value={data.age} onChange={handle} placeholder="22" unit="tuổi" error={errors.age} />
      </div>
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
function StepGoal({ data, update, errors }) {
  function handle(e){ update(e.target.name, e.target.value); }
  const speeds = [
    { v:"slow", title:"Chậm và ổn định", desc:"+300 kcal/ngày" },
    { v:"medium", title:"Vừa phải", desc:"+400 kcal/ngày" },
    { v:"fast", title:"Nhanh hơn", desc:"+500 kcal/ngày" },
  ];
  return (
    <div className="space-y-6">
      <NumberField label="Cân nặng mục tiêu" name="target_weight" value={data.target_weight} onChange={handle} placeholder="65" unit="kg" error={errors.target_weight} />
      <div>
        <p className="mb-3 text-sm font-bold text-[#0F172A]">Tốc độ tăng cân</p>
        <div className="grid gap-3 sm:grid-cols-3">
          {speeds.map(s=>(
            <OptionCard key={s.v} selected={data.gain_speed===s.v} onClick={()=>update("gain_speed",s.v)} title={s.title} desc={s.desc} />
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── StepDiet ────────────────────────────────────────────────────────────────
function StepDiet({ data, update }) {
  const diets = [
    { v:"balanced", title:"Cân bằng", icon:"⚖️" },
    { v:"eat_clean", title:"Eat Clean", icon:"🥬" },
    { v:"low_carb", title:"Giàu Protein", icon:"🥩" },
    { v:"vegetarian", title:"Tiết kiệm", icon:"🌱" },
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
      <TagInput label="Món không thích / dị ứng" name="unfavorite_foods" value={data.unfavorite_foods} onChange={handle} placeholder="Ví dụ: tôm, đậu phộng, gà" />
    </div>
  );
}

// ─── StepSummary ─────────────────────────────────────────────────────────────
function StepSummary({ data, onFinish, onContinue, isSaving, finishError, profileComplete }) {
  const preview = useMemo(()=>calculateNutritionTarget({
    weight: data.weight, height: data.height, age: data.age,
    sex: data.sex, activity: data.activity,
    goal_type: data.goal_type, gain_speed: data.gain_speed,
  }),[data]);

  const bmiLabel = preview.bmi < 18.5 ? "Thiếu cân" : preview.bmi < 25 ? "Bình thường" : "Thừa cân";
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
      <div className="mt-8 flex flex-col gap-3">
        {finishError && (
          <div className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-bold leading-6 text-red-600">
            {finishError}
          </div>
        )}
        <button onClick={onFinish} disabled={isSaving}
          className="h-14 w-full rounded-2xl bg-[#10B981] text-base font-bold text-white shadow-lg shadow-[#10B981]/25 transition hover:bg-[#047857] disabled:opacity-60">
          {isSaving ? "Đang cập nhật..." : profileComplete ? "Cập nhật và tạo thực đơn" : "Hoàn tất hồ sơ và tạo thực đơn"}
        </button>
        {profileComplete && (
          <button onClick={onContinue} disabled={isSaving}
            className="h-14 w-full rounded-2xl border-2 border-[#E2E8F0] bg-white text-base font-bold text-[#64748B] transition hover:border-[#10B981] hover:text-[#10B981] disabled:opacity-60">
            Tiếp tục vào Dashboard
          </button>
        )}
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
  return errs;
}

function validateProfile(data) {
  const errs = {};
  if (!data.sex) errs.sex = "Vui lòng chọn giới tính";
  if (!safeNum(data.weight || data.weight_kg)) errs.weight = "Vui lòng nhập cân nặng hợp lệ";
  if (!safeNum(data.height || data.height_cm)) errs.height = "Vui lòng nhập chiều cao hợp lệ";
  if (!safeNum(data.age)) errs.age = "Vui lòng nhập tuổi hợp lệ";
  if (!data.activity && !data.activity_level) errs.activity = "Vui lòng chọn mức độ vận động";
  if (!data.gain_speed && !data.weight_gain_speed) errs.gain_speed = "Vui lòng chọn tốc độ tăng cân";
  if (!data.diet_style && !data.diet_type) errs.diet_style = "Vui lòng chọn chế độ ăn";
  if (!data.budget_level) errs.budget_level = "Vui lòng chọn ngân sách";
  if (!data.meal_complexity && !data.items_per_meal) errs.meal_complexity = "Vui lòng chọn số món mỗi bữa";
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

export default function OnboardingView({ userEmail, onComplete, initialData, user, onLogout }) {
  const [step, setStep] = useState(0);
  const [data, setData] = useState(() => ({ ...INIT, ...(initialData || {}) }));
  const [errors, setErrors] = useState({});
  const [isSaving, setIsSaving] = useState(false);
  const [finishError, setFinishError] = useState("");
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
      meal_complexity: profile.items_per_meal === 3 ? "simple" : profile.items_per_meal === 5 ? "full" : prev.meal_complexity,
      diet_style: profile.diet_type ?? prev.diet_style,
      budget_level: profile.budget_level ?? prev.budget_level,
      favorite_foods: formatFoodListInput(profile.favorite_foods ?? prev.favorite_foods),
      unfavorite_foods: formatFoodListInput(profile.disliked_foods ?? prev.unfavorite_foods),
      disliked_foods: parseFoodList(profile.disliked_foods ?? prev.disliked_foods),
    }));
  }, [user]);

  // Check if we're editing an existing profile (not showing welcome step)
  const isEditing = Boolean(user?.profile);
  const stepsToShow = isEditing ? STEPS.filter(s => s !== "welcome") : STEPS;
  const stepName = stepsToShow[step];
  const isSummary = stepName === "summary";
  const profileComplete = isProfileDataComplete(data);
  const totalVisible = stepsToShow.length;
  const progressStep = Math.max(0, step);
  const progressPct = totalVisible > 1 ? Math.round((progressStep / (totalVisible - 1)) * 100) : 0;

  const stepTitles = {
    welcome: "Chào mừng đến NutriGain",
    gender: "Giới tính của bạn là gì?",
    body: "Thông tin cơ thể của bạn",
    activity: "Mức độ hoạt động hằng ngày",
    goal: "Mục tiêu tăng cân của bạn",
    diet: "Phong cách ăn uống",
    foods: "Sở thích và loại trừ",
    summary: isEditing ? "Xác nhận cập nhật hồ sơ" : "Hồ sơ của bạn đã sẵn sàng 🎉",
  };

  function update(field, value) {
    setData(p=>({...p,[field]:value}));
    setErrors(p=>({...p,[field]:"",_step:""}));
  }

  function handleChange(e){ update(e.target.name, e.target.value); }

  function goNext() {
    const errs = validateStep(stepName, data);
    if (Object.keys(errs).length > 0) { setErrors(errs); return; }
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
    const validationErrors = validateProfile(data);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      setFinishError("Vui lòng hoàn thiện các thông tin bắt buộc trước khi tạo thực đơn.");
      return;
    }

    setIsSaving(true);
    setFinishError("");
    setRegenerateFailed(false);
    setRegenerateErrorMsg("");
    try {
      // Convert form data to backend profile format
      const backendProfile = mapFormStateToBackendProfile(data);
      
      // Update user profile via API
      await updateUserProfile(backendProfile);
      const updatedUser = await fetchCurrentUser();

      // Regenerate meal plan (may fail) — handle regeneration errors separately
      let mealPlanResult = null;
      try {
        mealPlanResult = await postRegenerateMealPlan(buildRegeneratePayload(data));
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
      setFinishError(error?.message || "Không thể lưu hồ sơ. Vui lòng kiểm tra thông tin và thử lại.");
      setIsSaving(false);
    }
  }

  async function retryRegenerate() {
    setIsSaving(true);
    setFinishError("");
    setRegenerateFailed(false);
    try {
      const mealPlanResult = await postRegenerateMealPlan(buildRegeneratePayload(data));
      const updatedUser = await fetchCurrentUser();
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#ECFDF5] via-[#F8FAFC] to-[#FFF7ED] px-4 py-8 sm:px-6">
      {/* Top bar */}
      <div className="mx-auto flex max-w-3xl items-center justify-between">
        <NutriGainLogo size="sm" />
        <div className="flex items-center gap-4">
          {userEmail && <span className="text-sm text-[#64748B]">{userEmail}</span>}
          {isEditing && onLogout && (
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

        {/* Step content */}
        {stepName==="welcome" && <StepWelcome onNext={goNext} />}
        {stepName==="gender" && <StepGender data={data} update={update} />}
        {stepName==="body" && <StepBody data={data} update={update} errors={errors} onChange={handleChange} />}
        {stepName==="activity" && <StepActivity data={data} update={update} />}
        {stepName==="goal" && <StepGoal data={data} update={update} errors={errors} onChange={handleChange} />}
        {stepName==="diet" && <StepDiet data={data} update={update} />}
        {stepName==="foods" && <StepFoods data={data} update={update} onChange={handleChange} />}
        {stepName==="summary" && (
          <StepSummary data={data} isSaving={isSaving} finishError={finishError}
            onFinish={handleFinish} onContinue={gotoDashboard} profileComplete={profileComplete} />
        )}
        {profileComplete && !isSummary && !regenerateFailed && (
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            <button onClick={handleFinish} disabled={isSaving}
              className="h-12 rounded-2xl bg-[#10B981] text-sm font-bold text-white shadow-md shadow-[#10B981]/20 transition hover:bg-[#047857] disabled:opacity-60">
              {isSaving ? "Đang cập nhật..." : "Cập nhật và tạo thực đơn"}
            </button>
            <button onClick={gotoDashboard} disabled={isSaving}
              className="h-12 rounded-2xl border-2 border-[#E2E8F0] bg-white px-6 text-sm font-bold text-[#64748B] transition hover:border-[#10B981] hover:text-[#10B981] disabled:opacity-60">
              Tiếp tục vào Dashboard
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

        {/* Navigation buttons (not on welcome / summary) */}
        {stepName !== "welcome" && !isSummary && (
          <div className="mt-8 flex items-center justify-between gap-4">
            <button onClick={goBack}
              className="flex h-12 items-center gap-2 rounded-2xl border-2 border-[#E2E8F0] px-6 text-sm font-bold text-[#64748B] transition hover:border-[#10B981] hover:text-[#10B981]">
              ← Quay lại
            </button>
            <button onClick={goNext}
              className="flex h-12 flex-1 items-center justify-center gap-2 rounded-2xl bg-[#10B981] text-sm font-bold text-white shadow-md shadow-[#10B981]/20 transition hover:bg-[#047857]">
              Tiếp tục →
            </button>
          </div>
        )}
      </div>

    </div>
  );
}
