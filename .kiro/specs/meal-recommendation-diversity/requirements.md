# Requirements Document

## Introduction

NutriGain is a Vietnamese nutrition web application that generates personalised daily meal plans for users. Its recommendation engine (`recommender_service.py`) currently produces repetitive meals because:

1. Foods with the same core ingredient but different names or preparation descriptors are treated as distinct items (e.g. *Đậu phụ mềm*, *Đậu phụ cứng*, and *Đậu hũ* are all tofu yet count as three separate foods).
2. The semantic-key deduplication set (`selected_semantic_keys`) resets between meals, so a semantic group used in breakfast can reappear in lunch and dinner.
3. Day-level category limits are too permissive (e.g. up to 2 bean/tofu items per day).
4. No scoring mechanism exists to measure or optimise whole-day diversity.
5. Meal-type appropriateness for Vietnamese breakfast versus lunch/dinner is not enforced.

This feature improves diversity in the generated plans by expanding ingredient grouping, tightening cross-meal deduplication, adding per-category day limits, and introducing a diversity score — entirely within `recommender_service.py` without creating new files.

---

## Glossary

- **Recommender_Service**: The module `backend/app/services/recommender_service.py` that produces daily meal plans.
- **Semantic_Key**: A string label that groups foods sharing a core ingredient (e.g. `"tofu"` groups all tofu variants).
- **Normalize_Food_Key**: A new pure function that maps a food name string to its canonical root ingredient key.
- **SEMANTIC_FOOD_GROUP_TERMS**: An existing module-level constant (tuple of `(key, terms)` pairs) that the function `normalize_food_similarity_key` iterates to assign semantic keys.
- **selected_semantic_keys**: A `set[str]` that tracks which semantic groups have already been selected; currently scoped per-meal.
- **Day_Scope**: Variables or data structures that persist across all meals (breakfast, lunch, dinner) within a single call to `pickBalancedMeal`.
- **Day_Plan**: The complete collection of food items across all meals returned by a single `pickBalancedMeal` call.
- **Diversity_Score**: A float in `[0.0, 1.0]` produced by `compute_diversity_score` measuring ingredient variety across a Day_Plan.
- **Protein_Source**: One of the protein groups — meat, fish/seafood, egg, legume/tofu, or dairy — used to track cross-meal protein variety.
- **Carb_Source**: One of the carbohydrate groups — rice, noodle/pasta, potato/tuber, bread, oat/cereal — used to track cross-meal carb variety.
- **Descriptor_Word**: A cooking or processing adjective (e.g. *mềm*, *cứng*, *luộc*, *smoked*) that does not change the core identity of an ingredient.
- **Normalize_Text_Vi**: Existing function that strips Vietnamese diacritical marks, lowercases, and replaces `đ` → `d`.
- **family_counts**: Existing `dict[str, int]` tracking food-family occurrences across the day.
- **bean_count**: Existing `int` counter for `plant_protein` category foods selected across the day.

---

## Requirements

### Requirement 1: Core Ingredient Normalisation Function

**User Story:** As a developer maintaining the recommendation engine, I want a fast pure function that reduces a Vietnamese or English food name to its canonical root ingredient key, so that foods sharing the same ingredient are detected as duplicates regardless of preparation descriptors or spelling variants.

#### Acceptance Criteria

1. THE Recommender_Service SHALL expose a module-level function `normalize_food_key(food_name: str) -> str`.
2. WHEN `normalize_food_key` is called, THE Recommender_Service SHALL first apply `normalize_text_vi` to lowercase and strip diacritical marks from `food_name`.
3. WHEN `normalize_food_key` is called, THE Recommender_Service SHALL strip all Descriptor_Words — including *mềm*, *cứng*, *chín*, *luộc*, *sấy*, *ít béo*, *nguyên hạt*, *đóng hộp*, *giảm natri*, *non-fat*, *fat-free*, *reduced*, *low-fat*, *smoked*, *dried*, *raw*, *fresh* — from the normalised string before extracting the root keyword.
4. WHEN the normalised string contains any tofu-family token (*đậu hũ*, *dau hu*, *đậu phụ*, *dau phu*, *tau hu*), THE Recommender_Service SHALL return `"dau phu"` as the canonical key.
5. WHEN the normalised string contains any leafy-green token (*rau cải*, *rau bina*, *rau chân vịt*, *cải xanh*, *rau muống*, *rau cai*, *rau bina*, *rau chan vit*, *cai xanh*, *rau muong*), THE Recommender_Service SHALL return `"rau"` as the canonical key.
6. WHEN the normalised string does not match any alias mapping, THE Recommender_Service SHALL return the longest remaining non-descriptor token as the root key.
7. THE `normalize_food_key` function SHALL complete in O(k) time where k is the count of Descriptor_Words, performing no database lookups.
8. FOR ALL valid food name strings `s`, `normalize_food_key(normalize_food_key(s))` SHALL equal `normalize_food_key(s)` (idempotence).

