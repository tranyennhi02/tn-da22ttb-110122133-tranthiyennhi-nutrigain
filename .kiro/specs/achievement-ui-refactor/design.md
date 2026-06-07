# Achievement UI Refactor – Bugfix Design

## Overview

The Achievement page (`ThanhTuuView` + `GentleMotivationPanel`) renders correct data through a presentation layer that uses gamification-heavy iconography (Lucide `Trophy`, `Flame`, `Star`, `Target`, `Heart`), emoji characters as badge icons, and gradient-filled cards. This creates a visual tone that conflicts with the product's intended calm, professional wellness identity (Apple Health / Fitbit / Notion style).

The fix is purely presentational: remove decorative icons and emoji, replace with clean typographic hierarchy, real image badge assets, and flat/bordered cards — while leaving every piece of data logic, API call, and state management completely untouched.

---

## Glossary

- **Bug_Condition (C)**: The condition that triggers the defect — any render path in `GentleMotivationPanel` or `ThanhTuuView` that outputs a decorative Lucide icon (Trophy, Flame, Star, Target, Heart), an emoji character used as a visual badge, or a gradient background on a section card.
- **Property (P)**: The desired rendered output — clean flat cards, typographic hierarchy, image-based badges, neutral color palette, no gradient fills on section containers, no emoji in the UI.
- **Preservation**: All data-fetching, state management, business logic, and API contracts that must not be altered by this fix.
- **`GentleMotivationPanel`**: The component at `frontend/src/components/gamification/GentleMotivationPanel.jsx` that owns the full Achievement page UI — level summary, streak, today's challenge, badges, and encouragement block.
- **`ThanhTuuView`**: The thin view wrapper at `frontend/src/views/ThanhTuuView.jsx` that renders `PageHeader` + `GentleMotivationPanel`.
- **`BADGE_META`**: The object in `GentleMotivationPanel.jsx` (and mirrored in `mealRank.js`) that maps badge keys to visual attributes. Currently stores emoji `icon` strings; after the fix it will store `image` paths instead.
- **`resolveLevel`**: Pure function computing level tier, progress %, and pointsToNext from a total-points value — must not be changed.
- **`LEVEL_TIERS`**: Threshold table used by `resolveLevel` — must not be changed.
- **`weeklyCycleDay` / `weeklyProgress`**: Derived streak values using modulo-7 logic — must not be changed.
- **Locked badge**: An achievement entry where `ach.unlocked !== true` (or the key is absent from `summary.achievements`) — rendered grayscale + low opacity.
- **Unlocked badge**: An achievement present in `summary.achievements` — rendered at full color.

---

## Bug Details

### Bug Condition

The defect manifests in every render of `GentleMotivationPanel`. The component imports and renders `Trophy`, `Flame`, `Star`, `Target`, and `Heart` from `lucide-react` as decorative section icons. It also reads emoji strings (`🍽️`, `⚖️`, `✅`, `🔥`, `📅`, `🎯`, `💪`, `🥗`, `🏅`) from `BADGE_META` as badge visuals, and applies `bg-gradient-to-br` / `bg-gradient-to-r` classes to section card backgrounds.

**Formal Specification:**

```
FUNCTION isBugCondition(renderedOutput)
  INPUT: renderedOutput — the JSX/DOM produced by GentleMotivationPanel
  OUTPUT: boolean

  RETURN (
    renderedOutput CONTAINS LucideIcon WHERE iconName IN
        ['Trophy', 'Flame', 'Star', 'Target', 'Heart']
    OR renderedOutput CONTAINS element WHERE textContent MATCHES /[\u{1F300}-\u{1FFFF}]/u
       AND element.role IN ['img', 'presentation', 'icon-badge']
    OR renderedOutput CONTAINS element WHERE className INCLUDES 'bg-gradient-to-br'
       AND element.tagName IN ['article', 'div']  -- section-level container only
       AND NOT element CONTAINS [level-progress-bar]  -- progress bar gradient is kept
  )
END FUNCTION
```

### Examples

