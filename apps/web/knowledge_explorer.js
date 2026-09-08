/* AURORA Knowledge Explorer enhancement: uses the real /v1/knowledge/search API. */
(() => {
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const ctx = () => ({
    workspace: localStorage.getItem('workspaceId') || document.getElementById('workspace')?.value,
    token: localStorage.getItem('accessToken') || document.getElementById('token')?.value
  });
  const activate = (key) => { location.hash = key; window.dispatchEvent(new HashChangeEvent('hashchange')); };
  async function search(box, results, inspector) {
    const {workspace, token} = ctx();
    if (!workspace || !token) { results.innerHTML = '<div class="aurora-empty">Sign in and select a workspace before exploring knowledge.</div>'; return; }
    const q = box.querySelector('[data-kq]').value.trim();
    const kind = box.querySelector('[data-kk]').value;
    results.textContent = 'Searching…';
    try {
      const url = `/v1/knowledge/search?workspace_id=${encodeURIComponent(workspace)}&q=${encodeURIComponent(q)}&kind=${encodeURIComponent(kind)}&limit=50`;
      const response = await fetch(url, {headers:{Authorization:`Bearer ${token}`}});
      if (!response.ok) throw new Error((await response.text()) || `HTTP ${response.status}`);
      const rows = await response.json();
      if (!rows.length) { results.innerHTML = '<div class="aurora-empty">No matching knowledge objects.</div>'; return; }
      results.innerHTML = '';
      rows.forEach(item => {
        const el = document.createElement('button');
        el.type = 'button'; el.className = 'knowledge-result';
        el.innerHTML = `<strong>${esc(item.title)}</strong><div class="knowledge-meta">${esc(item.type)}${item.status ? ` · <span class="status-chip">${esc(item.status)}</span>` : ''}${item.confidence != null ? ` · confidence ${Number(item.confidence).toFixed(2)}` : ''}</div>${item.excerpt ? `<div class="knowledge-meta">${esc(item.excerpt.slice(0,240))}</div>` : ''}`;
        el.onclick = () => {
          inspector.innerHTML = `<section class="aurora-layer"><div class="aurora-layer-body"><h3>${esc(item.title)}</h3><div class="knowledge-meta">${esc(item.type)} · ${esc(item.id)}</div>${item.status ? `<p><span class="status-chip">${esc(item.status)}</span></p>` : ''}${item.confidence != null ? `<p>Confidence: ${Number(item.confidence).toFixed(3)}</p>` : ''}${item.excerpt ? `<p>${esc(item.excerpt)}</p>` : ''}<button type="button" data-open-prov>Open provenance</button></div></section>`;
          inspector.querySelector('[data-open-prov]').onclick = () => {
            activate('provenance');
            const claim = document.getElementById('claim-id');
            if (claim && item.type === 'claim') claim.value = item.id;
            const load = document.querySelector('[data-action="load-provenance"]');
            if (load && item.type === 'claim') load.click();
          };
        };
        results.appendChild(el);
      });
    } catch (error) { results.innerHTML = `<div class="aurora-empty">Knowledge search failed: ${esc(error.message)}</div>`; }
  }
  function mount() {
    const view = document.getElementById('aurora-view-knowledge');
    if (!view || view.dataset.knowledgeMounted) return !!view;
    view.dataset.knowledgeMounted = 'true';
    const panel = document.createElement('section'); panel.className = 'card';
    panel.innerHTML = `<h2>Knowledge explorer</h2><p class="muted">Search actual claims and documents stored in the current workspace.</p><div class="knowledge-toolbar"><input data-kq placeholder="Search claims or documents…"><select data-kk><option value="all">All objects</option><option value="claims">Claims</option><option value="documents">Documents</option></select><button type="button" data-ks>Search</button></div><div class="knowledge-results" data-kr></div><div class="knowledge-inspector" data-ki></div>`;
    view.appendChild(panel);
    const results = panel.querySelector('[data-kr]'), inspector = panel.querySelector('[data-ki]');
    panel.querySelector('[data-ks]').onclick = () => search(panel, results, inspector);
    panel.querySelector('[data-kq]').onkeydown = e => { if (e.key === 'Enter') search(panel, results, inspector); };
    return true;
  }
  const wait = setInterval(() => { if (mount()) clearInterval(wait); }, 100);
})();