---

### Requirement 2: Expanded Semantic Food Group Terms

**User Story:** As a developer, I want `SEMANTIC_FOOD_GROUP_TERMS` to cover a comprehensive set of Vietnamese and English food categories so that the semantic deduplication logic blocks more real-world duplicates.

#### Acceptance Criteria

1. THE Recommender_Service SHALL include in `SEMANTIC_FOOD_GROUP_TERMS` a `"tofu"` group containing all accent-stripped tokens for *đậu hũ*, *đậu phụ mềm*, *đậu phụ cứng*, and their English equivalents (*tofu*, *bean curd*, *tau hu*).
2. THE Recommender_Service SHALL include in `SEMANTIC_FOOD_GROUP_TERMS` a `"leafy_greens"` group containing accent-stripped tokens for *rau cải*, *rau bina*, *rau chân vịt*, *cải xanh*, *rau muống*, *spinach*, *watercress*, *kale*, *bok choy*.
3. THE Recommender_Service SHALL include in `SEMANTIC_FOOD_GROUP_TERMS` a `"root_vegetables"` group containing accent-stripped tokens for *cà rốt*, *củ dền*, *củ cải*, *carrot*, *beet*, *radish*, *turnip*.
4. THE Recommender_Service SHALL include in `SEMANTIC_FOOD_GROUP_TERMS` a `"rice"` group containing accent-stripped tokens for *cơm trắng*, *cơm gạo lứt*, *gạo*, *rice*, *brown rice*, *white rice*.
5. THE Recommender_Service SHALL include in `SEMANTIC_FOOD_GROUP_TERMS` an `"oat"` group containing tokens *yến mạch*, *yen mach*, *oat*, *oatmeal*, *granola*, *rolled oat*.
6. THE Recommender_Service SHALL include in `SEMANTIC_FOOD_GROUP_TERMS` a `"banana"` group containing tokens *chuối*, *chuoi*, *banana*.
7. THE Recommender_Service SHALL include in `SEMANTIC_FOOD_GROUP_TERMS` a `"citrus_fruit"` group containing tokens *cam*, *orange*, *quýt*, *quyt*, *mandarin*, *tangerine*, *bưởi*, *buoi*, *grapefruit*.
8. THE Recommender_Service SHALL include in `SEMANTIC_FOOD_GROUP_TERMS` a `"legume"` group containing tokens *đậu*, *dau*, *đỗ*, *do*, *bean*, *lentil*, *chickpea*, *đậu đen*, *dau den*, *đậu đỏ*, *dau do*, *đậu xanh*, *dau xanh*.
9. THE Recommender_Service SHALL include in `SEMANTIC_FOOD_GROUP_TERMS` a `"chicken"` group containing tokens *thịt gà*, *thit ga*, *ức gà*, *uc ga*, *gà nạc*, *ga nac*, *chicken*, *turkey*.
10. THE Recommender_Service SHALL include in `SEMANTIC_FOOD_GROUP_TERMS` a `"fish"` group containing tokens *cá hồi*, *ca hoi*, *salmon*, *cá thu*, *ca thu*, *mackerel*, *cá ngừ*, *ca ngu*, *tuna*, *cá*, *ca*, *fish*.
11. THE Recommender_Service SHALL include in `SEMANTIC_FOOD_GROUP_TERMS` a `"pork"` group containing tokens *thịt heo*, *thit heo*, *thịt lợn*, *thit lon*, *sườn heo*, *suon heo*, *pork*.
12. THE Recommender_Service SHALL include in `SEMANTIC_FOOD_GROUP_TERMS` a `"beef"` group containing tokens *thịt bò*, *thit bo*, *bò nạc*, *bo nac*, *beef*, *lean beef*.
13. WHEN `normalize_food_similarity_key` is called, THE Recommender_Service SHALL evaluate all entries in the expanded `SEMANTIC_FOOD_GROUP_TERMS` in order and return the key of the first matching group.
14. THE Recommender_Service SHALL preserve all existing group entries already present in `SEMANTIC_FOOD_GROUP_TERMS` so that previously working semantic deduplication is not broken.

---

### Requirement 3: Day-Level Cross-Meal Semantic Deduplication

**User Story:** As a user, I want my daily meal plan to not repeat the same core ingredient across breakfast, lunch, and dinner, so that I get genuinely varied nutrition throughout the day.

#### Acceptance Criteria

