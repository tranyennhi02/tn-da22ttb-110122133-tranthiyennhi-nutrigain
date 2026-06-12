/**
 * mealRank.js
 * Pure utility functions for the "Bữa Ăn Hoàn Hảo" gamification system.
 * All calculations are local — zero API calls.
 */

// ─── Rank Calculator ───────────────────────────────────────────────────────

/** @type {Array<{max: number, rank: string, label: string, color: string}>} */
const RANK_TIERS = [
  { max: 5,   rank: "SS", label: "🎯 Bữa ăn hoàn hảo!",            color: "gold"    },
  { max: 20,  rank: "S",  label: "🔥 Cân bằng cực tốt!",            color: "emerald" },
  { max: 50,  rank: "A",  label: "✅ Bữa ăn khá chuẩn!",            color: "green"   },
  { max: 100, rank: "B",  label: "👍 Khá ổn, có thể tối ưu thêm.",  color: "blue"    },
  { max: 150, rank: "C",  label: "⚠ Bữa ăn hơi lệch mục tiêu.",    color: "amber"   },
  { max: Infinity, rank: "D", label: "❌ Bạn cần điều chỉnh thêm.", color: "red"     },
];

/**
 * Compute meal rank from calorie difference.
 *
 * @param {number} totalKcal   - kcal from selected items
 * @param {number} targetKcal  - kcal target for this meal
 * @returns {{ rank: string, label: string, color: string, difference: number, accuracyPct: number } | null}
 *   null when targetKcal is 0 or undefined
 */
export function computeMealRank(totalKcal, targetKcal) {
  if (!targetKcal || targetKcal <= 0) return null;

  const difference = Math.abs(targetKcal - totalKcal);
  const tier = RANK_TIERS.find((t) => difference <= t.max) ?? RANK_TIERS[RANK_TIERS.length - 1];
  const accuracyPct = Math.max(0, Math.min(100, Math.round((1 - difference / targetKcal) * 100 * 10) / 10));

  return {
    rank: tier.rank,
    label: tier.label,
    color: tier.color,
    difference,
    accuracyPct,
  };
}

/**
 * Detect "Suýt Hoàn Hảo" (Almost Perfect) state.
 * Only triggers when user is UNDER target by 1–10 kcal.
 *
 * @param {number} totalKcal
 * @param {number} targetKcal
 * @returns {{ active: boolean, deficit: number }}
 */
export function computeAlmostPerfect(totalKcal, targetKcal) {
  if (!targetKcal || targetKcal <= 0) return { active: false, deficit: 0 };
  const deficit = targetKcal - totalKcal; // positive = under target
  if (deficit >= 1 && deficit <= 10) {
    return { active: true, deficit: Math.round(deficit) };
  }
  return { active: false, deficit: 0 };
}

// ─── Diversity Calculator ──────────────────────────────────────────────────

/**
 * Ordered food-group normalization rules (case-insensitive substring match,
 * first match wins). More specific patterns come before shorter ones.
 */
const DIVERSITY_RULES = [
  { patterns: ["đậu phụ", "đậu hũ", "tofu", "tàu hũ"],                                   key: "dau_phu"  },
  { patterns: ["bột yến mạch", "yến mạch", "oat"],                                         key: "yen_mach" },
  { patterns: ["ức gà", "thịt gà", "đùi gà", "cánh gà"],                                   key: "ga"       },
  { patterns: ["gà"],                                                                         key: "ga"       },
  { patterns: ["thịt heo", "thịt lợn", "thịt bò", "thịt"],                                 key: "thit"     },
  { patterns: ["cá hồi", "cá ngừ", "cá basa", "cá thu", "cá trích", "cá"],                 key: "ca"       },
  { patterns: ["trứng"],                                                                       key: "trung"    },
  { patterns: ["sữa chua", "yogurt", "yaourt", "phô mai", "sữa"],                           key: "sua"      },
  { patterns: ["rau xanh", "salad", "cải xanh", "cải thìa", "cải ngọt", "rau cải", "rau"], key: "rau"      },
  { patterns: ["cơm trắng", "cơm gạo lứt", "cơm"],                                          key: "com"      },
  { patterns: ["tôm"],                                                                         key: "tom"      },
  { patterns: ["cua"],                                                                         key: "cua"      },
  { patterns: ["thịt bò", "bò"],                                                              key: "bo"       },
];

/**
 * Resolve a food item's display name to a canonical food-group key.
 *
 * @param {object} item  - food item with name/dish_name_vi/food_id fields
 * @returns {string}     - canonical key or fallback to food_id
 */