| Section | Current (Defect) | Expected (Correct) |
|---|---|---|
| Level Summary | `<Trophy size={28}>` in a `bg-gradient-to-br from-emerald-50 to-emerald-100` box | Optional `<img src="/assets/icons/trophy.svg">` or no icon; flat card |
| Streak header | `<Flame size={36}>` in `bg-gradient-to-br from-amber-50 to-amber-100` box | No icon; streak number + "ngày" label in plain typography |
| Streak status pill | `<Star size={12}>` inside amber pill | Plain text pill, no icon (or `<Check>` for complete state — kept) |
| Weekly progress bar | `bg-gradient-to-r from-amber-400 to-amber-500` fill | Solid single-color fill (`bg-emerald-500` or `bg-slate-700`) |
| Today's Challenge card | `bg-gradient-to-br from-white to-emerald-50/30` + `<Target size={22}>` | Flat white / `bg-slate-50` card, no Target icon, informational copy |
| Encouragement block | `bg-gradient-to-r from-emerald-50 via-white to-emerald-50` + `<Heart size={18}>` | Left-bordered blockquote, no icon, no gradient |
| Badge entry (unlocked) | `{meta.icon}` renders `🍽️` emoji in colored box | `<img src="/assets/badges/first_meal_plan.png">` at full color |
| Badge entry (locked) | Same emoji, just not shown (absent from list) | `<img>` with `grayscale(100%) opacity-40` CSS filter |
| Empty badges state | `<Award size={32}>` icon + generic copy | No icon, text "Thành tích sẽ được mở khóa khi bạn đạt cột mốc" |

---

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- `getGamificationSummary()` API call — same endpoint, same request, same response parsing.
- `completeGamificationChallenge(key)` API call — same trigger condition (`today_challenge.key !== "first_complete_day"`), same refresh logic.
- `loadGamificationStats()` / `localStorage` read — same key (`nutrigain_gami_stats`), same shape.
- `resolveLevel(points)` computation — same `LEVEL_TIERS` thresholds and progress formula.
- `weeklyCycleDay`, `weeklyRemainingDays`, `isWeeklyComplete`, `weeklyProgress` — same modulo-7 derivation.
- First 6 achievements slice — `summary.achievements.slice(0, 6)`.
- `refreshKey` prop triggering re-fetch of both local stats and remote summary.
- `first_complete_day` challenge routing to `onAction()` instead of completing via API.
- `challengeDone` detection from `status === "completed"` (case-insensitive).
- `monthCareDays` null fallback to `"—"`.
- `Check` icon on the completed challenge button — this is functional, not decorative, so it is kept.

**Scope:**
All non-rendering code paths — API calls, localStorage access, derived value calculations, event handlers — are completely unaffected. Only JSX return values, import lists, className strings, and `BADGE_META` visual fields change.

---

## Hypothesized Root Cause

This is a presentation-layer design mismatch rather than a runtime error. The root causes are:

1. **Icon Library Overuse**: The component was built with Lucide icons as section identifiers. Every major section (Level, Streak, Challenge, Badges, Encouragement) has an accompanying decorative icon imported from `lucide-react`. These must be removed and replaced with image assets or pure typography.

2. **Emoji-as-Icon Pattern in BADGE_META**: `BADGE_META` stores emoji characters in an `icon` field, which renders as colorful glyph icons in badge rows. Emoji rendering varies across OS/browser and cannot be styled with CSS — this makes consistent locked/unlocked states impossible.

3. **Gradient Background Classes on Section Cards**: Multiple `article` and `div` containers use `bg-gradient-to-br` / `bg-gradient-to-r` classes that produce the visual warmth and game-UI feel. These need to be replaced with flat (`bg-white`, `bg-slate-50`) or very subtle bordered backgrounds.

4. **No Image Asset Infrastructure**: There is no `frontend/public/assets/badges/` or `frontend/public/assets/icons/` directory and no `image` field in `BADGE_META`. The badge rendering path goes straight from key → emoji, bypassing any asset pipeline.

5. **Missing Locked/Unlocked Badge Distinction**: The current implementation only shows unlocked achievements (those present in `summary.achievements`). There is no concept of showing all known badges with a locked visual state. The refactor adds this by rendering the full `BADGE_META` catalog with a locked state for badges not in the API response.

---

## Correctness Properties

Property 1: Bug Condition – Decorative Elements Are Absent from Rendered Output

