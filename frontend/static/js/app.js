/* app.js — GeoLabeler SPA controller */
(async () => {

  /* ── helpers ───────────────────────────────────────── */
  const $ = id => document.getElementById(id);
  const qs = sel => document.querySelector(sel);

  function toast(msg, type = 'info') {
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = msg;
    $('toast-container').appendChild(el);
    setTimeout(() => el.remove(), 3500);
  }

  function showModal(html) {
    $('modal-content').innerHTML = html;
    $('modal-overlay').classList.remove('hidden');
  }
  function closeModal() {
    $('modal-overlay').classList.add('hidden');
    $('modal-content').innerHTML = '';
  }
  $('modal-close').onclick = closeModal;
  $('modal-overlay').onclick = e => { if (e.target === $('modal-overlay')) closeModal(); };

  function setView(name) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    $(`view-${name}`).classList.add('active');
    qs(`[data-view="${name}"]`)?.classList.add('active');
    if (name === 'dashboard') loadDashboard();
    if (name === 'datasets')  loadDatasets();
    if (name === 'annotate')  loadAnnotateDatasets();
    if (name === 'review')    loadReviewQueue();
    if (name === 'export')    loadExportDatasets();
  }

  /* ── auth state ────────────────────────────────────── */
  let currentUser = null;

  function showScreen(name) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    $(name + '-screen').classList.add('active');
  }

  async function boot() {
    if (!Api.hasToken()) return showScreen('auth');
    try {
      currentUser = await Api.me();
      onLoggedIn();
    } catch {
      showScreen('auth');
    }
  }

  function onLoggedIn() {
    showScreen('main');
    $('user-name-sidebar').textContent = currentUser.username;
    $('user-role-sidebar').textContent = currentUser.role;
    $('user-avatar').textContent = currentUser.username[0].toUpperCase();
    setView('dashboard');
  }

  /* ── AUTH FORMS ────────────────────────────────────── */
  // Tab switching
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.auth-form').forEach(f => f.classList.remove('active'));
      btn.classList.add('active');
      $(`${btn.dataset.tab}-form`).classList.add('active');
    };
  });

  $('login-form').onsubmit = async e => {
    e.preventDefault();
    $('login-error').textContent = '';
    try {
      const res = await Api.login({
        username: $('login-username').value,
        password: $('login-password').value,
      });
      Api.setToken(res.access_token);
      currentUser = res.user;
      onLoggedIn();
    } catch (err) {
      $('login-error').textContent = err.message;
    }
  };

  $('register-form').onsubmit = async e => {
    e.preventDefault();
    $('register-error').textContent = '';
    try {
      const res = await Api.register({
        username: $('reg-username').value,
        email:    $('reg-email').value,
        password: $('reg-password').value,
        full_name: $('reg-name').value,
      });
      Api.setToken(res.access_token);
      currentUser = res.user;
      onLoggedIn();
    } catch (err) {
      $('register-error').textContent = err.message;
    }
  };

  $('logout-btn').onclick = async () => {
    try { await Api.logout(); } catch {}
    Api.clearToken();
    currentUser = null;
    showScreen('auth');
  };

  /* ── NAV ───────────────────────────────────────────── */
  document.querySelectorAll('.nav-item').forEach(item => {
    item.onclick = e => { e.preventDefault(); setView(item.dataset.view); };
  });

  /* ── DASHBOARD ─────────────────────────────────────── */
  async function loadDashboard() {
    try {
      const data = await Api.getDatasets({ per_page: 100 });
      const datasets = data.items || [];

      $('stat-datasets').textContent = data.total || 0;
      let totalImages = 0, totalAnnotations = 0, totalCompletion = 0;
      datasets.forEach(d => {
        totalImages      += d.image_count || 0;
        totalAnnotations += d.annotation_count || 0;
        totalCompletion  += d.completion_percentage || 0;
      });
      $('stat-images').textContent = totalImages;
      $('stat-annotations').textContent = totalAnnotations;
      $('stat-completion').textContent = datasets.length
        ? Math.round(totalCompletion / datasets.length) + '%' : '—';

      const list = $('recent-datasets-list');
      list.innerHTML = '';
      datasets.slice(0, 8).forEach(d => {
        const el = document.createElement('div');
        el.className = 'dataset-list-item';
        el.innerHTML = `<span class="dli-name">${d.name}</span><span class="dli-pct">${d.completion_percentage}%</span>`;
        el.onclick = () => setView('datasets');
        list.appendChild(el);
      });
      if (!datasets.length) list.innerHTML = '<p class="muted">No datasets yet.</p>';

    } catch (err) {
      toast('Failed to load dashboard: ' + err.message, 'error');
    }
  }

  /* ── DATASETS VIEW ─────────────────────────────────── */
  let datasetPage = 1;

  async function loadDatasets(page = 1) {
    datasetPage = page;
    const search = $('dataset-search').value;
    const type   = $('filter-type').value;
    const status = $('filter-status').value;

    try {
      const params = { page, per_page: 12 };
      if (search) params.search = search;
      if (type)   params.data_type = type;
      if (status) params.status = status;

      const data = await Api.getDatasets(params);
      renderDatasetGrid(data);
    } catch (err) {
      toast('Failed to load datasets: ' + err.message, 'error');
    }
  }

  function renderDatasetGrid(data) {
    const grid = $('datasets-grid');
    grid.innerHTML = '';
    if (!data.items.length) {
      grid.innerHTML = '<p class="muted">No datasets found.</p>';
    }
    data.items.forEach(d => {
      const el = document.createElement('div');
      el.className = 'dataset-card';
      el.innerHTML = `
        <div class="dataset-card-header">
          <span class="dataset-card-name">${d.name}</span>
          <span class="dataset-type-badge">${d.data_type || 'other'}</span>
        </div>
        <p class="dataset-card-desc">${d.description || 'No description'}</p>
        <div class="progress-bar"><div class="progress-fill" style="width:${d.completion_percentage}%"></div></div>
        <div class="dataset-meta">
          <span>◧ ${d.image_count} images</span>
          <span>◈ ${d.annotation_count} annotations</span>
          <span>◉ ${d.completion_percentage}%</span>
        </div>`;
      el.onclick = () => openDatasetDetail(d);
      grid.appendChild(el);
    });

    // Pagination
    const pg = $('datasets-pagination');
    pg.innerHTML = '';
    for (let i = 1; i <= data.pages; i++) {
      const btn = document.createElement('button');
      btn.className = 'page-btn' + (i === data.current_page ? ' active' : '');
      btn.textContent = i;
      btn.onclick = () => loadDatasets(i);
      pg.appendChild(btn);
    }
  }

  // Filters
  ['dataset-search','filter-type','filter-status'].forEach(id => {
    $(id).addEventListener('input', () => loadDatasets(1));
    $(id).addEventListener('change', () => loadDatasets(1));
  });

  $('new-dataset-btn').onclick = () => showNewDatasetModal();

  function showNewDatasetModal() {
    showModal(`
      <h2>New Dataset</h2>
      <div class="field-group"><label>Name</label><input id="m-name" type="text" placeholder="Sentinel-2 Europe 2023"/></div>
      <div class="field-group"><label>Description</label><input id="m-desc" type="text" placeholder="Optional description"/></div>
      <div class="field-group"><label>Data Type</label>
        <select id="m-type" class="select-input">
          <option value="sentinel_optical">Sentinel Optical</option>
          <option value="sentinel_sar">Sentinel SAR</option>
          <option value="climate_simulation">Climate Simulation</option>
          <option value="multispectral">Multispectral</option>
          <option value="other">Other</option>
        </select>
      </div>
      <button class="btn-primary full-width" id="m-create-btn" style="margin-top:20px">Create Dataset</button>
    `);
    $('m-create-btn').onclick = async () => {
      try {
        await Api.createDataset({
          name: $('m-name').value,
          description: $('m-desc').value,
          data_type: $('m-type').value,
        });
        closeModal();
        toast('Dataset created!', 'success');
        loadDatasets();
      } catch (err) { toast(err.message, 'error'); }
    };
  }

  function openDatasetDetail(dataset) {
    showModal(`
      <h2>${dataset.name}</h2>
      <p style="color:var(--text-2);margin-bottom:18px">${dataset.description || ''}</p>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:20px">
        <div class="stat-card"><span class="stat-label">Images</span><span class="stat-value" style="font-size:20px">${dataset.image_count}</span></div>
        <div class="stat-card"><span class="stat-label">Annotations</span><span class="stat-value" style="font-size:20px">${dataset.annotation_count}</span></div>
      </div>
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        <button class="btn-primary" id="d-open-annotate">Open in Studio</button>
        <button class="btn-secondary" id="d-upload-imgs">Upload Images</button>
        <button class="btn-ghost" id="d-delete" style="color:var(--red)">Delete</button>
      </div>
      <div id="d-upload-area" style="display:none;margin-top:16px">
        <input type="file" id="d-file-input" multiple accept=".png,.jpg,.jpeg,.tif,.tiff,.nc,.h5"/>
        <button class="btn-secondary" id="d-do-upload" style="margin-top:8px">Upload Selected</button>
      </div>
    `);
    $('d-open-annotate').onclick = () => { closeModal(); loadAnnotateForDataset(dataset); setView('annotate'); };
    $('d-upload-imgs').onclick = () => $('d-upload-area').style.display = 'block';
    $('d-do-upload').onclick = async () => {
      const files = $('d-file-input').files;
      if (!files.length) return;
      const fd = new FormData();
      Array.from(files).forEach(f => fd.append('file', f));
      try {
        const res = await Api.uploadImages(dataset.id, fd);
        toast(`Uploaded ${res.uploaded.length} image(s)`, 'success');
        closeModal();
        loadDatasets();
      } catch (err) { toast(err.message, 'error'); }
    };
    $('d-delete').onclick = async () => {
      if (!confirm(`Delete dataset "${dataset.name}"? This cannot be undone.`)) return;
      try {
        await Api.deleteDataset(dataset.id);
        toast('Dataset deleted', 'success');
        closeModal();
        loadDatasets();
      } catch (err) { toast(err.message, 'error'); }
    };
  }

  /* ── ANNOTATION STUDIO ─────────────────────────────── */
  let currentDataset = null;
  let currentImages  = [];
  let currentImage   = null;
  let currentLabelClasses = [];
  let pendingAnnotations = [];

  // Init canvas
  Canvas.init(
    $('annotation-canvas'),
    $('canvas-wrapper'),
    (anns) => { pendingAnnotations = anns; updateAnnList(); }
  );

  // Tool buttons
  document.querySelectorAll('.tool-btn').forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      Canvas.setTool(btn.dataset.tool);
    };
  });

  async function loadAnnotateDatasets() {
    const sel = $('annotate-dataset-select');
    sel.innerHTML = '<option value="">— select dataset —</option>';
    try {
      const data = await Api.getDatasets({ per_page: 100 });
      data.items.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d.id; opt.textContent = d.name;
        sel.appendChild(opt);
      });
    } catch {}
  }

  $('annotate-dataset-select').onchange = async function() {
    const id = +this.value;
    if (!id) return;
    try {
      currentDataset = await Api.getDataset(id);
      loadAnnotateForDataset(currentDataset);
    } catch (err) { toast(err.message, 'error'); }
  };

  async function loadAnnotateForDataset(dataset) {
    currentDataset = dataset;
    $('annotate-dataset-name').textContent = dataset.name;

    // Sync select
    const sel = $('annotate-dataset-select');
    sel.value = dataset.id;

    // Load label classes
    currentLabelClasses = dataset.label_schema?.classes || [
      { id: 'cls1', name: 'Object',  color: '#00c2ff' },
      { id: 'cls2', name: 'Cloud',   color: '#f0c040' },
      { id: 'cls3', name: 'Water',   color: '#2ecc8f' },
      { id: 'cls4', name: 'Anomaly', color: '#e05252' },
    ];
    renderLabelClasses();

    // Load images
    try {
      const data = await Api.getImages(dataset.id, { per_page: 50 });
      currentImages = data.items;
      renderImageStrip();
    } catch (err) { toast(err.message, 'error'); }
  }

  function renderLabelClasses() {
    const container = $('label-classes');
    container.innerHTML = '';
    currentLabelClasses.forEach((cls, i) => {
      const btn = document.createElement('div');
      btn.className = 'label-class-btn' + (i === 0 ? ' active' : '');
      btn.innerHTML = `<span class="label-dot" style="background:${cls.color}"></span>${cls.name}`;
      btn.onclick = () => {
        document.querySelectorAll('.label-class-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        Canvas.setActiveLabel({ name: cls.name, color: cls.color });
      };
      container.appendChild(btn);
    });
    if (currentLabelClasses.length > 0) {
      Canvas.setActiveLabel({ name: currentLabelClasses[0].name, color: currentLabelClasses[0].color });
    }
  }

  function renderImageStrip() {
    const strip = $('image-strip');
    strip.innerHTML = '';
    if (!currentImages.length) {
      strip.innerHTML = '<p class="strip-placeholder">No images in dataset</p>';
      return;
    }
    currentImages.forEach(img => {
      const thumb = document.createElement('div');
      thumb.className = 'strip-thumb' + (currentImage?.id === img.id ? ' active' : '');
      thumb.dataset.id = img.id;
      if (img.is_annotated) {
        thumb.innerHTML = '<div class="annotated-dot"></div>';
      }
      const el = document.createElement('img');
      el.src = Api.thumbnailUrl(img.id);
      el.onerror = () => { el.style.display = 'none'; };
      thumb.appendChild(el);
      thumb.onclick = () => selectImage(img);
      strip.appendChild(thumb);
    });
  }

  async function selectImage(img) {
    // Unlock previous
    if (currentImage) { try { await Api.unlockImage(currentImage.id); } catch {} }

    currentImage = img;
    document.querySelectorAll('.strip-thumb').forEach(t => {
      t.classList.toggle('active', +t.dataset.id === img.id);
    });

    // Lock current
    try { await Api.lockImage(img.id); } catch {}

    // Load into canvas
    await Canvas.loadImage(Api.imageFileUrl(img.id));
    Canvas.fitToWrapper();

    // Load existing annotations
    try {
      const data = await Api.getAnnotations(img.id);
      const anns = data.items || [];
      Canvas.setAnnotations(anns);
      pendingAnnotations = Canvas.getAnnotations();
      updateAnnList();
    } catch {}
  }

  function updateAnnList() {
    const anns = Canvas.getAnnotations();
    $('ann-count').textContent = anns.length;
    const list = $('annotation-list');
    list.innerHTML = '';
    anns.forEach(ann => {
      const el = document.createElement('div');
      el.className = 'ann-item';
      el.dataset.id = ann.id;
      el.innerHTML = `
        <span class="label-dot" style="background:${ann.color || '#00c2ff'}"></span>
        <span class="ann-label">${ann.label} (${ann.type})</span>
        <span class="ann-delete" data-id="${ann.id}">✕</span>`;
      el.onclick = () => Canvas.selectAnnotation(ann.id);
      el.querySelector('.ann-delete').onclick = e => {
        e.stopPropagation();
        if (ann._serverId) Api.deleteAnnotation(ann._serverId).catch(() => {});
        Canvas.removeAnnotation(ann.id);
      };
      list.appendChild(el);
    });
  }

  $('save-annotations-btn').onclick = async () => {
    if (!currentImage) return toast('Select an image first', 'error');
    const anns = Canvas.getAnnotations().filter(a => !a._serverId);
    if (!anns.length) return toast('No new annotations to save', 'info');

    try {
      const payload = {
        annotations: anns.map(a => ({
          annotation_type: a.type,
          label: a.label,
          geometry: a.geometry,
          confidence: a.confidence || 1.0,
          attributes: {},
        })),
      };
      await Api.bulkCreateAnnotations(currentImage.id, payload);
      toast(`Saved ${anns.length} annotation(s)`, 'success');
      // Reload to get server IDs
      const data = await Api.getAnnotations(currentImage.id);
      Canvas.setAnnotations(data.items || []);
      pendingAnnotations = Canvas.getAnnotations();
      updateAnnList();
      // Refresh strip dot
      renderImageStrip();
    } catch (err) { toast(err.message, 'error'); }
  };

  $('clear-annotations-btn').onclick = () => {
    if (!confirm('Clear all annotations from canvas? Saved annotations will remain.')) return;
    Canvas.clearAnnotations();
    updateAnnList();
  };

  $('ai-suggest-btn').onclick = async () => {
    if (!currentImage) return toast('Select an image first', 'error');
    try {
      const res = await Api.aiSuggest(currentImage.id);
      toast(`AI task queued (${res.task_id})`, 'success');
      // Poll for result
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        if (attempts > 20) { clearInterval(poll); return; }
        try {
          const status = await Api.get(`/images/task/${res.task_id}/status`);
          if (status.status === 'SUCCESS') {
            clearInterval(poll);
            toast(`AI created ${status.result?.annotations_created} annotations`, 'success');
            const data = await Api.getAnnotations(currentImage.id);
            Canvas.setAnnotations(data.items || []);
            pendingAnnotations = Canvas.getAnnotations();
            updateAnnList();
          }
        } catch {}
      }, 2000);
    } catch (err) { toast(err.message, 'error'); }
  };

  /* ── REVIEW VIEW ───────────────────────────────────── */
  async function loadReviewQueue() {
    const list = $('review-list');
    list.innerHTML = '<p class="muted">Loading…</p>';
    try {
      const data = await Api.getDatasets({ per_page: 100 });
      const items = [];
      for (const ds of data.items.slice(0, 5)) {
        const imgs = await Api.getImages(ds.id, { per_page: 20 });
        for (const img of imgs.items) {
          const anns = await Api.getAnnotations(img.id, { status: 'pending' });
          anns.items.forEach(a => items.push({ ann: a, img, ds }));
        }
      }

      list.innerHTML = '';
      if (!items.length) {
        list.innerHTML = '<p class="muted">No pending annotations for review.</p>';
        return;
      }

      items.slice(0, 30).forEach(({ ann, img, ds }) => {
        const card = document.createElement('div');
        card.className = 'review-card';
        card.innerHTML = `
          <div class="review-card-info">
            <h3>${ann.label} <small style="font-weight:400;color:var(--text-2)">(${ann.annotation_type})</small></h3>
            <p>Dataset: ${ds.name} · Image: ${img.original_filename || img.filename} · Confidence: ${(ann.confidence * 100).toFixed(0)}%</p>
          </div>
          <div class="review-actions">
            <button class="btn-approve" data-id="${ann.id}">✓ Approve</button>
            <button class="btn-reject"  data-id="${ann.id}">✕ Reject</button>
          </div>`;
        card.querySelector('.btn-approve').onclick = async () => {
          try {
            await Api.reviewAnnotation(ann.id, { status: 'approved' });
            card.remove(); toast('Approved', 'success');
          } catch (err) { toast(err.message, 'error'); }
        };
        card.querySelector('.btn-reject').onclick = async () => {
          const comment = prompt('Reason for rejection (optional):') || '';
          try {
            await Api.reviewAnnotation(ann.id, { status: 'rejected', comment });
            card.remove(); toast('Rejected', 'info');
          } catch (err) { toast(err.message, 'error'); }
        };
        list.appendChild(card);
      });
    } catch (err) {
      list.innerHTML = `<p class="muted">Error: ${err.message}</p>`;
    }
  }

  /* ── EXPORT VIEW ───────────────────────────────────── */
  async function loadExportDatasets() {
    const sel = $('export-dataset-select');
    sel.innerHTML = '<option value="">— select dataset —</option>';
    try {
      const data = await Api.getDatasets({ per_page: 100 });
      data.items.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d.id; opt.textContent = d.name;
        sel.appendChild(opt);
      });
    } catch {}
  }

  $('export-btn').onclick = async () => {
    const dsId = $('export-dataset-select').value;
    if (!dsId) return toast('Select a dataset', 'error');
    const fmt = qs('[name="export-format"]:checked')?.value || 'coco';
    try {
      const result = await Api.exportDataset(+dsId, fmt);
      const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href = url; a.download = `dataset_${dsId}_${fmt}.json`; a.click();
      URL.revokeObjectURL(url);
      $('export-result').innerHTML = `<span style="color:var(--green)">✓ Exported as ${fmt.toUpperCase()}</span>`;
    } catch (err) { toast(err.message, 'error'); }
  };

  /* ── GLOBE CANVAS (decorative) ─────────────────────── */
  function drawGlobe() {
    const c = $('globe-canvas');
    if (!c) return;
    c.width  = c.parentElement.clientWidth;
    c.height = c.parentElement.clientHeight;
    const ctx = c.getContext('2d');
    const cx = c.width * 0.75, cy = c.height * 0.5, r = Math.min(c.width, c.height) * 0.35;
    const t0 = Date.now();

    function frame() {
      ctx.clearRect(0, 0, c.width, c.height);
      const t = (Date.now() - t0) / 6000;

      // Globe outline
      ctx.strokeStyle = 'rgba(0,194,255,0.3)';
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI*2); ctx.stroke();

      // Latitude lines
      for (let lat = -60; lat <= 60; lat += 30) {
        const y = cy + r * Math.sin(lat * Math.PI/180);
        const rr = r * Math.cos(lat * Math.PI/180);
        ctx.beginPath(); ctx.ellipse(cx, y, rr, rr*0.15, 0, 0, Math.PI*2);
        ctx.strokeStyle = 'rgba(0,194,255,0.12)'; ctx.stroke();
      }

      // Longitude lines (rotating)
      for (let i = 0; i < 6; i++) {
        const angle = (i / 6) * Math.PI + t * Math.PI * 2;
        ctx.beginPath();
        ctx.ellipse(cx, cy, r * Math.abs(Math.cos(angle)), r, Math.PI/2, 0, Math.PI*2);
        ctx.strokeStyle = 'rgba(0,194,255,0.10)'; ctx.stroke();
      }

      // Dots (satellite orbits)
      for (let i = 0; i < 5; i++) {
        const angle = (i / 5) * Math.PI * 2 + t * Math.PI * 2 * (i % 2 === 0 ? 1 : -1.3);
        const ox = cx + r * 1.15 * Math.cos(angle);
        const oy = cy + r * 0.4  * Math.sin(angle);
        ctx.beginPath(); ctx.arc(ox, oy, 3, 0, Math.PI*2);
        ctx.fillStyle = 'rgba(0,194,255,0.6)'; ctx.fill();
      }

      requestAnimationFrame(frame);
    }
    frame();
  }
  drawGlobe();

  /* ── BOOT ──────────────────────────────────────────── */
  await boot();

})();
