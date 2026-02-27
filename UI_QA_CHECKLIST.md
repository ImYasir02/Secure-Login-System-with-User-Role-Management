# UI QA Checklist (Light/Dark, Desktop/Mobile)

Use this checklist after running the app locally. Test each page in:
- Desktop Light Mode
- Desktop Dark Mode
- Mobile Light Mode
- Mobile Dark Mode

Recommended viewport presets:
- Desktop: `1440x900`
- Tablet: `768x1024`
- Mobile: `390x844`

## Global Checks (Run on Every Page)

- Header/navbar alignment is stable (no wrapping/cutoff for links).
- Theme toggle switches correctly and preserves readability.
- Active nav item style is visible in both modes.
- Page background, card borders, and shadows match the new visual language.
- Buttons have consistent height, padding, and hover states.
- Inputs/selects/textareas have consistent height and focus ring.
- Labels have consistent spacing above controls.
- Text contrast is readable in both light and dark modes.
- No text overlaps, clipping, or unexpected wrapping.
- Footer spacing/links remain aligned and readable.
- No horizontal scroll on mobile (unless intentional table overflow container).

## Auth Pages

### `login`
- Split layout looks balanced on desktop.
- Right-side panel hides correctly on mobile and info cards move below form.
- Password eye toggle works.
- Password strength bar updates width/color.
- Forgot password link alignment stays correct.
- reCAPTCHA hidden flow does not break layout.

### `register`
- Form fields align consistently and full width.
- Password strength bar and checkbox row spacing look correct.
- Terms/Privacy links readable in both modes.
- Dev verification link box wraps long URL without overflow.

### `forgot_password`
- Form spacing and reset link card spacing are consistent.
- Long reset URL wraps correctly (no overflow).

### `reset_password`
- Both password fields align; show/hide buttons do not overlap text.

### `login_2fa`
- Single-card layout remains centered and balanced on mobile/desktop.

## Core Pages

### `home`
- Hero headline wraps cleanly on all viewports.
- CTA buttons spacing is consistent.
- Side cards stack correctly on smaller widths.
- "Why This Platform?" list item spacing is uniform.

### `about`
- Forms/cards inherit global styles cleanly.
- Editable item cards/details blocks are readable in dark mode.

### `achievements`
- Top hero + CTA spacing looks balanced.
- Filter row aligns correctly on desktop and stacks cleanly on mobile.
- Add Achievement form grid does not create uneven gaps.
- Achievement cards: badge chips, metadata lines, buttons align properly.
- Edit `details` panel controls remain readable and not cramped.
- Empty state card looks centered and consistent.

### `goals`
- Top notifications badge/panel spacing is stable.
- Add Goal / Share Tip forms have consistent control spacing.
- Saved Tips cards are visually consistent.
- Community tip cards maintain readable hierarchy (title/content/meta/actions).
- Comment blocks and nested edit forms remain readable in both modes.
- Pagination controls align and stay tappable on mobile.

### `contact`
- Form labels/fields spacing stays consistent.
- "Other Subject" field reveal does not shift layout awkwardly.
- Image preview box displays correctly without overflow.
- Right-side "Why Contact Us?" list aligns with left card height reasonably.

### `settings`
- Preference cards have consistent spacing and checkbox alignment.
- Action buttons row wraps cleanly on mobile.
- Danger Zone inputs/buttons remain readable and clearly separated.

### `security_settings`
- 4 security panels align well in 2-column desktop layout.
- Login history items are readable (timestamps don’t overflow).
- 2FA buttons and forms remain visually distinct.

### `profile`
- Profile info cards maintain equal spacing and readable labels.

### `dashboard`
- Stat cards align in grid without text clipping.
- Quick links cards have consistent hover states and spacing.

## User/Admin Pages

### `user_panel`
- Hero panel and stat/info cards align correctly.
- Quick action cards have consistent spacing/hover styles.

### `owner_panel`
- Summary stat cards align and scale properly.
- Action buttons wrap cleanly on mobile/tablet.
- Audit filter controls align with heading.
- Audit entries have consistent spacing and readable metadata.

### `contact_messages`
- Message cards maintain consistent spacing.
- Attachment button wraps long filenames safely.
- Long message bodies remain readable and do not overflow.

### `user_management`
- Add User form grid aligns on desktop and stacks on mobile.
- Mobile user cards: forms/buttons do not overlap.
- Desktop table:
  - header alignment consistent
  - row hover state visible
  - action buttons aligned
  - horizontal overflow works inside container only
- Status badges (active/inactive) readable in both modes.

## Policy/Utility Pages (Quick Pass)

Check these for typography and card consistency:
- `privacy_policy`
- `privacy_vault`
- `terms`
- `data_retention`
- `error`

## Interaction/Regression Checks

- Flash messages render correctly in both modes.
- `details/summary` toggles show `+ / -` indicator and remain clickable.
- File inputs show styled file button in both modes.
- Keyboard focus outline visible on links/buttons/inputs.
- Hover states do not reduce contrast in dark mode.

## Final Sign-off

- All tested pages pass in Light + Dark.
- All tested pages pass in Desktop + Mobile.
- No one-off spacing issues remain.
- No feature regressions observed during UI pass.

