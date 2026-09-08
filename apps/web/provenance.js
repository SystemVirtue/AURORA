/* AURORA provenance explorer: renders persisted causal relationships from the API. */
(() => {
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const get = id => document.getElementById(id);
  async function load() {
    const claimId = get('aurora-provenance-claim')?.value.trim();
    const workspace = localStorage.getItem('workspaceId') || get('workspace')?.value;
    const token = localStorage.getItem('accessToken') || get('token')?.value;
    const out = get('aurora-provenance-results');
    if (!out) return;
    if (!claimId || !workspace || !token) { out.innerHTML = '<div class="aurora-empty">Select a claim and ensure a workspace is active.</div>'; return; }
    out.textContent = 'Loading provenance…';
    try {
      const r = await fetch(`/v1/provenance/claims/${encodeURIComponent(claimId)}?workspace_id=${encodeURIComponent(workspace)}`, {headers:{Authorization:`Bearer ${token}`}});
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      const nodes = data.graph?.nodes || [];
      const edges = data.graph?.edges || [];
      if (!nodes.length) { out.innerHTML = '<div class="aurora-empty">No persisted provenance relationships were returned.</div>'; return; }
      const byType = nodes.reduce((a,n) => ((a[n.type] ||= []).push(n), a), {});
      const order = ['CLAIM','EVIDENCE','SOURCE','EVENT','REASONING_RUN','MODEL_CONTRIBUTION'];
      out.innerHTML = `<div class="aurora-provenance-summary"><strong>${nodes.length} objects</strong> · <strong>${edges.length} relationships</strong></div>` + order.filter(t=>byType[t]?.length).map(t => `<details class="aurora-layer" open><summary>${esc(t.replaceAll('_',' '))} · ${byType[t].length}</summary><div class="aurora-layer-body">${byType[t].map(n => `<div class="knowledge-result"><strong>${esc(n.label || n.name || n.id)}</strong><div class="knowledge-meta">${esc(n.id)}${n.status ? ` · ${esc(n.status)}` : ''}${n.model ? ` · ${esc(n.provider || '')}/${esc(n.model)}` : ''}</div></div>`).join('')}</div></details>`).join('') + `<details class="aurora-layer"><summary>Persisted relationships</summary><div class="aurora-layer-body">${edges.map(e => `<div class="knowledge-meta">${esc(e.source)} → ${esc(e.target)} · ${esc(e.type || e.relation || 'related')}</div>`).join('')}</div></details>`;
    } catch (e) { out.innerHTML = `<div class="aurora-empty">Provenance load failed: ${esc(e.message)}</div>`; }
  }
  function mount() {
    const view = document.getElementById('aurora-view-provenance'); if (!view || get('aurora-provenance-panel')) return;
    const panel = document.createElement('section'); panel.id='aurora-provenance-panel'; panel.className='card';
    panel.innerHTML='<h2>Provenance explorer</h2><p class="muted">Traverse persisted claim provenance. A relationship is shown only when AURORA has recorded it.</p><div class="knowledge-toolbar"><input id="aurora-provenance-claim" placeholder="Claim ID"><button id="aurora-provenance-load" type="button">Trace claim</button></div><div id="aurora-provenance-results"></div>';
    view.appendChild(panel); get('aurora-provenance-load').onclick=load;
  }
  document.addEventListener('DOMContentLoaded', () => setTimeout(mount, 0));
  window.AuroraProvenance = {mount, load};
})();
