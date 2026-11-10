# 🏸 VUB SportMix: Badminton Ranking System

A mobile-first Badminton Elo Ranking System modeled after the [SliceWin Elo System](https://slicewin.com/elo-system), backed by **Google Sheets** and **Google Apps Script**, and served via **GitHub Pages** so it works in any mobile browser (including Android Chrome with multiple signed-in Google accounts).

---

## 🔗 Live Links

- **📱 Mobile Web App (GitHub Pages):** [https://tbruneel.github.io/badminton-ranking-system/](https://tbruneel.github.io/badminton-ranking-system/)
- **📊 Google Sheet Backend:** [VUB SportMix: Badminton Ranking System](https://docs.google.com/spreadsheets/d/1wh-rut7wmhBYSq_nSNIjGrCqrq581fEa175uVqCl37Q/edit)
- **📖 HTML Documentation:** [readme.md.html](https://tbruneel.github.io/badminton-ranking-system/readme.md.html)

---

## ✨ Key Features

1. **Separate Singles & Doubles Rankings:**
   - Every player maintains an independent **Singles Elo** and **Doubles Elo**, each starting at **1000 points**.
2. **Random-Partner Doubles Support:**
   - Players can pair up with any partner for each Doubles match.
   - The system computes each pair's average pre-match Elo, determines expected win probability, applies a score-margin multiplier, and updates each player's personal Doubles Elo.
3. **Interactive Mobile UI (`index.html`):**
   - **Club Overview & Podiums:** Displays club session hours, amenities, and interactive Top 3 Podium cards (`#1 Gold`, `#2 Silver`, `#3 Bronze`) for Singles and Doubles.
   - **Leaderboards:** Searchable rankings with player initials, `W / L / T` records, trophy icons, and current Elo ratings.
   - **Match History:** Chronological match cards showing partner combinations, set scores, winning team trophy, and `+Δ / -Δ` Elo adjustments.
4. **Hardened Organizer Admin Mode (`🔒 Admin`):**
   - Public visitors have **read-only** access (no match-logging or player-editing buttons).
   - Organizers tap **`🔒 Admin`** in the top-right corner and enter the Admin Password to unlock **`＋ Log Match`** and **`＋👤 Add Player`**.

---

## 🧮 SliceWin Elo Calculation

For a match between Team/Player $A$ (rating $R_A$) and Team/Player $B$ (rating $R_B$):

1. **Team Rating (Doubles):**
   $$R_A = \frac{R_{A_1} + R_{A_2}}{2}, \qquad R_B = \frac{R_{B_1} + R_{B_2}}{2}$$
2. **Expected Score ($E_A$):**
   $$E_A = \frac{1}{1 + 10^{(R_B - R_A) / 400}}$$
3. **Score Margin Multiplier ($K_{\text{eff}}$):**
   $$K_{\text{eff}} = K_{\text{base}} + K_{\text{margin}} \cdot \frac{|\text{Points}_A - \text{Points}_B|}{\text{Points}_A + \text{Points}_B}$$
   *(Default: $K_{\text{base}} = 40$, $K_{\text{margin}} = 40$)*
4. **Elo Update ($\Delta$):**
   $$\Delta_A = \text{ROUND}\!\left(K_{\text{eff}} \cdot (S_A - E_A)\right), \qquad \Delta_B = -\Delta_A$$
   where $S_A = 1$ if Team $A$ wins more sets, or $0$ if Team $B$ wins more sets.

---

## 🔐 Security Architecture

- **Zero Plain-Text Password Storage:**
  - The Admin Password is never stored in `code.gs`, `index.html`, or in plain text inside `ScriptProperties`.
  - When set via the Google Sheet menu (`🔒 Badminton Admin > Set / Change Admin Password...`), `code.gs` generates a random UUID salt (`ADMIN_SALT`) and stores only `ADMIN_PASSWORD_HASH = SHA-256(salt + ":" + password)` in `ScriptProperties`.
- **Constant-Time Verification & Brute-Force Lockout:**
  - `timingSafeEqual_()` compares hashes in constant time.
  - `CacheService` locks out authentication for **15 minutes** after **5 failed attempts**.
- **HTTPS `POST`-Only Credentials & `credentials: "omit"`:**
  - Admin passwords are sent only inside encrypted HTTPS `POST` request bodies (never in URL query parameters).
  - Using `fetch(..., { credentials: "omit" })` from GitHub Pages strips browser Google cookies so Android Chrome's multi-account `script.google.com` bug (`Google Issue #69270374`) is bypassed completely.
- **Input Sanitization & Atomic Writes:**
  - Rejects strings starting with `=`, `+`, `-`, `@` to prevent spreadsheet formula injection.
  - Validates distinct players from the roster and whole-number set scores (`0–30`, no ties).
  - Serializes writes using `LockService.getScriptLock()`.

---

## 🛠️ Setup & Deployment Guide

1. **Update Google Apps Script:**
   - Open the [Google Sheet](https://docs.google.com/spreadsheets/d/1wh-rut7wmhBYSq_nSNIjGrCqrq581fEa175uVqCl37Q/edit) → **Extensions > Apps Script**.
   - Paste `code.gs` into `Code.gs` and `index.html` into `Index.html`, then save (**Ctrl+S**).
2. **Set Your Admin Password:**
   - Reload the Google Sheet in your browser.
   - Click **`🔒 Badminton Admin > Set / Change Admin Password...`** in the top toolbar and enter your password (at least 8 characters).
3. **Publish New Apps Script Version:**
   - In Apps Script, click **Deploy > Manage deployments > Edit (✏️) > Version: New version > Deploy** (`Execute as: Me`, `Who has access: Anyone`).
