const $ = (id) => document.getElementById(id);
const state = { sessionId: localStorage.getItem('aurora.session_id') || '', importedPayload: null };

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}
function workspace() { return $('workspace').value.trim(); }
function token() { return $('token').value.trim(); }
function headers() { return { 'Content-Type': 'application/json', Authorization: `Bearer ${token()}` }; }
function setStatus(id, text, ok = null) { $(id).textContent = text; $(id).className = `status ${ok === true ? 'ok' : ok === false ? 'err' : 'muted'}`; }
async function api(path, init = {}) {
  const response = await fetch(path, { ...init, headers: { ...headers(), ...(init.headers || {}) } });
  let data = {}; try { data = await response.json(); } catch {}
  if (!response.ok) throw new Error(data.detail || response.statusText);
  return data;
}

function saveLocal() {
  localStorage.setItem('aurora.config.v2', JSON.stringify({
    supabaseUrl: $('supabaseUrl').value.trim(), publishableKey: $('publishableKey').value.trim(),
    workspaceId: workspace(), token: token(), refreshToken: $('refreshToken').value.trim()
  }));
  setStatus('authStatus', 'Connection settings saved locally.', true);
}
function loadLocal() {
  try {
    const x = JSON.parse(localStorage.getItem('aurora.config.v2') || '{}');
    for (const [id, value] of Object.entries({ supabaseUrl: x.supabaseUrl, publishableKey: x.publishableKey, workspace: x.workspaceId, token: x.token, refreshToken: x.refreshToken })) if (value) $(id).value = value;
  } catch {}
}
async function supabaseAuth(grant, body) {
  const base = $('supabaseUrl').value.trim().replace(/\/$/, '');
  const key = $('publishableKey').value.trim();
  if (!base || !key) throw new Error('Supabase URL and publishable key are required.');
  const r = await fetch(`${base}/auth/v1/token?grant_type=${grant}`, { method: 'POST', headers: { 'Content-Type': 'application/json', apikey: key }, body: JSON.stringify(body) });
  const d = await r.json(); if (!r.ok) throw new Error(d.msg || d.message || d.error_description || 'Authentication failed'); return d;
}
async function signIn() {
  setStatus('authStatus', 'Signing in…');
  try { const d = await supabaseAuth('password', { email: $('email').value.trim(), password: $('password').value }); $('token').value = d.access_token; $('refreshToken').value = d.refresh_token || ''; saveLocal(); setStatus('authStatus', `Signed in as ${esc($('email').value.trim())}.`, true); await loadWorkspaces(); }
  catch (e) { setStatus('authStatus', e.message, false); }
}
async function refreshSession() {
  try { const d = await supabaseAuth('refresh_token', { refresh_token: $('refreshToken').value.trim() }); $('token').value = d.access_token; $('refreshToken').value = d.refresh_token || $('refreshToken').value; saveLocal(); setStatus('authStatus', 'Session refreshed.', true); }
  catch (e) { setStatus('authStatus', `Refresh failed: ${e.message}`, false); }
}
function signOut() { $('token').value = ''; $('refreshToken').value = ''; state.sessionId = ''; localStorage.removeItem('aurora.session_id'); setStatus('authStatus', 'Signed out locally.'); }
async function health() { try { const d = await fetch('/health').then(r => r.json()); setStatus('connection', `${d.status} · ${d.service}`, true); } catch (e) { setStatus('connection', e.message, false); } }

async function loadWorkspaces() {
  if (!token()) return;
  try { const d = await api('/v1/workspaces'); $('workspaceList').innerHTML = (d.workspaces || []).map(w => `<option value="${esc(w.id)}">${esc(w.name)} · ${esc(w.role)}</option>`).join(''); if (!workspace() && d.workspaces?.[0]) $('workspace').value = d.workspaces[0].id; }
  catch (e) { setStatus('workspaceStatus', e.message, false); }
}
async function createWorkspace() {
  const name = $('workspaceName').value.trim(); if (!name) return setStatus('workspaceStatus', 'Workspace name is required.', false);
  try { const d = await api('/v1/workspaces', { method: 'POST', body: JSON.stringify({ name }) }); $('workspace').value = d.workspace_id; await loadWorkspaces(); setStatus('workspaceStatus', `Created ${d.name}.`, true); }
  catch (e) { setStatus('workspaceStatus', e.message, false); }
}
function chooseWorkspace() { $('workspace').value = $('workspaceList').value; saveLocal(); loadWorkspaceState(); }