export function resolveFoodGroup(item) {
  const name = String(
    item.name ?? item.dish_name_vi ?? item.display_name ?? item.name_vi ?? ""
  ).toLowerCase();

  for (const rule of DIVERSITY_RULES) {
    if (rule.patterns.some((p) => name.includes(p.toLowerCase()))) {
      return rule.key;
    }
  }

  // fallback: unique group per item
  return String(item.id ?? item.food_id ?? name ?? Math.random());
}

/**
 * Compute diversity score from selected items.
 *
 * @param {Array} selectedItems
 * @returns {{ score: number, diversityPoints: number }}
 *   score = count of unique food groups
 *   diversityPoints = 15 if score >= 3, else 0
 */
export function computeDiversity(selectedItems) {
  if (!selectedItems || selectedItems.length === 0) {
    return { score: 0, diversityPoints: 0 };
  }
  const groups = new Set(selectedItems.map(resolveFoodGroup));
  const score = groups.size;
  return { score, diversityPoints: score >= 3 ? 15 : 0 };
}

// ─── Points preview (display only, not submitted) ──────────────────────────

const RANK_BASE_POINTS = { SS: 50, S: 35, A: 20, B: 10, C: 0, D: 0 };

/**
 * Preview total points the user would earn if they confirm now.
 *
 * @param {string} rank
 * @param {number} diversityPoints
 * @param {boolean} almostPerfect
 * @returns {number}
 */
export function previewPoints(rank, diversityPoints, almostPerfect) {
  const base = RANK_BASE_POINTS[rank] ?? 0;
  const almostBonus = almostPerfect && rank !== "SS" ? 10 : 0;
  return base + diversityPoints + almostBonus;
}

// ─── Local gamification stats (localStorage) ──────────────────────────────

const STORAGE_KEY = "nutrigain_gami_stats";
const VN_TIMEZONE = "Asia/Ho_Chi_Minh";
const MAIN_MEAL_TYPES = new Set(["breakfast", "lunch", "dinner"]);

const MEAL_TYPE_ALIASES = {
  breakfast: "breakfast",
  lunch: "lunch",
  dinner: "dinner",
  snacks: "snacks",
  snack: "snacks",
  "bữa sáng": "breakfast",
  "bua sang": "breakfast",
  "bữa trưa": "lunch",
  "bua trua": "lunch",
  "bữa tối": "dinner",
  "bua toi": "dinner",
  "bữa phụ": "snacks",
  "bua phu": "snacks",
};

function getVietnamTodayKey() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: VN_TIMEZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

function normalizeMealTypeForPoints(mealType) {
  const raw = String(mealType || "").trim().toLowerCase();
  return MEAL_TYPE_ALIASES[raw] || raw;
}

/**
 * @deprecated Không còn được dùng kể từ khi áp dụng chính sách khóa điểm theo ngày.
 * Giữ lại để tham khảo — KHÔNG gọi hàm này.
 */
// eslint-disable-next-line no-unused-vars
function revertTodayPoints(stats, today) {
  const todayEntries = stats.rankHistory.filter((entry) => entry.date === today);
  const revertedPoints = todayEntries.reduce((sum, entry) => sum + (Number(entry.points) || 0), 0);
  const revertedSsCount = todayEntries.filter((entry) => entry.rank === "SS").length;
  stats.rankHistory = stats.rankHistory.filter((entry) => entry.date !== today);
  stats.ssCount = Math.max(0, (stats.ssCount || 0) - revertedSsCount);
  if (stats.dailyPlanByDate) {
    delete stats.dailyPlanByDate[today];
  }
  return revertedPoints;
}

/**
 * Lấy key có scope theo email user hiện tại (nếu có).
 * Tránh nhiều tài khoản dùng chung điểm trên cùng trình duyệt.
 * Email được cache riêng để không bị mất khi session hết hạn.
 */
function getStorageKey() {
  try {
    // Ưu tiên đọc từ session auth
    const raw = localStorage.getItem("nutrigain_auth");
    if (raw) {
      const session = JSON.parse(raw);
      const email = session?.email || session?.user?.email;
      if (email) {
        // Cache email riêng để dùng khi session hết hạn
        localStorage.setItem("nutrigain_last_user_email", email);
        return `${STORAGE_KEY}_${email}`;
      }
    }
    // Fallback: dùng email đã cache từ lần đăng nhập trước
    const cachedEmail = localStorage.getItem("nutrigain_last_user_email");
    if (cachedEmail) {
      return `${STORAGE_KEY}_${cachedEmail}`;
    }
  } catch { /* ignore */ }
  return STORAGE_KEY;
}

