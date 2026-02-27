# Manual Test Matrix (UI + Basic Regression)

Use this sheet while testing the app manually. Fill one row per page and viewport/theme combination.

Status values (recommended):
- `PASS`
- `FAIL`
- `BLOCKED`
- `N/A`

Severity values (for failures):
- `Low`
- `Medium`
- `High`

## Test Environment

- Date:
- Tester:
- App URL:
- Browser:
- OS:
- Build/Version:

## Legend

- `Device`: `Desktop` / `Tablet` / `Mobile`
- `Theme`: `Light` / `Dark`
- `Area`: `Core` / `Auth` / `Admin` / `User` / `Policy`

## Matrix (Page-Level)

| ID | Area | Page | Route | Device | Theme | Layout/Spacing | Typography | Controls/Forms | Nav/Footer | Functional Smoke | Status | Severity | Notes | Retest Status | Retest Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Auth | Login | `/login` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 2 | Auth | Login | `/login` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |
| 3 | Auth | Login | `/login` | Mobile | Light |  |  |  |  |  |  |  |  |  |  |
| 4 | Auth | Login | `/login` | Mobile | Dark |  |  |  |  |  |  |  |  |  |  |
| 5 | Auth | Register | `/register` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 6 | Auth | Register | `/register` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |
| 7 | Auth | Register | `/register` | Mobile | Light |  |  |  |  |  |  |  |  |  |  |
| 8 | Auth | Register | `/register` | Mobile | Dark |  |  |  |  |  |  |  |  |  |  |
| 9 | Auth | Forgot Password | `/forgot-password` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 10 | Auth | Forgot Password | `/forgot-password` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |
| 11 | Auth | Forgot Password | `/forgot-password` | Mobile | Light |  |  |  |  |  |  |  |  |  |  |
| 12 | Auth | Forgot Password | `/forgot-password` | Mobile | Dark |  |  |  |  |  |  |  |  |  |  |
| 13 | Auth | Reset Password | `/reset-password/<token>` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 14 | Auth | Reset Password | `/reset-password/<token>` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |
| 15 | Auth | Login 2FA | `/login-2fa` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 16 | Auth | Login 2FA | `/login-2fa` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |
| 17 | Core | Home | `/` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 18 | Core | Home | `/` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |
| 19 | Core | Home | `/` | Mobile | Light |  |  |  |  |  |  |  |  |  |  |
| 20 | Core | Home | `/` | Mobile | Dark |  |  |  |  |  |  |  |  |  |  |
| 21 | Core | About | `/about` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 22 | Core | About | `/about` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |
| 23 | Core | Achievements | `/achievements` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 24 | Core | Achievements | `/achievements` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |
| 25 | Core | Achievements | `/achievements` | Mobile | Light |  |  |  |  |  |  |  |  |  |  |
| 26 | Core | Achievements | `/achievements` | Mobile | Dark |  |  |  |  |  |  |  |  |  |  |
| 27 | Core | Goals | `/goals` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 28 | Core | Goals | `/goals` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |
| 29 | Core | Goals | `/goals` | Mobile | Light |  |  |  |  |  |  |  |  |  |  |
| 30 | Core | Goals | `/goals` | Mobile | Dark |  |  |  |  |  |  |  |  |  |  |
| 31 | Core | Contact | `/contact` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 32 | Core | Contact | `/contact` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |
| 33 | Core | Contact | `/contact` | Mobile | Light |  |  |  |  |  |  |  |  |  |  |
| 34 | Core | Contact | `/contact` | Mobile | Dark |  |  |  |  |  |  |  |  |  |  |
| 35 | User | Dashboard | `/dashboard` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 36 | User | Dashboard | `/dashboard` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |
| 37 | User | User Panel | `/user-panel` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 38 | User | User Panel | `/user-panel` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |
| 39 | User | Profile | `/profile` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 40 | User | Profile | `/profile` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |
| 41 | User | Settings | `/settings` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 42 | User | Settings | `/settings` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |
| 43 | User | Security Settings | `/security-settings` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 44 | User | Security Settings | `/security-settings` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |
| 45 | Admin | Owner Panel | `/owner-panel` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 46 | Admin | Owner Panel | `/owner-panel` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |
| 47 | Admin | User Management | `/user-management` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 48 | Admin | User Management | `/user-management` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |
| 49 | Admin | Contact Messages | `/contact-messages` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 50 | Admin | Contact Messages | `/contact-messages` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |
| 51 | Policy | Privacy Policy | `/privacy-policy` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 52 | Policy | Privacy Policy | `/privacy-policy` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |
| 53 | Policy | Terms | `/terms` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 54 | Policy | Terms | `/terms` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |
| 55 | Policy | Privacy Vault | `/privacy-vault` | Desktop | Light |  |  |  |  |  |  |  |  |  |  |
| 56 | Policy | Privacy Vault | `/privacy-vault` | Desktop | Dark |  |  |  |  |  |  |  |  |  |  |

## Mobile Priority Retest Matrix (High-Value Pages)

| ID | Page | Route | Theme | Nav Wrap | Card Stack | Form Controls | Buttons | Overflow | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| M1 | Login | `/login` | Light |  |  |  |  |  |  |  |
| M2 | Login | `/login` | Dark |  |  |  |  |  |  |  |
| M3 | Home | `/` | Light |  |  |  |  |  |  |  |
| M4 | Home | `/` | Dark |  |  |  |  |  |  |  |
| M5 | Achievements | `/achievements` | Light |  |  |  |  |  |  |  |
| M6 | Achievements | `/achievements` | Dark |  |  |  |  |  |  |  |
| M7 | Goals | `/goals` | Light |  |  |  |  |  |  |  |
| M8 | Goals | `/goals` | Dark |  |  |  |  |  |  |  |
| M9 | Contact | `/contact` | Light |  |  |  |  |  |  |  |
| M10 | Contact | `/contact` | Dark |  |  |  |  |  |  |  |
| M11 | User Management | `/user-management` | Light |  |  |  |  |  |  |  |
| M12 | User Management | `/user-management` | Dark |  |  |  |  |  |  |  |

## Functional Smoke Checklist (Quick)

Mark per run:

- [ ] Theme toggle switches and persists
- [ ] Login form submits (valid/invalid path)
- [ ] Register form validation visible and usable
- [ ] Forgot password generates reset link (dev flow)
- [ ] Achievements filters submit and render
- [ ] Goal/tip forms render without layout break
- [ ] Contact form custom subject toggle works
- [ ] Settings save button reachable and aligned
- [ ] Security settings forms/buttons render correctly
- [ ] User management table/card actions visible and usable

## Bug Log (Detailed, Optional)

| Bug ID | Linked Matrix ID | Page | Device/Theme | Severity | Summary | Steps to Reproduce | Expected | Actual | Screenshot Ref | Fixed In | Retest |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B-001 |  |  |  |  |  |  |  |  |  |  |  |

## Best-Practice QA Flow (Suggested)

1. Run one full pass in `Desktop Light`.
2. Run one full pass in `Desktop Dark`.
3. Run `Mobile Priority Retest Matrix`.
4. Fix issues.
5. Retest only failed rows + linked neighbor pages.
6. Final sign-off with screenshot evidence for key pages.

