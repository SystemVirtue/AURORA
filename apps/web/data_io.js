/* AURORA Data IO: one surface for ingestion, conversation import and continuity. */
(() => {
  function mount(){
    const view=document.getElementById('aurora-view-io'); if(!view||document.getElementById('aurora-io-overview')) return;
    const p=document.createElement('section'); p.id='aurora-io-overview'; p.className='card';
    p.innerHTML='<h2>Data IO pipeline</h2><p class="muted">AURORA treats imported material as evidence-bearing input and exported cognitive state as portable state. Derived indexes can be rebuilt.</p><div class="aurora-grid"><div class="aurora-stat"><span>1 · Ingest</span><b>Source</b></div><div class="aurora-stat"><span>2 · Process</span><b>Parse / chunk</b></div><div class="aurora-stat"><span>3 · Cognition</span><b>Claims / evidence</b></div><div class="aurora-stat"><span>4 · Preserve</span><b>Export / restore</b></div></div>';
    view.insertBefore(p,view.children[1]||null);
  }
  document.addEventListener('DOMContentLoaded',()=>setTimeout(mount,0)); window.AuroraDataIO={mount};
})();
