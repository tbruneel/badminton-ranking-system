/**
 * VUB SportMix: Badminton Ranking System — Google Apps Script JSON Backend API
 * Bound to Spreadsheet ID: 1wh-rut7wmhBYSq_nSNIjGrCqrq581fEa175uVqCl37Q
 *
 * ARCHITECTURE:
 * - Frontend UI: Hosted exclusively on GitHub Pages (`index.html`)
 * - Backend API: This script (`code.gs`) serves only JSON via `doGet` and `doPost`
 * - Database: Minimal 3-tab Google Sheet (`Players`, `Doubles_Matches`, `Singles_Matches`)
 *
 * HOW TO SET YOUR ADMIN PASSWORD (NOT STORED IN PLAIN TEXT):
 * 1. Reload your Google Sheet in the browser.
 * 2. Click the top menu "🔒 Badminton Admin" -> "Set / Change Admin Password...".
 * 3. Type your password in the pop-up box. Only a random salt (`ADMIN_SALT`) and the
 *    salted SHA-256 hash (`ADMIN_PASSWORD_HASH`) are saved in ScriptProperties.
 */

const SPREADSHEET_ID = '1wh-rut7wmhBYSq_nSNIjGrCqrq581fEa175uVqCl37Q';
const MAX_FAILED_ATTEMPTS = 5;
const LOCKOUT_SECONDS = 900; // 15 minutes

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('🔒 Badminton Admin')
    .addItem('Set / Change Admin Password...', 'promptAndSaveAdminPassword')
    .addToUi();
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
    throw new Error('Admin password is not set yet. In your Google Sheet top menu, click "🔒 Badminton Admin" -> "Set / Change Admin Password...".');
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
 * Pure JSON GET endpoint — returns current rankings and match history.
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
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  const playersSheet = ss.getSheetByName('Players');
  const doublesSheet = ss.getSheetByName('Doubles_Matches');
  const singlesSheet = ss.getSheetByName('Singles_Matches');

  const pRows = playersSheet.getRange('A2:K50').getValues().filter(r => String(r[0]).trim() !== '');
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

  const dRows = doublesSheet.getRange('A3:U102').getDisplayValues().filter(r => r[2] !== '' && r[14] !== '');
  const doublesHistory = dRows.map(r => ({
    matchNum: Number(r[0]),
    date: r[1],
    t1: [r[2], r[3]],
    t2: [r[4], r[5]],
    sets: [[r[6], r[7]], [r[8], r[9]], [r[10], r[11]]]
      .filter(s => s[0] !== '' && s[1] !== '')
      .map(s => [Number(s[0]), Number(s[1])]),
    winner: r[14] === 'T1' ? 1 : (r[14] === 'T2' ? 2 : 0),
    delta1: Number(r[19] || 0),
    delta2: Number(r[20] || 0)
  })).reverse();

  const sRows = singlesSheet.getRange('A3:Q102').getDisplayValues().filter(r => r[2] !== '' && r[12] !== '');
  const singlesHistory = sRows.map(r => ({
    matchNum: Number(r[0]),
    date: r[1],
    p1: r[2],
    p2: r[3],
    sets: [[r[4], r[5]], [r[6], r[7]], [r[8], r[9]]]
      .filter(s => s[0] !== '' && s[1] !== '')
      .map(s => [Number(s[0]), Number(s[1])]),
    winner: r[12] === 'P1' ? 1 : (r[12] === 'P2' ? 2 : 0),
    delta1: Number(r[15] || 0),
    delta2: Number(r[16] || 0)
  })).reverse();

  return { players, doublesHistory, singlesHistory };
}

function getKnownPlayerSet_(ss) {
  const playersSheet = ss.getSheetByName('Players');
  const names = playersSheet.getRange('A2:A50').getValues()
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
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const knownPlayers = getKnownPlayerSet_(ss);
    allFour.forEach(p => {
      if (!knownPlayers.has(p)) {
        throw new Error('Unknown player: ' + p);
      }
    });

    const sheet = ss.getSheetByName('Doubles_Matches');
    const colC = sheet.getRange('C3:C102').getValues();
    let targetRow = -1;
    for (let i = 0; i < colC.length; i++) {
      if (String(colC[i][0]).trim() === '') {
        targetRow = 3 + i;
        break;
      }
    }
    if (targetRow === -1) {
      throw new Error('Match log is full (rows 3–102).');
    }

    const s1 = sets[0] || ['', ''];
    const s2 = sets[1] || ['', ''];
    const s3 = sets[2] || ['', ''];
    const dateStr = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');
    sheet.getRange(targetRow, 2, 1, 11).setValues([[
      dateStr,
      t1[0], t1[1], t2[0], t2[1],
      s1[0], s1[1], s2[0], s2[1], s3[0], s3[1]
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
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const knownPlayers = getKnownPlayerSet_(ss);
    if (!knownPlayers.has(p1) || !knownPlayers.has(p2)) {
      throw new Error('Both players must exist in the roster.');
    }

    const sheet = ss.getSheetByName('Singles_Matches');
    const colC = sheet.getRange('C3:C102').getValues();
    let targetRow = -1;
    for (let i = 0; i < colC.length; i++) {
      if (String(colC[i][0]).trim() === '') {
        targetRow = 3 + i;
        break;
      }
    }
    if (targetRow === -1) {
      throw new Error('Singles match log is full (rows 3–102).');
    }

    const s1 = sets[0] || ['', ''];
    const s2 = sets[1] || ['', ''];
    const s3 = sets[2] || ['', ''];
    const dateStr = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');
    sheet.getRange(targetRow, 2, 1, 9).setValues([[
      dateStr,
      p1, p2,
      s1[0], s1[1], s2[0], s2[1], s3[0], s3[1]
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
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const sheet = ss.getSheetByName('Players');
    const colA = sheet.getRange('A2:A50').getValues();
    for (let i = 0; i < colA.length; i++) {
      if (String(colA[i][0]).trim().toLowerCase() === cleanName.toLowerCase()) {
        throw new Error('Player already exists in roster.');
      }
      if (String(colA[i][0]).trim() === '') {
        sheet.getRange(2 + i, 1).setValue(cleanName);
        SpreadsheetApp.flush();
        return getAppState();
      }
    }
    throw new Error('Player roster is full (rows 2–50).');
  } finally {
    lock.releaseLock();
  }
}
