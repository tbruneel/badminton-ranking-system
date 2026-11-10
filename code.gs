/**
 * Generic Badminton Elo Ranking System — Google Apps Script JSON Backend API
 *
 * ZERO-CONFIG DATABASE AUTO-SETUP:
 * Attach this script to ANY new/blank Google Sheet (Extensions -> Apps Script).
 * It automatically creates and maintains the 3 minimal database tabs:
 *   1. `Players`         (Master roster & live W/L/T + Elo aggregations)
 *   2. `Doubles_Matches` (Chronological 2v2 match log & SliceWin Elo engine)
 *   3. `Singles_Matches` (Chronological 1v1 match log & SliceWin Elo engine)
 *
 * HOW TO DEPLOY FOR ANY NEW GOOGLE SHEET:
 * 1. Create a new blank Google Sheet and open Extensions -> Apps Script.
 * 2. Delete any HTML files, paste this file into `Code.gs`, and save (Ctrl+S).
 * 3. Reload the Google Sheet and click the top menu:
 *      "🔒 Badminton Admin" -> "🛠️ Initialize / Repair Database"
 *      "🔒 Badminton Admin" -> "🔑 Set / Change Admin Password..."
 * 4. In Apps Script, click Deploy -> New deployment -> Web app:
 *      - Execute as: Me
 *      - Who has access: Anyone
 * 5. Copy the `/exec` Web App URL into `CONFIG.apiUrl` in `index.html`.
 */

// Optional override if running standalone (unbound). Leave empty when bound to a Google Sheet.
const SPREADSHEET_ID_OVERRIDE = '';

const INITIAL_PLAYER_SLOTS = 50;   // Rows 2..50 pre-filled on init (auto-expands beyond 50)
const INITIAL_MATCH_SLOTS = 100;   // Rows 3..102 pre-filled on init (auto-expands beyond 100)
const MAX_FAILED_ATTEMPTS = 5;
const LOCKOUT_SECONDS = 900;       // 15 minutes

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('🔒 Badminton Admin')
    .addItem('🛠️ Initialize / Repair Database', 'initializeDatabaseFromMenu')
    .addSeparator()
    .addItem('🔑 Set / Change Admin Password...', 'promptAndSaveAdminPassword')
    .addToUi();
}

/**
 * Resolves the active container-bound spreadsheet (or falls back to stored/configured ID).
 */
function getSpreadsheet_() {
  const props = PropertiesService.getScriptProperties();
  if (SPREADSHEET_ID_OVERRIDE) {
    return SpreadsheetApp.openById(SPREADSHEET_ID_OVERRIDE);
  }
  let ss = null;
  try {
    ss = SpreadsheetApp.getActiveSpreadsheet();
  } catch (_) {
    ss = null;
  }
  if (ss) {
    if (props.getProperty('SPREADSHEET_ID') !== ss.getId()) {
      props.setProperty('SPREADSHEET_ID', ss.getId());
    }
    return ss;
  }
  const savedId = props.getProperty('SPREADSHEET_ID');
  if (!savedId) {
    throw new Error('No bound Google Sheet found. Bind this script via Extensions -> Apps Script or set SPREADSHEET_ID_OVERRIDE.');
  }
  return SpreadsheetApp.openById(savedId);
}

/**
 * Menu handler to initialize or repair the 3 minimal database sheets on any blank/existing spreadsheet.
 */
function initializeDatabaseFromMenu() {
  const ui = SpreadsheetApp.getUi();
  const ss = getSpreadsheet_();
  PropertiesService.getScriptProperties().setProperty('SPREADSHEET_ID', ss.getId());
  const created = ensureDatabase_(ss, true);
  ui.alert(
    'Database Ready',
    created.length > 0
      ? 'Created & initialized tabs: ' + created.join(', ')
      : 'Verified all 3 database tabs (Players, Doubles_Matches, Singles_Matches) and repaired formulas.',
    ui.ButtonSet.OK
  );
}

/**
 * Ensures the 3 minimal database sheets (`Players`, `Doubles_Matches`, `Singles_Matches`) exist.
 * Automatically provisions missing tabs, writes Row 1 headers + formulas, and removes empty default sheets.
 */