async function ingest() {
  if (!workspace() || !$('docname').value.trim() || !$('doccontent').value.trim()) return setStatus('ingestStatus', 'Workspace, name and content are required.', false);
  setStatus('ingestStatus', 'Ingesting…');
  try { const d = await api('/v1/documents', { method: 'POST', body: JSON.stringify({ workspace_id: workspace(), name: $('docname').value.trim(), content: $('doccontent').value, mime_type: 'text/plain' }) }); setStatus('ingestStatus', `Ingested ${d.chunks} chunks and ${d.candidate_claims} candidate claims (unverified).`, true); await scanContradictions(); }
  catch (e) { setStatus('ingestStatus', e.message, false); }
}
function renderQuorum(q) {
  if (!q) return $('quorum').innerHTML = '<span class="muted">Single-model reasoning. No QUORUM escalation was warranted.</span>';
  const cs = q.contributors || [], fs = q.failed_contributors || [];
  $('quorum').innerHTML = `<div class="quorum"><p><b>Warrant:</b> ${esc(q.warrant)}</p><span class="metric">Agreement ${((q.agreement || 0) * 100).toFixed(1)}%</span><span class="metric">Evidence ${((q.evidence_coverage || 0) * 100).toFixed(1)}%</span><span class="metric">Collective gain ${(q.collective_gain || 0).toFixed(4)}</span><p><b>Contributors (${cs.length})</b></p>${cs.map(c => `<article class="contributor"><b>${esc(c.model)}</b> <span class="muted">${esc(c.provider)} · ${esc(c.latency_ms)} ms</span><p class="answer">${esc(c.response)}</p></article>`).join('')}${fs.length ? `<p><b>Failed:</b> ${fs.map(c => `${esc(c.model)} — ${esc(c.error)}`).join('; ')}</p>` : ''}<p><b>Disagreements:</b><br>${(q.disagreements || []).map(esc).join('<br>') || 'None detected by the current heuristic.'}</p><p><b>Synthesis:</b> ${esc(q.synthesis_model)} via ${esc(q.synthesis_provider)}</p></div>`;
}
async function ask() {
  if (!workspace() || !$('question').value.trim()) return setStatus('answer', 'Workspace and question are required.', false);
  $('answer').textContent = 'Investigating…';
  try {
    const body = { workspace_id: workspace(), question: $('question').value.trim(), model: $('model').value.trim() || null, mode: $('mode').value, session_id: state.sessionId || null };
    const d = await api('/v1/ask', { method: 'POST', body: JSON.stringify(body) }); state.sessionId = d.session_id; localStorage.setItem('aurora.session_id', state.sessionId);
    $('answer').textContent = d.answer; $('trace').textContent = JSON.stringify(d.trace, null, 2); renderQuorum(d.quorum);
    $('epistemic').innerHTML = d.warrant ? `<b>Warrant:</b> ${esc(d.warrant)}` : 'Evidence-backed path: no escalation warrant was required.';
    $('evidence').innerHTML = d.evidence?.length ? d.evidence.map((e, i) => `<article><b>[${i + 1}] ${esc(e.document)}</b> · chunk ${esc(e.chunk_index)} · ${esc(e.retrieval)} · score ${Number(e.score || 0).toFixed(3)}<p>${esc(e.content)}</p><small>Evidence ID: ${esc(e.evidence_id || 'none')}</small></article><hr>`).join('') : 'No matching evidence. AURORA recorded an epistemic gap.';
  } catch (e) { $('answer').textContent = `Error: ${e.message}`; }
}