_For any_ render of `GentleMotivationPanel` with any combination of valid `summary` data and `localStats`, the refactored component SHALL NOT emit any of the following in the DOM:
- A Lucide `Trophy`, `Flame`, `Star`, `Target`, or `Heart` component,
- An element whose text content is an emoji character used as a badge icon (`🍽️`, `⚖️`, `✅`, `🔥`, `📅`, `🎯`, `💪`, `🥗`, `🏅`, `🏅`),
- A section-level container with a `bg-gradient-to-br` or `bg-gradient-to-r` background class (progress bar fill gradients within track elements are exempt).

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8**

---

Property 2: Preservation – All Data Logic and API Contracts Are Unchanged

_For any_ sequence of user interactions (page load, challenge complete, refreshKey change) where the bug condition does NOT hold (i.e., the code is already producing clean UI output), the refactored component SHALL produce exactly the same API calls, localStorage reads, derived values, and rendered data content as the original component — differing only in visual presentation (icons replaced, gradients removed, asset paths used).

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10**

---

## Fix Implementation

### Changes Required

#### File 1: `frontend/src/components/gamification/GentleMotivationPanel.jsx`

**Imports**
1. **Remove decorative icons**: Delete `Trophy`, `Flame`, `Star`, `Target`, `Heart`, `Award`, `Leaf`, `Sparkles`, `Zap` from the `lucide-react` import. Retain `Check` (used on the functional completed-button).

2. **Update `BADGE_META`**: Replace every `icon` emoji field with an `image` field pointing to `/assets/badges/{key}.png`. Add a `label` field for alt text. Example:
   ```js
   first_meal_plan: { image: "/assets/badges/first_meal_plan.png", label: "Kế hoạch bữa ăn đầu tiên" }
   ```

3. **Update `badgeMeta` fallback**: Default to `{ image: "/assets/badges/default.png", label: "Huy hiệu" }`.

**Section 1 – Level Summary**
4. **Remove Trophy icon box**: Delete the `<div className="flex-shrink-0 flex h-14 w-14 ... bg-gradient-to-br ..."><Trophy .../></div>` block. Optionally replace with `<img src="/assets/icons/trophy.svg" className="h-10 w-10 opacity-60" alt="">` if a trophy icon asset is available, otherwise omit entirely.
5. **Progress bar fill**: Change `bg-gradient-to-r from-emerald-400 to-emerald-500` to `bg-emerald-600` (solid color).

**Section 2 – Streak**
6. **Remove Flame icon box**: Delete the `<div className="... bg-gradient-to-br from-amber-50 to-amber-100 ..."><Flame .../></div>` block entirely.
7. **Replace Star in status pill**: Change the conditional `{isWeeklyComplete ? <Check size={12} /> : <Star size={12} />}` — remove the `<Star>` branch; render nothing (or a neutral dot `·`) for the non-complete state.
8. **Weekly progress bar fill**: Change `bg-gradient-to-r from-amber-400 to-amber-500` to `bg-slate-700`.
9. **Card border**: Change `border-amber-100` on the streak `<article>` to `border-slate-100`.
10. **Add 7-cell day strip** (optional visual enhancement): Below the streak number, render a `grid grid-cols-7` strip showing Mon–Sun with filled cells for days ≤ `weeklyCycleDay`. This replaces the amber progress bar. Cells use `bg-slate-800` for filled, `bg-slate-100` for empty.

**Section 3 – Today's Challenge**
11. **Remove gradient background**: Change `bg-gradient-to-br from-white to-emerald-50/30` to `bg-white` (or `bg-slate-50`) on the `<article>`.
12. **Remove Target icon box**: Delete the `<div className="flex h-11 w-11 ... bg-emerald-100 ..."><Target .../></div>`. Replace challenge title/description layout with a plain text-only block (no icon container).
13. **Update border**: Change `border-emerald-100` to `border-slate-100`.
14. **Update informational copy**: When `challengeDone` is true, display "Hôm nay: Đã hoàn thành đầy đủ 3 bữa" as a plain status label above the button.

**Section 4 – Badges**
15. **Replace emoji rendering**: Change the badge item `<div className={... meta.color}>{meta.icon}</div>` to:
    ```jsx
    <img
      src={meta.image}
      alt={meta.label}
      className={`h-9 w-9 rounded-xl object-cover ${ach.unlocked === false ? "grayscale opacity-40" : ""}`}
    />
    ```
