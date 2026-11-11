# Technical Architecture & Implementation Guide (`technical.md`)

This document explains **what** was implemented in `badminton-ranking-system`, **how** the Google Sheets formula engine and frontend work together, and **why** specific architectural decisions (such as hosting the frontend on GitHub Pages while using Google Sheets + Apps Script as a serverless backend) were made.

---

## 1. Why GitHub Pages + Google Apps Script?

A Google Sheet is an ideal database for a club ranking system: organizers can inspect it, back it up, or edit rows directly in a familiar spreadsheet UI at zero cost. However, serving a web interface directly from Google Apps Script (`HtmlService`) comes with major limitations:

1. **Double-Iframe Sandbox Restrictions:** Apps Script `HtmlService` wraps every web app inside a cross-origin Google sandbox iframe (`googleusercontent.com`). This breaks mobile `<meta name="viewport">` scaling, prevents custom tab favicons (`<link rel="icon">`) and clean page titles from working reliably, blocks URL query/path routing, and displays a permanent Google warning banner on mobile browsers.
2. **Cryptic URLs:** Apps Script URLs look like `https://script.google.com/macros/s/AKfycb.../exec`, which are hard to share or bookmark.
3. **Slow Cold Starts for HTML Rendering:** Rendering HTML via `HtmlService` requires a round-trip through Google's Caja/iframe sanitizer before anything appears on screen.

### Our Decoupled Architecture

By decoupling the system into a **static frontend on GitHub Pages** and a **pure JSON API in Google Apps Script (`ContentService`)**:

- **Clean URLs & Native Browser Behavior:** Each ranking instance lives at a clean path (e.g., `/vub-sportmix-badminton/`) with native mobile viewport scaling, custom club favicons, and instant first paint.
- **Multi-Tenant Single-Template Design:** The entire UI lives in a single shared [`template.html`](./template.html). Individual ranking pages (such as [`vub-sportmix-badminton/index.html`](./vub-sportmix-badminton/index.html)) are tiny 14-line bootstrap files that define `window.RANKING_CONFIG` (`title` and `apiUrl`) and load `../template.html` with `{ cache: "no-cache" }`.
- **Hidden Base Template:** Because the shared template is named `template.html` (rather than `index.html`) and checks for `window.RANKING_CONFIG` before initializing, visiting the root repository URL returns a `404` rather than exposing an unconfigured generic page.
- **CORS-Free JSON Communication:** POST requests from GitHub Pages to Apps Script use `Content-Type: text/plain;charset=utf-8` with `redirect: "follow"` and `credentials: "omit"`. Treating the JSON body as a CORS "simple request" avoids `OPTIONS` preflight requests (which Google Apps Script Web Apps do not support) while still delivering structured JSON payloads to `doPost(e)`.

---

## 2. Google Sheets Database & Formula Engine ([`code.gs`](./code.gs))

All ELO ratings, win/loss/tie records, and per-match ELO deltas are computed **natively inside Google Sheets via spreadsheet formulas**, making the Sheet the single source of truth.

### 2.1 Three-Sheet Schema

1. **`Players` (`A1:K50+`)**
   - **Columns `A–C`:** `Player Name`, `Short Name` (auto-extracted first name with disambiguating last initial when two players share a first name), and `Initials` (2-letter avatar code).
   - **Columns `D–G` (Singles):** `Singles W`, `Singles L`, `Singles T` (`COUNTIFS` over `Singles_Matches`), and `Singles ELO` (`1000 + SUMIF` of all personal deltas in `Singles_Matches`).
   - **Columns `H–K` (Doubles):** `Doubles W`, `Doubles L`, `Doubles T` (`COUNTIFS` across both team slots in `Doubles_Matches`), and `Doubles ELO` (`1000 + SUMIF` across all 4 player columns in `Doubles_Matches`).

