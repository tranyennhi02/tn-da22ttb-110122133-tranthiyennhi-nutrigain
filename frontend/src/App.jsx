import { useMemo, useState, useEffect, useCallback } from "react";

import { performLogout, readSession, submitLogin } from "./controllers/authController";
import { saveUserProfile, submitRecommendation } from "./controllers/recommendationController";
import { fetchCurrentUser } from "./services/apiService";
import DashboardView from "./views/DashboardView";
import LoginView from "./views/LoginView";
import OnboardingView from "./views/OnboardingView";
import { defaultFormState } from "./models/recommendationModel";
import { formatFoodListInput, parseFoodList } from "./utils/foodList.js";

export function isProfileComplete(user) {
  const profile = user?.profile || user?.nutrition_profile || user;
  return Boolean(
    profile &&
    profile.age &&
    (profile.sex || profile.gender) &&
    profile.height_cm &&
    profile.weight_kg &&
    profile.activity_level &&
    profile.weight_gain_speed &&
    profile.diet_type &&
    profile.budget_level &&
    profile.items_per_meal
  );
}

// ─── helpers ─────────────────────────────────────────────────────────────────
const ONBOARDING_DONE_KEY = "nutrigain_onboarding_done";

function markOnboardingDone() {
  localStorage.setItem(ONBOARDING_DONE_KEY, "1");
}

function clearOnboardingFlag() {
  localStorage.removeItem(ONBOARDING_DONE_KEY);
}

// ─── App ─────────────────────────────────────────────────────────────────────
export default function App() {
  const [session, setSession] = useState(() => readSession());
  const [authUser, setAuthUser] = useState(null);
  // "checking" | "onboarding" | "dashboard"
  const [appView, setAppView] = useState("checking");
  const [profileFormState, setProfileFormState] = useState(defaultFormState);
  const [initialMealResult, setInitialMealResult] = useState(null);
  const [initialSection, setInitialSection] = useState("overview");
  const [justLoggedIn, setJustLoggedIn] = useState(false);

  const userEmail = useMemo(() => session?.email || "", [session]);

  useEffect(() => {
    if (!session) {
      setAppView("checking");
      return;
    }
    if (justLoggedIn) {
      return;
    }
    let cancelled = false;

    async function syncProfile() {
      setAppView("checking");
      try {
        const currentUser = await fetchCurrentUser();
        const profile = currentUser?.profile;
        if (cancelled) return;
        setAuthUser(currentUser);
        if (profile) {
          setProfileFormState(mapUserProfileToFormState(profile));
        }
        if (isProfileComplete(currentUser) && localStorage.getItem(ONBOARDING_DONE_KEY) === "1") {
          setAppView("dashboard");
          return;
        }
      } catch (error) {
        console.error("Failed to load user from stored session", error);
        performLogout();
        clearOnboardingFlag();
        if (!cancelled) {
          setAuthUser(null);
          setSession(null);
          setAppView("checking");
        }
        return;
      }
      clearOnboardingFlag();
      if (!cancelled) setAppView("onboarding");
    }

    syncProfile();
    return () => {
      cancelled = true;
    };
  }, [session]);

  async function handleAuthSuccess(nextSession) {
    setJustLoggedIn(true);
    setSession(nextSession);
    setAuthUser(null);
    setProfileFormState(defaultFormState);
    setInitialMealResult(null);
    setInitialSection("overview");
    setAppView("checking");
    clearOnboardingFlag();

    try {
      const currentUser = await fetchCurrentUser();
      const profile = currentUser?.profile;
      setAuthUser(currentUser);
      if (profile) {
        setProfileFormState(mapUserProfileToFormState(profile));
      }

      setAppView("onboarding");
    } catch (error) {
      console.error("Failed to load user after auth", error);
      performLogout();
      clearOnboardingFlag();
      setJustLoggedIn(false);
      setSession(null);
      setAuthUser(null);
      setAppView("checking");
      throw error;
    }
  }

  async function handleAuthSubmit(loginState) {
    const nextSession = await submitLogin(loginState);
    await handleAuthSuccess(nextSession);
  }

  function handleLogout() {
    performLogout();
    clearOnboardingFlag();
    setJustLoggedIn(false);
    setSession(null);
    setAppView("checking");
    setInitialMealResult(null);
    setInitialSection("overview");
  }

  // Called when onboarding completes
  const handleOnboardingComplete = useCallback(async (onboardingData, generateMeal) => {
    // Map onboarding fields → recommendationModel fields
    const merged = {
      ...defaultFormState,
      weight: onboardingData.weight,
      height: onboardingData.height,
      age: onboardingData.age,
      sex: onboardingData.sex === "undisclosed" ? "" : onboardingData.sex,
      activity: onboardingData.activity,
      goal_type: onboardingData.goal_type || "gain",
      gain_speed: onboardingData.gain_speed || "slow",
      target_weight: onboardingData.target_weight,
      meal_complexity: onboardingData.meal_complexity || "balanced",
      diet_style: onboardingData.diet_style || "balanced",
      budget_level: onboardingData.budget_level || "standard",
      favorite_foods: onboardingData.favorite_foods || "",
      unfavorite_foods: onboardingData.unfavorite_foods || "",
      save_user_data: true,
    };

    // If onboarding already persisted the profile, trust its fresh user payload.
    if (onboardingData._updatedUser || onboardingData._mealPlanResult) {
      const mealPlanResult = onboardingData._mealPlanResult;
      const updatedUser = onboardingData._updatedUser;
      
      if (updatedUser) {
        setAuthUser(updatedUser);
      }
      
      setProfileFormState(updatedUser?.profile ? mapUserProfileToFormState(updatedUser.profile) : merged);
      setInitialMealResult(mealPlanResult);
      setInitialSection(mealPlanResult ? "meal-plan" : "overview");
      markOnboardingDone();
      setJustLoggedIn(false);
      setAppView("dashboard");
      return;
    }

    // Try to persist profile to backend (best-effort) if not already done
    try {
      await saveUserProfile(merged);
    } catch {
      // silently continue — don't block dashboard
    }

    let generatedResult = null;
    if (generateMeal) {
      generatedResult = await submitRecommendation(merged);
    }

    setProfileFormState(merged);
    setInitialMealResult(generatedResult);
    setInitialSection(generatedResult ? "meal-plan" : "overview");
    markOnboardingDone();
    setJustLoggedIn(false);
    setAppView("dashboard");
  }, []);

  function handleRequireProfile() {
    clearOnboardingFlag();
    setInitialMealResult(null);
    setInitialSection("overview");
    setAppView("onboarding");
  }

  // ── render ────────────────────────────────────────────────────────────────
  if (!session) {
    return <LoginView onAuthSuccess={handleAuthSubmit} />;
  }

  if (appView === "checking") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F8FAFC]">
        <div className="flex flex-col items-center">
          <span className="h-10 w-10 animate-spin rounded-full border-4 border-[#10B981]/20 border-t-[#10B981]" />
          <p className="mt-4 text-[#64748B] font-medium">Đang tải thông tin...</p>
        </div>
      </div>
    );
  }

  if (appView === "onboarding") {
    return (
      <OnboardingView
        userEmail={userEmail}
        user={authUser}
        onComplete={handleOnboardingComplete}
        initialData={profileFormState}
        onLogout={handleLogout}
      />
    );
  }

  return (
    <DashboardView
      userEmail={userEmail}
      user={authUser}
      onLogout={handleLogout}
      initialFormState={profileFormState}
      initialResult={initialMealResult}
      initialSection={initialSection}
      onRequireProfile={handleRequireProfile}
      onEditProfile={() => setAppView("onboarding")}
    />
  );
}

