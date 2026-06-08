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

/**
 * Lấy key có scope theo email user hiện tại (nếu có).
 * Tránh nhiều tài khoản dùng chung điểm trên cùng trình duyệt.
 */
function getStorageKey() {
  try {
    const raw = localStorage.getItem("nutrigain_auth");
    if (raw) {
      const session = JSON.parse(raw);
      const email = session?.email || session?.user?.email;
      if (email) return `${STORAGE_KEY}_${email}`;
    }
  } catch { /* ignore */ }
  return STORAGE_KEY;
}

/** @returns {{ totalPoints: number, ssCount: number, rankHistory: Array }} */
export function loadGamificationStats() {
  try {
    const raw = localStorage.getItem(getStorageKey());
    if (!raw) return { totalPoints: 0, ssCount: 0, rankHistory: [] };
    const parsed = JSON.parse(raw);
    return {
      totalPoints:  Number(parsed.totalPoints  ?? 0),
      ssCount:      Number(parsed.ssCount      ?? 0),
      rankHistory:  Array.isArray(parsed.rankHistory) ? parsed.rankHistory : [],
    };
  } catch {
    return { totalPoints: 0, ssCount: 0, rankHistory: [] };
  }
}

/**
 * Record points earned from a meal tick session.
 * Called automatically by MealScoreInline on every tick — idempotent per meal+day.
 * Mỗi ngày tối đa 3 bữa × 65 điểm (SS + diversity) = 195 điểm.
 *
 * @param {{ rank: string, points: number, mealType: string }} entry
 */
export function recordMealPoints({ rank, points, mealType }) {
  if (!rank || points <= 0) return;
  const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
  const stats = loadGamificationStats();

  // Dedup: only record once per mealType per day
  const key = `${today}__${mealType}`;
  const alreadyRecorded = stats.rankHistory.some((h) => h.key === key);
  if (alreadyRecorded) {
    // Update if better rank achieved today (e.g. user improved meal)
    const existing = stats.rankHistory.find((h) => h.key === key);
    if (!existing || existing.points >= points) return;
    // Revert old points, apply new delta
    stats.totalPoints = Math.max(0, stats.totalPoints - existing.points + points);
    if (rank === "SS" && existing.rank !== "SS") stats.ssCount += 1;
    existing.rank   = rank;
    existing.points = points;
    existing.ts     = Date.now();
  } else {
    // Kiểm tra tổng điểm đã cộng trong ngày hôm nay
    const todayEntries = stats.rankHistory.filter((h) => h.date === today);
    const todayMealTypes = new Set(todayEntries.map((h) => h.mealType));

    // Mỗi ngày chỉ được cộng điểm từ tối đa 3 bữa (sáng/trưa/tối)
    // Nếu mealType này đã cộng rồi thì bỏ qua (tránh cộng dồn khi sinh thực đơn mới)
    const normalizedMealType = String(mealType).toLowerCase();
    const alreadyHasThisMeal = todayEntries.some((h) =>
      String(h.mealType || "").toLowerCase() === normalizedMealType
    );
    if (alreadyHasThisMeal) return;

    stats.totalPoints += points;
    if (rank === "SS") stats.ssCount += 1;
    stats.rankHistory.unshift({ key, rank, points, mealType, date: today, ts: Date.now() });
    // Keep last 90 entries
    if (stats.rankHistory.length > 90) stats.rankHistory.length = 90;
  }

  try {
    localStorage.setItem(getStorageKey(), JSON.stringify(stats));
  } catch { /* storage full — silently skip */ }
}
