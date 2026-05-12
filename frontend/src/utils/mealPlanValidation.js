import { normalizeFoodCategory, stripAccents } from "./foodCategory";

function flattenMealPlan(mealPlan) {
  if (!mealPlan) return [];
  if (Array.isArray(mealPlan.meals)) {
    return mealPlan.meals.flatMap((meal) =>
      (Array.isArray(meal.items) ? meal.items : []).map((item) => ({ ...item, mealTitle: meal.meal_type || meal.title || meal.meal })),
    );
  }
  if (Array.isArray(mealPlan)) {
    return mealPlan.flatMap((meal) =>
      (Array.isArray(meal.items) ? meal.items : []).map((item) => ({ ...item, mealTitle: meal.title || meal.meal })),
    );
  }

  return Object.entries(mealPlan)
    .filter(([key, items]) => Array.isArray(items))
    .flatMap(([mealKey, items]) =>
      (items || []).map((item) => ({ ...item, mealTitle: mealKey })),
    );
}

function getMealEntries(mealPlan) {
  if (!mealPlan) return [];
  if (Array.isArray(mealPlan.meals)) {
    return mealPlan.meals.map((meal) => [meal.meal_type || meal.title || meal.meal, Array.isArray(meal.items) ? meal.items : []]);
  }
  if (Array.isArray(mealPlan)) {
    return mealPlan.map((meal) => [meal.title || meal.meal, Array.isArray(meal.items) ? meal.items : []]);
  }
  return Object.entries(mealPlan).filter(([key, items]) => Array.isArray(items));
}

function round(value) {
  return Math.round(Number(value) || 0);
}

function hasFoodTerm(text, term) {
  const normalizedTerm = stripAccents(term).toLowerCase();
  const pattern = new RegExp(`(^|[^a-z0-9])${normalizedTerm.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}($|[^a-z0-9])`);
  return pattern.test(text);
}

function foodFamily(food) {
  const text = stripAccents(`${food.name || ""} ${food.category || ""}`).toLowerCase();
  const families = {
    bean: ["bean", "soy", "tofu", "dau phu", "dau hu", "dau nanh", "dau ha lan"],
    rice: ["rice", "com"],
    corn: ["corn", "ngo"],
    potato: ["potato", "taro", "khoai"],
    pasta: ["pasta", "noodle", "spaghetti", "mi"],
    fish: ["fish", "salmon", "tuna", "ca"],
    shellfish: ["crab", "shrimp", "cua", "tom"],
    egg: ["egg", "trung"],
    dairy: ["milk", "yogurt", "sua"],
  };

  const match = Object.entries(families).find(([, terms]) => terms.some((term) => hasFoodTerm(text, term)));
  return match?.[0] || text.split(/\s+/).filter(Boolean)[0] || "other";
}

function macroWarnings(food) {
  const normalized = normalizeFoodCategory(food);
  const protein = Number(food.protein || 0);
  const fat = Number(food.fat || 0);
  const carbs = Number(food.carbs || 0);
  const calories = Number(food.calories || 0);
  const name = String(food.name || "Món ăn");
  const warnings = [];

  if (normalized.category === "Đạm" && ["Thịt", "Hải sản"].includes(normalized.subCategory)) {
    if (carbs > 2) warnings.push(`${name}: dữ liệu carbs có thể sai với nhóm ${normalized.subCategory}.`);
    if (protein <= carbs && protein <= fat) warnings.push(`${name}: protein không phải macro chính của món đạm.`);
  }

  if (normalized.category === "Tinh bột" && carbs < protein && carbs < fat) {
    warnings.push(`${name}: món tinh bột nhưng carbs không phải macro chính.`);
  }

  if (normalized.category === "Trái cây" && fat > Math.max(5, carbs * 0.5)) {
    warnings.push(`${name}: trái cây thường không có fat cao như dữ liệu hiện tại.`);
  }

  if (normalized.category === "Rau củ" && calories > 250) {
    warnings.push(`${name}: rau củ có kcal cao bất thường, nên kiểm tra khẩu phần.`);
  }

  const text = stripAccents(name).toLowerCase();
  if (text.includes("lamb") && carbs > 2) warnings.push(`${name}: thịt cừu có carbs > 2g, dữ liệu có thể sai.`);
  if ((text.includes("crab") || text.includes("cua")) && protein === 0 && carbs >= 10) {
    warnings.push(`${name}: cua có protein = 0 và carbs cao, dữ liệu có thể sai.`);
  }

  const macroKcal = protein * 4 + carbs * 4 + fat * 9;
  if (calories > 0 && macroKcal > 0 && Math.abs(calories - macroKcal) / calories > 0.12) {
    warnings.push(`${name}: kcal lệch đáng kể so với macro.`);
  }

  return warnings;
}

