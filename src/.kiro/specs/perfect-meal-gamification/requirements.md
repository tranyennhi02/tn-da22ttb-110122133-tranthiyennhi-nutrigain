# Requirements Document

## Introduction

Nâng cấp hệ thống gamification "Bữa Ăn Hoàn Hảo" (Perfect Meal System) cho ứng dụng NutriGain — một app theo dõi dinh dưỡng giúp người dùng tăng cân lành mạnh. Hệ thống bổ sung cơ chế xếp hạng bữa ăn theo độ chính xác calorie, phản hồi thời gian thực, huy hiệu thành tích dinh dưỡng, hệ thống điểm cấp độ người dùng và đa dạng thực đơn — tất cả tích hợp vào kiến trúc React + FastAPI hiện có mà không làm ảnh hưởng logic calorie đang hoạt động.

## Glossary

- **Rank_Calculator**: Module frontend (pure computed) tính rank và điểm từ `selectedIds` và `target_kcal`.
- **Diversity_Calculator**: Module frontend (pure computed) tính điểm đa dạng nhóm thực phẩm từ các món được chọn.
- **MealScorePanel**: Component UI hiển thị rank, điểm thành tích, điểm đa dạng trong `SingleMealSection`.
- **MealScoreService**: Backend service xử lý endpoint `/api/v1/gamification/meal-score`.
- **GamificationProfile**: Bảng `user_gamification_profile` lưu tổng điểm, số lần SS, số ngày kỷ luật của user.
- **Level_Engine**: Logic backend tính level, level title, tiến độ % từ tổng điểm.
- **Achievement_Engine**: Logic backend kiểm tra và mở khóa huy hiệu thành tích dinh dưỡng mới.
- **GamificationService**: Service backend hiện có, sẽ được mở rộng.
- **SingleMealSection**: Component React hiện có render một bữa ăn (sáng/trưa/tối/snack) với `selectedIds`.
- **System**: Toàn bộ hệ thống NutriGain (dùng khi không cần chỉ định cụ thể frontend/backend).
- **User**: Người dùng đã đăng nhập sử dụng NutriGain.
- **Rank**: Cấp độ chính xác calorie của bữa ăn: SS > S > A > B > C > D.
- **Discipline_Day**: Ngày calendar (Asia/Ho_Chi_Minh) trong đó User có ít nhất một meal submission với rank A, S, hoặc SS.
- **Food_Group**: Nhóm thực phẩm được chuẩn hóa dùng để tính điểm đa dạng (ví dụ: `com`, `dau_phu`, `yen_mach`).

---

## Requirements

---

### Requirement 1: Meal Rank System — Tính Rank Bữa Ăn Thời Gian Thực

**User Story:** As a User, I want to see a rank for my meal based on how close my selected calories are to the target, so that I have immediate feedback to optimize my food selection.

#### Acceptance Criteria

1. WHEN the User selects or deselects a food item in `SingleMealSection`, THE `Rank_Calculator` SHALL compute `difference = abs(target_kcal - total_selected_kcal)` and assign a rank according to the following thresholds:
   - `difference` 0–5 kcal → Rank SS
   - `difference` 6–20 kcal → Rank S
   - `difference` 21–50 kcal → Rank A
   - `difference` 51–100 kcal → Rank B
   - `difference` 101–150 kcal → Rank C
   - `difference` > 150 kcal → Rank D

2. WHILE `target_kcal` is 0 or undefined for a meal, THE `Rank_Calculator` SHALL return no rank and THE `MealScorePanel` SHALL not display a rank badge or rank label for that meal.

3. WHEN `target_kcal` is set but no food items are selected, THE `Rank_Calculator` SHALL treat `total_selected_kcal` as 0 and compute rank D (difference = target_kcal > 150 in all practical cases where target_kcal > 150).

4. WHEN the computed rank changes, THE `MealScorePanel` SHALL update the displayed rank badge within 100 milliseconds without making any additional network requests.

---

### Requirement 2: Realtime Feedback Messages — Thông Điệp Phản Hồi Tức Thì

**User Story:** As a User, I want to see a friendly, motivating message corresponding to my meal rank, so that I feel encouraged while building healthy eating habits.

#### Acceptance Criteria

1. WHEN `Rank_Calculator` outputs a rank, THE `MealScorePanel` SHALL immediately replace any prior rank message and display exactly the following message for that rank:
   - SS → "🎯 Bữa ăn hoàn hảo!"
   - S → "🔥 Cân bằng cực tốt!"
   - A → "✅ Bữa ăn khá chuẩn!"
   - B → "👍 Khá ổn, có thể tối ưu thêm."
   - C → "⚠ Bữa ăn hơi lệch mục tiêu."
   - D → "❌ Bạn cần điều chỉnh thêm."

