import { normalizeFoodCategory, stripAccents } from "./foodCategory";

function flattenMealPlan(mealPlan) {
  if (!mealPlan) return [];
  if (Array.isArray(mealPlan)) {
    return mealPlan.flatMap((meal) =>
      (meal.items || []).map((item) => ({ ...item, mealTitle: meal.title || meal.meal })),
    );
  }

  return Object.entries(mealPlan).flatMap(([mealKey, items]) =>
    (items || []).map((item) => ({ ...item, mealTitle: mealKey })),
  );
}

function getMealEntries(mealPlan) {
  if (!mealPlan) return [];
  if (Array.isArray(mealPlan)) {
    return mealPlan.map((meal) => [meal.title || meal.meal, meal.items || []]);
  }
  return Object.entries(mealPlan);
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
  const totalCalories = round(foods.reduce((sum, item) => sum + Number(item.calories || 0), 0));
  const totalProtein = round(foods.reduce((sum, item) => sum + Number(item.protein || 0), 0));
  const totalFat = round(foods.reduce((sum, item) => sum + Number(item.fat || 0), 0));
  const totalCarbs = round(foods.reduce((sum, item) => sum + Number(item.carbs || 0), 0));
  const goal = String(userProfile?.goal_type || userProfile?.goal || "gain").toLowerCase();

  let level = "success";
  let isValid = true;

  const minimumCalories = Number(target.minCalories || 0);

  if (goal === "gain" && totalCalories < minimumCalories) {
    isValid = false;
    level = "error";
    messages.push("Thực đơn chưa phù hợp mục tiêu tăng cân. Tổng năng lượng hiện thấp hơn mục tiêu.");
  }

  if (totalCalories < 1200) {
    isValid = false;
    level = "error";
    messages.push("Tổng năng lượng dưới 1200 kcal, không nên dùng thực đơn này cho người trưởng thành.");
  }

  if (totalProtein < target.proteinTarget * 0.8) {
    if (level !== "error") level = "warning";
    messages.push("Protein thấp hơn 80% mục tiêu. Nên thêm món đạm hoặc tăng khẩu phần.");
  }
  if (totalProtein > target.proteinTarget * 1.35) {
    if (level !== "error") level = "warning";
    messages.push("Protein đang cao hơn mục tiêu khá nhiều. Có thể giảm khẩu phần món đạm và tăng tinh bột/chất béo tốt.");
  }

  if (totalFat < target.fatTarget * 0.8) {
    isValid = false;
    level = "error";
    messages.push("Fat thap hon 80% muc tieu. Nen thay mon phu bang sua, sua chua, qua bo, hat, bo dau phong hoac pho mai phu hop.");
  }
  if (totalCarbs > target.carbTarget * 1.25) {
    if (level !== "error") level = "warning";
    messages.push("Carbs cao hon muc tieu, nen giam mon tinh bot/ngot va tang chat beo tot.");
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
    messages.push("Thực đơn phù hợp với mục tiêu hôm nay.");
  }

  return {
    isValid,
    level,
    messages,
    totalCalories,
    totalProtein,
    totalFat,
    totalCarbs,
  };
}
