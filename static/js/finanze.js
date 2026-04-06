// ═══════════════════════════════════════
// finanze.js — Gestione Finanze
// ═══════════════════════════════════════
const Finanze = (() => {
  let tipoFilter = 'Tutti';

  function setTipo(val, el) {
    tipoFilter = val;
    document.querySelectorAll('#fin-filters .filter-chip').forEach(x => x.classList.remove('active'));
    el.classList.add('active');
    load();
  }

  async function load() {
    const el = document.getElementById('finanze-list');
    el.innerHTML = skeleton();
    try {
      const [rip, fin] = await Promise.all([
        api('/api/finanze/riepilogo'),
        api('/api/finanze?tipo=' + tipoFilter)
      ]);
      renderSummary(rip.mese_corrente);
      render(fin, el);
    } catch(e) { el.innerHTML = `<div class="empty"><div class="empty-icon"><i class="fa fa-wifi"></i></div><p>Errore</p></div>`; }
  }

  function renderSummary(mc) {
    document.getElementById('fin-entrate').textContent = fmtMoney(mc.entrate);
    document.getElementById('fin-uscite').textContent  = fmtMoney(mc.uscite);
    const sEl = document.getElementById('fin-saldo');
    sEl.textContent = fmtMoney(Math.abs(mc.saldo));
    sEl.className = 'sum-val ' + (mc.saldo >= 0 ? 'col-green' : 'col-red');
  }

  function render(fin, el) {
    if (!fin.length) {
      el.innerHTML = `<div class="empty"><div class="empty-icon"><i class="fa fa-euro-sign"></i></div><p>Nessuna voce</p></div>`;
      return;
    }
    el.innerHTML = fin.map(f => `
      <div class="card">
        <div class="card-header">
          <div>
            <div class="card-title">${f.descrizione}</div>
            <div class="card-meta" style="margin-top:6px">
              <span class="badge badge-${f.tipo}">${f.tipo}</span>
              <span class="chip"><i class="fa fa-tag"></i> ${f.categoria || 'Altro'}</span>
              <span class="chip"><i class="fa fa-calendar"></i> ${fmtDate(f.data)}</span>
            </div>
          </div>
          <div style="font-size:20px;font-weight:800;color:${f.tipo==='Entrata'?'var(--green)':'var(--red)'};white-space:nowrap">
            ${f.tipo==='Entrata'?'+':'-'}${fmtMoney(f.importo)}
          </div>
        </div>
        ${f.note ? `<div style="margin-top:8px;font-size:12px;color:var(--text2)">${f.note}</div>` : ''}
        <div class="actions">
          <button class="act act-edit" onclick="Finanze.openEdit(${f._id})"><i class="fa fa-pen"></i> Modifica</button>
          <button class="act act-del"  onclick="Finanze.del(${f._id})"><i class="fa fa-trash"></i> Elimina</button>
        </div>
      </div>`).join('');
  }

  async function search(q) {
    const el = document.getElementById('finanze-list');
    const all = await api('/api/finanze');
    const ql = q.toLowerCase();
    render(all.filter(f =>
      f.descrizione?.toLowerCase().includes(ql) ||
      f.categoria?.toLowerCase().includes(ql) ||
      f.data?.includes(ql)
    ), el);
  }

  function openModal(data, id) {
    document.getElementById('fin-modal-title').textContent = data ? 'Modifica Voce' : 'Nuova Voce';
    document.getElementById('f-id').value          = id ?? '';
    document.getElementById('f-desc').value        = data?.descrizione ?? '';
    document.getElementById('f-importo').value     = data?.importo ?? '';
    document.getElementById('f-tipo').value        = data?.tipo ?? 'Uscita';
    document.getElementById('f-categoria').value  = data?.categoria ?? 'Altro';
    document.getElementById('f-data').value        = data?.data ?? new Date().toISOString().split('T')[0];
    document.getElementById('f-note').value        = data?.note ?? '';
    openModal('modal-finanza');
    setTimeout(() => document.getElementById('f-desc').focus(), 100);
  }

  async function openEdit(id) {
    const all = await api('/api/finanze');
    const f = all.find(x => x._id === id);
    if (f) openModal(f, id);
  }

  async function save() {
    const desc    = document.getElementById('f-desc').value.trim();
    const importo = document.getElementById('f-importo').value;
    if (!desc || !importo) { toast('Compila descrizione e importo', 'error'); return; }
    const id = document.getElementById('f-id').value;
    const payload = {
      descrizione: desc,
      importo: parseFloat(importo),
      tipo:      document.getElementById('f-tipo').value,
      categoria: document.getElementById('f-categoria').value,
      data:      document.getElementById('f-data').value,
      note:      document.getElementById('f-note').value.trim()
    };
    try {
      await api(id !== '' ? `/api/finanze/${id}` : '/api/finanze',
                id !== '' ? 'PUT' : 'POST', payload);
      closeModal('modal-finanza');
      toast(id !== '' ? 'Voce aggiornata ✓' : 'Voce aggiunta ✓');
      load();
    } catch(e) { toast('Errore', 'error'); }
  }

  function del(id) {
    confirmDelete(async () => {
      await api(`/api/finanze/${id}`, 'DELETE');
      toast('Voce eliminata');
      load();
    });
  }

  async function showRiepilogo() {
    const rip = await api('/api/finanze/riepilogo');
    const list = document.getElementById('riepilogo-list');
    list.innerHTML = rip.tutti_mesi.map(m => `
      <div class="card" style="margin-bottom:8px">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:700">${m.mese}</span>
          <span style="font-weight:800;color:${m.saldo>=0?'var(--green)':'var(--red)'}">${fmtMoney(m.saldo)}</span>
        </div>
        <div style="display:flex;gap:12px;margin-top:6px;font-size:13px">
          <span class="col-green">↑ ${fmtMoney(m.entrate)}</span>
          <span class="col-red">↓ ${fmtMoney(m.uscite)}</span>
        </div>
      </div>`).join('') || '<div class="empty"><p>Nessun dato</p></div>';
    openModal('modal-riepilogo');
  }

  return { load, search, openModal, openEdit, save, del, setTipo, showRiepilogo };
})();