16. **Show full badge catalog**: Render all keys from `BADGE_META` (not just `recentAchievements`). For each key, check whether it appears in `summary.achievements` to set locked/unlocked state.
17. **Empty state**: Replace the `<Award size={32}>` icon block with plain text only — no icon, text `"Thành tích sẽ được mở khóa khi bạn đạt cột mốc"` in `text-slate-400 text-sm text-center`.

**Section 5 – Encouragement**
18. **Remove gradient and Heart icon**: Replace the entire `<div className="... bg-gradient-to-r ..."><Heart .../><p>...` block with a left-bordered blockquote:
    ```jsx
    <blockquote className="border-l-2 border-slate-300 pl-4 py-1">
      <p className="text-sm text-slate-500 italic">{encouragement}</p>
    </blockquote>
    ```

#### File 2: `frontend/public/assets/badges/` (new directory + placeholder SVGs)

19. **Create placeholder SVG assets** for each BADGE_META key plus `default`. Each SVG is a simple circular shape with an initials letter or abstract mark — grayscale version at `locked_{key}.svg` is not needed since CSS filter handles the locked state; just one `{key}.png` (or `.svg`) per badge. A minimal placeholder SVG template:
    ```svg
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
      <circle cx="32" cy="32" r="30" fill="#e2e8f0" stroke="#94a3b8" stroke-width="2"/>
      <text x="32" y="38" text-anchor="middle" font-size="22" fill="#64748b" font-family="sans-serif">◉</text>
    </svg>
    ```
    Badges to create: `first_meal_plan`, `first_weight_log`, `first_complete_day`, `three_active_days`, `three_balanced_days_in_week`, `perfect_calories`, `discipline_eater`, `diverse_menu`, `default`.

#### File 3: `frontend/public/assets/icons/trophy.svg` (optional)

20. **Create minimal trophy SVG** if the Level Summary section opts to include a subdued icon. If omitted, the icon box is simply removed.

#### File 4: `frontend/src/utils/mealRank.js` (optional mirror update)

21. **Add `image` field to any BADGE_META mirror** if one exists. The current `mealRank.js` does not contain `BADGE_META` — it only has `RANK_TIERS`, `DIVERSITY_RULES`, and the localStorage helpers — so no change is required here. `BADGE_META` lives exclusively in `GentleMotivationPanel.jsx`.

---

## Testing Strategy

### Validation Approach

Testing follows two phases: first run tests on the **unfixed** code to surface the bug (confirm decorative elements are rendered), then run tests on the **fixed** code to verify correct output and that no data behavior regressed.

---

### Exploratory Bug Condition Checking

**Goal**: Confirm that the unfixed component does render the decorative elements described in the bug condition, establishing a baseline before any changes.

**Test Plan**: Mount `GentleMotivationPanel` with mock props in a test environment (Vitest + Testing Library). Assert presence of elements that should be absent after the fix.

**Test Cases**:

1. **Trophy Icon Present** – Query `document.querySelector('svg[aria-hidden="true"]')` or by test-id; confirm a Trophy-shaped SVG is in the level section (will pass on unfixed, fail on fixed).
2. **Flame Icon Present** – Confirm `Flame` SVG renders inside the streak number area (will pass on unfixed, fail on fixed).
3. **Emoji Badge Renders** – Confirm badge list items contain text matching `/[\u{1F300}-\u{1FFFF}]/u` (will pass on unfixed, fail on fixed).
4. **Gradient Class Present** – Confirm the streak article has `className` containing `bg-gradient-to-br` (will pass on unfixed, fail on fixed).
5. **Today's Challenge Gradient Present** – Confirm the challenge card has `from-white to-emerald-50/30` (will pass on unfixed, fail on fixed).

**Expected Counterexamples** (from unfixed code):
- Lucide icon SVG nodes are present in the rendered DOM.
- `textContent` of badge cells contains emoji code-point ranges.
- `className` of section articles contains `bg-gradient-to-br`.

---

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed component does NOT render any decorative elements.

**Pseudocode:**
```
FOR ALL summaryData IN [null, minimalSummary, fullSummaryWithAchievements, challengeCompleted] DO
  render GentleMotivationPanel_fixed(summaryData, localStats)
  result := getRenderedDOM()
  ASSERT NOT isBugCondition(result)
    -- no Trophy/Flame/Star/Target/Heart SVG nodes
    -- no emoji characters in badge cells
    -- no bg-gradient-to-br on article elements
    -- no bg-gradient-to-r on section containers
    -- empty state text == "Thành tích sẽ được mở khóa khi bạn đạt cột mốc"
    -- badge cells contain <img> elements, not text emoji
END FOR
```