function ensureDatabase_(ss, forceRepairFormulas) {
  const created = [];

  let playersSheet = ss.getSheetByName('Players');
  if (!playersSheet) {
    playersSheet = ss.insertSheet('Players', 0);
    setupPlayersSheet_(playersSheet, INITIAL_PLAYER_SLOTS);
    created.push('Players');
  } else if (forceRepairFormulas) {
    repairPlayersFormulas_(playersSheet);
  }

  let doublesSheet = ss.getSheetByName('Doubles_Matches');
  if (!doublesSheet) {
    doublesSheet = ss.insertSheet('Doubles_Matches', 1);
    setupDoublesSheet_(doublesSheet, INITIAL_MATCH_SLOTS);
    created.push('Doubles_Matches');
  } else if (forceRepairFormulas) {
    repairDoublesFormulas_(doublesSheet);
  }

  let singlesSheet = ss.getSheetByName('Singles_Matches');
  if (!singlesSheet) {
    singlesSheet = ss.insertSheet('Singles_Matches', 2);
    setupSinglesSheet_(singlesSheet, INITIAL_MATCH_SLOTS);
    created.push('Singles_Matches');
  } else if (forceRepairFormulas) {
    repairSinglesFormulas_(singlesSheet);
  }

  // Delete default blank sheet (e.g. "Sheet1", "Blad1") if completely empty
  if (created.length > 0) {
    const keepNames = new Set(['Players', 'Doubles_Matches', 'Singles_Matches']);
    ss.getSheets().forEach(sh => {
      if (!keepNames.has(sh.getName()) && sh.getLastRow() === 0 && sh.getLastColumn() === 0 && ss.getSheets().length > 3) {
        try {
          ss.deleteSheet(sh);
        } catch (_) {}
      }
    });
  }

  return created;
}

function playerRowFormulas_(r) {
  return [
    `=IF(A${r}="","",INDEX(SPLIT(TRIM(A${r})," "),1))`,
    `=IF(A${r}="","",UPPER(LEFT(TRIM(A${r}),1)&IF(ISNUMBER(FIND(" ",TRIM(A${r}))),LEFT(TRIM(MID(TRIM(A${r}),FIND(" ",TRIM(A${r}))+1,99)),1),"")))`,
    `=IF(A${r}="","",COUNTIFS(Singles_Matches!$C$3:$C,A${r},Singles_Matches!$M$3:$M,"P1")+COUNTIFS(Singles_Matches!$D$3:$D,A${r},Singles_Matches!$M$3:$M,"P2"))`,
    `=IF(A${r}="","",COUNTIFS(Singles_Matches!$C$3:$C,A${r},Singles_Matches!$M$3:$M,"P2")+COUNTIFS(Singles_Matches!$D$3:$D,A${r},Singles_Matches!$M$3:$M,"P1"))`,
    `=IF(A${r}="","",COUNTIFS(Singles_Matches!$C$3:$C,A${r},Singles_Matches!$M$3:$M,"TIE")+COUNTIFS(Singles_Matches!$D$3:$D,A${r},Singles_Matches!$M$3:$M,"TIE"))`,
    `=IF(A${r}="","",1000+SUMIF(Singles_Matches!$C$3:$C,A${r},Singles_Matches!$P$3:$P)+SUMIF(Singles_Matches!$D$3:$D,A${r},Singles_Matches!$Q$3:$Q))`,
    `=IF(A${r}="","",COUNTIFS(Doubles_Matches!$C$3:$C,A${r},Doubles_Matches!$O$3:$O,"T1")+COUNTIFS(Doubles_Matches!$D$3:$D,A${r},Doubles_Matches!$O$3:$O,"T1")+COUNTIFS(Doubles_Matches!$E$3:$E,A${r},Doubles_Matches!$O$3:$O,"T2")+COUNTIFS(Doubles_Matches!$F$3:$F,A${r},Doubles_Matches!$O$3:$O,"T2"))`,
    `=IF(A${r}="","",COUNTIFS(Doubles_Matches!$C$3:$C,A${r},Doubles_Matches!$O$3:$O,"T2")+COUNTIFS(Doubles_Matches!$D$3:$D,A${r},Doubles_Matches!$O$3:$O,"T2")+COUNTIFS(Doubles_Matches!$E$3:$E,A${r},Doubles_Matches!$O$3:$O,"T1")+COUNTIFS(Doubles_Matches!$F$3:$F,A${r},Doubles_Matches!$O$3:$O,"T1"))`,
    `=IF(A${r}="","",COUNTIFS(Doubles_Matches!$C$3:$C,A${r},Doubles_Matches!$O$3:$O,"TIE")+COUNTIFS(Doubles_Matches!$D$3:$D,A${r},Doubles_Matches!$O$3:$O,"TIE")+COUNTIFS(Doubles_Matches!$E$3:$E,A${r},Doubles_Matches!$O$3:$O,"TIE")+COUNTIFS(Doubles_Matches!$F$3:$F,A${r},Doubles_Matches!$O$3:$O,"TIE"))`,
    `=IF(A${r}="","",1000+SUMIF(Doubles_Matches!$C$3:$C,A${r},Doubles_Matches!$T$3:$T)+SUMIF(Doubles_Matches!$D$3:$D,A${r},Doubles_Matches!$T$3:$T)+SUMIF(Doubles_Matches!$E$3:$E,A${r},Doubles_Matches!$U$3:$U)+SUMIF(Doubles_Matches!$F$3:$F,A${r},Doubles_Matches!$U$3:$U))`
  ];
}

