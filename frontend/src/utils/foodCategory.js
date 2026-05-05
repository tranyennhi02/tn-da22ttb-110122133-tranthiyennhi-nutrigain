export const foodCategoryMap = {
  "Ngô": {
    category: "Tinh bột",
    subCategory: "Ngũ cốc",
  },
  "Cơm": {
    category: "Tinh bột",
    subCategory: "Ngũ cốc",
  },
  "Mì ống": {
    category: "Tinh bột",
    subCategory: "Ngũ cốc",
  },
  "Ngũ cốc": {
    category: "Tinh bột",
    subCategory: "Ngũ cốc",
  },
  "Khoai tây": {
    category: "Tinh bột",
    subCategory: "Củ",
  },
  "Khoai lang": {
    category: "Tinh bột",
    subCategory: "Củ",
  },
  "Khoai môn": {
    category: "Tinh bột",
    subCategory: "Củ",
  },
  "Khoai môn Tahiti": {
    category: "Tinh bột",
    subCategory: "Củ",
  },
  "Đậu phụ": {
    category: "Đạm",
    subCategory: "Đạm thực vật",
  },
  "Đậu hũ": {
    category: "Đạm",
    subCategory: "Đạm thực vật",
  },
  "Đậu nành": {
    category: "Đạm",
    subCategory: "Đạm thực vật",
  },
  "Cá": {
    category: "Đạm",
    subCategory: "Hải sản",
  },
  "Cua": {
    category: "Đạm",
    subCategory: "Hải sản",
  },
  "Trứng cá": {
    category: "Đạm",
    subCategory: "Hải sản",
  },
  "Thịt cừu": {
    category: "Đạm",
    subCategory: "Thịt",
  },
  "Gà": {
    category: "Đạm",
    subCategory: "Thịt",
  },
  "Sữa chua": {
    category: "Sữa",
    subCategory: "Sữa chua",
  },
  "Cải xoăn": {
    category: "Rau củ",
    subCategory: "Rau lá",
  },
  "Cải brussels": {
    category: "Rau củ",
    subCategory: "Rau họ cải",
  },
  "Táo tàu": {
    category: "Trái cây",
    subCategory: "Quả khô",
  },
  "Đồ ăn nhanh": {
    category: "Khác",
    subCategory: "Món chế biến",
  },
};

const categoryRules = [
  { terms: ["mut", "jam", "jelly"], category: "Bánh/ngọt", subCategory: "Món ngọt" },
  { terms: ["nuoc cam", "nuoc dua", "nuoc ep", "nuoc trai cay", "orange juice", "juice"], category: "Đồ uống tự nhiên", subCategory: "Đồ uống" },
  { terms: ["kem lua mi", "cream of wheat"], category: "Tinh bột", subCategory: "Ngũ cốc" },
  { terms: ["do an nhanh", "fast food", "mcdonald", "burger", "kfc", "subway", "pizza"], category: "Khác", subCategory: "Món chế biến" },
  { terms: ["ngo", "corn"], category: "Tinh bột", subCategory: "Ngũ cốc" },
  { terms: ["com", "rice"], category: "Tinh bột", subCategory: "Ngũ cốc" },
  { terms: ["mi ong", "pasta", "noodle", "spaghetti"], category: "Tinh bột", subCategory: "Ngũ cốc" },
  { terms: ["ngu coc", "cereal", "grain", "oat", "oatmeal"], category: "Tinh bột", subCategory: "Ngũ cốc" },
  { terms: ["khoai tay", "potato"], category: "Tinh bột", subCategory: "Củ" },
  { terms: ["khoai lang", "sweet potato"], category: "Tinh bột", subCategory: "Củ" },
  { terms: ["khoai mon", "taro"], category: "Tinh bột", subCategory: "Củ" },
  { terms: ["dau phu", "dau hu", "tofu"], category: "Đạm", subCategory: "Đạm thực vật" },
  { terms: ["dau nanh", "soybean", "soy"], category: "Đạm", subCategory: "Đạm thực vật" },
  { terms: ["trung ca", "roe"], category: "Đạm", subCategory: "Hải sản" },
  { terms: ["cua", "crab"], category: "Đạm", subCategory: "Hải sản" },
  { terms: ["ca", "fish", "salmon", "tuna"], category: "Đạm", subCategory: "Hải sản" },
  { terms: ["tom", "shrimp", "prawn", "lobster", "oyster", "clam"], category: "Đạm", subCategory: "Hải sản" },
  { terms: ["thit cuu", "lamb", "mutton"], category: "Đạm", subCategory: "Thịt" },
  { terms: ["ga", "chicken", "turkey"], category: "Đạm", subCategory: "Thịt" },
  { terms: ["bo", "beef", "pork", "heo", "lon"], category: "Đạm", subCategory: "Thịt" },
  { terms: ["trung", "egg"], category: "Đạm", subCategory: "Trứng" },
  { terms: ["sua chua", "yogurt", "yoghurt"], category: "Sữa", subCategory: "Sữa chua" },
  { terms: ["sua", "milk"], category: "Sữa", subCategory: "Sữa" },
  { terms: ["cai xoan", "kale"], category: "Rau củ", subCategory: "Rau lá" },
  { terms: ["cai brussels", "brussels sprout"], category: "Rau củ", subCategory: "Rau họ cải" },
  { terms: ["rau", "vegetable", "broccoli", "spinach"], category: "Rau củ", subCategory: "Rau củ" },
  { terms: ["tao tau", "jujube", "dried date"], category: "Trái cây", subCategory: "Quả khô" },
  { terms: ["chuoi", "banana", "apple", "tao", "fruit"], category: "Trái cây", subCategory: "Trái cây" },
];

