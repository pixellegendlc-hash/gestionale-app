// ═══════════════════════════════════════
// tasks.js — Gestione Task
// ═══════════════════════════════════════
const Tasks = (() => {
  let tab = 'attivi';
  let priFilter = 'Tutti';

  // ── SUB TAB ──
  function setTab(t, el) {
    tab = t;
    document.querySelectorAll('.task-sub-tab').forEach(x => x.classList.remove('active'));
    el.classList.add('active');
    document.getElementById('task-filters').style.display = t === 'attivi' ? 'flex' : 'none';
    load();
  }

  function setPri(val, el) {
    priFilter = val;
    document.querySelectorAll('#task-filters .filter-chip').forEach(x => x.classList.remove('active'));
    el.classList.add('active');
    load();
  }

  async function load() {
    const el = document.getElementById('tasks-list');
    el.innerHTML = skeleton();
    try {
      let data;
      if (tab === 'attivi') {
        data = await api(`/api/tasks?priorita=${priFilter}`);
      } else {
        const stato = tab === 'completati' ? 'Completato' : 'Falliti';
        data = await api(`/api/tasks/all?stato=${stato}`);
      }
      render(data, el);
    } catch(e) { el.innerHTML = `<div class="empty"><div class="empty-icon"><i class="fa fa-wifi"></i></div><p>Errore di connessione</p></div>`; }
  }

  async function search(q) {
    const el = document.getElementById('tasks-list');
    const all = await api('/api/tasks/all');
    const ql = q.toLowerCase();
    render(all.filter(t =>
      t.nome?.toLowerCase().includes(ql) ||
      t.note?.toLowerCase().includes(ql) ||
      t.scadenza?.includes(ql)
    ), el);
  }

  function render(tasks, el) {
    if (!tasks.length) {
      el.innerHTML = `<div class="empty"><div class="empty-icon"><i class="fa fa-clipboard-list"></i></div><p>Nessun task</p></div>`;
      return;
    }
    el.innerHTML = tasks.map(t => {
      const isAttivo = tab === 'attivi';
      const actions = isAttivo ? `
        <div class="actions">
          <button class="act act-done" onclick="Tasks.setStato(${t._id},'Completato')"><i class="fa fa-check"></i> Fatto</button>
          <button class="act act-fail" onclick="Tasks.setStato(${t._id},'Falliti')"><i class="fa fa-xmark"></i> Fallito</button>
          <button class="act act-edit" onclick="Tasks.openEdit(${t._id})"><i class="fa fa-pen"></i> Modifica</button>
          <button class="act act-del"  onclick="Tasks.del(${t._id})"><i class="fa fa-trash"></i></button>
        </div>` : `
        <div class="actions">
          <button class="act act-restore" onclick="Tasks.setStato(${t._id},'Da Iniziare')"><i class="fa fa-rotate-left"></i> Ripristina</button>
          <button class="act act-del" onclick="Tasks.del(${t._id})"><i class="fa fa-trash"></i> Elimina</button>
        </div>`;

      const scadenzaLabel = t.scadenza && t.scadenza !== '9999-01-01'
        ? `<span class="chip"><i class="fa fa-calendar"></i> ${fmtDate(t.scadenza)}</span>` : '';
      const noteLabel = t.note
        ? `<span class="chip"><i class="fa fa-note-sticky"></i> Nota</span>` : '';

      return `
        <div class="card pri-${t.priorita}">
          <div class="card-header">
            <div class="card-title">${t.nome}</div>
            ${daysLabel(t._giorni)}
          </div>
          <div class="card-meta">
            <span class="badge badge-${t.priorita}">${t.priorita.replace('_',' ')}</span>
            <span class="badge badge-${t.stato}">${t.stato}</span>
            ${scadenzaLabel}${noteLabel}
          </div>
          ${t.note ? `<div style="margin-top:10px;font-size:13px;color:var(--text2);line-height:1.5">${t.note}</div>` : ''}
          ${actions}
        </div>`;
    }).join('');
  }

  // ── MODAL ──
  function openModal(data, id) {
    const isEdit = data && id !== undefined;
    document.getElementById('task-modal-title').textContent = isEdit ? 'Modifica Task' : 'Nuovo Task';
    document.getElementById('t-id').value       = id ?? '';
    document.getElementById('t-nome').value     = data?.nome ?? '';
    document.getElementById('t-scadenza').value = data?.scadenza ?? '';
    document.getElementById('t-priorita').value = data?.priorita ?? 'Media';
    document.getElementById('t-stato').value    = data?.stato ?? 'Da Iniziare';
    document.getElementById('t-note').value     = data?.note ?? '';
    openModal('modal-task');
    setTimeout(() => document.getElementById('t-nome').focus(), 100);
  }

  async function openEdit(id) {
    const all = await api('/api/tasks/all');
    const t = all.find(x => x._id === id);
    if (t) openModal(t, id);
  }

  async function save() {
    const nome = document.getElementById('t-nome').value.trim();
    if (!nome) { toast('Il nome è obbligatorio', 'error'); return; }
    const id = document.getElementById('t-id').value;
    const payload = {
      nome,
      scadenza:  document.getElementById('t-scadenza').value,
      priorita:  document.getElementById('t-priorita').value,
      stato:     document.getElementById('t-stato').value,
      note:      document.getElementById('t-note').value.trim()
    };
    try {
      await api(id !== '' ? `/api/tasks/${id}` : '/api/tasks',
                id !== '' ? 'PUT' : 'POST', payload);
      closeModal('modal-task');
      toast(id !== '' ? 'Task aggiornato ✓' : 'Task creato ✓');
      load();
    } catch(e) { toast('Errore nel salvataggio', 'error'); }
  }

  async function setStato(id, stato) {
    try {
      await api(`/api/tasks/${id}/stato`, 'PATCH', { stato });
      toast(stato === 'Completato' ? '✓ Completato!' : stato === 'Falliti' ? 'Task fallito' : 'Task ripristinato');
      load();
    } catch(e) { toast('Errore', 'error'); }
  }

  function del(id) {
    confirmDelete(async () => {
      await api(`/api/tasks/${id}`, 'DELETE');
      toast('Task eliminato');
      load();
    });
  }

  return { load, search, openModal, openEdit, save, setStato, del, setTab, setPri };
})();
