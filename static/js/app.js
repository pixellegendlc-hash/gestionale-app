// ═══════════════════════════════════════
// app.js — Core: navigazione, toast, modal
// ═══════════════════════════════════════

let currentPage = 'tasks';
let searchOpen  = false;

// ── NAVIGATION ──
function goPage(page, el) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  el.classList.add('active');
  currentPage = page;
  closeSearch();
  loadPage(page);
}

function loadPage(page) {
  if (page === 'tasks')   Tasks.load();
  if (page === 'finanze') Finanze.load();
  if (page === 'appunti') { Appunti.showList(); Appunti.load(); }
  if (page === 'photos')  Photos.load();
  if (page === 'stats')   Stats.load();
}

// ── SEARCH ──
function toggleSearch() {
  searchOpen = !searchOpen;
  document.getElementById('search-bar').classList.toggle('open', searchOpen);
  if (searchOpen) { document.getElementById('search-input').focus(); }
  else { document.getElementById('search-input').value = ''; loadPage(currentPage); }
}
function closeSearch() {
  searchOpen = false;
  document.getElementById('search-bar').classList.remove('open');
  document.getElementById('search-input').value = '';
}
function onSearch(val) {
  if (!val.trim()) { loadPage(currentPage); return; }
  if (currentPage === 'tasks')   Tasks.search(val);
  if (currentPage === 'finanze') Finanze.search(val);
  if (currentPage === 'appunti') Appunti.search(val);
}

// ── FAB ──
function fabClick() {
  if (currentPage === 'tasks')   Tasks.openModal();
  if (currentPage === 'finanze') Finanze.openModal();
  if (currentPage === 'appunti') Appunti.openModal();
  if (currentPage === 'photos')  Photos.openUpload();
}

// ── MODAL ──
function openModal(id) {
  const m = document.getElementById(id);
  m.classList.add('open');
  m.addEventListener('click', e => { if(e.target===m) closeModal(id); }, {once:true});
}
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

// ── CONFIRM DELETE ──
function confirmDelete(cb) {
  openModal('modal-confirm');
  document.getElementById('confirm-yes').onclick = () => { closeModal('modal-confirm'); cb(); };
}

// ── TOAST ──
let _toastTimer;
function toast(msg, type = 'success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `show ${type}`;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => t.classList.remove('show'), 2500);
}

// ── API HELPER ──
async function api(url, method = 'GET', body = null) {
  const opts = { method, headers: {} };
  if (body) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ── SKELETON ──
function skeleton(n = 3) {
  return Array(n).fill('<div class="skeleton skel-card"></div>').join('');
}

// ── FORMAT DATE ──
function fmtDate(s) {
  if (!s) return '';
  return s.substring(0, 10);
}

// ── FORMAT MONEY ──
function fmtMoney(n) {
  return '€' + parseFloat(n).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g,',');
}

// ── DAYS LABEL ──
function daysLabel(g) {
  if (g === 9999) return '';
  if (g === -1)   return `<span class="giorni-scaduto"><i class="fa fa-circle-exclamation"></i> SCADUTO</span>`;
  if (g === 0)    return `<span class="giorni-urgente"><i class="fa fa-clock"></i> OGGI</span>`;
  if (g <= 3)     return `<span class="giorni-urgente"><i class="fa fa-clock"></i> ${g}g</span>`;
  return `<span class="giorni-normal">${g}g</span>`;
}

// ── INIT ──
document.addEventListener('DOMContentLoaded', () => {
  Tasks.load();
});
