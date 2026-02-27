# QA Bug Report Template

Use this template for UI bugs, visual regressions, and functional regressions found during manual QA.

Works for:
- GitHub Issues
- Notion bug database entries
- Jira tickets
- Spreadsheet-linked bug notes

## 1. Bug Title

`[Area][Page][Device/Theme] Short issue summary`

Examples:
- `[Core][Login][Mobile Dark] Password toggle button overlaps input text`
- `[Admin][User Management][Desktop Light] Table action buttons wrap unexpectedly`
- `[Core][Goals][Desktop Dark] Comment card text contrast is too low`

## 2. Metadata

- **Bug ID**: `B-###` (optional)
- **Date Found**:
- **Tester**:
- **Environment**:
  - Browser:
  - OS:
  - App URL:
  - Build/Version:
- **Area**: `Auth / Core / User / Admin / Policy`
- **Page**:
- **Route**:
- **Device**: `Desktop / Tablet / Mobile`
- **Viewport**: (e.g. `1440x900`, `390x844`)
- **Theme**: `Light / Dark`
- **Severity**: `Low / Medium / High`
- **Priority**: `P1 / P2 / P3` (optional)
- **Type**: `UI / UX / Visual Regression / Functional Regression / Accessibility`

## 3. Summary

Short description (1-3 lines):

> Describe what is broken and why it matters.

## 4. Preconditions

List any required setup before reproducing:

- User logged in as `user/admin/owner` (if required)
- Test data exists (achievement/goal/message/etc.)
- Specific mode enabled (dark mode)
- Page opened at mobile viewport

## 5. Steps to Reproduce

1. Go to `...`
2. Click `...`
3. Toggle `...`
4. Resize to `...`
5. Observe `...`

## 6. Expected Result

What should happen:

- UI should remain aligned
- Text should be readable
- Button should stay inside card
- Form should not overflow

## 7. Actual Result

What actually happens:

- Button overlaps text
- Card height collapses
- Text wraps into icon
- Dark mode contrast too low

## 8. Impact

Choose one or explain:

- Cosmetic only
- Readability issue
- Usability issue (hard to interact)
- Functional blocker
- Workflow blocked

## 9. Frequency

- `Always`
- `Intermittent`
- `Only on specific viewport`
- `Only in dark mode`

## 10. Evidence

- **Screenshot(s)**:
  - `filename.png`
- **Screen recording** (optional):
  - `filename.mp4`
- **Console errors** (if any):
  - `None / Paste logs`

## 11. Affected Scope

List related pages/components that may also be affected:

- Same form controls on other auth pages
- Same card style used in dashboard/admin pages
- Same table pattern used in user management

## 12. Suspected Cause (Optional)

Only if obvious:

- Missing responsive class
- Dark mode override too broad
- Global CSS rule affecting table rows
- Long text not wrapped (`break-all` missing)

## 13. Suggested Fix (Optional)

Example:

- Add `break-all` to attachment label
- Add `sm:`/`md:` responsive layout override
- Increase dark mode text contrast class
- Normalize button min-height

## 14. QA Tracking Linkage

- **Matrix Row ID** (from `manual_test_matrix.md` / CSV):  
- **Checklist Section** (from `UI_QA_CHECKLIST.md`):  
- **Runbook Phase** (from `qa_runbook.md`):  

## 15. Fix Verification (To Fill After Fix)

- **Fixed By**:
- **Fix Date**:
- **Retested By**:
- **Retest Date**:
- **Retest Environment**:
- **Retest Status**: `PASS / FAIL`
- **Retest Notes**:

---

# Quick Copy Variants

## A. Short Version (Fast Logging)

**Title**:  
**Page/Route**:  
**Device/Theme**:  
**Severity**:  
**Steps**:  
**Expected**:  
**Actual**:  
**Screenshot**:  
**Matrix Row ID**:  

## B. UI-Only Bug Version (Visual)

**Title**:  
**Page**:  
**Device/Theme**:  
**Viewport**:  
**Issue Type**: `Spacing / Alignment / Contrast / Overflow / Typography`  
**Steps to Reproduce**:  
**Expected UI**:  
**Actual UI**:  
**Screenshot(s)**:  
**Severity**:  
**Notes**:  

## C. Functional Regression Version

**Title**:  
**Page/Route**:  
**User Role**:  
**Preconditions**:  
**Steps to Reproduce**:  
**Expected Result**:  
**Actual Result**:  
**Regression From** (if known):  
**Console/Network Errors**:  
**Severity**:  
**Evidence**:  