function doublesCalcFormulas_(r) {
  const prev = r - 1;
  return [
    `=IF(C${r}="","",(G${r}>H${r})*(G${r}<>"")*1+(I${r}>J${r})*(I${r}<>"")*1+(K${r}>L${r})*(K${r}<>"")*1)`,
    `=IF(C${r}="","",(H${r}>G${r})*(H${r}<>"")*1+(J${r}>I${r})*(J${r}<>"")*1+(L${r}>K${r})*(L${r}<>"")*1)`,
    `=IF(OR(C${r}="",G${r}=""),"",IF(M${r}>N${r},"T1",IF(N${r}>M${r},"T2","TIE")))`,
    `=IF(C${r}="","",1000+SUMIF($C$2:C${prev},C${r},$T$2:T${prev})+SUMIF($D$2:D${prev},C${r},$T$2:T${prev})+SUMIF($E$2:E${prev},C${r},$U$2:U${prev})+SUMIF($F$2:F${prev},C${r},$U$2:U${prev}))`,
    `=IF(D${r}="","",1000+SUMIF($C$2:C${prev},D${r},$T$2:T${prev})+SUMIF($D$2:D${prev},D${r},$T$2:T${prev})+SUMIF($E$2:E${prev},D${r},$U$2:U${prev})+SUMIF($F$2:F${prev},D${r},$U$2:U${prev}))`,
    `=IF(E${r}="","",1000+SUMIF($C$2:C${prev},E${r},$T$2:T${prev})+SUMIF($D$2:D${prev},E${r},$T$2:T${prev})+SUMIF($E$2:E${prev},E${r},$U$2:U${prev})+SUMIF($F$2:F${prev},E${r},$U$2:U${prev}))`,
    `=IF(F${r}="","",1000+SUMIF($C$2:C${prev},F${r},$T$2:T${prev})+SUMIF($D$2:D${prev},F${r},$T$2:T${prev})+SUMIF($E$2:E${prev},F${r},$U$2:U${prev})+SUMIF($F$2:F${prev},F${r},$U$2:U${prev}))`,
    `=IF(O${r}="","",ROUND((40+40*(ABS(SUM(G${r},I${r},K${r})-SUM(H${r},J${r},L${r}))/MAX(1,SUM(G${r}:L${r}))))*(IF(O${r}="T1",1,IF(O${r}="T2",0,0.5))-1/(1+10^((AVERAGE(R${r}:S${r})-AVERAGE(P${r}:Q${r}))/400)))))`,
    `=IF(O${r}="","",-T${r})`
  ];
}