2. WHILE at least one food item is selected, THE `MealScorePanel` SHALL display exactly the rank message mapped in criterion 1 and no other rank text or icon outside of that message.

3. WHEN the count of selected food items drops to 0, THE `MealScorePanel` SHALL clear the rank message area so that no rank text or icon is visible.

---

### Requirement 3: "Suýt Hoàn Hảo" — Almost Perfect Nudge System

**User Story:** As a User, I want to know when I'm just a few calories away from a perfect meal, so that I'm motivated to make one small adjustment to reach rank SS.

#### Acceptance Criteria

1. WHEN `abs(target_kcal - total_selected_kcal)` is between 1 and 10 kcal (inclusive) AND `total_selected_kcal < target_kcal`, THE `MealScorePanel` SHALL display the message: "🔥 Chỉ còn thiếu [X] kcal để đạt Bữa Ăn Hoàn Hảo!" where [X] is `abs(target_kcal - total_selected_kcal)` rounded to the nearest integer.

2. WHEN `abs(target_kcal - total_selected_kcal)` is 0 kcal (rank SS achieved exactly), THE `MealScorePanel` SHALL not display the "Suýt Hoàn Hảo" message and SHALL display only the rank SS feedback message.

3. WHEN `abs(target_kcal - total_selected_kcal)` is greater than 10 kcal, THE `MealScorePanel` SHALL not display the "Suýt Hoàn Hảo" message.

4. WHEN `abs(target_kcal - total_selected_kcal)` is between 6 and 10 kcal (inclusive) AND `total_selected_kcal < target_kcal`, THE `MealScorePanel` SHALL display the "Suýt Hoàn Hảo" message alongside the rank S feedback message.

5. WHEN `abs(target_kcal - total_selected_kcal)` is between 1 and 5 kcal (inclusive) AND `total_selected_kcal < target_kcal`, THE `MealScorePanel` SHALL display the "Suýt Hoàn Hảo" message alongside the rank SS feedback message.

---

### Requirement 4: Achievement Points — Điểm Thành Tích Bữa Ăn (Backend)

**User Story:** As a User, I want to earn achievement points when I confirm a meal, so that my consistent effort is rewarded and tracked over time.

#### Acceptance Criteria

1. WHEN the `/api/v1/gamification/meal-score` endpoint receives a valid authenticated request, THE `MealScoreService` SHALL award base points according to the rank submitted:
   - Rank SS → 50 points
   - Rank S → 35 points
   - Rank A → 20 points
   - Rank B → 10 points
   - Rank C → 0 points
   - Rank D → 0 points

2. WHEN the submitted `diversity_points` equals 15 (indicating `diversity_score` ≥ 3 unique food groups computed by the frontend), THE `MealScoreService` SHALL add 15 bonus points to the total awarded.

3. WHEN the submitted `almost_perfect` is `true` AND the submitted `rank` is not SS, THE `MealScoreService` SHALL add 10 bonus points to the total awarded.

4. WHEN points are awarded, THE `MealScoreService` SHALL persist them by incrementing `total_points` in `GamificationProfile` for the authenticated user using an upsert operation (INSERT … ON DUPLICATE KEY UPDATE or equivalent).

5. THE `MealScoreService` SHALL only be invoked when the User explicitly confirms a meal via the confirm button in `MealScorePanel`, not on every food item tick.

6. IF the authenticated user does not yet have a `GamificationProfile` row at the time of the request, THEN THE `MealScoreService` SHALL create one with `total_points=0`, `ss_count=0`, `discipline_days=0` before adding the awarded points.

---

### Requirement 5: Level System — Hệ Thống Cấp Độ

**User Story:** As a User, I want to see my current level and progress toward the next level based on my accumulated achievement points, so that I have a long-term goal to work toward.

#### Acceptance Criteria

1. THE `Level_Engine` SHALL calculate the user's level from `total_points` using the following thresholds:
   - 0–99 pts → Level 1: "Người Mới"
   - 100–299 pts → Level 5: "Ăn Uống Điều Độ"
   - 300–699 pts → Level 10: "Chuyên Gia Bữa Ăn"
   - 700–1499 pts → Level 20: "Bậc Thầy Dinh Dưỡng"
   - ≥ 1500 pts → Level 30: "Cao Thủ Calories"