2. **`Doubles_Matches` (`A1:U102+`)**
   - **Row `2` (Hidden Baseline Anchor):** Holds the starting ELO constant (`1000`) in `P2:S2`. This ensures the cumulative `SUMIF($C$2:C(r-1), ...)` formulas on Row 3 always have a valid range without `#REF!` errors when inserting or sorting rows.
   - **Rows `3+`:**
     - **Inputs (`Col B–L`):** `Date` (`yyyy/mm/dd hh:mm`), `Team 1 Player 1`, `Team 1 Player 2`, `Team 2 Player 1`, `Team 2 Player 2`, and set scores `S1 T1..S3 T2`.
     - **Calculated Columns (`Col A` & `Col M–U`):** `Match #`, `Sets T1`, `Sets T2`, `Winner` (`T1`, `T2`, or `TIE`), pre-match ELO for each of the 4 players (`T1 P1 Pre-ELO` .. `T2 P2 Pre-ELO`), and `T1 ELO Delta` / `T2 ELO Delta`.

3. **`Singles_Matches` (`A1:Q102+`)**
   - Follows the exact same layout as `Doubles_Matches` with 2 players (`Player 1`, `Player 2`) instead of 4.

### 2.2 Row-Order ELO Calculation & Automatic Chronological Sorting

In Google Sheets, each match row `r` computes every participant's pre-match ELO by summing `1000` plus all ELO deltas from **rows `2` through `r - 1`**:

```excel
=1000 + SUMIF($C$2:C(r-1), C(r), $T$2:T(r-1)) + SUMIF($D$2:D(r-1), C(r), $T$2:T(r-1))
      + SUMIF($E$2:E(r-1), C(r), $U$2:U(r-1)) + SUMIF($F$2:F(r-1), C(r), $U$2:U(r-1))
```