1. WHEN `pickBalancedMeal` begins iterating over meals, THE Recommender_Service SHALL initialise `selected_semantic_keys` once at Day_Scope — before the meal loop — rather than once per meal.
2. WHEN a food item is added to any meal, THE Recommender_Service SHALL add that food's Semantic_Key to the shared day-level `selected_semantic_keys` set.
3. WHEN selecting a food for any slot in any meal, THE Recommender_Service SHALL use `_prefer_semantic_distinct` — which filters the candidate pool against the shared `selected_semantic_keys` — before choosing a candidate.
4. THE Recommender_Service SHALL maintain a day-level `set[str]` named `selected_day_food_keys` that tracks the `normalize_food_key` value of every food item selected across all meals.
5. WHEN selecting a candidate food for any slot, THE Recommender_Service SHALL skip any candidate whose `normalize_food_key` matches a value already present in `selected_day_food_keys`, unless the entire candidate pool for that slot consists of already-seen keys.
6. WHEN a food item is added to any meal, THE Recommender_Service SHALL add its `normalize_food_key` value to `selected_day_food_keys`.
7. THE existing `seen_food_ids` and `seen_food_names` sets SHALL remain at Day_Scope as currently implemented, ensuring no food ID or exact name is repeated across the day.

---

### Requirement 4: Diversity Scoring Function

**User Story:** As a developer or QA engineer, I want a function that scores a complete Day_Plan for ingredient variety, so that I can measure improvement and set quality thresholds.

#### Acceptance Criteria

1. THE Recommender_Service SHALL expose a module-level function `compute_diversity_score(plan: dict[str, list]) -> float`.
2. WHEN `compute_diversity_score` is called with a Day_Plan mapping meal names to lists of food item dicts, THE Recommender_Service SHALL compute `ingredient_diversity` as the ratio of unique `normalize_food_key` values to total food items across all meals.
3. WHEN `compute_diversity_score` is called, THE Recommender_Service SHALL compute `protein_diversity` as the count of distinct Protein_Sources present in the plan, where each source is one of `{"meat", "fish", "egg", "legume", "dairy"}`.
4. WHEN `compute_diversity_score` is called, THE Recommender_Service SHALL compute `vegetable_diversity` as the count of distinct vegetable Semantic_Key values (groups whose key ends with `"_greens"`, `"_vegetables"`, or whose category is `"vegetable"`) present in the plan.
5. WHEN `compute_diversity_score` is called, THE Recommender_Service SHALL compute `carb_diversity` as the count of distinct Carb_Source groups — one of `{"rice", "noodle", "oat", "potato", "bread"}` — present in the plan.
6. WHEN `compute_diversity_score` is called, THE Recommender_Service SHALL return a single float equal to the weighted average: `0.4 × ingredient_diversity + 0.3 × min(protein_diversity / 3, 1.0) + 0.15 × min(vegetable_diversity / 2, 1.0) + 0.15 × min(carb_diversity / 2, 1.0)`, rounded to four decimal places.
7. THE return value of `compute_diversity_score` SHALL always be in the closed interval `[0.0, 1.0]`.
8. WHEN `compute_diversity_score` is called with an empty plan or a plan containing zero food items, THE Recommender_Service SHALL return `0.0`.
9. FOR ALL valid Day_Plans `p`, `compute_diversity_score(p)` SHALL return the same value when called multiple times with the same input (determinism).

---

### Requirement 5: Tightened Per-Category Day Limits

**User Story:** As a user, I want the daily meal plan to respect stricter per-category limits so that no single ingredient group (e.g. tofu, rice, oats) dominates my plan.

#### Acceptance Criteria

1. WHEN `pickBalancedMeal` is selecting a food, THE Recommender_Service SHALL reject any candidate from the `"tofu"` or `"soy"` Semantic_Key groups when the combined tofu/soy count for the day has already reached `1`.
2. WHEN `pickBalancedMeal` is selecting a food, THE Recommender_Service SHALL reject any candidate whose Semantic_Key is `"oat"` when the oat count for the day has already reached `1`.
3. WHEN `pickBalancedMeal` is selecting a food, THE Recommender_Service SHALL reject any candidate whose Semantic_Key is `"rice"` when the rice count for the day has already reached `1`.
4. WHEN `pickBalancedMeal` is selecting a food, THE Recommender_Service SHALL reject any candidate whose Semantic_Key is `"leafy_greens"` when the leafy-greens count for the day has already reached `2`.
5. WHEN a meal has already included a Protein_Source group (e.g. `"chicken"`), THE Recommender_Service SHALL prefer — via `_prefer_semantic_distinct` — a different Protein_Source group for subsequent meals, so that chicken at lunch is not repeated at dinner.
6. WHEN rice has been selected in a prior meal, THE Recommender_Service SHALL apply a score penalty to rice candidates in subsequent meals and prefer noodle, potato, or bread Carb_Source candidates instead.
7. IF the entire candidate pool for a given slot consists only of items that would breach a day-limit, THEN THE Recommender_Service SHALL relax that limit and select from the full pool, logging a warning.