---

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed component produces the same data output (text content, API calls, event triggers) as the original.

**Pseudocode:**
```
FOR ALL summaryData IN validSummaryInputs DO
  FOR ALL userAction IN [pageLoad, refreshKeyChange, challengeComplete, firstCompleteDayAction] DO
    original_output := observe(GentleMotivationPanel_original, summaryData, userAction)
    fixed_output    := observe(GentleMotivationPanel_fixed,    summaryData, userAction)

    ASSERT original_output.apiCallCount   == fixed_output.apiCallCount
    ASSERT original_output.levelText      == fixed_output.levelText
    ASSERT original_output.streakNumber   == fixed_output.streakNumber
    ASSERT original_output.weeklyProgress == fixed_output.weeklyProgress
    ASSERT original_output.challengeTitle == fixed_output.challengeTitle
    ASSERT original_output.monthCareDays  == fixed_output.monthCareDays
    ASSERT original_output.onActionCalled == fixed_output.onActionCalled
  END FOR
END FOR
```

**Testing Approach**: Property-based testing with Vitest is recommended for preservation because:
- It generates many random `summary` payloads automatically, covering edge cases like `streak.current = 0`, `achievements = []`, `level = null`, and `monthCareDays = null`.
- It verifies that all text-content data values are identical between old and new renders.
- It catches accidental logic changes that pure snapshot tests might miss.

**Test Cases**:
1. **Level Data Preservation** – For any `totalPoints` in [0, 50, 100, 299, 300, 700, 1500, 9999], rendered level title and progress % must match `resolveLevel(totalPoints)`.
2. **Streak Number Preservation** – For any `streak.current` value, the rendered streak number and weekly cycle stats must match the modulo-7 derivation.
3. **monthCareDays Null Fallback** – When `monthCareDays` is null, the stats cell must show `"—"`.
4. **Challenge Button Preservation** – When `challengeDone = true`, the button must be disabled and show "Đã hoàn thành". When `key = "first_complete_day"`, clicking must call `onAction()` not the challenge API.
5. **refreshKey Re-fetch** – Changing `refreshKey` from 0 → 1 must trigger both `loadGamificationStats()` and `getGamificationSummary()`.

---

### Unit Tests

- Render with `summary = null` (loading state) — skeleton placeholders appear, no crash.
- Render with `summary` containing all 8 achievement keys — all 8 badge images render; none show emoji.
- Render with `summary.achievements = []` — empty state shows correct copy, no icon.
- Render with `streak.current = 7` — `isWeeklyComplete = true`, Check icon on pill, "Tuần mới bắt đầu" label.
- Render with `streak.current = 0` — "Nghỉ nhẹ" pill, streak number shows 0.
- Render with `today_challenge.status = "COMPLETED"` (uppercase) — challengeDone is true.

### Property-Based Tests

- **Badge image paths** – For any key in `BADGE_META`, `meta.image` starts with `/assets/badges/` and ends with `.png` or `.svg`.
- **No emoji in rendered output** – For any valid summary object, rendered HTML contains no Unicode emoji in the range `\u{1F300}–\u{1FFFF}`.
- **No gradient on section cards** – For any valid summary object, no `article` element has a `className` containing `bg-gradient-to-br` or `bg-gradient-to-r`.
- **Streak derivation invariant** – For any `streak.current = N`, `weeklyCycleDay = ((N-1) % 7) + 1` when `N > 0`, else 0.
- **Level progress bounds** – For any `totalPoints ≥ 0`, `levelInfo.progress` is in [0, 100].

### Integration Tests

- Full Achievement page load: mount `ThanhTuuView` → `GentleMotivationPanel` with mocked API; verify correct text content and no decorative icons in final DOM.
- Challenge complete flow: click "Hoàn thành" → API called → summary refreshed → button shows "Đã hoàn thành" → no visual regression.
- `refreshKey` cycle: change prop from 0 → 1 → 2; verify API called each time, rendered data updates, no crashes.
- Badge locked/unlocked states: mock API returning 2 of 8 achievements; verify 2 images are full-color and 6 are grayscale.
