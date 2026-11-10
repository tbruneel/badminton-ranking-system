# VUB SportMix: Badminton Ranking System (`badminton-ranking-system`)

A mobile-first badminton Elo ranking system modeled after the [SliceWin Elo System](https://slicewin.com/elo-system), supporting separate **Singles** and **Doubles** leaderboards where each player maintains an individual rating (`1000` starting Elo) and can pair up with any partner.

- **Live Web App (GitHub Pages — Sole UI):** <https://tbruneel.github.io/badminton-ranking-system/>
- **Google Sheet Database:** <https://docs.google.com/spreadsheets/d/1wh-rut7wmhBYSq_nSNIjGrCqrq581fEa175uVqCl37Q/edit>

---

## Architecture

| Layer | File / Resource | Role |
| :--- | :--- | :--- |
| **Frontend UI** | [`index.html`](./index.html) | Hosted on **GitHub Pages** (`https://tbruneel.github.io/badminton-ranking-system/`). Serves as the sole user interface (Read-Only public rankings by default + password-protected `🔒 Admin` mode). Communicates with the backend via `fetch(..., { credentials: "omit" })` to avoid Google's mobile multi-account redirect bug (`Google Issue #69270374`). |
| **JSON Backend API** | [`code.gs`](./code.gs) | Bound to the Google Sheet and deployed as a Google Apps Script Web App (`/exec`). Serves **pure JSON** via `doGet` and `doPost` (`ContentService.MimeType.JSON`) — no HTML is served from Apps Script. |
| **Minimal Database** | Google Sheet (`1wh-rut7wmhBYSq_nSNIjGrCqrq581fEa175uVqCl37Q`) | Contains solely 3 clean database tables (`Players`, `Doubles_Matches`, `Singles_Matches`) with Row 1 column headers and live chronological Elo formulas. |

---

## Minimal Google Sheet Database Schema

1. **`Players` (`A1:K50`)**
   - **Headers (`Row 1`):** `Player Name`, `Short Name`, `Initials`, `Singles W`, `Singles L`, `Singles T`, `Singles Elo`, `Doubles W`, `Doubles L`, `Doubles T`, `Doubles Elo`
   - **Rows `2–50`:** Master player roster and live `COUNTIFS` / `SUMIF` aggregations over `Singles_Matches` and `Doubles_Matches` starting from base Elo `1000`.
2. **`Doubles_Matches` (`A1:U102`)**
   - **Headers (`Row 1`):** `Match #`, `Date`, `Team 1 Player 1`, `Team 1 Player 2`, `Team 2 Player 1`, `Team 2 Player 2`, `S1 T1`, `S1 T2`, `S2 T1`, `S2 T2`, `S3 T1`, `S3 T2`, `Sets T1`, `Sets T2`, `Winner`, `T1 P1 Pre-Elo`, `T1 P2 Pre-Elo`, `T2 P1 Pre-Elo`, `T2 P2 Pre-Elo`, `T1 Elo Delta`, `T2 Elo Delta`
   - **Row `2`:** Baseline anchor row (`1000` initial rating).
   - **Rows `3–102`:** Chronological Doubles match log and per-match Elo deltas.
3. **`Singles_Matches` (`A1:Q102`)**
   - **Headers (`Row 1`):** `Match #`, `Date`, `Player 1`, `Player 2`, `S1 P1`, `S1 P2`, `S2 P1`, `S2 P2`, `S3 P1`, `S3 P2`, `Sets P1`, `Sets P2`, `Winner`, `P1 Pre-Elo`, `P2 Pre-Elo`, `P1 Elo Delta`, `P2 Elo Delta`
   - **Row `2`:** Baseline anchor row (`1000` initial rating).
   - **Rows `3–102`:** Chronological Singles match log and per-match Elo deltas.

---

## SliceWin Elo Rating Formulas

- **Starting Rating:** Every player starts at **`1000` Elo** in both Singles and Doubles.
- **Doubles Team Rating (Random Partners Supported):** Each team's effective rating is the average of the two partners' current Doubles Elos prior to the match:
  $$R_{\text{Team 1}} = \frac{R_{A_1} + R_{A_2}}{2}, \qquad R_{\text{Team 2}} = \frac{R_{B_1} + R_{B_2}}{2}$$
- **Expected Win Probability:**
  $$E_1 = \frac{1}{1 + 10^{(R_{\text{Team 2}} - R_{\text{Team 1}}) / 400}}, \qquad E_2 = 1 - E_1$$
- **Score-Margin Adjusted K-Factor ($K_{\text{base}} = 40$, $K_{\text{margin}} = 40$):**
  $$K_{\text{eff}} = 40 + 40 \times \frac{|\text{Pts}_1 - \text{Pts}_2|}{\max(1, \text{Pts}_1 + \text{Pts}_2)}$$
- **Rating Update:**
  $$\Delta_1 = \text{ROUND}\!\left(K_{\text{eff}} \times (S_1 - E_1)\right), \qquad \Delta_2 = -\Delta_1$$

---

## Security & Admin Authentication

- **Public Read-Only Default:** Visitors opening the GitHub Pages app can browse the **Club Podiums**, **Doubles & Singles Leaderboards**, and **Match History** without logging in.
- **Salted SHA-256 Admin Password (Never Stored in Plain Text):**
  1. Open the Google Sheet and click **🔒 Badminton Admin → Set / Change Admin Password...** in the top menu bar.
  2. `promptAndSaveAdminPassword()` generates a random UUID salt (`ADMIN_SALT`) and computes `ADMIN_PASSWORD_HASH = SHA-256(ADMIN_SALT + ":" + password)` using `Utilities.computeDigest()`.
  3. Only `ADMIN_SALT` and `ADMIN_PASSWORD_HASH` are stored in `ScriptProperties`.
- **Brute-Force & Injection Protection:**
  - Constant-time hash comparison (`timingSafeEqual_`).
  - Automatic **15-minute lockout** (`CacheService`) after 5 failed password attempts.
  - Concurrency locking (`LockService.getScriptLock()`), strict set score validation (`0–30`, no tied sets), and formula-injection sanitization (`^[=+\-@]` blocked).

---

## Updating the Google Apps Script Deployment

1. Open the [Google Sheet](https://docs.google.com/spreadsheets/d/1wh-rut7wmhBYSq_nSNIjGrCqrq581fEa175uVqCl37Q/edit) and click **Extensions → Apps Script**.
2. If an `Index.html` file exists in the Apps Script sidebar, click the **⋮** menu next to `Index.html` and click **Delete** (GitHub Pages is now the sole UI).
3. Replace the contents of `Code.gs` with [`code.gs`](./code.gs) from this repository and press **Ctrl+S**.
4. Click **Deploy → Manage deployments → ✏️ Edit (pencil icon) → Version: New version → Deploy**.