2. THE `Level_Engine` SHALL compute `level_progress_pct` as `(total_points - tier_start) / (tier_end - tier_start) * 100`, clamped to [0.0, 100.0]; WHEN the user is at the maximum level (Level 30, tier_start = 1500), `level_progress_pct` SHALL equal 100.0.

3. THE `Level_Engine` SHALL compute `points_to_next_level` as `tier_end - total_points`; IF the user is at Level 30 (maximum level), THEN `points_to_next_level` SHALL be 0.

4. WHEN the `/api/v1/gamification/summary` endpoint responds successfully, THE `GamificationService` SHALL include `total_points`, `level`, `level_title`, `level_progress_pct`, and `points_to_next_level` in the JSON response body; IF the profile data cannot be retrieved, THEN the endpoint SHALL return HTTP 500 with a safe error message.

5. WHEN the `ThanhTuuView` dashboard loads and the `/api/v1/gamification/summary` response is available, THE `GentleMotivationPanel` SHALL display a level progress bar showing current level title, progress percentage, and points to next level; WHILE the data is loading, it SHALL display a loading placeholder; IF the request fails, it SHALL display a non-blocking error indicator.

---

### Requirement 6: Nutrition Badges — Huy Hiệu Dinh Dưỡng (Backend)

**User Story:** As a User, I want to earn special badges for consistent nutritional achievements, so that my healthy habits are recognized with meaningful rewards.

#### Acceptance Criteria

1. WHEN `GamificationProfile.ss_count` reaches 10 AND no `user_achievements` row with `achievement_key = 'perfect_calories'` exists for the user, THE `Achievement_Engine` SHALL insert a `user_achievements` row with `achievement_key='perfect_calories'`, `title='🎯 Chuẩn Calories'`, and `description='Đạt SS 10 lần — bạn là bậc thầy kiểm soát calorie!'`.

2. WHEN `GamificationProfile.discipline_days` reaches 7 AND no `user_achievements` row with `achievement_key = 'discipline_eater'` exists for the user, THE `Achievement_Engine` SHALL insert a `user_achievements` row with `achievement_key='discipline_eater'`, `title='🔥 Ăn Uống Kỷ Luật'`, and `description='7 ngày ăn đúng mục tiêu — kỷ luật đáng nể!'`.

3. WHEN a meal submission includes `diversity_points = 15` AND the total number of `meal_score` submissions with `diversity_points = 15` for this user reaches 5 AND no `user_achievements` row with `achievement_key = 'diverse_menu'` exists, THE `Achievement_Engine` SHALL insert a `user_achievements` row with `achievement_key='diverse_menu'`, `title='🍱 Thực Đơn Đa Dạng'`, and `description='Thực đơn phong phú nhiều nhóm thực phẩm — rất tốt cho sức khỏe!'`.

4. WHEN a meal submission includes `rank` of A, S, or SS AND the current calendar date (Asia/Ho_Chi_Minh) has not yet been counted as a `Discipline_Day` for this user, THE `Achievement_Engine` SHALL increment `GamificationProfile.discipline_days` by 1 (counted at most once per user per calendar day).

5. WHEN a meal submission includes `rank` SS AND the submission is not a duplicate (same user + same `meal_type` + same calendar date already recorded), THE `Achievement_Engine` SHALL increment `GamificationProfile.ss_count` by 1.

6. THE `Achievement_Engine` SHALL execute all checks (points update, ss_count increment, discipline_days increment, badge unlock inserts) within a single database transaction; IF any step fails, THE `Achievement_Engine` SHALL roll back the entire transaction and no partial state SHALL be persisted.

7. WHEN a badge is newly unlocked, THE `Achievement_Engine` SHALL insert a row into `user_achievements` following the existing `UserAchievement` entity pattern (`user_id`, `achievement_key`, `title`, `description`, `unlocked_at = datetime.utcnow()`).

8. WHEN the `/api/v1/gamification/meal-score` request completes successfully, THE response SHALL include a `new_badges` field containing a list of objects (each with `achievement_key`, `title`, `description`) for badges unlocked during that request; IF no badges were unlocked, `new_badges` SHALL be an empty list `[]`.

---

### Requirement 7: Diversity Points System — Điểm Đa Dạng Thực Đơn (Pure Frontend)

**User Story:** As a User, I want to see how diverse my meal is in terms of food groups, so that I'm encouraged to include a variety of foods for better nutrition.

#### Acceptance Criteria