/** @returns {{ totalPoints: number, ssCount: number, rankHistory: Array, dailyPlanByDate: Record<string, string> }} */
export function loadGamificationStats() {
  try {
    const raw = localStorage.getItem(getStorageKey());
    if (!raw) return { totalPoints: 0, ssCount: 0, rankHistory: [], dailyPlanByDate: {} };
    const parsed = JSON.parse(raw);
    return {
      totalPoints: Number(parsed.totalPoints ?? 0),
      ssCount: Number(parsed.ssCount ?? 0),
      rankHistory: Array.isArray(parsed.rankHistory) ? parsed.rankHistory : [],
      dailyPlanByDate: parsed.dailyPlanByDate && typeof parsed.dailyPlanByDate === "object"
        ? parsed.dailyPlanByDate
        : {},
    };
  } catch {
    return { totalPoints: 0, ssCount: 0, rankHistory: [], dailyPlanByDate: {} };
  }
}

/**
 * Record points earned from a meal tick session.
 * Called automatically by MealScoreInline on every tick — idempotent per meal+day.
 *
 * RULE: Mỗi ngày chỉ 1 thực đơn đầu tiên được tính điểm (tối đa 3 bữa chính).
 * Nếu user tạo thêm thực đơn trong ngày và tick món → điểm KHÔNG thay đổi.
 * Điểm chỉ được cộng tiếp vào ngày hôm sau với thực đơn mới.
 *
 * @param {{ rank: string, points: number, mealType: string, mealPlanId?: string|number|null }} entry
 */
export function recordMealPoints({ rank, points, mealType, mealPlanId = null }) {
  if (!rank || points <= 0 || !mealType) return;

  const today = getVietnamTodayKey();
  const canonicalMealType = normalizeMealTypeForPoints(mealType);
  if (!MAIN_MEAL_TYPES.has(canonicalMealType)) return;

  const stats = loadGamificationStats();
  if (!stats.dailyPlanByDate) stats.dailyPlanByDate = {};

  const normalizedPlanId = mealPlanId != null && mealPlanId !== "" ? String(mealPlanId) : null;
  const lockedPlanId = stats.dailyPlanByDate[today] || null;

  // ── KHÓA NGÀY: Nếu ngày hôm nay đã có thực đơn được tính điểm,
  // và thực đơn mới khác với thực đơn đầu tiên → bỏ qua hoàn toàn.
  // Điểm hôm nay KHÔNG bị xóa / cộng thêm từ thực đơn khác.
  if (normalizedPlanId && lockedPlanId && lockedPlanId !== normalizedPlanId) {
    // Kiểm tra xem ngày hôm nay đã có điểm thực sự chưa
    const todayHasPoints = stats.rankHistory.some((entry) => entry.date === today);
    if (todayHasPoints) {
      // Đã có điểm hôm nay → từ chối thực đơn mới, giữ nguyên toàn bộ
      return;
    }
    // Chưa có điểm thực sự (chỉ có locked plan) → cập nhật locked plan
    stats.dailyPlanByDate[today] = normalizedPlanId;
  } else if (normalizedPlanId && !lockedPlanId) {
    // Lần đầu trong ngày → ghi nhận thực đơn này làm "thực đơn gốc" của ngày
    stats.dailyPlanByDate[today] = normalizedPlanId;
  }

  const key = `${today}__${canonicalMealType}`;
  const alreadyRecorded = stats.rankHistory.some((entry) => entry.key === key);

  if (alreadyRecorded) {
    // Bữa này đã được tính điểm hôm nay → chỉ cập nhật nếu điểm MỚI CAO HƠN
    // (cùng thực đơn, user tick thêm món để tối ưu rank)
    const existing = stats.rankHistory.find((entry) => entry.key === key);
    if (!existing || existing.points >= points) return;

    // Chỉ cho phép nâng điểm nếu vẫn thuộc cùng thực đơn gốc của ngày
    const currentLocked = stats.dailyPlanByDate[today];
    if (normalizedPlanId && currentLocked && currentLocked !== normalizedPlanId) {
      // Thực đơn khác → không cho nâng điểm
      return;
    }

    stats.totalPoints = Math.max(0, stats.totalPoints - existing.points + points);
    if (rank === "SS" && existing.rank !== "SS") stats.ssCount += 1;
    existing.rank = rank;
    existing.points = points;
    existing.mealType = canonicalMealType;
    existing.mealPlanId = normalizedPlanId;
    existing.ts = Date.now();
  } else {
    // Bữa này chưa được tính hôm nay → cộng điểm
    stats.totalPoints += points;
    if (rank === "SS") stats.ssCount += 1;
    stats.rankHistory.unshift({
      key,
      rank,
      points,
      mealType: canonicalMealType,
      mealPlanId: normalizedPlanId,
      date: today,
      ts: Date.now(),
    });
    if (stats.rankHistory.length > 90) stats.rankHistory.length = 90;
  }

  try {
    localStorage.setItem(getStorageKey(), JSON.stringify(stats));
  } catch { /* storage full — silently skip */ }
}
