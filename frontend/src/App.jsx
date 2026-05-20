import { useMemo, useState, useEffect, useCallback } from "react";

import { performLogout, readSession, submitLogin } from "./controllers/authController";
import { saveUserProfile, submitRecommendation } from "./controllers/recommendationController";
import { fetchCurrentUser } from "./services/apiService";
import DashboardView from "./views/DashboardView";
import AdminView from "./views/AdminView";
import ForgotPasswordView from "./views/ForgotPasswordView";
import LoginView from "./views/LoginView";
import OnboardingView from "./views/OnboardingView";
import ResetPasswordView from "./views/ResetPasswordView";
import { defaultFormState } from "./models/recommendationModel";
import { parseFoodList } from "./utils/foodList.js";
import { normalizeProfilePayload, foodListToInput } from "./utils/profileFormUtils.js";

export function isProfileComplete(profile) {
  if (!profile) return false;

  const requiredFields = [
    "weight_kg",
    "height_cm",
    "age",
    "target_weight_kg",
    "activity_level",
    "diet_type",
    "budget_level",
    "items_per_meal",
  ];

  const hasRequiredFields = requiredFields.every((key) => {
    const value = profile[key];
    return value !== null && value !== undefined && value !== "";
  });

  const hasGender = Boolean(profile.gender || profile.sex);

  return hasRequiredFields && hasGender;
}

// ─── helpers ─────────────────────────────────────────────────────────────────
const ONBOARDING_DONE_KEY = "nutrigain_onboarding_done";
const DISLIKED_FOODS_KEY = "nutrigain_disliked_foods";
const DISLIKED_FOOD_GROUPS_KEY = "nutrigain_disliked_food_groups";
const PROFILE_CACHE_KEYS = [
  DISLIKED_FOODS_KEY,
  DISLIKED_FOOD_GROUPS_KEY,
  "nutritionProfile",
  "onboardingData",
  "userProfile",
  "currentUser",
  "mealPlan",
  "progressSummary",
  "dashboardData",
  "dislikedFoods",
  "favoriteFoods",
  "profile",
  "weightSummary",
];

function markOnboardingDone() {
  localStorage.setItem(ONBOARDING_DONE_KEY, "1");
}

function clearOnboardingFlag() {
  localStorage.removeItem(ONBOARDING_DONE_KEY);
}

function clearProfileCacheKeys() {
  for (const key of PROFILE_CACHE_KEYS) {
    localStorage.removeItem(key);
    sessionStorage.removeItem(key);
  }
  try {
    const keysToRemove = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && (key.startsWith("profile") || key.startsWith("mealPlan") || key.startsWith("weightSummary") || key.startsWith("nutritionProfile"))) {
        keysToRemove.push(key);
      }
    }
    for (const k of keysToRemove) {
      localStorage.removeItem(k);
      sessionStorage.removeItem(k);
    }
  } catch {}
}

function normalizeProfileArrays(profile) {
  if (!profile) return profile;
  return {
    ...profile,
    favorite_foods: Array.isArray(profile.favorite_foods) ? profile.favorite_foods : parseFoodList(profile.favorite_foods),
    disliked_foods: Array.isArray(profile.disliked_foods) ? profile.disliked_foods : parseFoodList(profile.disliked_foods),
    disliked_food_groups: Array.isArray(profile.disliked_food_groups) ? profile.disliked_food_groups : parseFoodList(profile.disliked_food_groups),
  };
}

function normalizeUserProfileArrays(user) {
  if (!user) return user;
  return {
    ...user,
    profile: normalizeProfileArrays(user.profile),
  };
}

function syncAuthToken(authResult) {
  const token = authResult?.access_token || authResult?.accessToken || "";
  if (!token) {
    return;
  }

  const rawSession = localStorage.getItem("nutrigain_auth");
  if (!rawSession) {
    return;
  }

  try {
    const session = JSON.parse(rawSession);
    localStorage.setItem(
      "nutrigain_auth",
      JSON.stringify({
        ...session,
        accessToken: token,
      })
    );
  } catch {
    // Keep the session as-is if storage is corrupted.
  }
}

