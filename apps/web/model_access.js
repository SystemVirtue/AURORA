/* AURORA model-access layer: explicit OpenRouter-Free and keyless Puter.js paths. */
(() => {
  const state = { provider: 'openrouter', openrouter: [], puter: [], puterLoaded: false };

  function escLocal(value) {
    return String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  }
  function selectedModels() {
    return [...document.querySelectorAll('#modelPicker option:checked')].map(o => o.value).filter(Boolean);
  }
  function setModels(models) {
    const select = document.getElementById('modelPicker');
    if (!select) return;
    const previous = new Set(selectedModels());
    select.innerHTML = models.map(m => `<option value="${escLocal(m.id)}">${escLocal(m.name || m.id)} · ${escLocal(m.id)}</option>`).join('');
    const keep = [...select.options].filter(o => previous.has(o.value));
    if (keep.length) keep.forEach(o => { o.selected = true; });
    else if (select.options[0]) select.options[0].selected = true;
    document.getElementById('model').value = selectedModels()[0] || '';
    document.getElementById('modelAccessStatus').textContent = `${models.length} ${state.provider === 'puter' ? 'keyless Puter free' : 'OpenRouter free'} models available.`;
  }

  async function loadOpenRouter() {
    try {
      const data = await fetch('/v1/models?provider=openrouter&free_only=true').then(r => r.json());
      if (!data.models) throw new Error(data.detail || 'OpenRouter catalogue unavailable');
      state.openrouter = data.models;
      if (state.provider === 'openrouter') setModels(state.openrouter);
    } catch (error) {
      document.getElementById('modelAccessStatus').textContent = `OpenRouter catalogue error: ${error.message}`;
    }
  }

  async function ensurePuter() {
    if (window.puter) return window.puter;
    await new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://js.puter.com/v2/';
      script.onload = resolve;
      script.onerror = () => reject(new Error('Puter.js could not be loaded.'));
      document.head.appendChild(script);
    });
    return window.puter;
  }

  async function loadPuter() {
    try {
      const puter = await ensurePuter();
      const models = await puter.ai.listModels();
      state.puter = (models || []).filter(m => {
        const cost = m.cost || {};
        return Number(cost.input || 0) === 0 && Number(cost.output || 0) === 0;
      }).map(m => ({ ...m, name: m.name || m.id })).sort((a, b) => a.name.localeCompare(b.name));
      state.puterLoaded = true;
      if (state.provider === 'puter') setModels(state.puter);
      document.getElementById('puterStatus').textContent = puter.auth?.isSignedIn?.() ? 'Puter account connected.' : 'Puter ready — sign in when you run a request.';
    } catch (error) {
      document.getElementById('modelAccessStatus').textContent = `Puter error: ${error.message}`;
    }
  }

  async function switchProvider() {
    state.provider = document.getElementById('modelProvider').value;
    document.getElementById('model').value = '';
    document.getElementById('modelPicker').multiple = state.provider === 'puter';
    if (state.provider === 'puter') {
      await loadPuter();
      document.getElementById('modelAccessNote').textContent = 'Puter.js executes in the browser. No provider API key is sent to AURORA. The list is initially restricted to models reporting zero input/output cost.';
    } else {
      setModels(state.openrouter);
      document.getElementById('modelAccessNote').textContent = 'OpenRouter pathway: AURORA exposes only currently $0 input/$0 output models by default. The OpenRouter API key remains server-side.';
    }
  }

  async function connectPuter() {
    try {
      const puter = await ensurePuter();
      await puter.auth.signIn();
      document.getElementById('puterStatus').textContent = 'Puter account connected.';
    } catch (error) {
      document.getElementById('puterStatus').textContent = `Puter sign-in failed: ${error.message || error}`;
    }
  }

  function contentOf(response) {
    const content = response?.message?.content ?? response?.content ?? response;
    if (Array.isArray(content)) return content.map(x => x?.text || '').join('');
    return String(content ?? '');
  }

  async function puterCall(model, prompt) {
    const puter = await ensurePuter();
    if (!puter.auth.isSignedIn()) await puter.auth.signIn();
    const started = performance.now();
    const response = await puter.ai.chat([
      { role: 'system', content: 'You are an AURORA reasoning contributor. Separate evidence-supported claims from uncertainty. Never describe a model assertion as independently verified.' },
      { role: 'user', content: prompt },
    ], { model, normalize: true });
    return { model, provider: 'puter', response: contentOf(response), latency_ms: Math.round(performance.now() - started) };
  }

  async function askPuter() {
    const question = document.getElementById('question').value.trim();
    if (!workspace() || !question) throw new Error('Workspace and question are required.');
    const models = selectedModels();
    if (!models.length) throw new Error('Select at least one Puter model.');
    const retrieved = await api(`/v1/retrieval?workspace_id=${encodeURIComponent(workspace())}&question=${encodeURIComponent(question)}`);
    const evidence = retrieved.evidence || [];
    const context = evidence.length ? evidence.map((e, i) => `[Evidence ${i + 1} | ${e.evidence_id}] ${e.content}`).join('\n\n') : '(No matching workspace evidence was retrieved.)';
    const prompt = `Evidence/context:\n${context}\n\nQuestion:\n${question}`;
    const mode = document.getElementById('mode').value;
    const contributors = [];
    for (const model of mode === 'quorum' || mode === 'deep' ? models.slice(0, 3) : models.slice(0, 1)) {
      contributors.push(await puterCall(model, prompt));
    }
    let synthesis = null;
    if ((mode === 'quorum' || mode === 'deep') && contributors.length > 0) {
      const deliberation = contributors.map((c, i) => `CONTRIBUTOR ${i + 1} — ${c.model}\n${c.response}`).join('\n\n');
      const synthesisModel = models[0];
      synthesis = await puterCall(synthesisModel, `You are the AURORA synthesis model. Preserve material disagreement, distinguish evidence from model assertions, identify uncertainty, and answer the original question.\n\nOriginal question:\n${question}\n\nIndependent contributions:\n${deliberation}`);
    }
    const body = {
      workspace_id: workspace(), question, session_id: localStorage.getItem('aurora.session_id') || null, mode,
      contributions: contributors.map(c => ({ model: c.model, provider: 'puter', response: c.response, latency_ms: c.latency_ms })),
      synthesis: synthesis ? { model: synthesis.model, response: synthesis.response, latency_ms: synthesis.latency_ms } : null,
    };
    const persisted = await api('/v1/ask/puter', { method: 'POST', body: JSON.stringify(body) });
    localStorage.setItem('aurora.session_id', persisted.session_id);
    return persisted;
  }

  function renderAccessPanel() {
    const modelInput = document.getElementById('model');
    if (!modelInput) return;
    modelInput.style.display = 'none';
    const host = modelInput.parentElement;
    const panel = document.createElement('div');
    panel.className = 'item';
    panel.innerHTML = `<label>Model access pathway</label>
      <select id="modelProvider"><option value="openrouter">OpenRouter — FREE models</option><option value="puter">Puter.js — keyless</option></select>
      <label>Explicit model selection <span class="muted">(Ctrl/Cmd-click for Puter QUORUM)</span></label>
      <select id="modelPicker" size="5"></select>
      <div class="row"><button type="button" onclick="loadModelAccess()">Refresh models</button><button type="button" class="secondary" onclick="connectPuter()">Connect Puter</button></div>
      <div id="modelAccessNote" class="status muted">OpenRouter pathway: AURORA exposes only currently $0 input/$0 output models by default. The OpenRouter API key remains server-side.</div>
      <div id="puterStatus" class="status muted">Puter not connected.</div>
      <div id="modelAccessStatus" class="status muted">Loading free model catalogue…</div>`;
    host.insertBefore(panel, modelInput);
    document.getElementById('modelProvider').addEventListener('change', switchProvider);
    document.getElementById('modelPicker').addEventListener('change', () => {
      document.getElementById('model').value = selectedModels()[0] || '';
    });
  }

  window.loadModelAccess = async () => {
    await loadOpenRouter();
    if (state.provider === 'puter') await loadPuter();
  };
  window.connectPuter = connectPuter;

  const originalAsk = window.ask;
  window.ask = async function () {
    if (state.provider !== 'puter') return originalAsk();
    document.getElementById('answer').textContent = 'Reasoning through Puter.js…';
    try {
      const d = await askPuter();
      document.getElementById('answer').textContent = d.answer;
      document.getElementById('trace').textContent = JSON.stringify(d.trace, null, 2);
      if (typeof renderQuorum === 'function') renderQuorum(d.quorum);
      document.getElementById('epistemic').innerHTML = d.evidence?.length ? '<b>Evidence:</b> lexical workspace retrieval used.' : '<b>Warrant:</b> missing_evidence';
      document.getElementById('evidence').innerHTML = d.evidence?.length ? d.evidence.map((e, i) => `<article><b>[${i + 1}] ${escLocal(e.document)}</b> · chunk ${escLocal(e.chunk_index)} · score ${Number(e.score || 0).toFixed(3)}<p>${escLocal(e.content)}</p><small>Evidence ID: ${escLocal(e.evidence_id || 'none')}</small></article><hr>`).join('') : 'No matching evidence. AURORA recorded an epistemic gap.';
    } catch (error) {
      document.getElementById('answer').textContent = `Error: ${error.message || error}`;
    }
  };

  document.addEventListener('DOMContentLoaded', async () => {
    renderAccessPanel();
    await loadOpenRouter();
  });
})();
