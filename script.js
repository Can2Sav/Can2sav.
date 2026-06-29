/* ============================================================
   CAN DE SAV — app.js
   Logique du site : matchs, classement, modal d'édition
   ============================================================ */

/* ---- DONNÉES — modifiez ici pour changer les équipes et matchs ---- */

const GROUP_COLORS = {
  A: 'var(--color-group-a)',
  B: 'var(--color-group-b)',
  C: 'var(--color-group-c)',
  D: 'var(--color-group-d)',
};

let matches = [
  { id: 1,  group: 'A', home: 'Algerie',      away: 'DOM-TOM',        scoreH: null,    scoreA: null,    status: 'upcoming',     date: 'Lun 22 juin', time: '19h00' },
  { id: 2,  group: 'A', home: 'Côte d\'Ivoire', away: 'Nigeria',       scoreH: null,    scoreA: null,    status: 'upcoming',     date: 'Lun 22 juin', time: '19h00' },
  { id: 3,  group: 'B', home: 'RD Congo',         away: 'Afrique du Sud', scoreH: null,    scoreA: null,    status: 'upcoming',     date: 'Lun 22 juin', time: '20h00' },
  { id: 4,  group: 'B', home: 'Cap Vert',     away: 'Togo',       scoreH: null,    scoreA: null,    status: 'upcoming',     date: 'Lun 22 juin', time: '20h00' },
  { id: 5,  group: 'C', home: 'Senegal',      away: 'Palestine',        scoreH: null,    scoreA: null,    status: 'upcoming',     date: 'Mar 23 juin', time: '19h00' },
  { id: 6,  group: 'C', home: 'Congo',        away: 'Tunisie',      scoreH: null,    scoreA: null,    status: 'upcoming',     date: 'Mar 23 juin', time: '19h00' },
  { id: 7,  group: 'D', home: 'Comores',      away: 'Mali',       scoreH: null,    scoreA: null,    status: 'upcoming',     date: 'Mar 23 juin', time: '20h00' },
  { id: 8,  group: 'D', home: 'Cameroun',         away: 'Maroc',          scoreH: null,    scoreA: null,    status: 'upcoming',     date: 'Mar 23 juin', time: '20h00' }
];

/* ---- ÉTAT ---- */
let currentFilter  = 'all';
let editingMatchId = null;
let addingMatch    = false;

const REMOTE_API_BASE = 'https://can2sav.onrender.com'; // Remplace par l'URL publique de ton serveur, ex: 'https://monserveur.example.com'
const LOCAL_API_BASE  = 'http://127.0.0.1:8000';
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? LOCAL_API_BASE
  : REMOTE_API_BASE;

// IMPORTANT : pour GitHub Pages, configure REMOTE_API_BASE avec l'URL du serveur déployé.
// Exemple : const REMOTE_API_BASE = 'https://monserveur.example.com';

const useBackend = Boolean(API_BASE);

const AUTH_TOKEN_KEY = 'can2sav_admin_token';
let adminToken = sessionStorage.getItem(AUTH_TOKEN_KEY) || '';

const LOCAL_DATA_KEY = 'can2sav_local_data';

let teamsEffectif = {};

function loadLocalData() {
  const raw = localStorage.getItem(LOCAL_DATA_KEY);
  if (!raw) return;
  try {
    const data = JSON.parse(raw);
    if (Array.isArray(data.matches)) {
      matches = data.matches;
    }
    if (data.teamsEffectif && typeof data.teamsEffectif === 'object') {
      teamsEffectif = data.teamsEffectif;
    }
  } catch (e) {
    console.warn('Impossible de charger les données locales', e);
  }
}

function saveLocalData() {
  localStorage.setItem(LOCAL_DATA_KEY, JSON.stringify({ matches, teamsEffectif }));
}

