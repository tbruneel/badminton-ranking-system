# Badminton ELO Ranking System (`badminton-ranking-system`)

A zero-config badminton ELO ranking system supporting separate **Doubles** and **Singles** leaderboards where each player maintains an individual rating (`1000` starting ELO) and can pair up with any partner.

- **Live Deployment (VUB SportMix):** <https://tbruneel.github.io/badminton-ranking-system/vub-sportmix-badminton/>
- **Technical Architecture & Implementation Guide:** [`technical.md`](./technical.md)

---

## Repository Structure

```text
badminton-ranking-system/
├── code.gs                          # Google Apps Script backend bound to a Google Sheet
├── template.html                    # Shared frontend application template
├── vub-sportmix-badminton/
│   └── index.html                   # VUB SportMix ranking page configuration & entry point
├── README.md                        # Usage & deployment guide
└── technical.md                     # Technical architecture, ELO math & design rationale
```

---

## How to Use This Repo (Deploy Your Own Ranking Page)

### Step 1: Set Up the Google Sheet & Apps Script Backend

1. **Create a Blank Google Sheet:**
   - Open [sheets.new](https://sheets.new) and name your spreadsheet (e.g., `My Club Badminton Rankings`).
2. **Attach [`code.gs`](./code.gs):**
   - In your Google Sheet, click **Extensions → Apps Script**.
   - Select all existing code in the editor (`Ctrl+A`), delete it, paste the full contents of [`code.gs`](./code.gs), and save (`Ctrl+S`).
3. **Initialize the Sheet & Configure an Admin Password:**
   - Reload your Google Sheet. A custom menu **Admin** will appear in the top toolbar:
     - Click **Initialize database** to automatically create and format the `Players`, `Doubles_Matches`, and `Singles_Matches` tabs (or reset an existing database to a clean empty state).
     - Click **Configure password** to set the password used for adding/editing matches and adding players from the web interface.
4. **Deploy as a Web App:**
   - Back in the Apps Script editor, click **Deploy → New deployment**:
     - **Select type:** `Web app`
     - **Execute as:** `Me`
     - **Who has access:** `Anyone`
   - Click **Deploy**, authorize the script when prompted, and copy the generated `/exec` **Web app URL**.

---

### Step 2: Create a Ranking Subpage

Each club or group gets its own subfolder (e.g., `<your-club>/index.html`) that configures the page title, tab icon, and Apps Script `/exec` URL, and loads the shared [`template.html`](./template.html):

1. Copy [`vub-sportmix-badminton/index.html`](./vub-sportmix-badminton/index.html) into a new folder `<your-club>/index.html`:
   ```html
   <!DOCTYPE html>
   <link rel="icon" type="image/svg+xml" href="https://example.com/favicon.svg" />
   <script>
     window.RANKING_CONFIG = {
       title: "Your Club: Badminton",
       apiUrl: "https://script.google.com/macros/s/<YOUR_DEPLOYMENT_ID>/exec"
     };
     const icons = [...document.querySelectorAll('link[rel*="icon"]')].map(l => l.outerHTML).join("");
     fetch("../template.html", { cache: "no-cache" })
       .then(r => r.text())
       .then(h => { document.open(); document.write(h.replace("<head>", "<head>" + icons)); document.close(); });
   </script>
   ```
2. Commit and push to `main`. Your ranking page will be live at:
   `https://<username>.github.io/badminton-ranking-system/<your-club>/`

---

## Managing Players & Matches

- **From the Web UI (Recommended):**
  1. Click **🔒 Admin** in the top-right corner and enter your admin password.
  2. Click **＋ Add Player** to add a new player to the roster (starts at `1000` ELO in both Doubles and Singles).
  3. Click **＋ Add Match** to record a **Doubles** or **Singles** result with live ELO delta preview (any unknown player names can be created automatically upon confirmation), or click **Edit** on any match card to modify or delete it.
- **Directly in the Google Sheet:**
  - You can also edit match dates, scores, or player names directly in the `Players`, `Doubles_Matches`, or `Singles_Matches` tabs.
  - The script automatically sorts match rows chronologically by the **Date** column (`Col B`) and recalculates all ELO ratings in the Sheet.