Because these formulas depend strictly on **row order** (top to bottom) rather than parsing timestamps inside complex array formulas:
- [`sortMatchesByDate_`](file:///d:/Development/badminton-ranking-system/code.gs#L186-L224) in [`code.gs`](./code.gs) automatically sorts the match input columns (`Col B–L` for Doubles, `Col B–J` for Singles) chronologically by the timestamp in `Col B` (using a stable sort that preserves row order when timestamps are identical).
- Because the formula columns (`Col A` and `Col M–U` / `Col K–Q`) stay anchored to their row indices, the Sheet immediately recalculates the entire ELO history in the updated chronological order whenever a match date is edited or added out of order.

### 2.3 Database Initialization & Reset

Running **Badminton Admin → Initialize Database** creates and formats the `Players`, `Doubles_Matches`, and `Singles_Matches` tabs on a blank Google Sheet, or prompts for confirmation before resetting an existing spreadsheet to a clean empty database.

---

## 3. ELO Rating Model

All ELO parameters are defined once at the top of [`code.gs`](./code.gs) (`STARTING_ELO = 1000`, `BASE_K = 40`, `MARGIN_K = 40`) and passed to the frontend via `eloConfig` in `getAppState()` so the live match preview uses the exact same constants as the Google Sheet.

1. **Individual Ratings in Random-Partner Doubles:**
   - Every player carries their own personal Doubles ELO (`1000` baseline) and Singles ELO (`1000` baseline).
   - In Doubles, a team's effective rating is the arithmetic mean of the two partners' pre-match Doubles ELOs:
     $$R_{\text{Team 1}} = \frac{R_{A_1} + R_{A_2}}{2}, \qquad R_{\text{Team 2}} = \frac{R_{B_1} + R_{B_2}}{2}$$

2. **Expected Win Probability:**
   - Using the standard logistic curve with scale `400`:
     $$E_1 = \frac{1}{1 + 10^{(R_{\text{Team 2}} - R_{\text{Team 1}}) / 400}}, \qquad E_2 = 1 - E_1$$

3. **Score-Margin Multiplier ($K_{\text{base}} = 40$, $K_{\text{margin}} = 40$):**
   - To reward decisive point differentials across all played sets while keeping upsets responsive, the effective K-factor scales linearly with the total point margin divided by total points played:
     $$K_{\text{eff}} = K_{\text{base}} + K_{\text{margin}} \times \frac{|\text{Pts}_1 - \text{Pts}_2|}{\max(1, \text{Pts}_1 + \text{Pts}_2)}$$

4. **Zero-Sum Rating Update:**
   - For a win ($S_1 = 1$) or loss ($S_1 = 0$), both partners on Team 1 receive $\Delta_1$ and both partners on Team 2 receive $\Delta_2 = -\Delta_1$:
     $$\Delta_1 = \text{ROUND}\!\left(K_{\text{eff}} \times (S_1 - E_1)\right), \qquad \Delta_2 = -\Delta_1$$
   - If a match ends tied in sets (`1–1` when only 2 sets are played), `Winner` is recorded as `TIE` and $\Delta_1 = \Delta_2 = 0$.

---

## 4. Security & Concurrency in [`code.gs`](./code.gs)

- **Salted SHA-256 Admin Authentication:** Plaintext passwords are never stored in the code or spreadsheet. Setting an admin password generates a random UUID salt (`ADMIN_SALT`) and stores `SHA-256(salt + ":" + password)` (`ADMIN_PASSWORD_HASH`) in `PropertiesService.getScriptProperties()`.
- **Constant-Time Hash Verification:** `timingSafeEqual_` compares the candidate hash and stored hash in constant time.
- **Brute-Force Lockout:** `CacheService.getScriptCache()` tracks failed password attempts (`AUTH_FAIL_COUNT`) and locks admin authentication for 15 minutes after 5 failed attempts.
- **Concurrency Locking & Formula Injection Prevention:** All write operations (`addNewPlayer`, `logDoublesMatch`, `logSinglesMatch`) acquire a script-wide mutex via `LockService.getScriptLock()` and sanitize text inputs via `sanitizeText_` to reject leading formula characters (`=`, `+`, `-`, `@`).

---

## 5. Frontend UX & Engineering Details ([`template.html`](./template.html))

- **Responsive Dual-Discipline Layout:**
  - Displays stacked **Doubles** and **Singles** podium cards (`#1` Gold, `#2` Silver, `#3` Bronze) at the top, followed by a 12-column desktop split (`7` columns for the Leaderboard, `5` columns for Match History) that collapses into a segmented view switcher on mobile screens.
- **Player Profile Modal:**
  - Clicking any player name anywhere in the app (podiums, leaderboard, match history cards, or head-to-head rows) opens their profile modal with a discipline toggle (`Doubles` / `Singles`) and page switcher (`Statistics` / `Match History`).
  - **Statistics View:** Displays `Current ELO`, `Peak ELO` (with date achieved), wide cards combining `W-L-T` / `W-L` records and `Win Rate` for **Matches**, **Sets**, and **Points**, and a complete **Head-to-Head** opponent breakdown.
  - **Match History View:** Lists every match played by the selected player, always formatting the player's own name (and partner) on the first line (`<player> (<elo>) & <partner> (<elo>)`), opponents on the second line, set scores from the player's perspective, and a single-line personal ELO progression (`<old ELO> +-<delta> → <new ELO>`).
- **Layout Stability & Polish:**
  - **Zero Scroll-Jump View Switching:** Switching disciplines or mobile tabs preserves viewport scroll position (`preserveViewportScroll`).
  - **Scrollbar-Width Compensation:** Opening any modal overlay measures `window.innerWidth - document.documentElement.clientWidth` and applies matching `padding-right` to `document.body` so hiding the window scrollbar never shifts the background page horizontally.
  - **Drag-Safe Modal Backdrops:** Modal backdrops verify that `mousedown` originated on the backdrop before closing on `click`, preventing accidental closes when selecting text or dragging the cursor outside a card.
  - **SliceWin-Style Match Logging:** The `Log Match Result` modal anchors its top position (`items-start`) so the `Doubles`/`Singles` buttons stay stationary when toggling modes, provides filterable player comboboxes with `Tab` (cycle next) and `Enter` (autocomplete) keyboard navigation, and uses aligned per-side rows with a `+ Set` button for intuitive set score entry.