function saveEffectif() { saveLocalData(); }
function ensureTeamsEffectif() {
  matches.forEach(m => {
    if (teamsEffectif[m.home] === undefined) teamsEffectif[m.home] = 0;
    if (teamsEffectif[m.away] === undefined) teamsEffectif[m.away] = 0;
  });
}

async function loadServerData() {
  if (!useBackend) return;
  try {
    const res = await fetch(`${API_BASE}/api/data`);
    if (!res.ok) throw new Error('Erreur serveur');
    const data = await res.json();
    if (Array.isArray(data.matches)) {
      matches = data.matches;
    }
    if (data.teamsEffectif && typeof data.teamsEffectif === 'object') {
      teamsEffectif = data.teamsEffectif;
    }
  } catch (err) {
    console.warn('Impossible de charger les données serveur:', err.message);
  }
}

async function saveServerData() {
  if (!useBackend) return;
  if (!adminToken) {
    console.warn('Enregistrement serveur ignoré : pas connecté en admin');
    return;
  }
  try {
    const payload = { matches, teamsEffectif };
    await fetch(`${API_BASE}/api/save`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${adminToken}`,
      },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    console.warn('Impossible d enregistrer sur le serveur:', err.message);
  }
}

function isAdmin() {
  return Boolean(adminToken);
}

function setAdminToken(token) {
  adminToken = token;
  if (token) {
    sessionStorage.setItem(AUTH_TOKEN_KEY, token);
  } else {
    sessionStorage.removeItem(AUTH_TOKEN_KEY);
  }
  updateAdminUi();
}

function updateAdminUi() {
  const adminBtn = document.getElementById('btn-admin-login');
  const addBtn = document.getElementById('btn-add-match');
  if (isAdmin()) {
    adminBtn.textContent = 'Admin ✓';
    adminBtn.classList.add('active');
    addBtn.style.display = '';
  } else {
    adminBtn.textContent = 'Admin';
    adminBtn.classList.remove('active');
    addBtn.style.display = 'none';
  }
}

function openAdminLogin() {
  if (!useBackend) {
    alert('Serveur non configuré. Remplace REMOTE_API_BASE dans script.js par l\'URL de ton serveur.');
    return;
  }
  document.getElementById('admin-password').value = '';
  document.getElementById('admin-error').textContent = '';
  const overlay = document.getElementById('admin-login-overlay');
  overlay.classList.add('open');
  overlay.setAttribute('aria-hidden', 'false');
}

function closeAdminLogin() {
  const overlay = document.getElementById('admin-login-overlay');
  overlay.classList.remove('open');
  overlay.setAttribute('aria-hidden', 'true');
  document.getElementById('admin-error').textContent = '';
}

async function submitAdminLogin() {
  const password = document.getElementById('admin-password').value.trim();
  if (!password) {
    document.getElementById('admin-error').textContent = 'Veuillez saisir le mot de passe.';
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      const message = data.error || 'Mot de passe incorrect';
      document.getElementById('admin-error').textContent = message;
      return;
    }
    setAdminToken(data.token);
    closeAdminLogin();
    renderMatches();
    renderStandings();
  } catch (err) {
    document.getElementById('admin-error').textContent = 'Erreur de connexion : ' + err.message;
  }
}

function editEffectif(team) {
  const cur = teamsEffectif[team] ?? 0;
  const val = prompt(`Effectif pour ${team} :`, String(cur));
  if (val === null) return;
  const n = parseInt(val, 10);
  if (isNaN(n) || n < 0) { alert('Veuillez entrer un nombre valide.'); return; }
  teamsEffectif[team] = n;
  saveLocalData();
  saveServerData();
  renderStandings();
}

async function initApp() {
  loadLocalData();
  await loadServerData();
  ensureTeamsEffectif();
  renderMatches();
  renderStandings();
}

initApp();

/* ============================================================
   NAVIGATION
   ============================================================ */
document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('sec-' + btn.dataset.section).classList.add('active');
  });
});

/* ============================================================
   FILTRES GROUPES
   ============================================================ */
document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentFilter = btn.dataset.filter;
    renderMatches();
  });
});

document.getElementById('btn-admin-login').addEventListener('click', () => {
  if (isAdmin()) {
    setAdminToken('');
  } else {
    openAdminLogin();
  }
});
document.getElementById('btn-admin-cancel').addEventListener('click', closeAdminLogin);
document.getElementById('btn-admin-submit').addEventListener('click', submitAdminLogin);

/* ============================================================
   RENDU MATCHS
   ============================================================ */
function renderMatches() {
  const filtered = matches.filter(m => {
    if (currentFilter === 'all')   return true;
    if (currentFilter === 'final') return m.group === 'final';
    return m.group === currentFilter;
  });

  // Grouper par date
  const byDate = {};
  filtered.forEach(m => {
    if (!byDate[m.date]) byDate[m.date] = [];
    byDate[m.date].push(m);
  });

  let html = '';
  for (const date in byDate) {
    html += `<div class="match-day"><div class="match-day-label">${date}</div>`;
    byDate[date].forEach(m => {
      const color = GROUP_COLORS[m.group] || '#888';
      const scoreOrTime = m.status === 'upcoming'
        ? `<div class="match-time">${m.time}</div>`
        : `<div class="score-box">
             <span class="score-num">${m.scoreH}</span>
             <span class="score-sep">-</span>
             <span class="score-num">${m.scoreA}</span>
           </div>`;
      const statusLabel = m.status === 'done' ? 'Terminé' : m.status === 'live' ? 'En direct' : 'À venir';
      const statusClass = 'match-status status-' + m.status;
      html += `
        <div class="match-card" data-id="${m.id}">
          <div class="match-group-dot" style="background:${color}"></div>
          <span class="team-name">${m.home}</span>
          ${scoreOrTime}
          <span class="team-name team-name--right">${m.away}</span>
          <span class="${statusClass}">${statusLabel}</span>
        </div>`;
    });
    html += '</div>';
  }

  if (!html) {
    html = '<p style="color:var(--text-muted);font-size:13px;padding:1rem 0;">Aucun match dans cette catégorie.</p>';
  }

  document.getElementById('matches-container').innerHTML = html;

  // Attacher les événements de clic sur chaque carte
  if (isAdmin()) {
    document.querySelectorAll('.match-card').forEach(card => {
      card.addEventListener('click', () => openEditMatch(parseInt(card.dataset.id)));
    });
  }

  updateHeroStats();
}

/* ============================================================
   STATS HERO
   ============================================================ */
function updateHeroStats() {
  const done = matches.filter(m => m.status === 'done');
  const buts = done.reduce((s, m) => s + (m.scoreH || 0) + (m.scoreA || 0), 0);
  const allTeams = new Set();
  matches.forEach(m => { allTeams.add(m.home); allTeams.add(m.away); });

  document.getElementById('nb-matchs').textContent  = done.length;
  document.getElementById('nb-buts').textContent    = buts;
  document.getElementById('nb-equipes').textContent = allTeams.size;
}

/* ============================================================
   RENDU CLASSEMENT
   ============================================================ */
function computeStandings() {
  const teams = {};

  matches
    .filter(m => m.status === 'done' && m.group !== 'final')
    .forEach(m => {
      [
        { name: m.home, scored: m.scoreH, conceded: m.scoreA, group: m.group },
        { name: m.away, scored: m.scoreA, conceded: m.scoreH, group: m.group },
      ].forEach(({ name, scored, conceded, group }) => {
        if (!teams[name]) teams[name] = { name, group, pts: 0, j: 0, g: 0, n: 0, d: 0, bp: 0, bc: 0, effectif: teamsEffectif[name] || 0 };
        teams[name].j++;
        teams[name].bp += scored;
        teams[name].bc += conceded;
      });

      if (m.scoreH > m.scoreA) {
        teams[m.home].pts += 3; teams[m.home].g++;
        teams[m.away].d++;
      } else if (m.scoreH < m.scoreA) {
        teams[m.away].pts += 3; teams[m.away].g++;
        teams[m.home].d++;
      } else {
        teams[m.home].pts++; teams[m.home].n++;
        teams[m.away].pts++; teams[m.away].n++;
      }
    });

  return teams;
}

function renderStandings() {
  const teams = computeStandings();

  // Regrouper par groupe
  const groups = {};
  Object.values(teams).forEach(t => {
    if (!groups[t.group]) groups[t.group] = [];
    groups[t.group].push(t);
  });

  // Trier les groupes alphabétiquement (A, B, C…)
  const sortedGroups = Object.keys(groups).sort();

  let html = '';
  sortedGroups.forEach(g => {
    const sorted = groups[g].sort((a, b) => b.pts - a.pts || (b.bp - b.bc) - (a.bp - a.bc));
    const color  = GROUP_COLORS[g] || '#888';
    html += `
      <div class="group-block">
        <div class="group-title">
          <div class="group-color-dot" style="background:${color}"></div>
          Groupe ${g}
        </div>
        <table class="rank-table">
          <thead>
            <tr>
              <th>#</th><th>Équipe</th>
              <th title="Joués">J</th><th title="Gagnés">G</th>
              <th title="Nuls">N</th><th title="Défaites">D</th>
              <th title="Buts pour">Bp</th><th title="Buts contre">Bc</th>
              <th title="Points">Pts</th>
            </tr>
          </thead>
          <tbody>`;

    sorted.forEach((t, i) => {
      const qualified = i < 2;
      html += `
        <tr class="${qualified ? 'qualified' : ''}">
          <td class="rank-pos">${i + 1}${qualified ? '<span class="qualified-dot"></span>' : ''}</td>
          <td class="rank-team">
            <span class="editable-team" data-team="${t.name}">${t.name}</span>
            <span class="team-eff"> &nbsp;•&nbsp; ${t.effectif || 0}</span>
          </td>
          <td>${t.j}</td><td>${t.g}</td><td>${t.n}</td><td>${t.d}</td>
          <td>${t.bp}</td><td>${t.bc}</td>
          <td class="rank-pts">${t.pts}</td>
        </tr>`;
    });

    html += '</tbody></table></div>';
  });

  if (!html) {
    html = '<p style="color:var(--text-muted);font-size:13px;">Aucun résultat encore.</p>';
  }

  document.getElementById('standings-container').innerHTML = html;
  // Attacher écouteurs pour éditer l'effectif
  if (isAdmin()) {
    document.querySelectorAll('.editable-team').forEach(el => {
      el.addEventListener('click', e => {
        const team = e.currentTarget.dataset.team;
        editEffectif(team);
      });
    });
  }
}

/* ============================================================
   MODAL — MODIFIER UN MATCH
   ============================================================ */
function openEditMatch(id) {
  if (!isAdmin()) return;
  editingMatchId = id;
  addingMatch    = false;

  const m = matches.find(x => x.id === id);
  document.getElementById('modal-title').textContent = `${m.home} vs ${m.away}`;

  document.getElementById('modal-body').innerHTML = `
    <div class="field">
      <label>Score ${m.home}</label>
      <input type="number" id="ed-sh" min="0" value="${m.scoreH ?? ''}" placeholder="0" />
    </div>
    <div class="field">
      <label>Score ${m.away}</label>
      <input type="number" id="ed-sa" min="0" value="${m.scoreA ?? ''}" placeholder="0" />
    </div>
    <div class="field">
      <label>Statut</label>
      <select id="ed-status">
        <option value="upcoming" ${m.status === 'upcoming' ? 'selected' : ''}>À venir</option>
        <option value="live"     ${m.status === 'live'     ? 'selected' : ''}>En direct</option>
        <option value="done"     ${m.status === 'done'     ? 'selected' : ''}>Terminé</option>
      </select>
    </div>
    <div class="field">
      <label>Date (ex : Sam 14 juin)</label>
      <input type="text" id="ed-date" value="${m.date}" />
    </div>
    <div class="field">
      <label>Heure (ex : 10h00)</label>
      <input type="text" id="ed-time" value="${m.time}" />
    </div>`;

  openModal();
}

/* ============================================================
   MODAL — AJOUTER UN MATCH
   ============================================================ */
document.getElementById('btn-add-match').addEventListener('click', () => {
  addingMatch    = true;
  editingMatchId = null;

  document.getElementById('modal-title').textContent = 'Ajouter un match';
  document.getElementById('modal-body').innerHTML = `
    <div class="field">
      <label>Équipe domicile</label>
      <input type="text" id="add-home" placeholder="Ex : Sénégal" />
    </div>
    <div class="field">
      <label>Équipe extérieur</label>
      <input type="text" id="add-away" placeholder="Ex : Mali" />
    </div>
    <div class="field">
      <label>Groupe</label>
      <select id="add-group">
        <option value="A">Groupe A</option>
        <option value="B">Groupe B</option>
        <option value="C">Groupe C</option>
        <option value="D">Groupe D</option>
        <option value="final">Phase finale</option>
      </select>
    </div>
    <div class="field">
      <label>Date (ex : Sam 14 juin)</label>
      <input type="text" id="add-date" placeholder="Sam 14 juin" />
    </div>
    <div class="field">
      <label>Heure (ex : 10h00)</label>
      <input type="text" id="add-time" placeholder="10h00" />
    </div>`;

  openModal();
});

/* ============================================================
   MODAL — SAVE / CLOSE
   ============================================================ */
function openModal() {
  document.getElementById('modal-overlay').classList.add('open');
  document.getElementById('modal-overlay').setAttribute('aria-hidden', 'false');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
  document.getElementById('modal-overlay').setAttribute('aria-hidden', 'true');
}

document.getElementById('btn-cancel').addEventListener('click', closeModal);
document.getElementById('modal-overlay').addEventListener('click', e => {
  if (e.target === document.getElementById('modal-overlay')) closeModal();
});

document.getElementById('btn-save').addEventListener('click', () => {
  if (addingMatch) {
    const home = document.getElementById('add-home').value.trim();
    const away = document.getElementById('add-away').value.trim();
    if (!home || !away) {
      alert('Veuillez renseigner les deux équipes.');
      return;
    }
    matches.push({
      id:      Date.now(),
      group:   document.getElementById('add-group').value,
      home,
      away,
      scoreH:  null,
      scoreA:  null,
      status:  'upcoming',
      date:    document.getElementById('add-date').value.trim() || 'À venir',
      time:    document.getElementById('add-time').value.trim() || 'TBD',
    });
    saveLocalData();
    saveServerData();
  } else {
    const m      = matches.find(x => x.id === editingMatchId);
    const sh     = parseInt(document.getElementById('ed-sh').value, 10);
    const sa     = parseInt(document.getElementById('ed-sa').value, 10);
    m.scoreH     = isNaN(sh) ? null : sh;
    m.scoreA     = isNaN(sa) ? null : sa;
    m.status     = document.getElementById('ed-status').value;
    m.date       = document.getElementById('ed-date').value.trim();
    m.time       = document.getElementById('ed-time').value.trim();
  }

  closeModal();
  saveServerData();
  renderMatches();
  renderStandings();
});

/* ============================================================
   INIT
   ============================================================ */
const addBtn = document.getElementById('btn-add-match');

async function initApp() {
  loadLocalData();
  await loadServerData();
  ensureTeamsEffectif();
  renderMatches();
  renderStandings();
}

initApp();

// Fermeture de la bannière si l'utilisateur clique sur la croix
const bannerCloseBtn = document.querySelector('.banner-close');
if (bannerCloseBtn) {
  bannerCloseBtn.addEventListener('click', () => {
    const b = document.querySelector('.site-banner');
    if (b) b.style.display = 'none';
  });
}