function singlesCalcFormulas_(r) {
  const prev = r - 1;
  return [
    `=IF(C${r}="","",(E${r}>F${r})*(E${r}<>"")*1+(G${r}>H${r})*(G${r}<>"")*1+(I${r}>J${r})*(I${r}<>"")*1)`,
    `=IF(C${r}="","",(F${r}>E${r})*(F${r}<>"")*1+(H${r}>G${r})*(H${r}<>"")*1+(J${r}>I${r})*(J${r}<>"")*1)`,
    `=IF(OR(C${r}="",E${r}=""),"",IF(K${r}>L${r},"P1",IF(L${r}>K${r},"P2","TIE")))`,
    `=IF(C${r}="","",1000+SUMIF($C$2:C${prev},C${r},$P$2:P${prev})+SUMIF($D$2:D${prev},C${r},$Q$2:Q${prev}))`,
    `=IF(D${r}="","",1000+SUMIF($C$2:C${prev},D${r},$P$2:P${prev})+SUMIF($D$2:D${prev},D${r},$Q$2:Q${prev}))`,
    `=IF(M${r}="","",ROUND((40+40*(ABS(SUM(E${r},G${r},I${r})-SUM(F${r},H${r},J${r}))/MAX(1,SUM(E${r}:J${r}))))*(IF(M${r}="P1",1,IF(M${r}="P2",0,0.5))-1/(1+10^((O${r}-N${r})/400)))))`,
    `=IF(M${r}="","",-P${r})`
  ];
}

function setupPlayersSheet_(sheet, slots) {
  const headers = [
    'Player Name', 'Short Name', 'Initials',
    'Singles W', 'Singles L', 'Singles T', 'Singles Elo',
    'Doubles W', 'Doubles L', 'Doubles T', 'Doubles Elo'
  ];
  const rows = [headers];
  for (let i = 0; i < slots - 1; i++) {
    const r = i + 2;
    rows.push(['', ...playerRowFormulas_(r)]);
  }
  sheet.getRange(1, 1, rows.length, headers.length).setValues(rows);
  styleDatabaseSheet_(sheet, headers.length, rows.length);
}

function repairPlayersFormulas_(sheet) {
  const maxRow = Math.max(sheet.getLastRow(), INITIAL_PLAYER_SLOTS);
  const formulas = [];
  for (let r = 2; r <= maxRow; r++) {
    formulas.push(playerRowFormulas_(r));
  }
  sheet.getRange(2, 2, formulas.length, 10).setValues(formulas);
}

function setupDoublesSheet_(sheet, matchSlots) {
  const headers = [
    'Match #', 'Date',
    'Team 1 Player 1', 'Team 1 Player 2', 'Team 2 Player 1', 'Team 2 Player 2',
    'S1 T1', 'S1 T2', 'S2 T1', 'S2 T2', 'S3 T1', 'S3 T2',
    'Sets T1', 'Sets T2', 'Winner',
    'T1 P1 Pre-Elo', 'T1 P2 Pre-Elo', 'T2 P1 Pre-Elo', 'T2 P2 Pre-Elo',
    'T1 Elo Delta', 'T2 Elo Delta'
  ];
  const baseline = [0, 'Baseline', '', '', '', '', '', '', '', '', '', '', 0, 0, '', 1000, 1000, 1000, 1000, 0, 0];
  const rows = [headers, baseline];
  for (let i = 0; i < matchSlots; i++) {
    const r = i + 3;
    rows.push([
      `=IF(C${r}="","",ROW()-2)`,
      '', '', '', '', '', '', '', '', '', '', '',
      ...doublesCalcFormulas_(r)
    ]);
  }
  sheet.getRange(1, 1, rows.length, headers.length).setValues(rows);
  styleDatabaseSheet_(sheet, headers.length, rows.length);
}

function repairDoublesFormulas_(sheet) {
  const maxRow = Math.max(sheet.getLastRow(), INITIAL_MATCH_SLOTS + 2);
  const colA = [];
  const calcCols = [];
  for (let r = 3; r <= maxRow; r++) {
    colA.push([`=IF(C${r}="","",ROW()-2)`]);
    calcCols.push(doublesCalcFormulas_(r));
  }
  sheet.getRange(3, 1, colA.length, 1).setValues(colA);
  sheet.getRange(3, 13, calcCols.length, 9).setValues(calcCols);
}

