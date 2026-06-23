# Bugfix Requirements Document

## Introduction

The NutriGain Achievement page (`ThanhTuuView` + `GentleMotivationPanel`) currently presents a gamification-heavy UI with emojis, icon-library components, sticker-style badge indicators, and playful motivational copy. This visual language conflicts with the product's goal of being a calm, professional wellness tool in the style of Apple Health or Fitbit.

The "bug" is a presentation-layer mismatch: the data, logic, and API integrations are correct and must remain untouched, but the visual and tonal output they produce is inappropriate for the intended user experience. This document captures what currently renders incorrectly (defect), what should render instead (correct behavior), and what must not change (regression prevention).

---

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the Achievement page renders the Level Summary section THEN the system displays a Lucide `Trophy` icon inside a decorative gradient box alongside the level title, creating a game-like visual rather than a clean dashboard card.

1.2 WHEN the Achievement page renders the Streak section THEN the system displays a large Lucide `Flame` icon (size 36) inside an amber gradient box, evoking a gamification flame indicator rather than a calm wellness metric.

1.3 WHEN the Achievement page renders streak status THEN the system uses a `Star` icon inside an amber pill badge, reinforcing a game-point aesthetic.

1.4 WHEN the Achievement page renders badge/achievement entries THEN the system displays emoji icons (🍽️, ⚖️, ✅, 🔥, 📅, 🎯, 💪, 🥗, 🏅) as the primary visual identifier for each badge.

1.5 WHEN the Achievement page renders the empty badges state THEN the system displays the text "Huy hiệu sẽ xuất hiện khi bạn đạt được thành tích." which is generic placeholder copy.

1.6 WHEN the Achievement page renders the Today's Challenge section THEN the system displays a Lucide `Target` icon and uses a gradient background (`from-white to-emerald-50/30`), giving a game-quest appearance rather than a clean informational card.

1.7 WHEN the Achievement page renders the Encouragement block THEN the system uses a Lucide `Heart` icon inside a gradient banner, producing a sticker-style motivational widget rather than a calm, typographic note.

1.8 WHEN the Achievement page renders MEALRANK badge meta entries THEN the system defines badge colors and emoji icons inline in `BADGE_META` using emoji characters as the icon source, with no support for real image assets.

---

### Expected Behavior (Correct)

2.1 WHEN the Achievement page renders the Level Summary section THEN the system SHALL display a clean card with no icon or only a real image asset (medal/trophy render), using strict typographic hierarchy: title text, level number, thin progress bar, and a remaining-points label — with no decorative gradient boxes.

2.2 WHEN the Achievement page renders the Streak section THEN the system SHALL replace the Flame icon with either a subtle 7-cell calendar-strip visualization or a simple plain number display with supporting label text ("Chuỗi duy trì: N ngày") using neutral colors, with no amber flame icon.

2.3 WHEN the Achievement page renders streak status THEN the system SHALL display the status as plain text or a minimal neutral pill (no star or game icon), consistent with an informational analytics style.

2.4 WHEN the Achievement page renders badge/achievement entries THEN the system SHALL display a real image asset (grayscale PNG/SVG for locked, metallic-style render for unlocked) as the badge visual, with no emoji characters used as icons.

2.5 WHEN the Achievement page renders the empty badges state THEN the system SHALL display the text "Thành tích sẽ được mở khóa khi bạn đạt cột mốc" with no emoji, no icon, and no placeholder illustration.

2.6 WHEN the Achievement page renders the Today's Challenge / Daily Completion section THEN the system SHALL display a single clean status card with a soft, non-gradient background, a plain check or status indicator (no Target or game icon), and strictly informational copy such as "Hôm nay: Đã hoàn thành đầy đủ 3 bữa".

2.7 WHEN the Achievement page renders the Encouragement block THEN the system SHALL display the encouragement text as a quiet typographic quote or note card with no icon, no gradient, and calm tone — e.g., a left-bordered blockquote style.

2.8 WHEN the Achievement page renders MEALRANK badge meta entries THEN the system SHALL resolve badge visuals from real image asset paths (e.g., `/assets/badges/first_meal_plan.png`) rather than from inline emoji strings.

---

### Unchanged Behavior (Regression Prevention)

3.1 WHEN `getGamificationSummary()` API is called THEN the system SHALL CONTINUE TO fetch streak, achievements, level, and today_challenge data from the existing backend endpoint without any modification to the request or response contract.

3.2 WHEN `completeGamificationChallenge(key)` is called via the button THEN the system SHALL CONTINUE TO send the challenge completion request to the existing backend endpoint and refresh summary data on success.

3.3 WHEN `loadGamificationStats()` is called from `mealRank.js` THEN the system SHALL CONTINUE TO read totalPoints and ssCount from localStorage using the existing `nutrigain_gami_stats` key and format.

3.4 WHEN `resolveLevel(points)` computes the user's level THEN the system SHALL CONTINUE TO apply the existing `LEVEL_TIERS` thresholds (0–99 → Lv.1, 100–299 → Lv.5, etc.) and progress percentage calculation without change.

3.5 WHEN streak data is derived from `summary.streak.current` THEN the system SHALL CONTINUE TO compute `weeklyCycleDay`, `weeklyRemainingDays`, `isWeeklyComplete`, and `weeklyProgress` using the existing modulo-7 logic.

3.6 WHEN achievements are available in `summary.achievements` THEN the system SHALL CONTINUE TO display the first 6 entries, preserving the slice limit.

3.7 WHEN `refreshKey` prop changes THEN the system SHALL CONTINUE TO reload both `localStats` from localStorage and the remote gamification summary via the API.

3.8 WHEN the Today's Challenge key is `"first_complete_day"` THEN the system SHALL CONTINUE TO invoke `onAction()` (navigate to journal) instead of calling the complete challenge API.

3.9 WHEN the challenge status field equals `"completed"` (case-insensitive) THEN the system SHALL CONTINUE TO show the completed state on the action button without re-triggering the API.

3.10 WHEN `monthCareDays` is null or undefined THEN the system SHALL CONTINUE TO display "—" as the fallback value for the monthly stat cell.