---

### Requirement 6: Meal-Type Appropriate Food Guidance (Vietnamese Context)

**User Story:** As a Vietnamese user, I want breakfast suggestions to reflect typical Vietnamese morning foods (cháo, phở, bún, bánh mì, xôi, trứng, sữa, yến mạch, trái cây) and lunch/dinner to emphasise cooked meals (cơm, bún, mì, thịt, cá, rau xào, canh), so that my plan feels culturally appropriate.

#### Acceptance Criteria

1. THE Recommender_Service SHALL define a module-level constant `BREAKFAST_PREFERRED_TERMS` containing accent-stripped tokens for: *cháo*, *phở*, *bún*, *bánh mì*, *xôi*, *trứng*, *sữa*, *yến mạch*, *trái cây*, *oat*, *egg*, *milk*, *fruit*, *porridge*, *congee*, *bread*.
2. THE Recommender_Service SHALL define a module-level constant `LUNCH_DINNER_PREFERRED_TERMS` containing accent-stripped tokens for: *cơm*, *bún*, *mì*, *thịt*, *cá*, *rau xào*, *canh*, *rice*, *noodle*, *meat*, *fish*, *stir fry*, *soup*.
3. WHEN scoring candidates for the `"breakfast"` meal slot, THE Recommender_Service SHALL add a positive score adjustment of `+0.15` for any candidate whose name matches a token in `BREAKFAST_PREFERRED_TERMS`.
4. WHEN scoring candidates for `"lunch"` or `"dinner"` meal slots, THE Recommender_Service SHALL add a positive score adjustment of `+0.15` for any candidate whose name matches a token in `LUNCH_DINNER_PREFERRED_TERMS`.
5. WHEN scoring candidates for the `"breakfast"` meal slot, THE Recommender_Service SHALL apply a negative score adjustment of `-0.2` for any candidate that is a heavy animal protein (matching `_row_is_heavy_breakfast_protein`) to discourage red meat at breakfast.
6. THE scoring adjustments in acceptance criteria 3–5 SHALL be applied additively with existing slot-score adjustments and SHALL NOT override hard category filters.

---

### Requirement 7: No New Files

**User Story:** As a developer maintaining a clean repository, I want all changes to be contained in the existing `recommender_service.py` file so that no new modules, packages, or configuration files are introduced.

#### Acceptance Criteria

1. THE Recommender_Service SHALL implement all new functions (`normalize_food_key`, `compute_diversity_score`), all new constants (`BREAKFAST_PREFERRED_TERMS`, `LUNCH_DINNER_PREFERRED_TERMS`, expanded `SEMANTIC_FOOD_GROUP_TERMS`), and all modified logic exclusively in `backend/app/services/recommender_service.py`.
2. THE Recommender_Service SHALL NOT introduce any new `.py` files, new modules, or new packages as part of this feature.

---

### Requirement 8: API Compatibility

**User Story:** As a backend developer, I want all existing function signatures, return types, and API contracts to remain unchanged so that no callers need to be updated.

#### Acceptance Criteria

1. THE Recommender_Service SHALL preserve the existing signature `normalize_food_similarity_key(food: pd.Series | dict) -> str` without modification.
2. THE Recommender_Service SHALL preserve the existing signature `normalize_ingredient_name(value: object) -> str` without modification.
3. THE Recommender_Service SHALL preserve the existing signature `pickBalancedMeal(ranked, meal_structure, target) -> dict[str, pd.DataFrame]` without modification.
4. WHEN called with the same arguments as before this feature, THE Recommender_Service SHALL produce output that satisfies the same structural contract (dict mapping meal names to DataFrames of food items).
5. THE Recommender_Service SHALL NOT remove or rename any existing module-level constants, functions, or classes that are used by other files in the project.

---

### Requirement 9: Performance

**User Story:** As a developer, I want the new normalisation and scoring functions to execute efficiently so that recommendation latency is not meaningfully increased.

#### Acceptance Criteria

1. THE `normalize_food_key` function SHALL execute in O(k) time where k is the number of Descriptor_Words, independent of the size of the food catalogue.
2. THE `compute_diversity_score` function SHALL execute in O(n) time where n is the total number of food items in the Day_Plan.
3. WHILE `pickBalancedMeal` is running, THE Recommender_Service SHALL NOT perform any database lookups inside the new normalisation or deduplication logic added by this feature.