function setupSinglesSheet_(sheet, matchSlots) {
  const headers = [
    'Match #', 'Date', 'Player 1', 'Player 2',
    'S1 P1', 'S1 P2', 'S2 P1', 'S2 P2', 'S3 P1', 'S3 P2',
    'Sets P1', 'Sets P2', 'Winner',
    'P1 Pre-Elo', 'P2 Pre-Elo', 'P1 Elo Delta', 'P2 Elo Delta'
  ];
  const baseline = [0, 'Baseline', '', '', '', '', '', '', '', '', 0, 0, '', 1000, 1000, 0, 0];
  const rows = [headers, baseline];
  for (let i = 0; i < matchSlots; i++) {
    const r = i + 3;
    rows.push([
      `=IF(C${r}="","",ROW()-2)`,
      '', '', '', '', '', '', '', '', '',
      ...singlesCalcFormulas_(r)
    ]);
  }
  sheet.getRange(1, 1, rows.length, headers.length).setValues(rows);
  styleDatabaseSheet_(sheet, headers.length, rows.length);
}

function repairSinglesFormulas_(sheet) {
  const maxRow = Math.max(sheet.getLastRow(), INITIAL_MATCH_SLOTS + 2);
  const colA = [];
  const calcCols = [];
  for (let r = 3; r <= maxRow; r++) {
    colA.push([`=IF(C${r}="","",ROW()-2)`]);
    calcCols.push(singlesCalcFormulas_(r));
  }
  sheet.getRange(3, 1, colA.length, 1).setValues(colA);
  sheet.getRange(3, 11, calcCols.length, 7).setValues(calcCols);
}

function styleDatabaseSheet_(sheet, numCols, numRows) {
  sheet.setFrozenRows(1);
  sheet.getRange(1, 1, 1, numCols).setFontWeight('bold').setBackground('#F3F4F6');
  const maxCols = sheet.getMaxColumns();
  if (maxCols > numCols) {
    sheet.deleteColumns(numCols + 1, maxCols - numCols);
  }
  const maxRows = sheet.getMaxRows();
  if (maxRows > numRows) {
    sheet.deleteRows(numRows + 1, maxRows - numRows);
  }
}

function promptAndSaveAdminPassword() {
  const ui = SpreadsheetApp.getUi();
  const response = ui.prompt(
    'Set Admin Password',
    'Enter a new Admin Password (at least 8 characters).\nOnly its salted SHA-256 hash will be stored in ScriptProperties:',
    ui.ButtonSet.OK_CANCEL
  );
  if (response.getSelectedButton() !== ui.Button.OK) return;

  const password = String(response.getResponseText() || '').trim();
  if (password.length < 8) {
    ui.alert('Password too short', 'Please choose a password with at least 8 characters.', ui.ButtonSet.OK);
    return;
  }

  const salt = Utilities.getUuid();
  const hash = sha256Hex_(salt + ':' + password);
  const props = PropertiesService.getScriptProperties();
  props.setProperties({
    ADMIN_SALT: salt,
    ADMIN_PASSWORD_HASH: hash
  });
  props.deleteProperty('ADMIN_PASSCODE');
  CacheService.getScriptCache().remove('AUTH_FAIL_COUNT');

  ui.alert(
    'Admin Password Saved',
    'Your salted SHA-256 password hash has been saved to ScriptProperties. Plain text was NOT stored.',
    ui.ButtonSet.OK
  );
}

function sha256Hex_(input) {
  const digest = Utilities.computeDigest(
    Utilities.DigestAlgorithm.SHA_256,
    input,
    Utilities.Charset.UTF_8
  );
  return digest.map(b => ('0' + ((b & 0xff).toString(16))).slice(-2)).join('');
}

function timingSafeEqual_(a, b) {
  const strA = String(a || '');
  const strB = String(b || '');
  if (strA.length !== strB.length || strA.length === 0) return false;
  let diff = 0;
  for (let i = 0; i < strA.length; i++) {
    diff |= strA.charCodeAt(i) ^ strB.charCodeAt(i);
  }
  return diff === 0;
}

