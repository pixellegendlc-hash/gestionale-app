// ═══════════════════════════════════════
// photos.js — Gestione Foto
// ═══════════════════════════════════════
const Photos = (() => {
  let currentGroup = 'Tutte';
  let currentPhoto = null;

  async function load() {
    const el = document.getElementById('photos-grid');
    el.innerHTML = `<div class="loader" style="grid-column:1/-1"><div class="spinner"></div></div>`;
    try {
      await loadGroups();
      const photos = await api('/api/photos' + (currentGroup !== 'Tutte' ? `?group=${encodeURIComponent(currentGroup)}` : ''));
      render(photos, el);
    } catch(e) {
      el.innerHTML = `<div class="empty" style="grid-column:1/-1"><div class="empty-icon"><i class="fa fa-image"></i></div><p>Errore caricamento foto</p></div>`;
    }
  }

  async function loadGroups() {
    const groups = await api('/api/photos/groups');
    const el = document.getElementById('photos-groups');
    el.innerHTML = groups.map(g => `
      <button class="filter-chip ${g === currentGroup ? 'active' : ''}" onclick="Photos.setGroup('${g}',this)">${g}</button>
    `).join('');
  }

  function setGroup(g, el) {
    currentGroup = g;
    document.querySelectorAll('#photos-groups .filter-chip').forEach(x => x.classList.remove('active'));
    el.classList.add('active');
    load();
  }

  function render(photos, el) {
    if (!photos.length) {
      el.innerHTML = `<div class="empty" style="grid-column:1/-1"><div class="empty-icon"><i class="fa fa-images"></i></div><p>Nessuna foto${currentGroup !== 'Tutte' ? ' in questo gruppo' : ''}</p></div>`;
      return;
    }
    el.innerHTML = photos.map(p => `
      <div class="photo-thumb" onclick="Photos.openLightbox(${JSON.stringify(p).replace(/"/g,'&quot;')})">
        <img src="${p.download_url}" alt="${p.name}" loading="lazy">
        <div class="photo-name">${p.name}</div>
      </div>`).join('');
  }

  function openLightbox(photo) {
    currentPhoto = photo;
    document.getElementById('lightbox-name').textContent = photo.name;
    document.getElementById('lightbox-img-el').src = photo.download_url;
    document.getElementById('lightbox').classList.add('open');
  }

  function closeLightbox() {
    document.getElementById('lightbox').classList.remove('open');
    currentPhoto = null;
  }

  function deleteCurrentPhoto() {
    if (!currentPhoto) return;
    confirmDelete(async () => {
      try {
        await api('/api/photos/delete', 'POST', { path: currentPhoto.path, sha: currentPhoto.sha });
        toast('Foto eliminata');
        closeLightbox();
        load();
      } catch(e) { toast('Errore eliminazione', 'error'); }
    });
  }

  function openUpload() { openModal('modal-upload'); }

  function onFileSelect(input) {
    const files = input.files;
    if (!files.length) return;
    const preview = document.getElementById('upload-preview');
    preview.innerHTML = Array.from(files).map(f =>
      `<div style="font-size:13px;color:var(--text2);padding:4px 0"><i class="fa fa-image"></i> ${f.name}</div>`
    ).join('');
  }

  async function doUpload() {
    const input = document.getElementById('photo-file-input');
    const group = document.getElementById('upload-group').value.trim() || null;
    if (!input.files.length) { toast('Seleziona almeno una foto', 'error'); return; }

    const btn = document.getElementById('upload-btn');
    btn.disabled = true;
    btn.textContent = 'Caricamento...';

    let ok = 0, fail = 0;
    for (const file of input.files) {
      try {
        const b64 = await fileToBase64(file);
        const res = await api('/api/photos/upload', 'POST', {
          filename: file.name,
          content:  b64,
          group:    group || null
        });
        if (res.ok) ok++; else fail++;
      } catch(e) { fail++; }
    }

    btn.disabled = false;
    btn.textContent = 'Carica';
    closeModal('modal-upload');
    input.value = '';
    document.getElementById('upload-preview').innerHTML = '';

    if (ok > 0) toast(`${ok} foto caricate ✓`);
    if (fail > 0) toast(`${fail} foto fallite`, 'error');
    if (ok > 0) { if (group) currentGroup = group; load(); }
  }

  async function createGroup() {
    const name = document.getElementById('new-group-name').value.trim();
    if (!name) { toast('Inserisci il nome del gruppo', 'error'); return; }
    await api('/api/photos/groups', 'POST', { name });
    toast(`Gruppo "${name}" creato ✓`);
    document.getElementById('new-group-name').value = '';
    loadGroups();
  }

  function fileToBase64(file) {
    return new Promise((res, rej) => {
      const r = new FileReader();
      r.onload = () => res(r.result.split(',')[1]);
      r.onerror = rej;
      r.readAsDataURL(file);
    });
  }

  return { load, setGroup, openLightbox, closeLightbox, deleteCurrentPhoto, openUpload, onFileSelect, doUpload, createGroup };
})();
