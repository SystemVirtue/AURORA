/* AURORA Dashboard: workspace overview, global connection status and destructive account/workspace controls. */
(() => {
  const $ = id => document.getElementById(id);
  const esc = v => String(v ?? '').replace(/[&<>\"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
  const token = () => typeof window.token === 'function' ? window.token() : '';
  const api = (path, init={}) => window.api(path, init);
  function addStyle(){
    const s=document.createElement('style');s.textContent=`
      .aurora-statusbar{grid-column:1/-1;display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:8px 22px;background:#111821;border-bottom:1px solid #273342;font-size:12px;position:sticky;top:0;z-index:6}.aurora-statusbar .seg{display:flex;align-items:center;gap:7px}.aurora-statusbar .sep{color:#536171}.aurora-statusbar .profile-chip{cursor:pointer}.aurora-statusbar .profile-icon{width:22px;height:22px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;background:#273342;color:#dce9f4;font-size:11px;font-weight:700}.conn-edit{padding:4px 8px!important;font-size:11px}.conn-good{color:#72d39b}.conn-bad{color:#ff9a9a}.conn-neutral{color:#b7c2ce}.workspace-picker{position:relative}.workspace-picker select{margin:0!important;width:auto;min-width:230px;padding:5px 30px 5px 8px!important}.dashboard-workspace{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:0 0 18px}.dashboard-workspace h2{font-size:24px;margin:0}.dashboard-workspace select{width:auto;min-width:280px;margin:0}.danger-card{border:1px solid #7b3434!important;background:#170f11!important}.danger-card h2{color:#ffb0b0}.danger-actions{display:flex;gap:8px;flex-wrap:wrap}.danger-actions button{background:#8f3030!important;color:#fff!important}.aurora-confirm-backdrop{position:fixed;inset:0;z-index:11000;background:#000b;display:flex;align-items:center;justify-content:center;padding:20px}.aurora-confirm{width:min(500px,100%);background:#111821;border:1px solid #7b3434;border-radius:12px;padding:22px;box-shadow:0 20px 80px #0008}.aurora-confirm h2{margin-top:0}.aurora-confirm input{margin:8px 0 12px}.aurora-confirm .confirm-actions{display:flex;justify-content:flex-end;gap:8px}.aurora-confirm .confirm-delete{background:#a33!important;color:#fff!important}.dashboard-summary{margin-bottom:16px}
    `;document.head.appendChild(s);
  }
  function findView(key){return document.querySelector(`.aurora-view[data-view="${key}"]`)}
  function profileButton(){return [...document.querySelectorAll('.aurora-nav button')].find(b=>(b.textContent||'').trim().toLowerCase()==='profile')}
  function goProfile(){profileButton()?.click()}
  function statusLabel(ok, unavailable='Disconnected'){return ok===true?'Connected':ok===false?unavailable:'Checking…'}
  async function refreshConnections(){
    if(!token()) return;
    try{
      const d=await api('/v1/profile/connections');
      const or=d.openrouter?.status||'No API Key Available', pu=d.puter?.status||'No Account Linked';
      const o=$('connOpenRouter'),p=$('connPuter'); if(o){o.textContent=or;o.className=`${or==='Connected'?'conn-good':or.includes('Invalid')||or==='Disconnected'?'conn-bad':'conn-neutral'}`}; if(p){p.textContent=pu;p.className=`${pu==='Connected'?'conn-good':pu.includes('Invalid')||pu==='Disconnected'?'conn-bad':'conn-neutral'}`};
    }catch(e){if($('connOpenRouter'))$('connOpenRouter').textContent='Disconnected';if($('connPuter'))$('connPuter').textContent='Disconnected';}
  }
  function buildStatusBar(){
    if(document.querySelector('.aurora-statusbar'))return;
    const top=document.querySelector('.aurora-top'),shell=document.querySelector('.aurora-shell'); if(!top||!shell)return;
    const bar=document.createElement('div');bar.className='aurora-statusbar';bar.innerHTML=`<div class="seg profile-chip" id="statusProfile"><span class="profile-icon" id="profileIcon">?</span><span>PROFILE: <b id="statusEmail">Not signed in</b></span></div><span class="sep">|</span><div class="seg"><b>Workspace:</b><span id="statusWorkspace">—</span></div><span class="sep">|</span><div class="seg"><b>CONNECTIONS:</b><button class="conn-edit" id="connectionsEdit" type="button">EDIT</button></div><div class="seg">OPENROUTER <b id="connOpenRouter" class="conn-neutral">No API Key Available</b></div><div class="seg">PUTER <b id="connPuter" class="conn-neutral">No Account Linked</b></div>`;
    shell.insertBefore(bar,top);$('connectionsEdit').onclick=goProfile;$('statusProfile').onclick=goProfile;
  }
  function buildDashboard(){
    const home=findView('home');if(!home||home.dataset.dashboardBuilt)return;home.dataset.dashboardBuilt='true';
    const hero=home.querySelector('.aurora-hero');if(hero){const h=hero.querySelector('h1');if(h)h.textContent='Dashboard';const p=hero.querySelector('p');if(p)p.textContent='Workspace overview — current cognitive state, evidence, reasoning and activity.';const k=hero.querySelector('.aurora-kicker');if(k)k.textContent='AURORA / DASHBOARD';}
    const workspaceTitle=document.createElement('div');workspaceTitle.className='dashboard-workspace';workspaceTitle.innerHTML='<h2>WORKSPACE : <span id="dashboardWorkspaceName">—</span></h2><select id="dashboardWorkspaceSelect" aria-label="Select workspace"><option>Loading workspaces…</option></select>';
    home.insertBefore(workspaceTitle,home.querySelector('.aurora-grid'));
    const summary=document.createElement('div');summary.className='card dashboard-summary';summary.innerHTML='<h2>Current workspace overview</h2><div class="aurora-grid"><div class="aurora-stat"><span>Workspace</span><b id="dashWorkspaceCount">—</b></div><div class="aurora-stat"><span>Reasoning</span><b id="dashReasoning">—</b></div><div class="aurora-stat"><span>Evidence</span><b id="dashEvidence">—</b></div><div class="aurora-stat"><span>Knowledge</span><b id="dashClaims">—</b></div></div>';
    home.insertBefore(summary,home.querySelector('.aurora-grid'));
    const danger=document.createElement('section');danger.className='card danger-card';danger.innerHTML='<h2>DANGER</h2><p class="muted">These operations are irreversible. Workspace deletion removes its workspace data. Profile deletion removes the authenticated AURORA identity and associated user data.</p><div class="danger-actions"><button id="deleteWorkspaceBtn" type="button">DELETE WORKSPACE</button><button id="deleteProfileBtn" type="button">DELETE PROFILE</button></div><div id="dangerStatus" class="status muted"></div>';
    home.appendChild(danger);
    const select=$('dashboardWorkspaceSelect');select.onchange=()=>{if($('workspace'))$('workspace').value=select.value; if(typeof window.saveLocal==='function')window.saveLocal(); if(typeof window.loadWorkspaceState==='function')window.loadWorkspaceState(); refreshDashboard();};
    $('deleteWorkspaceBtn').onclick=()=>confirmAction('workspace');$('deleteProfileBtn').onclick=()=>confirmAction('profile');
    refreshDashboard();
  }
  async function refreshDashboard(){
    if(!token())return; const ws=typeof window.workspace==='function'?window.workspace():$('workspace')?.value||'';
    const select=$('dashboardWorkspaceSelect'); if(select){try{const d=await api('/v1/workspaces');const list=d.workspaces||[];select.innerHTML=list.length?'<option value="">Select workspace…</option>'+list.map(w=>`<option value="${esc(w.id)}">${esc(w.name)} · ${esc(w.role)}</option>`).join(''):'<option value="">No workspaces</option>';if(ws&&list.some(w=>w.id===ws))select.value=ws;else if(list[0]){select.value=list[0].id;if($('workspace'))$('workspace').value=list[0].id;}}catch{}}
    const currentName=select?.selectedOptions?.[0]?.textContent?.split(' · ')[0]||'—';if($('dashboardWorkspaceName'))$('dashboardWorkspaceName').textContent=currentName;if($('statusWorkspace'))$('statusWorkspace').textContent=currentName;
    if($('dashWorkspaceCount'))$('dashWorkspaceCount').textContent=currentName==='—'?'—':'Active';
    try{const [g,t,d,c]=await Promise.all([api(`/v1/goals?workspace_id=${encodeURIComponent(ws)}`),api(`/v1/tasks?workspace_id=${encodeURIComponent(ws)}`),api(`/v1/decisions?workspace_id=${encodeURIComponent(ws)}`),api(`/v1/claims/contradictions?workspace_id=${encodeURIComponent(ws)}`)]);if($('dashReasoning'))$('dashReasoning').textContent=(g.goals?.length||0)+(t.tasks?.length||0)+(d.decisions?.length||0);if($('dashEvidence'))$('dashEvidence').textContent='—';if($('dashClaims'))$('dashClaims').textContent=String(c.contradictions?.length||0);}catch{}
  }
  function confirmAction(kind){
    const isWs=kind==='workspace',name=$('dashboardWorkspaceName')?.textContent?.trim()||'',email=$('statusEmail')?.textContent?.trim()||'';if((isWs&&!name)||(!isWs&&!email)||!token()){return setStatus('dangerStatus','You must be signed in with an active workspace.',false)}
    const backdrop=document.createElement('div');backdrop.className='aurora-confirm-backdrop';const label=isWs?'workspace name':'email address';backdrop.innerHTML=`<div class="aurora-confirm" role="dialog" aria-modal="true"><h2>Confirm DELETE ${isWs?'WORKSPACE':'PROFILE'}</h2><p>This cannot be undone. Enter your ${label} exactly, then type <b>DELETE</b>.</p><label>${esc(label)}</label><input id="confirmIdentity" autocomplete="off"><label>Confirmation</label><input id="confirmWord" autocomplete="off" placeholder="DELETE"><div class="confirm-actions"><button id="confirmCancel" class="secondary">CANCEL</button><button id="confirmDelete" class="confirm-delete">DELETE</button></div><div id="confirmStatus" class="status muted"></div></div>`;document.body.appendChild(backdrop);
    $('confirmCancel').onclick=()=>backdrop.remove();$('confirmDelete').onclick=async()=>{if($('confirmIdentity').value.trim()!==(isWs?name:email)||$('confirmWord').value.trim()!=='DELETE'){return $('confirmStatus').textContent=`Enter the exact ${label} and DELETE.`}try{if(isWs){await api(`/v1/workspaces/${encodeURIComponent($('workspace').value.trim())}`,{method:'DELETE'});backdrop.remove();await window.loadWorkspaces?.();refreshDashboard();setStatus('dangerStatus','Workspace deleted.',true)}else{await api('/v1/profile',{method:'DELETE'});backdrop.remove();window.signOut?.();location.reload();}}catch(e){$('confirmStatus').textContent=e.message||'Delete failed.'}};
  }
  function setStatus(id,text,ok){if(window.setStatus)return window.setStatus(id,text,ok);const el=$(id);if(el)el.textContent=text}
  function syncProfileStatus(){
    const email=$('email')?.value?.trim()||'Not signed in';if($('statusEmail'))$('statusEmail').textContent=email;const initial=email&&email!=='Not signed in'?email.charAt(0).toUpperCase():'?';if($('profileIcon'))$('profileIcon').textContent=initial;
  }
  function boot(){if(!document.querySelector('.aurora-shell'))return setTimeout(boot,50);addStyle();buildStatusBar();buildDashboard();syncProfileStatus();refreshConnections();setInterval(()=>{syncProfileStatus();refreshConnections();refreshDashboard()},15000);}
  boot();
})();
