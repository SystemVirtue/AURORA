/* AURORA UX-MVP layer: application shell + layered cognitive workspace. */
(() => {
  const byHeading = (needle) => [...document.querySelectorAll('body > section')].find(s => (s.querySelector('h2')?.textContent || '').toLowerCase().includes(needle));
  const make = (tag, cls, text) => { const el = document.createElement(tag); if (cls) el.className = cls; if (text != null) el.textContent = text; return el; };

  function injectStyle() {
    const style = document.createElement('style');
    style.textContent = `
      :root{--bg:#0b0f14;--panel:#111821;--panel2:#151e29;--line:#273342;--text:#e7edf4;--muted:#8d9aaa;--accent:#8fb7d9;--good:#79c7a3;--warn:#d8b36b;--bad:#d98b8b;--radius:10px}
      html,body{background:var(--bg)!important;color:var(--text)!important}body{max-width:none!important;margin:0!important;padding:0!important;font-size:14px}body>header{display:none}
      .aurora-shell{min-height:100vh;display:grid;grid-template-columns:218px minmax(0,1fr);grid-template-rows:auto 1fr}
      .aurora-rail{grid-row:1/3;background:#080c11;border-right:1px solid var(--line);padding:18px 12px;position:sticky;top:0;height:100vh}
      .aurora-brand{font-weight:750;letter-spacing:.12em;font-size:18px;padding:4px 10px}.aurora-sub{font-size:10px;color:var(--muted);padding:4px 10px 18px;text-transform:uppercase;letter-spacing:.12em}
      .aurora-nav{display:grid;gap:3px}.aurora-nav button{background:transparent!important;color:#aeb9c6!important;text-align:left;border:0;padding:10px 11px;border-radius:7px;font-size:13px}.aurora-nav button:hover,.aurora-nav button.active{background:#17202b!important;color:#fff!important}
      .aurora-top{border-bottom:1px solid var(--line);background:#0d131a;display:flex;align-items:center;justify-content:space-between;padding:10px 22px;gap:14px;position:sticky;top:0;z-index:5}.aurora-context{display:flex;align-items:center;gap:10px;min-width:0}.aurora-context strong{font-size:13px}.aurora-context span{color:var(--muted);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.aurora-askbar{display:flex;gap:7px;max-width:620px;width:100%}.aurora-askbar input{margin:0!important;background:#111a23!important;color:var(--text)!important;border-color:var(--line)!important}.aurora-askbar button{background:#dce9f4!important;color:#10161d!important;font-weight:650}
      .aurora-main{padding:24px;max-width:1450px;width:100%;margin:0 auto}.aurora-view{display:none}.aurora-view.active{display:block}.aurora-view>section{margin-top:0!important;margin-bottom:14px}.aurora-view>.grid{margin-bottom:14px}
      .aurora-hero{margin-bottom:18px}.aurora-kicker{color:var(--accent);font-size:11px;text-transform:uppercase;letter-spacing:.12em}.aurora-hero h1{font-size:28px;margin:4px 0}.aurora-hero p{color:var(--muted);margin:0;max-width:780px}
      .aurora-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:16px 0}.aurora-stat{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:14px}.aurora-stat b{display:block;font-size:20px;margin-top:4px}.aurora-stat span{font-size:11px;color:var(--muted)}
      .aurora-next{background:linear-gradient(135deg,#121c27,#10161d);border:1px solid #334252;border-radius:var(--radius);padding:18px;margin-bottom:14px}.aurora-next h3{margin:0 0 5px}.aurora-next p{color:var(--muted);margin:0 0 12px}.aurora-next button{margin-right:6px}
      .card{background:var(--panel)!important;border-color:var(--line)!important;border-radius:var(--radius)!important;box-shadow:none!important}.card h2{color:#f2f6fa}.card h3{color:#dce5ed}.muted{color:var(--muted)!important}input,textarea,select{background:#0d141c!important;color:var(--text)!important;border-color:#33404f!important;border-radius:7px!important}button{background:#dce9f4;color:#10161d}button.secondary{background:#202a35!important;color:#dce5ed!important}.item,.claim,.contributor{border-color:var(--line)!important;background:#0d141c}.node{background:#0d141c;border-color:var(--line);color:var(--text)}pre{background:#090e14;color:#b9c7d5;border-color:var(--line)}hr{border-color:var(--line)}.metric,.badge{background:#1c2732;color:#c9d4df}.quorum{border-left-color:var(--accent)}
      .aurora-layer{border-top:1px solid var(--line);margin-top:14px;padding-top:14px}.aurora-layer summary{cursor:pointer;color:#cbd6e1;font-weight:600}.aurora-layer .layer-body{padding-top:10px}
      .aurora-view[data-view="think"] .card{margin-top:0}.aurora-view[data-view="think"]>section:nth-of-type(3){border-left:3px solid var(--accent)}
      .aurora-empty{border:1px dashed var(--line);border-radius:var(--radius);padding:24px;color:var(--muted)}
      @media(max-width:900px){.aurora-shell{grid-template-columns:1fr}.aurora-rail{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line);padding:10px}.aurora-sub{display:none}.aurora-nav{display:flex;overflow:auto}.aurora-nav button{white-space:nowrap}.aurora-top{position:static}.aurora-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.aurora-main{padding:14px}}
      @media(max-width:600px){.aurora-grid{grid-template-columns:1fr 1fr}.aurora-askbar{display:none}.aurora-main{padding:10px}.aurora-hero h1{font-size:23px}}
    `;
    document.head.appendChild(style);
  }

  function createShell() {
    const original = [...document.body.children].filter(el => el.tagName === 'SECTION');
    const identity = byHeading('identity & workspace');
    const investigateAsk = [...document.querySelectorAll('body > section')].find(s => (s.querySelector('h2')?.textContent || '').includes('Investigate — ingest evidence'));
    const answer = byHeading('answer');
    const trace = [...document.querySelectorAll('body > section')].find(s => (s.textContent || '').includes('Reasoning trace') && (s.textContent || '').includes('Epistemic status'));
    const quorum = byHeading('quorum deliberation');
    const evidence = byHeading('retrieved evidence');
    const claims = byHeading('claims, belief revision & provenance');
    const actions = byHeading('goals, tasks & decisions');
    const imports = byHeading('conversation import');
    const continuity = byHeading('continuity / machine reincarnation');
    const appScript = [...document.scripts].find(s => s.src.endsWith('/ux.js'));

    const shell = make('div','aurora-shell');
    const rail = make('aside','aurora-rail');
    rail.innerHTML = `<div class="aurora-brand">AURORA</div><div class="aurora-sub">Transparent cognition</div><nav class="aurora-nav" aria-label="Primary navigation"></nav>`;
    const nav = rail.querySelector('nav');
    const top = make('header','aurora-top');
    top.innerHTML = `<div class="aurora-context"><strong id="aurora-view-title">HOME</strong><span id="aurora-context-status">Cognitive workspace</span></div><div class="aurora-askbar"><input id="aurora-global-question" placeholder="Ask AURORA…"><button type="button" id="aurora-global-ask">Think</button></div>`;
    const main = make('main','aurora-main');
    const views = {};
    const view = (key, title, subtitle) => { const v=make('div','aurora-view'); v.dataset.view=key; v.id=`aurora-view-${key}`; const hero=make('div','aurora-hero'); hero.innerHTML=`<div class="aurora-kicker">AURORA / ${title}</div><h1>${title}</h1><p>${subtitle}</p>`; v.appendChild(hero); views[key]=v; main.appendChild(v); return v; };

    const home=view('home','Home','A cognitive cockpit for current work, conclusions, uncertainty and next actions.');
    const think=view('think','Think','Ask a question, inspect its context, see the epistemic warrant, compare reasoning and follow the evidence.');
    const knowledge=view('knowledge','Knowledge','Explore claims, evidence and belief revision without collapsing uncertainty into certainty.');
    const provenance=view('provenance','Provenance','Trace a claim through evidence, source, reasoning contributions and synthesis.');
    const action=view('action','Action','Turn cognition into goals, tasks and recorded decisions.');
    const io=view('io','Data IO','Bring knowledge into AURORA and carry authoritative cognitive state back out.');
    const system=view('system','System','Authentication, workspace selection, connection state and model access controls.');

    const items=[['home','Home'],['think','Think'],['knowledge','Knowledge'],['provenance','Provenance'],['action','Action'],['io','Data IO'],['system','System']];
    items.forEach(([key,label])=>{const b=make('button','',label);b.type='button';b.dataset.view=key;b.onclick=()=>activate(key);nav.appendChild(b);});

    // Preserve the existing working controls by relocating, not rewriting, them.
    if (investigateAsk) think.appendChild(investigateAsk);
    if (answer) think.appendChild(answer);
    if (trace) think.appendChild(trace);
    if (quorum) think.appendChild(quorum);
    if (evidence) think.appendChild(evidence);
    if (claims) { knowledge.appendChild(claims); provenance.appendChild(claims.cloneNode(false)); }
    if (actions) action.appendChild(actions);
    if (imports) io.appendChild(imports);
    if (continuity) io.appendChild(continuity);
    if (identity) system.appendChild(identity);

    const stats=make('div','aurora-grid');
    stats.innerHTML='<div class="aurora-stat"><span>Latest reasoning</span><b id="home-answer-state">—</b></div><div class="aurora-stat"><span>Epistemic state</span><b id="home-epistemic-state">Waiting</b></div><div class="aurora-stat"><span>Evidence retrieved</span><b id="home-evidence-count">0</b></div><div class="aurora-stat"><span>Open contradictions</span><b id="home-contradiction-state">Unknown</b></div>';
    home.appendChild(stats);
    const next=make('div','aurora-next'); next.innerHTML='<h3>Recommended next move</h3><p id="home-next-text">Start by selecting a workspace, importing evidence, or asking AURORA a question.</p><button type="button" data-go="think">Ask AURORA</button><button type="button" class="secondary" data-go="io">Import evidence</button><button type="button" class="secondary" data-go="knowledge">Inspect knowledge</button>';home.appendChild(next);
    next.querySelectorAll('[data-go]').forEach(b=>b.onclick=()=>activate(b.dataset.go));
    home.appendChild(make('div','aurora-empty','The Home view is intentionally a summary layer. Detailed cognitive state remains one click deeper.'));

    main.querySelectorAll(':scope > .aurora-view').forEach(v=>v.hidden=false);
    shell.appendChild(rail); shell.appendChild(top); shell.appendChild(main);
    document.body.innerHTML=''; document.body.appendChild(shell);

    function activate(key){
      Object.values(views).forEach(v=>v.classList.toggle('active',v.dataset.view===key));
      nav.querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.dataset.view===key));
      const title=items.find(x=>x[0]===key)?.[1]||key.toUpperCase();
      document.getElementById('aurora-view-title').textContent=title.toUpperCase();
      document.getElementById('aurora-context-status').textContent=key==='think'?'Question → evidence → reasoning → answer':'Transparent cognitive workspace';
      history.replaceState(null,'',`#${key}`);
    }

    const globalInput=document.getElementById('aurora-global-question');
    document.getElementById('aurora-global-ask').onclick=()=>{const q=globalInput.value.trim();if(!q)return;const target=document.getElementById('question');if(target){target.value=q;activate('think');if(typeof window.ask==='function')window.ask();}};
    globalInput.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();document.getElementById('aurora-global-ask').click();}});
    activate(location.hash.slice(1) || 'home');
    if(appScript) appScript.dataset.uxMounted='true';

    // Live summary: read only from existing rendered AURORA outputs; never invent state.
    setInterval(()=>{
      const answerText=document.getElementById('answer')?.textContent?.trim()||'';
      document.getElementById('home-answer-state').textContent=answerText && !answerText.startsWith('No reasoning') ? (answerText.length>58?answerText.slice(0,58)+'…':answerText) : '—';
      const epi=document.getElementById('epistemic')?.textContent?.trim()||'Waiting'; document.getElementById('home-epistemic-state').textContent=epi.length>28?epi.slice(0,28)+'…':epi;
      const ev=document.querySelectorAll('#evidence article').length;document.getElementById('home-evidence-count').textContent=String(ev);
      const claimsText=document.getElementById('claims')?.textContent||'';document.getElementById('home-contradiction-state').textContent=claimsText.includes('No competing')?'0':claimsText.includes('Scanning')?'Scanning':'Review';
      const nextText=document.getElementById('home-next-text'); if(answerText && !answerText.startsWith('No reasoning')) nextText.textContent='A reasoning run exists. Inspect the epistemic status and retrieved evidence, then open provenance if you need to audit the chain.';
    },1200);
  }

  document.addEventListener('DOMContentLoaded',()=>{injectStyle();createShell();});
})();