function verifyAdminPasscode_(providedKey) {
  const cache = CacheService.getScriptCache();
  const failCount = Number(cache.get('AUTH_FAIL_COUNT') || 0);
  if (failCount >= MAX_FAILED_ATTEMPTS) {
    throw new Error('Too many failed login attempts. Admin mode is locked for 15 minutes.');
  }

  const props = PropertiesService.getScriptProperties();
  const salt = props.getProperty('ADMIN_SALT');
  const storedHash = props.getProperty('ADMIN_PASSWORD_HASH');

  if (!salt || !storedHash) {
    throw new Error('Admin password is not set yet. In your Google Sheet top menu, click "🔒 Badminton Admin" -> "🔑 Set / Change Admin Password...".');
  }

  const candidateHash = sha256Hex_(salt + ':' + String(providedKey || ''));
  if (!timingSafeEqual_(candidateHash, storedHash.toLowerCase())) {
    cache.put('AUTH_FAIL_COUNT', String(failCount + 1), LOCKOUT_SECONDS);
    throw new Error('Invalid Admin Password.');
  }

  if (failCount > 0) {
    cache.remove('AUTH_FAIL_COUNT');
  }
}

function verifyAdminPassword(password) {
  verifyAdminPasscode_(password);
  return { ok: true };
}

function sanitizeText_(val) {
  const s = String(val || '').trim();
  if (/^[=+\-@]/.test(s)) {
    throw new Error('Invalid input: leading formula characters (=, +, -, @) are not allowed.');
  }
  return s;
}

function validateSets_(sets) {
  if (!Array.isArray(sets) || sets.length < 1 || sets.length > 3) {
    throw new Error('Invalid match sets: must provide between 1 and 3 sets.');
  }
  return sets.map(pair => {
    if (!Array.isArray(pair) || pair.length !== 2) {
      throw new Error('Invalid set score pair.');
    }
    const a = Number(pair[0]);
    const b = Number(pair[1]);
    if (!Number.isInteger(a) || !Number.isInteger(b) || a < 0 || a > 30 || b < 0 || b > 30) {
      throw new Error('Set scores must be whole numbers between 0 and 30.');
    }
    if (a === b) {
      throw new Error('A badminton set cannot end in a tie score.');
    }
    return [a, b];
  });
}

function jsonResponse_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Pure JSON GET endpoint — auto-initializes database if attached to a blank sheet and returns state.
 */
function doGet() {
  try {
    return jsonResponse_({ ok: true, data: getAppState() });
  } catch (err) {
    return jsonResponse_({ ok: false, error: err.message || String(err) });
  }
}

/**
 * Pure JSON POST endpoint — handles state reads and authenticated admin mutations.
 */
function doPost(e) {
  try {
    const body = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    const action = body.action || 'state';
    if (action === 'state') {
      return jsonResponse_({ ok: true, data: getAppState() });
    }
    if (action === 'verifyAdmin') {
      return jsonResponse_(verifyAdminPassword(body.adminPassword));
    }
    if (action === 'logDoubles') {
      return jsonResponse_({ ok: true, data: logDoublesMatch(body.payload, body.adminPassword) });
    }
    if (action === 'logSingles') {
      return jsonResponse_({ ok: true, data: logSinglesMatch(body.payload, body.adminPassword) });
    }
    if (action === 'addPlayer') {
      return jsonResponse_({ ok: true, data: addPlayerToSheet(body.name, body.adminPassword) });
    }
    throw new Error('Unknown API action.');
  } catch (err) {
    return jsonResponse_({ ok: false, error: err.message || String(err) });
  }
}

