# UI QA Checklist

Manual QA checklist for the Home page `Vault AI Demo Popup`, PWA install UX, and related UI polish.

## Scope

- Home page AI launcher card + popup
- Popup tabs (`Presets`, `JSON Preview`, `Quick Actions`)
- Mobile sheet behavior + swipe close
- Accessibility behaviors (keyboard/focus/ARIA)
- Deep-link popup open state
- PWA preview routes

## Test Environments

- Desktop Chrome/Chromium (latest)
- Desktop Firefox (latest)
- Mobile viewport in browser devtools (iPhone + Android sizes)
- Real mobile device (recommended for swipe + install prompts)
- Reduced-motion enabled OS/browser setting (at least one pass)

## Quick Smoke (Automated)

Run local smoke checklist:

```bash
./venv/bin/python scripts/ui_regression_smoke_checklist.py
```

Expected:

- All checks `PASS`
- No `500` responses

## Desktop QA (Home Page)

### 1. Home page loads cleanly

Steps:

1. Open `/`
2. Observe hero section and right-side Vault AI card

Expected:

- No broken layout
- AI card appears compact (not overloaded)
- `AI Demo Tools` button visible
- `AI Demo Popup` secondary trigger visible

### 2. Open popup from button

Steps:

1. Click `AI Demo Tools`

Expected:

- Backdrop appears
- Popup opens with smooth animation
- Body/background scroll locked
- Focus moves into popup
- URL updates with `?ai_demo=1` (and current tab)

### 3. Open popup from card trigger

Steps:

1. Close popup
2. Click `AI Demo Popup` row trigger

Expected:

- Same popup opens
- On close, focus returns to exact trigger used (card row)

## Popup Tabs QA

### 4. Tab switching (mouse)

Steps:

1. Open popup
2. Switch between `Presets`, `JSON Preview`, `Quick Actions`

Expected:

- Active tab visual state updates
- Correct panel content shown
- Non-active panels hidden
- Smooth crossfade/slide transition (unless reduced motion enabled)

### 5. Tab switching (keyboard)

Steps:

1. Focus a tab button
2. Press `ArrowRight`, `ArrowLeft`, `Home`, `End`

Expected:

- Focus moves across tabs
- Active tab changes
- Correct panel shown
- `aria-selected` updates correctly

### 6. Last opened tab memory

Steps:

1. Open popup and switch to `JSON Preview`
2. Close popup
3. Refresh page
4. Reopen popup

Expected:

- Popup opens on last selected tab (`JSON Preview`)

## JSON Preview Tools QA

### 7. Preset selector updates preview

Steps:

1. Open popup -> `Presets`
2. Change preset (`Goal`, `Doc`, `Roadmap`)
3. Open `JSON Preview` tab

Expected:

- Header preset badge updates (e.g. `Doc Demo`)
- Preview title/description/icon/output label update
- Sample JSON updates

### 8. JSON controls (copy / wrap / download)

Steps:

1. Open `JSON Preview`
2. Toggle `No wrap` / `Wrap`
3. Toggle `Pretty` / `Minified`
4. Click `Copy JSON`
5. Click `Download .json`

Expected:

- Wrap state changes preview formatting
- Wrap preference persists after refresh
- Copy button shows temporary success/failure label
- Download file name matches selected preset and format (`pretty` or `min`)

## Quick Actions QA

### 9. Quick actions work

Steps:

1. Open popup -> `Quick Actions`
2. Click `Randomize`
3. Click `Copy Demo Prompt`
4. Click `See JSON Preview`

Expected:

- Randomize changes preset selection and labels
- Copy action updates button text briefly
- `See JSON Preview` switches tab to JSON panel

## Accessibility QA

### 10. Dialog semantics

Steps:

1. Inspect popup in browser devtools (Elements)

Expected:

- Popup has `role="dialog"`
- `aria-modal="true"`
- `aria-labelledby` and `aria-describedby` present

### 11. Focus trap

Steps:

1. Open popup
2. Press `Tab` repeatedly
3. Press `Shift+Tab` repeatedly

Expected:

- Focus remains inside popup
- Does not move to page content behind popup

### 12. Escape to close

Steps:

1. Open popup
2. Press `Esc`

Expected:

- Popup closes
- Focus returns to opener

### 13. Inert background support (where supported)

Steps:

1. Open popup
2. Try interacting with background content (click/tab)

Expected:

- Background interaction blocked or ignored
- Popup remains primary focus area

## Mobile / Touch QA

### 14. Mobile full-screen sheet layout

Steps:

1. Open `/` in mobile viewport or real mobile device
2. Open popup

Expected:

- Popup behaves like full-screen sheet
- Drag handle visible
- Header/tabs visible and usable
- Content scrolls within popup body

### 15. Swipe-down close (top-only guard)

Steps:

1. Open popup on mobile
2. Scroll popup content down
3. Try swipe-down from header/handle
4. Scroll back to top
5. Swipe-down again

Expected:

- When content is scrolled down: popup should **not** close accidentally
- At top: swipe-down closes popup
- Drag indicator animates during swipe

### 16. Touch interactions

Steps:

1. Tap tabs
2. Tap buttons inside popup
3. Tap backdrop

Expected:

- Tabs switch correctly
- Buttons respond correctly
- Backdrop tap closes popup

## Deep-Link QA

### 17. Open popup via query param

Steps:

1. Open `/?ai_demo=1`

Expected:

- Popup opens automatically on page load

### 18. Open popup at specific tab

Steps:

1. Open `/?ai_demo=1&ai_demo_tab=json`
2. Open `/?ai_demo=1&ai_demo_tab=quick`

Expected:

- Popup opens automatically
- Correct tab is active

### 19. URL sync on popup actions

Steps:

1. Open popup manually
2. Switch tabs
3. Close popup

Expected:

- Open adds `ai_demo=1` + `ai_demo_tab=<tab>`
- Tab switch updates `ai_demo_tab`
- Close removes `ai_demo` params

## Reduced Motion QA

### 20. Reduced-motion behavior

Steps:

1. Enable `prefers-reduced-motion` (OS/browser)
2. Reload home page
3. Open popup and switch tabs
4. Try swipe interaction on mobile viewport

Expected:

- Popup/tab animations minimized or near-instant
- No excessive motion effects
- Functionality remains unchanged

## PWA Preview Routes QA

### 21. PWA preview renders

Steps:

1. Open `/pwa-preview?layout=wide`
2. Open `/pwa-preview?layout=mobile`

Expected:

- Both pages render `200 OK`
- No template errors
- Layout is stable for screenshot capture

## Regression Notes Template

Use this while testing:

- Browser/device:
- Route:
- Steps:
- Actual result:
- Expected result:
- Screenshot/video:
- Severity: (`Low` / `Medium` / `High`)

