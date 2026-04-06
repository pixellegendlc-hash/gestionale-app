// ═══════════════════════════════════════
// appunti.js — Gestione Appunti
// ═══════════════════════════════════════
const Appunti = (() => {
  let currentId = null;

  function showList() {
    document.getElementById('appunti-list-view').style.display = 'block';
    document.getElementById('appunti-detail-view').style.display = 'none';
    document.getElementById('main-fab').style.display = 'flex';
  }

  function showDetail() {
    document.getElementById('appunti-list-view').style.display = 'none';
    document.getElementById('appunti-detail-view').style.display = 'block';
    document.getElementById('main-fab').style.display = 'none';
  }

  async function load(q) {
    const el = document.getElementById('appunti-list');
    el.innerHTML = skeleton();
    try {
      const notes = await api('/api/appunti' + (q ? `?q=${encodeURIComponent(q)}` : ''));
      if (!notes.length) {
        el.innerHTML = `<div class="empty"><div class="empty-icon"><i class="fa fa-sticky-note"></i></div><p>Nessun appunto</p></div>`;
        return;
      }
      el.innerHTML = notes.map(n => `
        <div class="card note-${n.colore||'default'}" onclick="Appunti.view(${n._id})" style="cursor:pointer">
          <div class="card-title">${n.titolo}</div>
          <div style="font-size:13px;color:var(--text2);margin-top:6px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical">${n.contenuto || ''}</div>
          <div class="card-meta" style="margin-top:8px">
            <span class="chip"><i class="fa fa-clock"></i> ${fmtDate(n.data)}</span>
          </div>
        </div>`).join('');
    } catch(e) { el.innerHTML = `<div class="empty"><p>Errore</p></div>`; }
  }

  function search(q) { load(q); }

  async function view(id) {
    currentId = id;
    const n = await api(`/api/appunti/${id}`);
    document.getElementById('detail-title').textContent   = n.titolo;
    document.getElementById('detail-date').textContent    = n.data?.substring(0,16) ?? '';
    document.getElementById('detail-content').textContent = n.contenuto;

    // History
    const hist = n.history || [];
    const histEl = document.getElementById('detail-history');
    if (hist.length) {
      histEl.innerHTML = `<div class="section-hdr" style="margin-top:18px"><span class="section-title">Versioni precedenti (${hist.length})</span></div>` +
        hist.slice().reverse().map((v,i) => `
          <div class="history-item" onclick="Appunti.restoreVersion(${id}, ${hist.length-1-i})">
            <span style="font-weight:700">v${hist.length-i}</span> — ${fmtDate(v.date||v.data||'')}
            <div style="margin-top:4px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">${v.contenuto?.substring(0,60)||''}</div>
          </div>`).join('');
    } else {
      histEl.innerHTML = '';
    }
    showDetail();
  }

  async function restoreVersion(noteId, versionIdx) {
    const n = await api(`/api/appunti/${noteId}`);
    const version = n.history[versionIdx];
    if (!version) return;
    await api(`/api/appunti/${noteId}`, 'PUT', {
      titolo: version.titolo,
      contenuto: version.contenuto
    });
    toast('Versione ripristinata ✓');
    view(noteId);
  }

  function openModal(data, id) {
    document.getElementById('note-modal-title').textContent = data ? 'Modifica Appunto' : 'Nuovo Appunto';
    document.getElementById('n-id').value       = id ?? '';
    document.getElementById('n-titolo').value   = data?.titolo ?? '';
    document.getElementById('n-contenuto').value= data?.contenuto ?? '';
    document.getElementById('n-colore').value   = data?.colore ?? 'default';
    openModal('modal-appunto');
    setTimeout(() => document.getElementById('n-titolo').focus(), 100);
  }

  function editCurrent() {
    if (currentId === null) return;
    const title   = document.getElementById('detail-title').textContent;
    const content = document.getElementById('detail-content').textContent;
    openModal({ titolo: title, contenuto: content }, currentId);
  }

  async function save() {
    const titolo = document.getElementById('n-titolo').value.trim();
    if (!titolo) { toast('Il titolo è obbligatorio', 'error'); return; }
    const id = document.getElementById('n-id').value;
    const payload = {
      titolo,
      contenuto: document.getElementById('n-contenuto').value,
      colore:    document.getElementById('n-colore').value
    };
    try {
      await api(id !== '' ? `/api/appunti/${id}` : '/api/appunti',
                id !== '' ? 'PUT' : 'POST', payload);
      closeModal('modal-appunto');
      toast(id !== '' ? 'Appunto aggiornato ✓' : 'Appunto creato ✓');
      if (id !== '') { view(parseInt(id)); }
      else { showList(); load(); }
    } catch(e) { toast('Errore', 'error'); }
  }

  function delCurrent() {
    if (currentId === null) return;
    confirmDelete(async () => {
      await api(`/api/appunti/${currentId}`, 'DELETE');
      toast('Appunto eliminato');
      showList();
      load();
    });
  }

  return { load, search, view, openModal, editCurrent, save, delCurrent, showList, showDetail, restoreVersion };
})();
