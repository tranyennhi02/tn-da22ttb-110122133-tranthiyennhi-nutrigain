# Implementation Plan

## Overview

This plan implements the Achievement UI refactor for `GentleMotivationPanel.jsx` following the exploratory bugfix workflow. It removes decorative Lucide icons (Trophy, Flame, Star, Target, Heart), emoji badge icons, and gradient card backgrounds — replacing them with clean flat cards, image-based badge assets, and typographic hierarchy — while leaving all data-fetching, state management, business logic, and API contracts completely untouched.

## Task Dependency Graph

```json
{
  "waves": [
    ["1", "2"],
    ["3.1", "3.2"],
    ["3.3", "3.4", "3.5", "3.7", "3.9"],
    ["3.6", "3.8"],
    ["3.10", "3.11"],
    ["4"]
  ]
}
```

## Tasks

- [ ] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Decorative Elements Rendered in GentleMotivationPanel
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples proving that decorative elements are present in the current render
  - **Scoped PBT Approach**: Scope the property to the concrete failing cases — mount with `summaryData` from the set `[null, minimalSummary, fullSummaryWithAchievements]` and assert none of the outputs contain decorative elements
  - Create test file at `frontend/src/components/gamification/__tests__/GentleMotivationPanel.bug.test.jsx`
  - Mock `getGamificationSummary` and `loadGamificationStats` so the component mounts without real API calls
  - Write property-based test (using `@fast-check/vitest` or manual parameterisation) iterating over all `summaryData` variants
  - For each rendered output assert: no `<svg>` node whose aria-label or test-id matches Trophy, Flame, Star, Target, or Heart; no text node whose content matches `/[\u{1F300}-\u{1FFFF}]/u`; no `article` element with a `className` containing `bg-gradient-to-br` or `bg-gradient-to-r`
  - Bug Condition from design: `isBugCondition(renderedOutput)` returns true when output contains any of the above
  - Expected behavior (post-fix): `isBugCondition(renderedOutput)` returns false for all inputs
  - Run test on UNFIXED code — **EXPECTED OUTCOME: Test FAILS** (this is correct — it proves the bug exists)
  - Document counterexamples found, e.g. "Trophy SVG present in level section", "🍽️ emoji in badge cell", "`bg-gradient-to-br` on streak article"
  - Mark task complete when test is written, run, and failures are documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