// ─── App ─────────────────────────────────────────────────────────────────────
export default function App() {
  const [session, setSession] = useState(() => readSession());
  const [authUser, setAuthUser] = useState(null);
  // "checking" | "onboarding" | "dashboard" | "admin"
  const [appView, setAppView] = useState("checking");
  const [profileFormState, setProfileFormState] = useState(defaultFormState);
  const [initialMealResult, setInitialMealResult] = useState(null);
  const [initialSection, setInitialSection] = useState("overview");
  const [justLoggedIn, setJustLoggedIn] = useState(false);
  const [profileFormMode, setProfileFormMode] = useState("register_onboarding");
  const [locationPath, setLocationPath] = useState(() => window.location.pathname);

  const userEmail = useMemo(() => session?.email || "", [session]);
  const isAdminUser = useCallback((user) => ["ADMIN", "SUPER_ADMIN"].includes(String(user?.role || "").toUpperCase()), []);
  const isPasswordAuthRoute = locationPath === "/forgot-password" || locationPath === "/reset-password";

  function navigateTo(path) {
    if (window.location.pathname !== path) {
      window.history.pushState({}, "", path);
    }
    setLocationPath(path);
  }

  useEffect(() => {
    function syncLocation() {
      setLocationPath(window.location.pathname);
    }
    window.addEventListener("popstate", syncLocation);
    return () => window.removeEventListener("popstate", syncLocation);
  }, []);

  function handleBackToLogin() {
    performLogout();
    clearOnboardingFlag();
    clearProfileCacheKeys();
    setJustLoggedIn(false);
    setAuthUser(null);
    setProfileFormState(defaultFormState);
    setSession(null);
    setAppView("checking");
    setInitialMealResult(null);
    setInitialSection("overview");
    navigateTo("/login");
  }

  function handleForgotPasswordRoute() {
    navigateTo("/forgot-password");
  }

  useEffect(() => {
    if (isPasswordAuthRoute) {
      return;
    }
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
        const rawUser = await fetchCurrentUser();
        if (!rawUser) {
          throw new Error("No user profile session returned from API or server offline");
        }
        const currentUser = normalizeUserProfileArrays(rawUser);
        const profile = currentUser?.profile;
        if (cancelled) return;
        console.log("[AFTER LOGIN /users/me]", currentUser);
        setAuthUser(currentUser);
        if (isAdminUser(currentUser)) {
          navigateTo(window.location.pathname.startsWith("/admin") ? window.location.pathname : "/admin/overview");
          setAppView("admin");
          return;
        }
        const hasProfile = Boolean(profile);
        if (hasProfile) {
          setProfileFormState(mapUserProfileToFormState(profile));
          setProfileFormMode("edit_after_auth");
        } else {
          setProfileFormState(defaultFormState);
          setProfileFormMode("register_onboarding");
        }

        setInitialMealResult(null);
        setInitialSection("overview");
        clearOnboardingFlag();
        console.log("[AUTH REDIRECT]", hasProfile ? "user_profile_form_prefilled" : "user_profile_form_empty");
        navigateTo("/onboarding");
        setAppView("onboarding");
        return;
      } catch (error) {
        console.error("Failed to load user from stored session:", error);
        performLogout();
        clearOnboardingFlag();
        clearProfileCacheKeys();
        if (!cancelled) {
          setAuthUser(null);
          setSession(null);
        }
        return;
      }
      clearOnboardingFlag();
      setProfileFormMode("register_onboarding");
      setProfileFormState(defaultFormState);
      setInitialMealResult(null);
      setInitialSection("overview");
      navigateTo("/onboarding");
      if (!cancelled) setAppView("onboarding");
    }

    syncProfile();
    return () => {
      cancelled = true;
    };
  }, [session, isAdminUser, isPasswordAuthRoute]);

  async function handleUserAuthSuccess(authResult) {
    setJustLoggedIn(true);
    syncAuthToken(authResult);
    setSession(authResult);
    setAuthUser(null);
    setProfileFormState(defaultFormState);
    setInitialMealResult(null);
    setInitialSection("overview");
    setAppView("checking");
    clearOnboardingFlag();
    clearProfileCacheKeys();

    try {
      const rawUser = await fetchCurrentUser();
      if (!rawUser) {
        throw new Error("Could not fetch user profile after login");
      }
      const currentUser = normalizeUserProfileArrays(rawUser);
      
      console.log("[AUTH SUCCESS USER]", currentUser);
      setAuthUser(currentUser);
      if (isAdminUser(currentUser)) {
        navigateTo("/admin/overview");
        setJustLoggedIn(false);
        setAppView("admin");
        return;
      }

      const profile = currentUser?.profile;
      const formState = mapUserProfileToFormState(profile);
      const hasProfile = Boolean(profile);
      setProfileFormState(formState);
      setProfileFormMode(hasProfile ? "edit_after_auth" : "register_onboarding");
      setInitialMealResult(null);
      setInitialSection("overview");
      console.log("[PROFILE FORM PREFILL]", formState);
      console.log("[AUTH REDIRECT]", hasProfile ? "user_profile_form_prefilled" : "user_profile_form_empty");
      navigateTo("/onboarding");
      setAppView("onboarding");
      setJustLoggedIn(false);
    } catch (error) {
      console.error("Failed to load user after auth", error);
      performLogout();
      clearOnboardingFlag();
      clearProfileCacheKeys();
      setJustLoggedIn(false);
      setSession(null);
      setAuthUser(null);
      setAppView("checking");
      throw error;
    }
  }

  async function handleAuthSubmit(loginState) {
    const authResult = await submitLogin(loginState);
    console.log("[AUTH SUCCESS]", authResult);
    await handleUserAuthSuccess(authResult);
  }

  function handleLogout() {
    performLogout();
    clearOnboardingFlag();
    clearProfileCacheKeys();
    setJustLoggedIn(false);
    setAuthUser(null);
    setProfileFormState(defaultFormState);
    setSession(null);
    setAppView("checking");
    setInitialMealResult(null);
    setInitialSection("overview");
    navigateTo("/login");
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
      diet_style: onboardingData.diet_style || onboardingData.diet_type || "balanced",
      diet_type: onboardingData.diet_type || onboardingData.diet_style || "balanced",
      budget_level: onboardingData.budget_level || "standard",
      favorite_foods: onboardingData.favorite_foods || "",
      unfavorite_foods: onboardingData.unfavorite_foods || "",
      save_user_data: true,
    };

    // If onboarding already persisted the profile, trust its fresh user payload.
    if (onboardingData._updatedUser || onboardingData._mealPlanResult) {
      const mealPlanResult = onboardingData._mealPlanResult;
      const updatedUser = normalizeUserProfileArrays(onboardingData._updatedUser);
      
      if (updatedUser) {
        console.log("[PROFILE STATE AFTER SAVE]", {
          weight_kg: updatedUser?.profile?.weight_kg,
          target_weight_kg: updatedUser?.profile?.target_weight_kg,
          favorite_foods: updatedUser?.profile?.favorite_foods,
          disliked_foods: updatedUser?.profile?.disliked_foods,
        });
        setAuthUser(updatedUser);
      }
      
      setProfileFormState(updatedUser?.profile ? mapUserProfileToFormState(updatedUser.profile) : merged);
      setInitialMealResult(mealPlanResult);
      setInitialSection(mealPlanResult ? "meal-plan" : "overview");
      markOnboardingDone();
      setJustLoggedIn(false);
      navigateTo("/dashboard");
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
    navigateTo("/dashboard");
    setAppView("dashboard");
  }, []);

  function handleRequireProfile() {
    clearOnboardingFlag();
    setInitialMealResult(null);
    setInitialSection("overview");
    setAppView("onboarding");
  }

  const handleProfileUpdate = useCallback((updatedUser) => {
    const normalizedUser = normalizeUserProfileArrays(updatedUser);
    console.log("[PROFILE STATE AFTER SAVE]", {
      weight_kg: normalizedUser?.profile?.weight_kg,
      target_weight_kg: normalizedUser?.profile?.target_weight_kg,
      favorite_foods: normalizedUser?.profile?.favorite_foods,
      disliked_foods: normalizedUser?.profile?.disliked_foods,
    });
    setAuthUser(normalizedUser);
    if (normalizedUser?.profile) {
      setProfileFormState(mapUserProfileToFormState(normalizedUser.profile));
    }
  }, []);

  // ── render ────────────────────────────────────────────────────────────────
  if (locationPath === "/forgot-password") {
    return <ForgotPasswordView onBackToLogin={handleBackToLogin} />;
  }

  if (locationPath === "/reset-password") {
    return <ResetPasswordView onBackToLogin={handleBackToLogin} onForgotPassword={handleForgotPasswordRoute} />;
  }

  if (!session) {
    return (
      <LoginView
        onAuthSuccess={handleAuthSubmit}
        initialMode={locationPath === "/login" ? "login" : null}
        onForgotPassword={handleForgotPasswordRoute}
      />
    );
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
        profileFormMode={profileFormMode}
      />
    );
  }

  if (appView === "admin") {
    return <AdminView user={authUser} onLogout={handleLogout} />;
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
      onProfileUpdate={handleProfileUpdate}
    />
  );
}

export { parseFoodList };

// Convert frontend form state to backend profile format
export function mapFormStateToBackendProfile(formState) {
  return normalizeProfilePayload(formState);
}

export function mapUserProfileToFormState(profile) {
  if (!profile) return defaultFormState;
  const normalizedProfile = normalizeProfileArrays(profile);
  const surplus = Number(profile.surplus_kcal || 0);
  const gainSpeed = surplus >= 475 ? "fast" : surplus >= 375 ? "medium" : "slow";
  const complexity = profile.items_per_meal === 3 ? "simple" : profile.items_per_meal === 5 ? "full" : "balanced";
  const rawDiet = profile.diet_type || profile.diet_style || "balanced";
  const dietStyle = rawDiet === "low_carb" ? "high_protein" : rawDiet;
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
    diet_style: dietStyle,
    diet_type: dietStyle,
    budget_level: profile.budget_level || "standard",
    surplus_kcal: profile.surplus_kcal,
    favorite_foods: foodListToInput(normalizedProfile.favorite_foods),
    unfavorite_foods: foodListToInput(normalizedProfile.disliked_foods),
    disliked_foods: normalizedProfile.disliked_foods,
    disliked_food_groups: normalizedProfile.disliked_food_groups,
    save_user_data: true,
  };
}
