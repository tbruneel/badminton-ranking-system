# Badminton Elo Ranking System (`badminton-ranking-system`)

A generic, zero-config badminton Elo ranking system supporting separate **Singles** and **Doubles** leaderboards where each player maintains an individual rating (`1000` starting Elo) and can pair up with any partner.

- **Live VUB SportMix Page:** <https://tbruneel.github.io/badminton-ranking-system/vub-sportmix-badminton/>
- **Generic Template UI:** <https://tbruneel.github.io/badminton-ranking-system/>
- **Google Sheet Database:** <https://docs.google.com/spreadsheets/d/1wh-rut7wmhBYSq_nSNIjGrCqrq581fEa175uVqCl37Q/edit>

---

## Key Features

- **Zero-Config Database Provisioning ([`code.gs`](./code.gs))** — Attach `code.gs` to **any new/blank Google Sheet** (`Extensions → Apps Script`). It automatically creates and maintains the 3 minimal database tables (`Players`, `Doubles_Matches`, `Singles_Matches`), writes all chronological Elo formulas, and removes empty default tabs.
- **Generic, Easily Configurable Frontend ([`index.html`](./index.html))** — Edit the single `CONFIG` object at the top of `index.html` (or pass `?api=<WEB_APP_EXEC_URL>`) to point the UI at any deployed Google Sheet backend. Automatically adopts the connected Google Sheet's title when `useSpreadsheetTitle: true`.
- **Responsive Modern Interface** — Adapts seamlessly from mobile phones to wide desktop monitors:
  - **Two Stacked Podium Cards** for **Doubles** and **Singles** Top 3 leaders.
  - **Side-by-Side Leaderboard & Match History** on desktop (`lg:grid-cols-12`), and a clean segmented view switcher on mobile.
- **Per-Player Match History (Singles & Doubles)** — Click any player in the podiums, leaderboard, or match cards to open their **Player Profile Modal**, featuring discipline toggles (`Doubles` / `Singles`), Current Elo, Peak Elo, Win Rate, and their complete chronological match log with partner/opponent breakdowns and personal Elo progression (`preElo → postElo`).

---

## Deploying to Any New / Blank Google Sheet

1. **Create a Blank Google Sheet:**
   - Open [sheets.new](https://sheets.new) and give your spreadsheet a name (e.g., `My Club Badminton Rankings`).
2. **Attach [`code.gs`](./code.gs):**
   - Click **Extensions → Apps Script**, paste the contents of [`code.gs`](./code.gs) into `Code.gs` (ensure no HTML files exist in the Apps Script sidebar), and press **Ctrl+S**.
3. **Initialize Database & Admin Password:**
   - Reload the Google Sheet and use the top menu **🔒 Badminton Admin**:
     - Click **🛠️ Initialize / Repair Database** (or let the first Web App API request auto-initialize the 3 tabs).
     - Click **🔑 Set / Change Admin Password...** to store a salted SHA-256 hash (`ADMIN_SALT` + `ADMIN_PASSWORD_HASH`) in `ScriptProperties`.
4. **Deploy as a JSON Web App API:**
   - In Apps Script, click **Deploy → New deployment → Web app**:
     - **Execute as:** `Me`
     - **Who has access:** `Anyone`
   - Copy the generated `/exec` URL.
5. **Configure [`index.html`](./index.html) or Add a Subpath Page:**
   - **Single deployment:** Update `CONFIG.apiUrl` and `CONFIG.title` in [`index.html`](./index.html) with your `/exec` URL.
   - **Multiple subpath deployments in the same repo:** Copy [`vub-sportmix-badminton/index.html`](./vub-sportmix-badminton/index.html) into `<your-subpath>/index.html` and set `window.RANKING_CONFIG = { title: "...", apiUrl: "..." }`. Every subpath automatically shares the root [`index.html`](./index.html) UI template and deploys to `https://<user>.github.io/<repo>/<your-subpath>/`.

---

## Minimal Google Sheet Database Schema

1. **`Players` (`A1:K50+`)**
   - **Headers (`Row 1`):** `Player Name`, `Short Name`, `Initials`, `Singles W`, `Singles L`, `Singles T`, `Singles Elo`, `Doubles W`, `Doubles L`, `Doubles T`, `Doubles Elo`
   - **Rows `2+`:** Master player roster and live `COUNTIFS` / `SUMIF` aggregations over `Singles_Matches` and `Doubles_Matches` starting from base Elo `1000`.
2. **`Doubles_Matches` (`A1:U102+`)**
   - **Headers (`Row 1`):** `Match #`, `Date`, `Team 1 Player 1`, `Team 1 Player 2`, `Team 2 Player 1`, `Team 2 Player 2`, `S1 T1`, `S1 T2`, `S2 T1`, `S2 T2`, `S3 T1`, `S3 T2`, `Sets T1`, `Sets T2`, `Winner`, `T1 P1 Pre-Elo`, `T1 P2 Pre-Elo`, `T2 P1 Pre-Elo`, `T2 P2 Pre-Elo`, `T1 Elo Delta`, `T2 Elo Delta`
   - **Row `2`:** Baseline anchor row (`1000` initial rating).
   - **Rows `3+`:** Chronological Doubles match log and per-match Elo deltas.
3. **`Singles_Matches` (`A1:Q102+`)**
   - **Headers (`Row 1`):** `Match #`, `Date`, `Player 1`, `Player 2`, `S1 P1`, `S1 P2`, `S2 P1`, `S2 P2`, `S3 P1`, `S3 P2`, `Sets P1`, `Sets P2`, `Winner`, `P1 Pre-Elo`, `P2 Pre-Elo`, `P1 Elo Delta`, `P2 Elo Delta`
   - **Row `2`:** Baseline anchor row (`1000` initial rating).
   - **Rows `3+`:** Chronological Singles match log and per-match Elo deltas.

---

## Elo Rating Formulas

- **Starting Rating:** Every player starts at **`1000` Elo** in both Singles and Doubles.
- **Doubles Team Rating (Random Partners Supported):** Each team's effective rating is the average of the two partners' current Doubles Elos prior to the match:
  $$R_{\text{Team 1}} = \frac{R_{A_1} + R_{A_2}}{2}, \qquad R_{\text{Team 2}} = \frac{R_{B_1} + R_{B_2}}{2}$$
- **Expected Win Probability:**
  $$E_1 = \frac{1}{1 + 10^{(R_{\text{Team 2}} - R_{\text{Team 1}}) / 400}}, \qquad E_2 = 1 - E_1$$
- **Score-Margin Adjusted K-Factor ($K_{\text{base}} = 40$, $K_{\text{margin}} = 40$):**
  $$K_{\text{eff}} = 40 + 40 \times \frac{|\text{Pts}_1 - \text{Pts}_2|}{\max(1, \text{Pts}_1 + \text{Pts}_2)}$$
- **Rating Update:**
  $$\Delta_1 = \text{ROUND}\!\left(K_{\text{eff}} \times (S_1 - E_1)\right), \qquad \Delta_2 = -\Delta_1$$