async function scanContradictions() {
  if (!workspace()) return setStatus('claims', 'Select a workspace first.', false);
  $('claims').textContent = 'Scanning…';
  try { const d = await api(`/v1/claims/contradictions?workspace_id=${encodeURIComponent(workspace())}`); $('claims').innerHTML = d.contradictions?.length ? d.contradictions.map(c => `<div class="claim"><b>${esc(c.subject)}</b> — ${esc(c.predicate)}<br>${esc(c.object)} <b>vs</b> ${esc(c.opposing_object)}<br><small>${esc(c.claim_id)} ↔ ${esc(c.opposing_claim_id)}</small><div class="row"><button onclick="inspect('${c.claim_id}')">Provenance</button><select id="review-${c.claim_id}"><option value="supported">supported</option><option value="contested">contested</option><option value="rejected">rejected</option><option value="unverified">unverified</option></select><button class="secondary" onclick="reviewClaim('${c.claim_id}')">Apply review</button></div></div>`).join('') : 'No competing non-rejected assertions detected.'; }
  catch (e) { $('claims').textContent = `Error: ${e.message}`; }
}
async function reviewClaim(id) { try { const status = $(`review-${id}`).value; await api(`/v1/claims/${id}/review`, { method: 'POST', body: JSON.stringify({ workspace_id: workspace(), status, rationale: 'Reviewed in AURORA workspace.' }) }); setStatus('claims', 'Claim revision applied.', true); await scanContradictions(); } catch (e) { setStatus('claims', e.message, false); } }
async function inspect(id) { $('provenance').textContent = 'Loading provenance…'; try { const d = await api(`/v1/provenance/claims/${id}?workspace_id=${encodeURIComponent(workspace())}`); $('provenance').innerHTML = `<p><b>Claim:</b> ${esc(d.claim_id)}</p><div>${(d.nodes || []).map(n => `<span class="node"><b>${esc(n.type)}</b><br>${esc(n.label || n.id)}${n.provider ? `<br><small>${esc(n.provider)}</small>` : ''}</span>`).join('')}</div><h3>Relationships</h3><ul>${(d.edges || []).map(e => `<li>${esc(e.source)} → <b>${esc(e.relation)}</b> → ${esc(e.target)}</li>`).join('') || '<li>None</li>'}</ul>`; } catch (e) { $('provenance').textContent = e.message; } }

async function loadWorkspaceState() { await Promise.all([loadGoals(), loadTasks(), loadDecisions()]); }
async function loadGoals() { try { const d = await api(`/v1/goals?workspace_id=${encodeURIComponent(workspace())}`); $('goals').innerHTML = (d.goals || []).map(g => `<article class="item"><b>${esc(g.title)}</b><span class="badge">${esc(g.status)}</span><p>${esc(g.description || '')}</p><small>Priority ${g.priority}</small><button class="secondary" onclick="toggleGoal('${g.id}','${g.status}')">${g.status === 'completed' ? 'Reopen' : 'Complete'}</button></article>`).join('') || '<span class="muted">No goals yet.</span>'; } catch (e) { $('goals').textContent = e.message; } }
async function createGoal() { const title = $('goalTitle').value.trim(); if (!title) return; try { await api('/v1/goals', { method: 'POST', body: JSON.stringify({ workspace_id: workspace(), title, priority: Number($('goalPriority').value || 0) }) }); $('goalTitle').value = ''; await loadGoals(); } catch (e) { setStatus('actionStatus', e.message, false); } }
async function toggleGoal(id, status) { try { await api(`/v1/goals/${id}`, { method: 'PATCH', body: JSON.stringify({ workspace_id: workspace(), status: status === 'completed' ? 'active' : 'completed' }) }); await loadGoals(); } catch (e) { setStatus('actionStatus', e.message, false); } }
async function loadTasks() { try { const d = await api(`/v1/tasks?workspace_id=${encodeURIComponent(workspace())}`); $('tasks').innerHTML = (d.tasks || []).map(t => `<article class="item"><b>${esc(t.title)}</b><span class="badge">${esc(t.status)}</span><p>${esc(t.description || '')}</p><button class="secondary" onclick="toggleTask('${t.id}','${t.status}')">${t.status === 'completed' ? 'Reopen' : 'Complete'}</button></article>`).join('') || '<span class="muted">No tasks yet.</span>'; } catch (e) { $('tasks').textContent = e.message; } }
async function createTask() { const title = $('taskTitle').value.trim(); if (!title) return; try { await api('/v1/tasks', { method: 'POST', body: JSON.stringify({ workspace_id: workspace(), title, goal_id: $('taskGoal').value || null }) }); $('taskTitle').value = ''; await loadTasks(); } catch (e) { setStatus('actionStatus', e.message, false); } }
async function toggleTask(id, status) { try { await api(`/v1/tasks/${id}`, { method: 'PATCH', body: JSON.stringify({ workspace_id: workspace(), status: status === 'completed' ? 'open' : 'completed' }) }); await loadTasks(); } catch (e) { setStatus('actionStatus', e.message, false); } }
async function loadDecisions() { try { const d = await api(`/v1/decisions?workspace_id=${encodeURIComponent(workspace())}`); $('decisions').innerHTML = (d.decisions || []).map(x => `<article class="item"><b>${esc(x.title)}</b><p>${esc(x.decision)}</p><small>Confidence ${x.confidence == null ? '—' : Number(x.confidence).toFixed(2)}</small></article>`).join('') || '<span class="muted">No decisions recorded yet.</span>'; } catch (e) { $('decisions').textContent = e.message; } }
async function createDecision() { const title = $('decisionTitle').value.trim(), decision = $('decisionText').value.trim(); if (!title || !decision) return; try { await api('/v1/decisions', { method: 'POST', body: JSON.stringify({ workspace_id: workspace(), title, decision, confidence: Number($('decisionConfidence').value || 0) || null }) }); $('decisionTitle').value = ''; $('decisionText').value = ''; await loadDecisions(); } catch (e) { setStatus('actionStatus', e.message, false); } }