export { parseFoodList };

// Convert frontend form state to backend profile format
export function mapFormStateToBackendProfile(formState) {
  return {
    age: formState.age ? parseInt(formState.age, 10) : null,
    sex: formState.sex || formState.gender || null,
    gender: formState.sex || formState.gender || null,
    height_cm: formState.height || formState.height_cm ? parseFloat(formState.height || formState.height_cm) : null,
    weight_kg: formState.weight || formState.weight_kg ? parseFloat(formState.weight || formState.weight_kg) : null,
    target_weight_kg: formState.target_weight || formState.target_weight_kg ? parseFloat(formState.target_weight || formState.target_weight_kg) : null,
    activity_level: formState.activity || formState.activity_level || "moderate",
    weight_gain_speed: formState.gain_speed || formState.weight_gain_speed || "slow",
    diet_type: formState.diet_style || formState.diet_type || "balanced",
    budget_level: formState.budget_level || "standard",
    items_per_meal: formState.meal_complexity === "simple" ? 3 : formState.meal_complexity === "full" ? 5 : 4,
    favorite_foods: formatFoodListInput(formState.favorite_foods),
    disliked_foods: parseFoodList(formState.unfavorite_foods || formState.disliked_foods),
    disliked_food_groups: formState.disliked_food_groups || [],
  };
}

export function mapUserProfileToFormState(profile) {
  if (!profile) return defaultFormState;
  const surplus = Number(profile.surplus_kcal || 0);
  const gainSpeed = surplus >= 475 ? "fast" : surplus >= 375 ? "medium" : "slow";
  const complexity = profile.items_per_meal === 3 ? "simple" : profile.items_per_meal === 5 ? "full" : "balanced";
  return {
    ...defaultFormState,
    weight: profile.weight_kg ?? "",
    weight_kg: profile.weight_kg ?? "",
    height: profile.height_cm ?? "",
    height_cm: profile.height_cm ?? "",
    age: profile.age ?? "",
    sex: profile.sex ?? "",
    gender: profile.gender ?? profile.sex ?? "",
    activity: profile.activity_level || "moderate",
    activity_level: profile.activity_level || "moderate",
    goal_type: "gain",
    gain_speed: profile.weight_gain_speed || gainSpeed,
    weight_gain_speed: profile.weight_gain_speed || gainSpeed,
    target_weight: profile.target_weight_kg ?? "",
    target_weight_kg: profile.target_weight_kg ?? "",
    meal_complexity: complexity,
    items_per_meal: profile.items_per_meal ?? 4,
    diet_style: profile.diet_type || "balanced",
    diet_type: profile.diet_type || "balanced",
    budget_level: profile.budget_level || "standard",
    surplus_kcal: profile.surplus_kcal,
    favorite_foods: formatFoodListInput(profile.favorite_foods),
    unfavorite_foods: formatFoodListInput(profile.disliked_foods),
    disliked_foods: parseFoodList(profile.disliked_foods),
    disliked_food_groups: parseFoodList(profile.disliked_food_groups),
    save_user_data: true,
  };
}
