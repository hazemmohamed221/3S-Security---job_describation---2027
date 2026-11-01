# Stage 4 navigation and Arabic presentation

Implemented and verified on 30 October 2026. This is a presentation change; database content, schema, authorization and document interchange contracts are unchanged.

## Modified files

| File | Change |
|---|---|
| `app.py` | Replaced top-level horizontal tabs with role-aware sidebar radio navigation. Only the selected screen executes. Admin settings have two short internal tabs for users/permissions and backups, with KPIs above them. Simplified the main banner; added complete audit-record details and escaped before/after text. Every dataframe goes through the shared presentation renderer. |
| `presentation.py` | New shared navigation labels, Arabic action/field/role labels, timestamp formatting, readable audit notes, explicit audit column schema and a common dataframe renderer with right-aligned text and deliberate widths. Long Arabic numeric headers get wider columns. |
| `utils.py` | Replaced global font/RTL overrides on every `div`/`span` and every grid descendant with targeted text styles. Preserves native icon fonts and canvas geometry. Adds a 340px desktop sidebar with 320px minimum width, natural identity wrapping, selected/admin navigation emphasis, compact banner/badges, toolbar clearance and production-chrome hiding. |
| `auth.py` | Compact sidebar brand and profile markup using scoped classes. Existing escaped identity text, session validation and logout remain intact. |
| `.streamlit/config.toml` | Declares Cairo through Streamlit's theme so native dataframe canvas text also uses it. Uses minimal toolbar mode. Existing telemetry/error masking, CORS/XSRF and disabled magic settings remain in force. |
| `tests/test_app_smoke.py`; `tests/test_stage2_app.py`; `tests/test_admin_management.py` | Existing workflow tests now select their sidebar screen before interacting. Admin visibility assertions inspect sidebar options rather than removed top-level tabs. The existing 224 cases and their behavior/security checks are retained. |
| `tests/test_stage4_ui.py` | 24 new cases for all admin/member routes, inactive-screen isolation, stale navigation recovery, Arabic actions/roles/fields, timestamp handling, full audit notes, dataframe column configuration, numeric-header width and icon-safe CSS. |
| `docs/STAGE4_UI_UX.md` | This change summary and verification record. |

## Navigation and layout

The administrator sidebar exposes all seven requested screens in order: dashboard, card directory, reviews, Word import, interviews, audit history and **⚙️ لوحة الإدارة والإعدادات**. The admin option has a persistent accent. Managers/employees retain their assigned-card, requests, company-directory and Word-export screens; restricted HR/admin workflows are not exposed. All write operations still enforce the verified actor on the server.

Invalid/stale navigation values reset to a valid role-specific screen. Switching to export retains a manager's browsed card while employees remain scoped to their assignment. Accounts without an assignment can still open their requests and the readable company directory.

Only the active top-level screen runs. Navigating to the dashboard/settings no longer generates hidden Word exports or evaluates the review queue. Horizontal tabs are confined to the two short subsections inside admin settings.

Sidebar typography uses normal Arabic word wrapping, adequate padding and a desktop width of 340px (minimum 320px). The responsive CSS constrains the sidebar to the available narrow viewport. The collapsible-sidebar control remains available; deployment, main-menu and footer chrome are hidden.

## Tables and icons

The old `div`/`span` font rule applied Cairo with `!important` to Material icon elements, replacing the icon typeface. The old grid-descendant RTL rule also interfered with native grid internals. Both broad overrides are removed. Cairo is now configured in the theme and scoped to text, while native icon glyphs retain their own fonts.

Native canvas coordinates remain LTR to preserve grid/toolbar geometry; each displayed data column explicitly right-aligns its content. This separates Arabic text alignment from the framework's drawing coordinates. Dataframes have 20px top margin plus toolbar padding, hidden indexes, explicit column configuration and larger row heights.

Audit rows use Arabic action labels such as `تعديل بيانات`, `اعتماد نهائي`, `رفض` and `استيراد بطاقة`. Known role and field codes are translated; existing Arabic names/text are retained. Internal `actor_id`/`version` note labels are displayed readably without discarding their values. This conversion never changes audit rows or hashes in SQLite.

Timestamps display as `YYYY-MM-DD HH:mm`. Aware timestamps are converted to Africa/Cairo; historical naive timestamps retain their clock time because their original timezone is not reconstructed. Empty/invalid timestamps show an explicit label. Structured interview timestamps are formatted, while existing human-written Arabic day labels are preserved.

The audit grid declares all seven columns: record ID, timestamp, title, section, action, actor and notes. Titles and notes receive large widths. Wide records intentionally scroll horizontally instead of squeezing letters into unreadable fragments. The native fullscreen option remains available. The record inspector below the table shows the full title, section, action, notes and before/after content without clipping or substring truncation.

## Verification

- Required command: **248 passed**, no failures/skips, in **26.73 seconds**: all **224 existing + 24 new** cases.
- `pip check`: **No broken requirements found**.
- Ninety upstream `importlib.metadata` deprecation warnings were emitted by Streamlit AppTest. As in earlier stages, the full tests ran outside the Windows sandbox's temp/socket restrictions.
- Real browser QA used a separate synthetic database and a localhost server on port 8510. No real credentials or personnel data were used in browser testing.
- At **1280 × 720**, all seven admin menu items, including the highlighted settings option, were visible without horizontal navigation truncation. Long Arabic identity/department text wrapped naturally. The admin page displayed its KPIs and two short subsection tabs.
- The audit grid displayed full Arabic titles and minute-formatted dates in Cairo. The toolbar was separated from its descriptive text. The native column menu was opened: sorting arrows, statistics, autosize, pinning and visibility rendered as icons rather than raw Material glyph names. Deploy/main-menu/footer chrome was absent.
- Synthetic screenshots are retained locally under `_stage3_work/stage4-ui/`: `admin-screen.png`, `audit-screen.png` and `audit-menu.png`. They are visual QA artifacts and are excluded from the patch.
- The complete logical SHA-256 of the business database matched its pre-change baseline. All existing values, IDs and history are unchanged: **15 users, 26 cards, 399 responsibilities, 9 interviews and 28 audit events**.
- `docs/changes/stage4-ui-ux.patch` contains the 10 changed/new text files listed above. It is checked and applied against an isolated pre-Stage-4 baseline, then each reconstructed file is compared to the delivered source. It excludes databases, backups and screenshots.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python -B -m pytest -q
.\.venv\Scripts\python -m pip check
```

Restart the Streamlit process to load the theme configuration. Browser refresh then loads the new CSS and navigation. Visual checks covered the desktop viewport above; no screen-reader or physical mobile-device certification is claimed.

The native font configuration follows [Streamlit's custom-font documentation](https://docs.streamlit.io/develop/concepts/configuration/theming-customize-fonts), which also covers dataframe fonts. Cairo continues to load from Google Fonts as requested, with CSS text fallbacks to Tahoma/sans-serif.