function getAppState() {
  const ss = getSpreadsheet_();
  ensureDatabase_(ss, false);

  const playersSheet = ss.getSheetByName('Players');
  const doublesSheet = ss.getSheetByName('Doubles_Matches');
  const singlesSheet = ss.getSheetByName('Singles_Matches');

  const pMaxRow = Math.max(playersSheet.getLastRow(), 2);
  const pRows = pMaxRow >= 2
    ? playersSheet.getRange(2, 1, pMaxRow - 1, 11).getValues().filter(r => String(r[0]).trim() !== '')
    : [];

  const players = pRows.map((r, idx) => ({
    name: String(r[0]).trim(),
    short: String(r[1]).trim() || String(r[0]).trim().split(/\s+/)[0],
    initials: String(r[2]).trim(),
    singlesW: Number(r[3] || 0),
    singlesL: Number(r[4] || 0),
    singlesT: Number(r[5] || 0),
    singlesElo: Number(r[6] || 1000),
    doublesW: Number(r[7] || 0),
    doublesL: Number(r[8] || 0),
    doublesT: Number(r[9] || 0),
    doublesElo: Number(r[10] || 1000),
    order: idx
  }));

  const dMaxRow = Math.max(doublesSheet.getLastRow(), 3);
  const dRows = dMaxRow >= 3
    ? doublesSheet.getRange(3, 1, dMaxRow - 2, 21).getDisplayValues().filter(r => r[2] !== '' && r[14] !== '')
    : [];

  const doublesHistory = dRows.map(r => ({
    matchNum: Number(r[0]),
    date: r[1],
    t1: [r[2], r[3]],
    t2: [r[4], r[5]],
    sets: [[r[6], r[7]], [r[8], r[9]], [r[10], r[11]]]
      .filter(s => s[0] !== '' && s[1] !== '')
      .map(s => [Number(s[0]), Number(s[1])]),
    winner: r[14] === 'T1' ? 1 : (r[14] === 'T2' ? 2 : 0),
    preElo: {
      t1p1: Number(r[15] || 1000),
      t1p2: Number(r[16] || 1000),
      t2p1: Number(r[17] || 1000),
      t2p2: Number(r[18] || 1000)
    },
    delta1: Number(r[19] || 0),
    delta2: Number(r[20] || 0)
  })).reverse();

  const sMaxRow = Math.max(singlesSheet.getLastRow(), 3);
  const sRows = sMaxRow >= 3
    ? singlesSheet.getRange(3, 1, sMaxRow - 2, 17).getDisplayValues().filter(r => r[2] !== '' && r[12] !== '')
    : [];

  const singlesHistory = sRows.map(r => ({
    matchNum: Number(r[0]),
    date: r[1],
    p1: r[2],
    p2: r[3],
    sets: [[r[4], r[5]], [r[6], r[7]], [r[8], r[9]]]
      .filter(s => s[0] !== '' && s[1] !== '')
      .map(s => [Number(s[0]), Number(s[1])]),
    winner: r[12] === 'P1' ? 1 : (r[12] === 'P2' ? 2 : 0),
    preElo: {
      p1: Number(r[13] || 1000),
      p2: Number(r[14] || 1000)
    },
    delta1: Number(r[15] || 0),
    delta2: Number(r[16] || 0)
  })).reverse();

  return {
    spreadsheetTitle: ss.getName(),
    players,
    doublesHistory,
    singlesHistory
  };
}

function getKnownPlayerSet_(ss) {
  const playersSheet = ss.getSheetByName('Players');
  const maxRow = Math.max(playersSheet.getLastRow(), 2);
  const names = playersSheet.getRange(2, 1, maxRow - 1, 1).getValues()
    .map(r => String(r[0]).trim())
    .filter(Boolean);
  return new Set(names);
}