1. WHEN the User selects food items, THE `Diversity_Calculator` SHALL normalize each food's display name to a food group key by applying the following rules in order, using case-insensitive substring matching, stopping at the first match:
   - Contains "đậu phụ", "đậu hũ", or "tofu" → `dau_phu`
   - Contains "yến mạch", "bột yến mạch", or "oat" → `yen_mach`
   - Contains "ức gà", "thịt gà" → `ga`
   - Contains "gà" (standalone) → `ga`
   - Contains "thịt heo", "thịt lợn", "thịt bò" → `thit`
   - Contains "cá hồi", "cá ngừ", "cá basa", "cá" → `ca`
   - Contains "trứng" → `trung`
   - Contains "sữa chua", "yogurt", "phô mai", "sữa" → `sua`
   - Contains "rau xanh", "salad", "cải", "rau" → `rau`
   - Contains "cơm trắng", "cơm gạo lứt", "cơm" → `com`
   - No match → use the item's `food_id` as the group key (unique group)

2. WHEN multiple selected items resolve to the same group key, THE `Diversity_Calculator` SHALL count them as one group, not multiple.

3. WHEN `diversity_score` (count of unique group keys) is ≥ 3, THE `MealScorePanel` SHALL display "+15 Điểm Đa Dạng".

4. WHEN `diversity_score` is 1 or 2, THE `MealScorePanel` SHALL display "0 Điểm Đa Dạng".

5. WHEN no food item is selected, THE `MealScorePanel` SHALL display "0 Điểm Đa Dạng".

6. WHEN `selectedIds` changes, THE `Diversity_Calculator` SHALL recompute `diversity_score` using only client-side item data already present in `SingleMealSection` without making any API calls.

---

### Requirement 8: MealScorePanel UI — Giao Diện Điểm Bữa Ăn

**User Story:** As a User, I want to see a compact, real-time score panel inside each meal section showing my rank, accuracy, and potential points, so that I can make informed food selection decisions.

#### Acceptance Criteria

1. WHEN at least one food item is selected in a meal section and `target_kcal` > 0, THE `MealScorePanel` SHALL render inside `SingleMealSection` showing:
   - Rank badge (color-coded: SS=gold/yellow, S=emerald, A=green, B=blue, C=amber, D=red)
   - Accuracy percentage: `max(0, round((1 - abs(target_kcal - total_selected_kcal) / target_kcal) * 100, 1))`
   - Pending achievement points (base points + diversity bonus, not yet submitted)
   - Diversity points indicator ("0 Điểm Đa Dạng" or "+15 Điểm Đa Dạng")
   - Rank feedback message (from Requirement 2)

2. WHEN `abs(target_kcal - total_selected_kcal)` is between 1 and 10 kcal AND `total_selected_kcal < target_kcal`, THE `MealScorePanel` SHALL additionally display the "Suýt Hoàn Hảo" nudge message below the rank badge.

3. THE `MealScorePanel` SHALL apply a CSS transition of at least `transition-all duration-300` on rank badge color changes, point value changes, and message text changes.

4. THE `MealScorePanel` SHALL render as a single horizontal strip on viewports ≥ 640px wide, and as a vertically stacked compact layout on viewports < 640px, without altering the existing `SingleMealSection` grid or header layout.

5. WHEN the User clicks the "Xác nhận bữa ăn" button in `MealScorePanel`, THE `MealScorePanel` SHALL call the `/api/v1/gamification/meal-score` endpoint with `meal_type`, `rank`, `points`, `diversity_points`, `almost_perfect`, and `selected_food_ids`.

6. WHILE the confirm API call is in flight, THE `MealScorePanel` SHALL disable the confirm button and display a loading spinner to prevent duplicate submissions.

7. WHEN the confirm API call succeeds, THE `MealScorePanel` SHALL display an inline success message for at least 3 seconds showing the total points awarded and any newly unlocked badge titles from the `new_badges` response field.

8. IF the confirm API call returns an error, THE `MealScorePanel` SHALL re-enable the confirm button and display an inline error message without losing the current meal selection state.

---

### Requirement 9: New Backend Endpoint — POST /api/v1/gamification/meal-score

**User Story:** As a User, I want my meal score to be recorded server-side when I confirm a meal, so that my progress is accurately tracked and contributes to level-up and badge unlocks.

#### Acceptance Criteria

