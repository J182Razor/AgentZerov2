// NVIDIA Models Management Panel
// Provides live model/role assignment with per-key validation

const NVIDIA_ROLE_LABELS = {
  chat:      'Chat Reasoning',
  utility:   'Utility / Summary',
  browser:   'Browser / Vision',
  code:      'Code Generation',
  reasoning: 'Deep Reasoning',
  fast:      'Fast Inference',
  embedding: 'Embeddings',
};

const ROLE_ORDER = ['chat','utility','browser','code','reasoning','fast','embedding'];

async function nvFetch(path, opts = {}) {
  const r = await fetch(path, {
    headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
    ...opts,
  });
  return r.json();
}

window.NvidiaModels = {
  _state: { roles: {}, knownModels: [], dirty: false },

  async init(containerEl) {
    this._container = containerEl;
    await this.load();
    this.render();
  },

  async load() {
    try {
      const data = await nvFetch('/api/nvidia_roles');
      this._state.roles = data.roles || {};
      this._state.knownModels = (data.known_models || []).map(m => m.id);
    } catch(e) {
      console.warn('NvidiaModels: could not load roles', e);
    }
  },

  render() {
    const c = this._container;
    if (!c) return;
    c.innerHTML = this._buildHTML();
    this._attachEvents(c);
  },

  _buildHTML() {
    const rows = ROLE_ORDER.map(role => {
      const cfg = this._state.roles[role] || {};
      const label = NVIDIA_ROLE_LABELS[role] || role;
      const model = cfg.model || '';
      const keyEnv = cfg.api_key_env || '';
      return `
        <tr data-role="${role}">
          <td class="nvidia-role-label">${label}</td>
          <td><input class="nvidia-model-input" data-field="model" value="${model}" list="nvidia-models-list" placeholder="model/name" /></td>
          <td>
            <div class="nvidia-key-wrap">
              <input class="nvidia-key-input" data-field="api_key_env" type="password" value="${keyEnv}" placeholder="NVIDIA_API_KEY_XXX" />
              <button class="nvidia-key-reveal" title="Show/hide" onclick="this.previousElementSibling.type=this.previousElementSibling.type==='password'?'text':'password'">&#x1F441;</button>
            </div>
          </td>
          <td><span class="nvidia-status-badge idle" data-status="${role}">— idle</span></td>
          <td><button class="nvidia-test-btn" data-test="${role}">Test</button></td>
        </tr>`;
    }).join('');

    const modelOptions = this._state.knownModels.map(m => `<option value="${m}">`).join('');

    return `
      <datalist id="nvidia-models-list">${modelOptions}</datalist>
      <div class="nvidia-models-panel">
        <table class="nvidia-models-table">
          <thead>
            <tr>
              <th>Role</th><th>Model</th><th>API Key Env Var</th><th>Status</th><th></th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
        <div class="nvidia-panel-actions">
          <button class="nvidia-save-btn" id="nvidia-save-btn">Save &amp; Apply</button>
          <button class="nvidia-secondary-btn" id="nvidia-test-all-btn">Test All</button>
          <button class="nvidia-secondary-btn" id="nvidia-export-btn">Export JSON</button>
          <button class="nvidia-secondary-btn" id="nvidia-import-btn">Import JSON</button>
          <input type="file" id="nvidia-import-file" accept=".json" style="display:none" />
          <span class="nvidia-status-msg" id="nvidia-save-status"></span>
        </div>
      </div>`;
  },

  _attachEvents(c) {
    // Mark dirty on any input change
    c.querySelectorAll('.nvidia-model-input, .nvidia-key-input').forEach(el => {
      el.addEventListener('input', () => { this._state.dirty = true; });
    });

    // Per-row test buttons
    c.querySelectorAll('[data-test]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const role = btn.dataset.test;
        await this._testRole(role, c);
      });
    });

    // Save & Apply
    c.querySelector('#nvidia-save-btn').addEventListener('click', () => this._save(c));

    // Test All
    c.querySelector('#nvidia-test-all-btn').addEventListener('click', async () => {
      for (const role of ROLE_ORDER) await this._testRole(role, c);
    });

    // Export
    c.querySelector('#nvidia-export-btn').addEventListener('click', () => {
      const data = this._collectFormData(c);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
      a.download = 'nvidia_roles.json'; a.click();
    });

    // Import
    const importBtn = c.querySelector('#nvidia-import-btn');
    const importFile = c.querySelector('#nvidia-import-file');
    importBtn.addEventListener('click', () => importFile.click());
    importFile.addEventListener('change', async (e) => {
      const file = e.target.files[0]; if (!file) return;
      const text = await file.text();
      try {
        const data = JSON.parse(text);
        this._applyToForm(data, c);
      } catch { alert('Invalid JSON file'); }
    });
  },

  _collectFormData(c) {
    const result = {};
    c.querySelectorAll('[data-role]').forEach(row => {
      const role = row.dataset.role;
      result[role] = {
        model: row.querySelector('[data-field="model"]').value.trim(),
        api_key_env: row.querySelector('[data-field="api_key_env"]').value.trim(),
      };
    });
    return result;
  },

  _applyToForm(data, c) {
    Object.entries(data).forEach(([role, cfg]) => {
      const row = c.querySelector(`[data-role="${role}"]`);
      if (!row) return;
      if (cfg.model) row.querySelector('[data-field="model"]').value = cfg.model;
      if (cfg.api_key_env) row.querySelector('[data-field="api_key_env"]').value = cfg.api_key_env;
    });
    this._state.dirty = true;
  },

  async _testRole(role, c) {
    const row = c.querySelector(`[data-role="${role}"]`);
    if (!row) return;
    const model = row.querySelector('[data-field="model"]').value.trim();
    const apiKeyEnv = row.querySelector('[data-field="api_key_env"]').value.trim();
    const badge = c.querySelector(`[data-status="${role}"]`);

    badge.className = 'nvidia-status-badge testing';
    badge.textContent = '\u23F3 testing\u2026';

    try {
      const res = await nvFetch('/api/nvidia_roles/test', {
        method: 'POST',
        body: JSON.stringify({ model, api_key: apiKeyEnv }),
      });
      if (res.ok) {
        badge.className = 'nvidia-status-badge ok';
        badge.textContent = '\u2705 OK';
      } else {
        badge.className = 'nvidia-status-badge fail';
        badge.textContent = `\u274C ${(res.error || 'fail').slice(0, 40)}`;
      }
    } catch(e) {
      badge.className = 'nvidia-status-badge fail';
      badge.textContent = '\u274C network error';
    }
  },

  async _save(c) {
    const btn = c.querySelector('#nvidia-save-btn');
    const msg = c.querySelector('#nvidia-save-status');
    btn.disabled = true;
    try {
      const data = this._collectFormData(c);
      const res = await nvFetch('/api/nvidia_roles', {
        method: 'PUT',
        body: JSON.stringify({ roles: data }),
      });
      if (res.ok !== false) {
        this._state.roles = res.roles || data;
        msg.textContent = '\u2705 Saved & applied'; msg.className = 'nvidia-status-msg visible ok';
        this._state.dirty = false;
      } else {
        msg.textContent = '\u274C Save failed'; msg.className = 'nvidia-status-msg visible fail';
      }
    } catch(e) {
      msg.textContent = '\u274C Network error'; msg.className = 'nvidia-status-msg visible fail';
    }
    btn.disabled = false;
    setTimeout(() => { msg.className = 'nvidia-status-msg'; }, 4000);
  },
};