function logDoublesMatch(payload, adminPassword) {
  verifyAdminPasscode_(adminPassword);
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const t1 = Array.isArray(payload.t1) ? payload.t1.map(sanitizeText_) : [];
    const t2 = Array.isArray(payload.t2) ? payload.t2.map(sanitizeText_) : [];
    if (t1.length !== 2 || t2.length !== 2) {
      throw new Error('Doubles match requires 2 players per team.');
    }
    const allFour = [t1[0], t1[1], t2[0], t2[1]];
    if (new Set(allFour).size !== 4) {
      throw new Error('All 4 players in a Doubles match must be distinct.');
    }

    const sets = validateSets_(payload.sets);
    const ss = getSpreadsheet_();
    ensureDatabase_(ss, false);

    const knownPlayers = getKnownPlayerSet_(ss);
    allFour.forEach(p => {
      if (!knownPlayers.has(p)) {
        throw new Error('Unknown player: ' + p);
      }
    });

    const sheet = ss.getSheetByName('Doubles_Matches');
    const scanMax = Math.max(sheet.getLastRow(), 3);
    const colC = sheet.getRange(3, 3, scanMax - 2, 1).getValues();
    let targetRow = -1;
    for (let i = 0; i < colC.length; i++) {
      if (String(colC[i][0]).trim() === '') {
        targetRow = 3 + i;
        break;
      }
    }
    if (targetRow === -1) {
      targetRow = scanMax + 1;
    }

    const s1 = sets[0] || ['', ''];
    const s2 = sets[1] || ['', ''];
    const s3 = sets[2] || ['', ''];
    const dateStr = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');

    sheet.getRange(targetRow, 1, 1, 21).setValues([[
      `=IF(C${targetRow}="","",ROW()-2)`,
      dateStr,
      t1[0], t1[1], t2[0], t2[1],
      s1[0], s1[1], s2[0], s2[1], s3[0], s3[1],
      ...doublesCalcFormulas_(targetRow)
    ]]);
    SpreadsheetApp.flush();
    return getAppState();
  } finally {
    lock.releaseLock();
  }
}

function logSinglesMatch(payload, adminPassword) {
  verifyAdminPasscode_(adminPassword);
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const p1 = sanitizeText_(payload.p1);
    const p2 = sanitizeText_(payload.p2);
    if (!p1 || !p2 || p1 === p2) {
      throw new Error('Singles match requires 2 distinct players.');
    }

    const sets = validateSets_(payload.sets);
    const ss = getSpreadsheet_();
    ensureDatabase_(ss, false);

    const knownPlayers = getKnownPlayerSet_(ss);
    if (!knownPlayers.has(p1) || !knownPlayers.has(p2)) {
      throw new Error('Both players must exist in the roster.');
    }

    const sheet = ss.getSheetByName('Singles_Matches');
    const scanMax = Math.max(sheet.getLastRow(), 3);
    const colC = sheet.getRange(3, 3, scanMax - 2, 1).getValues();
    let targetRow = -1;
    for (let i = 0; i < colC.length; i++) {
      if (String(colC[i][0]).trim() === '') {
        targetRow = 3 + i;
        break;
      }
    }
    if (targetRow === -1) {
      targetRow = scanMax + 1;
    }

    const s1 = sets[0] || ['', ''];
    const s2 = sets[1] || ['', ''];
    const s3 = sets[2] || ['', ''];
    const dateStr = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');

    sheet.getRange(targetRow, 1, 1, 17).setValues([[
      `=IF(C${targetRow}="","",ROW()-2)`,
      dateStr,
      p1, p2,
      s1[0], s1[1], s2[0], s2[1], s3[0], s3[1],
      ...singlesCalcFormulas_(targetRow)
    ]]);
    SpreadsheetApp.flush();
    return getAppState();
  } finally {
    lock.releaseLock();
  }
}

function addPlayerToSheet(playerName, adminPassword) {
  verifyAdminPasscode_(adminPassword);
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const cleanName = sanitizeText_(playerName);
    if (cleanName.length < 2 || cleanName.length > 40) {
      throw new Error('Player name must be between 2 and 40 characters.');
    }
    const ss = getSpreadsheet_();
    ensureDatabase_(ss, false);

    const sheet = ss.getSheetByName('Players');
    const scanMax = Math.max(sheet.getLastRow(), 2);
    const colA = sheet.getRange(2, 1, scanMax - 1, 1).getValues();
    let targetRow = -1;
    for (let i = 0; i < colA.length; i++) {
      const existing = String(colA[i][0]).trim();
      if (existing.toLowerCase() === cleanName.toLowerCase()) {
        throw new Error('Player already exists in roster.');
      }
      if (existing === '' && targetRow === -1) {
        targetRow = 2 + i;
      }
    }
    if (targetRow === -1) {
      targetRow = scanMax + 1;
    }

    sheet.getRange(targetRow, 1, 1, 11).setValues([[
      cleanName,
      ...playerRowFormulas_(targetRow)
    ]]);
    SpreadsheetApp.flush();
    return getAppState();
  } finally {
    lock.releaseLock();
  }
}