const rawCategoryLabels = {
  staple: "Tinh bột",
  grain: "Tinh bột",
  starch: "Tinh bột",
  carb: "Tinh bột",
  carbohydrate: "Tinh bột",
  vegetable: "Rau củ",
  fruit: "Trái cây",
  dairy: "Sữa",
  milk: "Sữa",
  drink_natural: "Đồ uống tự nhiên",
  dessert_sweets: "Bánh/ngọt",
  sweet_spread: "Bánh/ngọt",
  starch_grain: "Tinh bột",
  starch_tuber: "Tinh bột",
  protein_meat: "Đạm",
  protein_seafood: "Đạm",
  protein_plant: "Đạm",
  fats_good: "Chất béo tốt",
  fat: "Chất béo tốt",
  healthy_fat: "Chất béo tốt",
  side: "Món phụ",
  other: "Khác",
  protein: "Đạm",
  meat: "Đạm",
  seafood: "Đạm",
  fish: "Đạm",
  egg: "Đạm",
  plant_protein: "Đạm",
};

const unsafeFallbackCategories = new Set(["dam"]);
const unsafeFallbackSubCategories = new Set(["thit", "hai san", "meat", "seafood"]);

const exactCategoryLookup = new Map(
  Object.entries(foodCategoryMap).map(([name, category]) => [normalizedText(name), category]),
);

export function stripAccents(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D");
}

function normalizedText(value) {
  return stripAccents(value).toLowerCase().trim().replace(/\s+/g, " ");
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function hasFoodTerm(text, term) {
  const normalizedTerm = normalizedText(term);
  if (!normalizedTerm) return false;

  const pattern = new RegExp(`(^|[^a-z0-9])${escapeRegExp(normalizedTerm)}($|[^a-z0-9])`);
  return pattern.test(text);
}

function inferCategoryByName(name) {
  const lookupKey = normalizedText(name);
  const exactMatch = exactCategoryLookup.get(lookupKey);
  if (exactMatch) return exactMatch;

  return categoryRules.find((entry) => entry.terms.some((term) => hasFoodTerm(lookupKey, term)));
}

function safeFallbackCategory(food) {
  const existingCategory = localizeFoodCategory(food?.category || food?.type || "");
  if (!existingCategory || unsafeFallbackCategories.has(normalizedText(existingCategory))) {
    return "Khác";
  }

  return existingCategory;
}

function safeFallbackSubCategory(food) {
  const existingSubCategory = String(food?.subCategory || "").trim();
  if (!existingSubCategory || unsafeFallbackSubCategories.has(normalizedText(existingSubCategory))) {
    return "Chưa phân loại";
  }

  return existingSubCategory;
}

export function normalizeFoodCategory(food) {
  if (!food || !food.name) return food;

  const matched = inferCategoryByName(food.name);
  if (matched) {
    return {
      ...food,
      category: matched.category,
      subCategory: matched.subCategory,
    };
  }

  return {
    ...food,
    category: safeFallbackCategory(food),
    subCategory: safeFallbackSubCategory(food),
  };
}

export function localizeFoodCategory(value) {
  const rawKey = normalizedText(value).replace(/\s+/g, "_");
  return rawCategoryLabels[rawKey] || value || "Khác";
}