export function validateMealPlan(mealPlan, userProfile, target) {
  const foods = flattenMealPlan(mealPlan).map(normalizeFoodCategory);
  const messages = [];
  const explicitTotalCalories = mealPlan?.total_kcal ?? mealPlan?.totalKcal ?? mealPlan?.total_calories;
  const totalCalories = round(explicitTotalCalories ?? foods.reduce((sum, item) => sum + Number(item.calories || 0), 0));
  const totalProtein = round(foods.reduce((sum, item) => sum + Number(item.protein || 0), 0));
  const totalFat = round(foods.reduce((sum, item) => sum + Number(item.fat || 0), 0));
  const totalCarbs = round(foods.reduce((sum, item) => sum + Number(item.carbs || 0), 0));
  const goal = String(userProfile?.goal_type || userProfile?.goal || "gain").toLowerCase();

  let level = "success";
  let isValid = true;

  const targetKcal = Number(target?.target_kcal ?? target?.targetKcal ?? target?.targetCalories ?? target?.calories ?? 0);
  const minKcal = targetKcal * 0.95;
  const maxKcal = targetKcal * 1.05;
  const kcalDiff = totalCalories - targetKcal;
  const kcalDiffAbs = Math.abs(kcalDiff);
  const kcalDiffPct = targetKcal > 0 ? (kcalDiffAbs / targetKcal) * 100 : 100;
  const isKcalValid = targetKcal > 0 && totalCalories >= minKcal && totalCalories <= maxKcal;
  const direction = kcalDiff > 0 ? "cao hơn" : "thấp hơn";
  const detailedReason = isKcalValid
    ? null
    : `Thực đơn hiện tại đạt ${Math.round(totalCalories)} kcal, ${direction} mục tiêu ${Math.round(targetKcal)} kcal khoảng ${Math.round(kcalDiffAbs)} kcal, tương đương ${kcalDiffPct.toFixed(2)}%. Vui lòng tạo lại để có thực đơn phù hợp hơn.`;

  if (goal === "gain" && !isKcalValid) {
    isValid = false;
    level = "error";
    messages.push(detailedReason || `Tổng kcal (${Math.round(totalCalories)}) lệch ${kcalDiffPct.toFixed(2)}% so với target (${Math.round(targetKcal)})`);
  }

  if (totalCalories < 1200) {
    isValid = false;
    level = "error";
    messages.push("Tổng năng lượng dưới 1200 kcal, không nên dùng thực đơn này cho người trưởng thành.");
  }

  if (totalProtein < target.proteinTarget * 0.8) {
    if (level !== "error") level = "warning";
    messages.push("Bữa này còn thiếu đạm. Có thể thêm trứng, cá, thịt nạc, đậu hũ hoặc sữa chua Hy Lạp.");
  }
  if (totalProtein > target.proteinTarget * 1.35) {
    if (level !== "error") level = "warning";
    messages.push("Protein đang cao hơn mục tiêu khá nhiều. Có thể giảm khẩu phần món đạm và tăng tinh bột/chất béo tốt.");
  }

  if (totalFat < target.fatTarget * 0.8) {
    isValid = false;
    level = "error";
    messages.push("Bữa này còn thiếu chất béo tốt. Có thể thêm bơ, hạt, trứng, cá béo hoặc sữa nguyên kem.");
  }
  if (totalCarbs > target.carbTarget * 1.15) {
    if (level !== "error") level = "warning";
    messages.push("Bữa này hơi nhiều tinh bột. Có thể giảm một phần tinh bột hoặc đổi sang bơ, hạt, trứng hay sữa nguyên kem.");
  }

  for (const [mealName, items] of getMealEntries(mealPlan)) {
    const mealCalories = round((items || []).reduce((sum, item) => sum + Number(item.calories || 0), 0));
    if (["breakfast", "lunch", "dinner", "Bữa sáng", "Bữa trưa", "Bữa tối"].includes(mealName) && mealCalories < 450) {
      if (level !== "error") level = "warning";
      messages.push(`${mealName}: bữa chính đang quá nhẹ (${mealCalories} kcal).`);
    }

    if ((items || []).length === 0) {
      isValid = false;
      level = "error";
      messages.push(`${mealName}: chưa có món nào.`);
    }
  }

  const familyCounts = foods.reduce((acc, food) => {
    const family = foodFamily(food);
    acc[family] = (acc[family] || 0) + 1;
    return acc;
  }, {});
  Object.entries(familyCounts).forEach(([family, count]) => {
    if (count > 2) {
      if (level !== "error") level = "warning";
      messages.push(`Nhóm nguyên liệu ${family} xuất hiện ${count} lần trong ngày, nên đa dạng hơn.`);
    }
  });

  foods.flatMap(macroWarnings).forEach((message) => {
    if (level !== "error") level = "warning";
    messages.push(message);
  });

  if (messages.length === 0) {
    messages.push("Bữa ăn đã đủ nhóm chính và phù hợp với kế hoạch tăng cân hôm nay.");
  }

  const proteinRatio = target.proteinTarget > 0 ? totalProtein / target.proteinTarget : 1;
  const fatRatio = target.fatTarget > 0 ? totalFat / target.fatTarget : 1;
  const carbRatio = target.carbTarget > 0 ? totalCarbs / target.carbTarget : 1;
  let status = "valid";
  if (!foods.length || totalCalories <= 0) {
    status = "invalid";
  } else if (kcalDiffPct <= 10 && proteinRatio >= 0.9 && proteinRatio <= 1.1 && fatRatio >= 0.8 && fatRatio <= 1.2 && carbRatio >= 0.8 && carbRatio <= 1.2) {
    status = "valid";
  } else if (kcalDiffPct <= 10 && proteinRatio <= 1.3 && fatRatio >= 0.7 && carbRatio <= 1.3) {
    status = "minor_adjustment";
  } else {
    status = "major_adjustment";
  }

  return {
    isValid,
    status,
    level,
    messages,
    reason: detailedReason,
    targetKcal,
    totalKcal: totalCalories,
    kcalDiff,
    kcalDiffPct,
    totalCalories,
    totalProtein,
    totalFat,
    totalCarbs,
  };
}
