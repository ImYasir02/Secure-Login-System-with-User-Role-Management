# QA Runbook (Fast, Structured UI + Regression Pass)

This runbook gives a practical testing sequence so you can validate the UI refresh quickly without missing critical flows.

Use with:
- `UI_QA_CHECKLIST.md`
- `manual_test_matrix.md`
- `qa_status_template.csv`

## 1. Goal

Validate that:
- Light/Dark theme UI is consistent
- Desktop/Mobile layouts are stable
- Core user flows still work (no regressions)
- Admin/User pages remain usable after UI-only changes

## 2. Pre-Run Setup

Before starting:

1. Start the app locally.
2. Open browser devtools.
3. Prepare test accounts:
   - normal user
   - admin/owner (if available)
4. Keep one sheet open:
   - `qa_status_template.csv` (spreadsheet)
5. Keep one reference open:
   - `UI_QA_CHECKLIST.md`

Recommended browser setup:
- Chrome/Edge (primary)
- Optional spot-check in Firefox

Recommended viewports:
- Desktop: `1440x900`
- Mobile: `390x844`

## 3. Test Strategy (Fastest Order)

Do not test randomly. Use this order:

1. `Desktop Light` full critical-path pass
2. `Desktop Dark` full critical-path pass
3. `Mobile Light` priority pages
4. `Mobile Dark` priority pages
5. Admin/User pages (desktop first)
6. Policy/utility pages quick typography pass
7. Targeted retest of failures only

Why this order:
- Most layout/theme issues appear early on desktop
- Dark mode catches many contrast/override problems
- Mobile catches stacking/overflow issues after desktop fixes
- Admin pages are lower traffic but still important

## 4. Execution Phases

## Phase A: Smoke + Theme Baseline (10-15 min)

Purpose: confirm app is testable before deep QA.

Steps:

1. Open `/`
2. Toggle theme Light -> Dark -> Light
3. Verify header/footer render properly
4. Open `/login`
5. Verify form fields + CTA visible
6. Open `/register`
7. Open `/contact`
8. Open `/achievements`
9. Open `/goals`

If any page is broken visually (major overlap/blank/missing styles):
- Stop
- Log in matrix as `FAIL`
- Fix before continuing deep pass

## Phase B: Core UI Pass (Desktop Light) (20-35 min)

Use `qa_status_template.csv`.

Priority pages:

1. `/login`
2. `/register`
3. `/forgot-password`
4. `/`
5. `/achievements`
6. `/goals`
7. `/contact`
8. `/dashboard` (logged in)
9. `/settings`
10. `/security-settings`

For each page:
- Mark `layout_spacing`
- Mark `typography`
- Mark `controls_forms`
- Mark `nav_footer`
- Mark `functional_smoke`
- Set overall `status`
- Add notes if issue found

## Phase C: Core UI Pass (Desktop Dark) (20-35 min)

Repeat the same priority pages in dark mode.

Focus on:
- text contrast
- hidden borders
- button hover states
- glow/gradient overlays not blocking content
- form focus rings
- table readability (if present)

## Phase D: Mobile Priority Pass (Light + Dark) (20-30 min)

Use mobile emulator (`390x844`).

Priority list:

1. `/login`
2. `/`
3. `/achievements`
4. `/goals`
5. `/contact`
6. `/user-management` (admin)

For each page check:
- nav wrap
- stacking order
- button tap sizes
- text clipping
- overflow/horizontal scroll
- form spacing

Use the `Mobile Priority Retest Matrix` in `manual_test_matrix.md`.

## Phase E: User/Admin Desktop Pass (15-25 min)

User pages:
- `/user-panel`
- `/profile`
- `/settings`
- `/security-settings`
- `/dashboard`

Admin pages:
- `/owner-panel`
- `/user-management`
- `/contact-messages`

Focus:
- cards/tables alignment
- action button consistency
- table hover/readability
- form rows and grid spacing
- long text wrapping (emails/messages)

## Phase F: Policy / Utility Quick Pass (5-10 min)

Quick visual consistency check only:
- `/privacy-policy`
- `/privacy-vault`
- `/terms`
- `/data-retention`
- error page (trigger or route if available)

Focus:
- typography rhythm
- card spacing
- dark mode readability

## 5. Functional Smoke Scenarios (Minimal but Important)

Run these once per major pass (preferably desktop light, then spot-check dark):

1. Theme toggle changes mode and persists after page navigation
2. Login form:
   - invalid submit shows message
   - password eye toggle works
3. Register form:
   - strength bar moves
   - terms checkbox visible and usable
4. Forgot password:
   - form submit returns reset link (dev flow)
5. Contact form:
   - subject `Other` reveals custom input
   - image preview appears for image file
6. Achievements:
   - filters submit without layout break
7. Goals:
   - filters/forms render correctly
   - comments/actions area readable
8. User management:
   - table/card actions visible
   - mobile card layout not broken

## 6. Issue Logging Rules (Best Way)

When you find a bug:

1. Add `FAIL` in matrix row
2. Set severity:
   - `High`: blocks interaction or page unusable
   - `Medium`: visible UI break / hard-to-use control
   - `Low`: minor spacing/visual inconsistency
3. Add short reproducible note
4. (Optional) Add detailed entry in `manual_test_matrix.md` bug log

Good note format:
- `Dark mode / mobile / goals: comment action buttons wrap into text block at 390px`

## 7. Retest Flow

After fixes:

1. Retest only failed rows first
2. Retest neighboring pages that share same layout pattern
   - auth pages together
   - admin table pages together
   - forms-heavy pages together
3. Update:
   - `retest_status`
   - `retest_notes`
4. If fix introduces new issue:
   - create new bug entry / note

## 8. Sign-Off Criteria

Sign off only when:

- No `High` severity failures remain
- All critical pages are `PASS` in Desktop Light/Dark
- Mobile priority pages are `PASS` in Light/Dark
- No blocking admin-page issues remain
- Theme toggle and core forms work

## 9. Suggested Timeboxed Plan (Single Tester)

Fast pass (60-90 min):

1. Phase A
2. Phase B (critical pages only)
3. Phase C (critical pages only)
4. Phase D (mobile priority)
5. Log issues

Full pass (2-3 hours):

1. Phase A-F
2. Functional smoke
3. Retest cycle
4. Final sign-off

## 10. Optional Evidence Pack (Recommended)

Capture screenshots for:

- Home (Light + Dark, Desktop)
- Login (Light + Dark, Desktop)
- Achievements (Desktop + Mobile)
- Goals (Desktop + Mobile)
- Contact (Desktop + Mobile)
- User Management (Desktop + Mobile)

Store with naming pattern:
- `YYYY-MM-DD_page_theme_device.png`
- Example: `2026-02-24_login_dark_desktop.png`