1. WHEN a POST request is sent to `/api/v1/gamification/meal-score`, THE `MealScoreService` SHALL accept a JSON body with:
   - `meal_type` (string, required): one of "breakfast", "lunch", "dinner", "snack"
   - `rank` (string, required): one of "SS", "S", "A", "B", "C", "D"
   - `points` (integer, required): base points ≥ 0 and ≤ 10,000
   - `diversity_points` (integer, required): 0 or 15
   - `almost_perfect` (boolean, required)
   - `selected_food_ids` (list of strings, required, 1–20 items)

2. WHEN the request has no valid authentication token, THE `MealScoreService` SHALL return HTTP 401 without processing the payload.

3. IF `rank` is not one of the six valid values, THEN THE `MealScoreService` SHALL return HTTP 422 with a message identifying the invalid field.

4. WHEN the `GamificationProfile` update, `ss_count` increment, `discipline_days` increment, and badge unlock inserts all succeed, THE `MealScoreService` SHALL commit a single database transaction and return HTTP 200.

5. IF a database error occurs during the transaction, THEN THE `MealScoreService` SHALL roll back the entire transaction and return HTTP 500 with a safe error message that does not expose internal stack traces.

6. WHEN the transaction commits successfully, THE `MealScoreService` SHALL return a JSON response with: `success=true`, `total_points` (int), `level` (int), `level_title` (str), `level_progress_pct` (float 0.0–100.0), `points_to_next_level` (int), and `new_badges` (list).

7. WHEN the same `user_id` + `meal_type` combination has already been submitted for the current calendar day (Asia/Ho_Chi_Minh), THE `MealScoreService` SHALL return HTTP 409 with message "Bữa ăn này đã được xác nhận hôm nay." without updating any data.

8. THE `MealScoreService` SHALL NOT read or write to `meal_plans`, `meals`, `meal_plan_items`, `food_logs`, `food_log_items`, or `meal_consumption_logs` tables — all writes are isolated to `user_gamification_profile` and `user_achievements`.

---

### Requirement 10: Extended GET /api/v1/gamification/summary

**User Story:** As a User, I want the gamification summary to include my level and points information so that the ThanhTuuView dashboard shows my full progress.

#### Acceptance Criteria

1. WHEN the `/api/v1/gamification/summary` endpoint is called by an authenticated user, THE `GamificationService` SHALL include in the response:
   - `total_points` (int, default 0 if no `GamificationProfile` exists)
   - `level` (int)
   - `level_title` (str)
   - `level_progress_pct` (float, 0.0–100.0)
   - `points_to_next_level` (int)
   - `new_badges` (list of badge objects unlocked within the last 24 hours, each with `achievement_key`, `title`, `description`)

2. WHEN no `GamificationProfile` row exists for the user, THE `GamificationService` SHALL return default values `total_points=0`, `level=1`, `level_title="Người Mới"`, `level_progress_pct=0.0`, `points_to_next_level=100` without inserting a new row.

3. THE `GamificationService` SHALL return the five new fields alongside all existing fields (`streak`, `achievements`, `today_challenge`, `encouragement`) without removing, renaming, or changing the type of any existing field.

---

### Requirement 11: Database Schema — user_gamification_profile Table

**User Story:** As a developer, I want a minimal dedicated table for gamification statistics so that points tracking does not pollute existing tables and can evolve independently.

#### Acceptance Criteria

1. WHEN `ensure_database_schema` runs and the `user_gamification_profile` table does not yet exist, THE System SHALL execute a CREATE TABLE statement creating the table with columns:
   - `id` INTEGER, primary key, auto-increment
   - `user_id` INTEGER, UNIQUE, NOT NULL, foreign key to `users.id`
   - `total_points` INTEGER, NOT NULL, DEFAULT 0
   - `ss_count` INTEGER, NOT NULL, DEFAULT 0
   - `discipline_days` INTEGER, NOT NULL, DEFAULT 0
   - `updated_at` DATETIME, default CURRENT_TIMESTAMP, ON UPDATE CURRENT_TIMESTAMP

2. IF the `user_gamification_profile` table already exists when `ensure_database_schema` runs, THEN THE System SHALL NOT attempt to recreate it and SHALL NOT modify existing data, ensuring the migration is idempotent across repeated application restarts.

3. THE System SHALL define a `UserGamificationProfile` SQLAlchemy entity in `entities.py` using the `mapped_column` pattern consistent with existing entities, with `uselist=False` relationship to `User` via `back_populates`, cascade `all, delete-orphan`, and a corresponding `gamification_profile` relationship attribute added to the `User` class.

4. THE System SHALL NOT add gamification-related columns to `user_daily_activity`, `user_achievements`, or any other existing table.