- [ ] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Data Logic, API Contracts, and Derived Values Are Unchanged
  - **IMPORTANT**: Follow observation-first methodology — run unfixed code with non-bug-condition inputs and record actual outputs first
  - Create test file at `frontend/src/components/gamification/__tests__/GentleMotivationPanel.preservation.test.jsx`
  - Mock `getGamificationSummary` and `completeGamificationChallenge` and `loadGamificationStats`
  - Observe on unfixed code:
    - `resolveLevel(0)` → `{ level: 1, title: "Người Mới", progress: 0 }`
    - `resolveLevel(150)` → `{ level: 5, title: "Ăn Uống Điều Độ", progress: 25 }`
    - `streak.current = 7` → `weeklyCycleDay = 7`, `isWeeklyComplete = true`, pill shows "Tuần mới bắt đầu"
    - `streak.current = 0` → `weeklyCycleDay = 0`, pill shows "Nghỉ nhẹ"
    - `monthCareDays = null` → stats cell shows "—"
    - `today_challenge.key = "first_complete_day"` → button click calls `onAction()`, NOT `completeGamificationChallenge`
    - `today_challenge.status = "COMPLETED"` (uppercase) → `challengeDone = true`, button disabled
    - `summary.achievements.slice(0, 6)` — only first 6 entries rendered
    - `refreshKey` change from 0 → 1 → triggers both `loadGamificationStats()` and `getGamificationSummary()`
  - Write property-based tests capturing all of the above as invariants across generated inputs:
    - **Level derivation**: for any `totalPoints ∈ [0, 9999]`, rendered level title and progress % match `resolveLevel(totalPoints)` — progress is in [0, 100]
    - **Streak derivation**: for any `streak.current = N ≥ 0`, rendered streak number equals N; `weeklyCycleDay = ((N-1) % 7) + 1` when N > 0, else 0
    - **monthCareDays null fallback**: when null/undefined, cell shows "—"
    - **Challenge routing invariant**: `first_complete_day` key → `onAction` called; any other key → `completeGamificationChallenge` called
    - **challengeDone case-insensitivity**: status `"completed"` / `"COMPLETED"` / `"Completed"` all yield `challengeDone = true`
    - **Achievement slice limit**: for any achievements array of length ≥ 6, only 6 rows rendered
  - Run all tests on UNFIXED code — **EXPECTED OUTCOME: All tests PASS** (confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and all passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10_

- [ ] 3. Fix: Achievement UI — remove decorative icons, emoji, and gradient backgrounds

  - [ ] 3.1 Create badge asset directory and placeholder SVG files
    - Create directory `frontend/public/assets/badges/`
    - Create one SVG file per badge key using the minimal placeholder template from design (64×64 circle with a neutral `◉` glyph)
    - Files to create: `first_meal_plan.svg`, `first_weight_log.svg`, `first_complete_day.svg`, `three_active_days.svg`, `three_balanced_days_in_week.svg`, `perfect_calories.svg`, `discipline_eater.svg`, `diverse_menu.svg`, `default.svg`
    - Optionally create `frontend/public/assets/icons/trophy.svg` for the level section
    - _Requirements: 2.4, 2.8_

  - [ ] 3.2 Remove decorative Lucide icon imports
    - In `GentleMotivationPanel.jsx`, edit the `lucide-react` import line
    - Remove: `Award`, `Flame`, `Heart`, `Leaf`, `Sparkles`, `Star`, `Target`, `Trophy`, `Zap`
    - Retain: `Check` (used on the functional completed-state button — non-decorative)
    - _Bug_Condition: import of Trophy, Flame, Star, Target, Heart, Award, Leaf, Sparkles, Zap from lucide-react_
    - _Expected_Behavior: only `Check` remains in the lucide-react import_
    - _Requirements: 2.1, 2.2, 2.3, 2.6, 2.7_

  - [ ] 3.3 Update BADGE_META to use image paths instead of emoji icons
    - Replace every `icon` + `color` field in `BADGE_META` with `image` + `label` fields
    - Example: `first_meal_plan: { image: "/assets/badges/first_meal_plan.svg", label: "Kế hoạch bữa ăn đầu tiên" }`
    - All 8 keys: `first_meal_plan`, `first_weight_log`, `first_complete_day`, `three_active_days`, `three_balanced_days_in_week`, `perfect_calories`, `discipline_eater`, `diverse_menu`
    - Update `badgeMeta` fallback to `{ image: "/assets/badges/default.svg", label: "Huy hiệu" }`
    - _Bug_Condition: BADGE_META entries contain emoji `icon` strings (`🍽️`, `⚖️`, `✅`, `🔥`, `📅`, `🎯`, `💪`, `🥗`)_
    - _Expected_Behavior: every `meta.image` starts with `/assets/badges/` and ends with `.svg` or `.png`; no emoji fields remain_
    - _Preservation: `badgeMeta(key)` still returns a defined object for all 8 known keys and for unknown keys_
    - _Requirements: 2.4, 2.8_

  - [ ] 3.4 Refactor Level Summary section
    - Remove the Trophy icon box: delete the `<div className="flex-shrink-0 flex h-14 w-14 ... bg-gradient-to-br from-emerald-50 to-emerald-100 ..."><Trophy size={28} /></div>` block
    - Optionally replace with `<img src="/assets/icons/trophy.svg" className="h-10 w-10 opacity-60" alt="" />` if the icon asset was created in task 3.1; otherwise omit entirely
    - Change the progress bar fill from `bg-gradient-to-r from-emerald-400 to-emerald-500` to `bg-emerald-600` (solid color)
    - _Bug_Condition: `<Trophy>` SVG rendered inside `bg-gradient-to-br` box; progress bar uses `bg-gradient-to-r`_
    - _Expected_Behavior: no Trophy icon; progress bar fill is solid `bg-emerald-600`_
    - _Preservation: level title, `Lv.X`, total-points display, progress width percentage, and `pointsToNext` label are all unchanged_
    - _Requirements: 2.1_

  - [ ] 3.5 Refactor Streak section
    - Remove the Flame icon box: delete `<div className="... bg-gradient-to-br from-amber-50 to-amber-100 ..."><Flame size={36} /></div>` entirely
    - Replace the `<Star size={12} />` in the status pill with nothing (or a neutral `·` text node) for the non-complete state; keep `<Check size={12} />` for the complete state
    - Change `border-amber-100` on the streak `<article>` to `border-slate-100`
    - Change the status pill non-complete colors from `bg-amber-50 text-amber-700 ring-amber-100` to `bg-slate-100 text-slate-600 ring-slate-200`
    - Change the weekly progress bar fill from `bg-gradient-to-r from-amber-400 to-amber-500` to `bg-slate-700`
    - Optionally add a 7-cell day strip (`grid grid-cols-7`) below the streak number showing Mon–Sun cells: filled = `bg-slate-800`, empty = `bg-slate-100`, based on `weeklyCycleDay`
    - _Bug_Condition: `<Flame>` SVG in `bg-gradient-to-br from-amber-50 to-amber-100` box; `<Star>` in status pill; `bg-gradient-to-r from-amber-400 to-amber-500` progress fill_
    - _Expected_Behavior: no Flame or Star icons; neutral pill; solid `bg-slate-700` fill_
    - _Preservation: `streakDays` number, `weeklyCycleDay`, `weeklyProgress`, `isWeeklyComplete`, `weeklyRemainingDays`, `monthCareDays`, `streakStatusPill` text, `streakSupportCopy` text are all unchanged_
    - _Requirements: 2.2, 2.3_

  - [ ] 3.6 Refactor Weekly Progress bar fill color
    - Confirm the weekly progress bar fill change from task 3.5 is applied: class should be `bg-slate-700` not `bg-gradient-to-r from-amber-400 to-amber-500`
    - Verify width is still driven by `weeklyProgress` percentage (derived value unchanged)
    - _Requirements: 2.2_

  - [ ] 3.7 Refactor Today's Challenge section
    - Change `<article>` background from `bg-gradient-to-br from-white to-emerald-50/30` to `bg-white` (or `bg-slate-50`)
    - Change `border-emerald-100` on the article to `border-slate-100`
    - Remove the Target icon box: delete `<div className="flex h-11 w-11 ... bg-emerald-100 ..."><Target size={22} /></div>` and replace the flex-with-icon layout with a plain text-only block for title + description
    - Change the divider from `border-emerald-100` to `border-slate-100`
    - When `challengeDone` is true, show "Hôm nay: Đã hoàn thành đầy đủ 3 bữa" as an informational status label above the button
    - _Bug_Condition: `bg-gradient-to-br from-white to-emerald-50/30` on article; `<Target>` icon in `bg-emerald-100` box_
    - _Expected_Behavior: flat `bg-white` or `bg-slate-50` card; no Target icon; informational status copy when done_
    - _Preservation: challenge title, description, `challengeDone` state, `handleCompleteChallenge` handler, `first_complete_day` routing, button disabled state and "Đã hoàn thành" text are all unchanged_
    - _Requirements: 2.6_

  - [ ] 3.8 Refactor Badges / Rewards section to render full catalog with locked/unlocked states
    - Change the section title from "Huy hiệu đã mở khóa" to "Huy hiệu & Thành tích"
    - Replace `recentAchievements.map(...)` with a render over all keys in `BADGE_META`
    - For each key, determine locked/unlocked: `const isUnlocked = summary?.achievements?.some(a => a.key === key)`
    - Replace the emoji `<div>{meta.icon}</div>` with:
      ```jsx
      <img
        src={meta.image}
        alt={meta.label}
        className={`h-9 w-9 rounded-xl object-cover ${!isUnlocked ? "grayscale opacity-40" : ""}`}
      />
      ```
    - For unlocked badges, look up title/description from `summary.achievements` array; for locked badges, use the `meta.label` as the title with a "Chưa mở khóa" sub-label
    - Replace the empty-state block: remove `<Award size={32}>` icon; replace text with `"Thành tích sẽ được mở khóa khi bạn đạt cột mốc"` in `text-slate-400 text-sm text-center`
    - _Bug_Condition: emoji `{meta.icon}` rendered in badge cell; `<Award>` icon in empty state; only unlocked badges shown_
    - _Expected_Behavior: `<img>` elements with asset paths for all 8 badges; grayscale filter for locked; no emoji; no Award icon; correct empty-state copy_
    - _Preservation: `summary.achievements.slice(0, 6)` contract honored for unlocked data lookup; loading skeleton unchanged_
    - _Requirements: 2.4, 2.5, 2.8_

  - [ ] 3.9 Refactor Encouragement block
    - Remove the entire `<div className="... bg-gradient-to-r from-emerald-50 via-white to-emerald-50 ..."><div ...><Heart .../></div><p>...</p></div>` block
    - Replace with a left-bordered blockquote:
      ```jsx
      <blockquote className="border-l-2 border-slate-300 pl-4 py-1">
        <p className="text-sm text-slate-500 italic">{encouragement}</p>
      </blockquote>
      ```
    - Preserve the outer `{encouragement && (...)}` guard so the block is still hidden when `encouragement` is empty/falsy
    - _Bug_Condition: `bg-gradient-to-r from-emerald-50 via-white to-emerald-50` on container; `<Heart>` icon in `bg-emerald-100` box_
    - _Expected_Behavior: plain left-bordered `<blockquote>`; no Heart icon; no gradient_
    - _Preservation: `encouragement` text content is unchanged; block still conditionally rendered when truthy_
    - _Requirements: 2.7_

  - [ ] 3.10 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Decorative Elements Are Absent from Rendered Output
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - The test from task 1 encodes the expected behavior — when it passes, the bug is fixed
    - Run: `npx vitest run frontend/src/components/gamification/__tests__/GentleMotivationPanel.bug.test.jsx`
    - **EXPECTED OUTCOME: Test PASSES** (confirms all decorative elements have been removed)
    - If any assertion still fails, return to the relevant sub-task (3.2–3.9) and complete the fix
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_

  - [ ] 3.11 Verify preservation tests still pass
    - **Property 2: Preservation** - All Data Logic and API Contracts Are Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run: `npx vitest run frontend/src/components/gamification/__tests__/GentleMotivationPanel.preservation.test.jsx`
    - **EXPECTED OUTCOME: All tests PASS** (confirms no regressions in data logic or API behavior)
    - If any assertion fails, investigate the corresponding sub-task (3.3–3.9) for accidental data-logic changes
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10_

- [ ] 4. Checkpoint — Ensure all tests pass
  - Run the full frontend test suite: `npx vitest run --reporter=verbose`
  - Confirm both test files pass: `GentleMotivationPanel.bug.test.jsx` and `GentleMotivationPanel.preservation.test.jsx`
  - Visually inspect the Achievement page in the browser: no emoji in badge cells, no gradient backgrounds, no decorative icons, badge images render (placeholder SVGs), encouragement block shows as blockquote
  - Verify locked/unlocked badge states render correctly: unlocked badges are full-color, locked badges are grayscale + opacity-40
  - Confirm that clicking "Hoàn thành" still triggers the API call and refreshes the panel
  - Confirm that `first_complete_day` challenge still routes to `onAction()` instead of completing via API
  - Ask the user if any questions or visual adjustments are needed before closing this spec

## Notes

- All changes are confined to `frontend/src/components/gamification/GentleMotivationPanel.jsx` and the new `frontend/public/assets/` directories. `ThanhTuuView.jsx` and `mealRank.js` require no modifications.
- The `Check` icon from `lucide-react` is intentionally retained — it is a functional indicator on the challenge completion button, not a decorative section icon.
- Badge assets are placeholder SVGs. They can be replaced with final artwork at any point without changing the component code — just swap the files at the same paths.
- The progress bar gradient inside the level `<div>` track (not the section `<article>` container) is changed to a solid fill per the design spec. This is not exempt from the bug condition.
- Property-based testing is strongly recommended (e.g., `@fast-check/vitest`) for both the exploration and preservation tests to maximize input coverage. Manual parameterisation with `test.each` is an acceptable fallback.
- Run commands: `npx vitest run` for a single-pass test run (use `--run` flag to avoid watch mode).