function importFile(input) { const file = input.files?.[0]; if (!file) return; file.text().then(text => { state.importedPayload = JSON.parse(text); setStatus('importStatus', `Loaded ${file.name}. Ready to import.`); }).catch(e => setStatus('importStatus', `Invalid JSON: ${e.message}`, false)); }
async function importConversation() { if (!state.importedPayload) return setStatus('importStatus', 'Choose a JSON export first.', false); try { const d = await api('/v1/conversations/import', { method: 'POST', body: JSON.stringify({ workspace_id: workspace(), provider: $('importProvider').value, source_name: $('importName').value.trim() || 'Imported conversation', payload: state.importedPayload }) }); setStatus('importStatus', `Imported ${d.messages_imported} messages. Historical model text was not promoted to fact.`, true); } catch (e) { setStatus('importStatus', e.message, false); } }

async function exportState() { setStatus('continuity', 'Exporting…'); try { const d = await api(`/v1/continuity/export?workspace_id=${encodeURIComponent(workspace())}`); const blob = new Blob([JSON.stringify(d, null, 2)], { type: 'application/json' }); const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `aurora-export-${workspace().slice(0, 8)}.json`; a.click(); URL.revokeObjectURL(a.href); setStatus('continuity', 'Deterministic export generated.', true); } catch (e) { setStatus('continuity', e.message, false); } }
async function restoreState(input) { const file = input.files?.[0]; if (!file) return; try { const bundle = JSON.parse(await file.text()); const d = await api('/v1/continuity/restore', { method: 'POST', body: JSON.stringify({ workspace_id: workspace(), user_id_map: {}, bundle, dry_run: true }) }); setStatus('continuity', `Dry-run restore validated: ${JSON.stringify(d)}`, true); } catch (e) { setStatus('continuity', `Dry-run: ${e.message}`, false); } input.value = ''; }

window.health = health; window.saveLocal = saveLocal; window.signIn = signIn; window.refreshSession = refreshSession; window.signOut = signOut; window.loadWorkspaces = loadWorkspaces; window.chooseWorkspace = chooseWorkspace; window.createWorkspace = createWorkspace; window.ingest = ingest; window.ask = ask; window.scanContradictions = scanContradictions; window.reviewClaim = reviewClaim; window.inspect = inspect; window.createGoal = createGoal; window.toggleGoal = toggleGoal; window.createTask = createTask; window.toggleTask = toggleTask; window.createDecision = createDecision; window.importFile = importFile; window.importConversation = importConversation; window.exportState = exportState; window.restoreState = restoreState;
loadLocal(); if (token()) loadWorkspaces();
