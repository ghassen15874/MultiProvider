/**
 * Universal AI Framework - Frontend Application Controller
 * Handles Key Pool Dashboard, Dynamic Groq Model Selector, Real-time SSE Chat, and Syntax-Colored SDK Exporter.
 */

// State
const state = {
  activeTab: 'tab-monitor',
  strategy: 'smart-adaptive',
  keys: [],
  events: [],
  groqModels: [],
  modelsCatalog: {},
  chatHistory: [],
  isGeneratingChat: false,
  pollTimer: null
};

// DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initControls();
  initPlayground();
  loadAllGroqModels();
  
  // Initial fetch and start polling pool status
  fetchPoolStatus();
  state.pollTimer = setInterval(fetchPoolStatus, 3000);
});

// ========================================================
// 1. Tab Navigation
// ========================================================
function initTabs() {
  const tabBtns = document.querySelectorAll('.tab-btn');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-tab');
      tabBtns.forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add('active');
      state.activeTab = targetId;
    });
  });
}

// ========================================================
// 2. Key Pool Monitor & Controls
// ========================================================
function initControls() {
  const strategySelect = document.getElementById('strategySelect');
  strategySelect.addEventListener('change', async (e) => {
    const newStrategy = e.target.value;
    try {
      const res = await fetch('/api/models/strategy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ strategy: newStrategy })
      });
      const data = await res.json();
      if (data.status === 'ok') {
        state.strategy = data.active_strategy;
        document.getElementById('headerStrategyBadge').textContent = formatStrategy(data.active_strategy);
        fetchPoolStatus();
      }
    } catch (err) {
      alert(`Failed to change strategy: ${err.message}`);
    }
  });

  document.getElementById('testAllKeysBtn').addEventListener('click', async () => {
    const btn = document.getElementById('testAllKeysBtn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Testing 6 Keys...`;

    try {
      const res = await fetch('/api/models/keys/test', { method: 'POST' });
      const data = await res.json();
      if (data.status === 'ok') {
        fetchPoolStatus();
      }
    } catch (err) {
      alert(`Error testing keys: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  });

  // Add Key Modal
  const modal = document.getElementById('addKeyModal');
  document.getElementById('openAddKeyModalBtn').addEventListener('click', () => {
    modal.classList.add('open');
  });
  document.getElementById('closeAddKeyModalBtn').addEventListener('click', () => {
    modal.classList.remove('open');
  });
  document.getElementById('submitAddKeyBtn').addEventListener('click', async () => {
    const name = document.getElementById('newKeyName').value.trim();
    const apiKey = document.getElementById('newKeyVal').value.trim();
    if (!apiKey) {
      alert('Please provide a Groq API key (starts with gsk_...)');
      return;
    }

    try {
      const res = await fetch('/api/models/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey, name: name || undefined })
      });
      const data = await res.json();
      if (data.status === 'ok') {
        modal.classList.remove('open');
        document.getElementById('newKeyVal').value = '';
        document.getElementById('newKeyName').value = '';
        fetchPoolStatus();
      } else {
        alert(data.detail || 'Failed to add key');
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  });
}

function formatStrategy(s) {
  if (s === 'smart-adaptive') return 'Smart-Adaptive';
  if (s === 'round-robin') return 'Round-Robin';
  if (s === 'failover-sequential') return 'Failover-Sequential';
  if (s === 'least-used') return 'Least-Used';
  return s;
}

async function fetchPoolStatus() {
  try {
    const res = await fetch('/api/models/pool-status');
    const data = await res.json();
    if (data.status === 'ok') {
      state.keys = data.keys || [];
      state.events = data.recent_events || [];
      state.strategy = data.strategy || 'smart-adaptive';

      // Update Header & KPI Indicators
      const available = data.available_keys || 0;
      const total = data.total_keys || 0;
      document.getElementById('activeKeysCount').textContent = `${available} / ${total} Online`;
      document.getElementById('headerStrategyBadge').textContent = formatStrategy(state.strategy);

      // Aggregate Headroom Stats
      const totalRemTokens = state.keys.reduce((acc, k) => acc + (k.remaining_tokens || 0), 0);
      const totalRemReqs = state.keys.reduce((acc, k) => acc + (k.remaining_requests || 0), 0);

      const kpiHealth = document.getElementById('kpiHealthVal');
      const kpiTokens = document.getElementById('kpiTokensVal');
      const kpiReqs = document.getElementById('kpiRequestsVal');

      if (kpiHealth) kpiHealth.textContent = `${available} / ${total}`;
      if (kpiTokens) kpiTokens.textContent = totalRemTokens.toLocaleString();
      if (kpiReqs) kpiReqs.textContent = totalRemReqs.toLocaleString();

      renderKeyCards(state.keys);
      renderTerminalLog(state.events);
    }
  } catch (err) {
    console.error('Failed to poll status:', err);
  }
}

function renderKeyCards(keys) {
  const grid = document.getElementById('keysGrid');
  grid.innerHTML = '';

  keys.forEach((k, idx) => {
    const card = document.createElement('div');
    const isCooling = k.status === 'cooling';
    const isInvalid = k.status === 'invalid';
    card.className = `key-card glass ${isCooling ? 'cooling-card' : isInvalid ? 'invalid-card' : 'active-card'}`;

    // Token & request percentage
    const tokenPct = Math.min(100, Math.max(0, (k.remaining_tokens / Math.max(1, k.limit_tokens)) * 100));
    const reqPct = Math.min(100, Math.max(0, (k.remaining_requests / Math.max(1, k.limit_requests)) * 100));

    let statusPillClass = 'pill-active';
    let statusText = 'Ready / Active';
    if (isCooling) {
      statusPillClass = 'pill-cooling';
      statusText = `Cooling (${k.cooldown_remaining_sec}s)`;
    } else if (isInvalid) {
      statusPillClass = 'pill-invalid';
      statusText = 'Invalid';
    }

    card.innerHTML = `
      <div class="key-card-header">
        <div class="key-title-area">
          <div class="key-index-chip">#0${idx + 1}</div>
          <div>
            <div class="key-name-title">${k.name}</div>
            <div style="margin-top: 2px;"><span class="key-masked-code">${k.masked_key}</span></div>
          </div>
        </div>
        <span class="key-status-pill ${statusPillClass}">${statusText}</span>
      </div>

      <!-- Token Headroom Meter -->
      <div class="metric-row">
        <div class="metric-labels">
          <span>Remaining Tokens (TPM)</span>
          <span class="metric-val">${k.remaining_tokens.toLocaleString()} / ${k.limit_tokens.toLocaleString()}</span>
        </div>
        <div class="progress-track">
          <div class="progress-fill fill-tokens" style="width: ${tokenPct}%"></div>
        </div>
      </div>

      <!-- Request Headroom Meter -->
      <div class="metric-row">
        <div class="metric-labels">
          <span>Remaining Requests (RPM)</span>
          <span class="metric-val">${k.remaining_requests.toLocaleString()} / ${k.limit_requests.toLocaleString()}</span>
        </div>
        <div class="progress-track">
          <div class="progress-fill fill-requests" style="width: ${reqPct}%"></div>
        </div>
      </div>

      <!-- Mini Stats Footer -->
      <div class="key-stats-mini">
        <div class="mini-stat-item">
          <span class="mini-stat-label">Calls</span>
          <span class="mini-stat-val">${k.total_calls}</span>
        </div>
        <div class="mini-stat-item">
          <span class="mini-stat-label">Success Rate</span>
          <span class="mini-stat-val">${k.success_rate}%</span>
        </div>
        <div class="mini-stat-item">
          <span class="mini-stat-label">Latency</span>
          <span class="mini-stat-val">${k.last_latency_ms ? k.last_latency_ms + 'ms' : '-'}</span>
        </div>
      </div>
    `;
    grid.appendChild(card);
  });
}

function renderTerminalLog(events) {
  const box = document.getElementById('terminalLog');
  box.innerHTML = '';
  if (!events || events.length === 0) {
    box.innerHTML = `<div class="log-entry"><span class="log-time">[Ready]</span><span>No events recorded yet.</span></div>`;
    return;
  }

  events.slice(0, 15).forEach(evt => {
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = `
      <span class="log-time">[${evt.time || 'now'}]</span>
      <span class="log-tag tag-${evt.type}">${evt.type}</span>
      <span>${evt.message}</span>
    `;
    box.appendChild(entry);
  });
}

// ========================================================
// 3. Load All Groq Models Dynamically
// ========================================================
async function loadAllGroqModels() {
  try {
    const res = await fetch('/api/models');
    const data = await res.json();
    if (data.status === 'ok') {
      state.groqModels = data.groq_models || [];
      state.modelsCatalog = data.models || {};
      
      const select = document.getElementById('modelSelect');
      const badge = document.getElementById('modelTagBadge');

      select.addEventListener('change', () => {
        const selectedVal = select.value;
        const meta = state.modelsCatalog[selectedVal];
        if (meta && meta.context_window) {
          badge.textContent = `${meta.context_window >= 1000 ? Math.round(meta.context_window/1000) + 'k' : meta.context_window} Context`;
        } else {
          badge.textContent = 'Groq Console Model';
        }
      });

      // Custom model override button
      const customInput = document.getElementById('customModelInput');
      const applyCustomBtn = document.getElementById('applyCustomModelBtn');
      if (applyCustomBtn && customInput) {
        applyCustomBtn.addEventListener('click', () => {
          const customVal = customInput.value.trim();
          if (customVal) {
            // Check if option exists, or create new option
            let opt = Array.from(select.options).find(o => o.value === customVal);
            if (!opt) {
              opt = document.createElement('option');
              opt.value = customVal;
              opt.textContent = `Custom: ${customVal}`;
              select.appendChild(opt);
            }
            select.value = customVal;
            badge.textContent = 'Custom Model';
          }
        });
      }
    }
  } catch (err) {
    console.error('Failed to load Groq models:', err);
  }
}

// ========================================================
// 4. Playground & Live Streaming Chat
// ========================================================
function initPlayground() {
  const tempSlider = document.getElementById('tempSlider');
  const tempVal = document.getElementById('tempVal');
  tempSlider.addEventListener('input', () => tempVal.textContent = tempSlider.value);

  const tokensSlider = document.getElementById('tokensSlider');
  const tokensVal = document.getElementById('tokensVal');
  tokensSlider.addEventListener('input', () => tokensVal.textContent = tokensSlider.value);

  const clearBtn = document.getElementById('clearChatBtn');
  clearBtn.addEventListener('click', () => {
    state.chatHistory = [];
    document.getElementById('chatHistory').innerHTML = `
      <div class="chat-bubble assistant">
        <p>👋 Chat reset. What would you like to explore next?</p>
      </div>
    `;
  });

  const chatInput = document.getElementById('chatInput');
  const sendBtn = document.getElementById('sendChatBtn');

  const sendMessage = async () => {
    const text = chatInput.value.trim();
    if (!text || state.isGeneratingChat) return;

    chatInput.value = '';
    state.isGeneratingChat = true;

    // Add user bubble
    appendChatBubble('user', text);
    state.chatHistory.push({ role: 'user', content: text });

    const model = document.getElementById('modelSelect').value;
    const systemPrompt = document.getElementById('systemPromptInput').value.trim();
    const temperature = parseFloat(tempSlider.value);
    const max_tokens = parseInt(tokensSlider.value);
    const useStream = document.getElementById('streamToggle').checked;

    const messages = [];
    if (systemPrompt) messages.push({ role: 'system', content: systemPrompt });
    messages.push(...state.chatHistory);

    if (useStream) {
      await handleStreamChat(messages, model, temperature, max_tokens);
    } else {
      await handleDirectChat(messages, model, temperature, max_tokens);
    }

    state.isGeneratingChat = false;
  };

  sendBtn.addEventListener('click', sendMessage);
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
}

function appendChatBubble(role, content, meta = null) {
  const history = document.getElementById('chatHistory');
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;

  let metaHtml = '';
  if (meta) {
    metaHtml = `
      <div class="bubble-meta">
        <span>🔑 ${meta.key_name || 'Rotated Key'} (${meta.masked_key || ''})</span>
        <span>•</span>
        <span>⏱️ ${meta.latency_ms || ''}ms</span>
        <span>•</span>
        <span>⚡ ${meta.speed_tps ? meta.speed_tps + ' t/s' : meta.model}</span>
      </div>
    `;
  }

  bubble.innerHTML = `<p style="white-space: pre-wrap;">${escapeHtml(content)}</p>${metaHtml}`;
  history.appendChild(bubble);
  history.scrollTop = history.scrollHeight;
  return bubble;
}

async function handleDirectChat(messages, model, temperature, max_tokens) {
  const history = document.getElementById('chatHistory');
  const tempBubble = appendChatBubble('assistant', 'Thinking...');

  try {
    const res = await fetch('/api/inference/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages, model, temperature, max_tokens })
    });
    const data = await res.json();
    history.removeChild(tempBubble);

    if (data.choices && data.choices[0]) {
      const content = data.choices[0].message.content;
      const rotator = data._rotator || {};
      const tokens = data.usage?.completion_tokens || 0;
      const speed = rotator.latency_ms ? roundDec((tokens / (rotator.latency_ms / 1000)), 1) : 0;

      appendChatBubble('assistant', content, {
        key_name: rotator.key_name,
        masked_key: rotator.masked_key,
        latency_ms: rotator.latency_ms,
        speed_tps: speed,
        model: rotator.model
      });
      state.chatHistory.push({ role: 'assistant', content });
      fetchPoolStatus();
    } else {
      appendChatBubble('assistant', `⚠️ Error: ${JSON.stringify(data)}`);
    }
  } catch (err) {
    history.removeChild(tempBubble);
    appendChatBubble('assistant', `⚠️ Network error: ${err.message}`);
  }
}

async function handleStreamChat(messages, model, temperature, max_tokens) {
  const history = document.getElementById('chatHistory');
  const streamBubble = appendChatBubble('assistant', '');
  const pElem = streamBubble.querySelector('p');

  let fullText = '';
  let metaCaptured = null;
  const t0 = performance.now();

  try {
    const resp = await fetch('/api/inference/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages, model, temperature, max_tokens })
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line.startsWith('data: ')) {
          try {
            const dataObj = JSON.parse(line.slice(6));
            if (dataObj.type === 'token') {
              fullText += dataObj.token;
              pElem.textContent = fullText;
              history.scrollTop = history.scrollHeight;
              if (dataObj.meta && !metaCaptured) metaCaptured = dataObj.meta;
            } else if (dataObj.type === 'done') {
              if (dataObj.meta) metaCaptured = dataObj.meta;
            } else if (dataObj.type === 'error') {
              pElem.textContent += `\n[Stream Error: ${dataObj.error}]`;
            }
          } catch (_) {}
        }
      }
    }

    const elapsedMs = Math.round(performance.now() - t0);
    const tokensEstimated = Math.max(1, Math.ceil(fullText.length / 4));
    const speed = roundDec(tokensEstimated / (elapsedMs / 1000), 1);

    if (metaCaptured) {
      const metaElem = document.createElement('div');
      metaElem.className = 'bubble-meta';
      metaElem.innerHTML = `
        <span>🔑 ${metaCaptured.key_name} (${metaCaptured.masked_key})</span>
        <span>•</span>
        <span>⏱️ ${elapsedMs}ms</span>
        <span>•</span>
        <span>⚡ ${speed} t/s</span>
      `;
      streamBubble.appendChild(metaElem);
    }

    state.chatHistory.push({ role: 'assistant', content: fullText });
    fetchPoolStatus();

  } catch (err) {
    pElem.textContent += `\n[Connection Error: ${err.message}]`;
  }
}

// ========================================================
// 5. Code Copy Utility with Visual Feedback
// ========================================================
window.copySnippetText = function(btn, elementId) {
  const elem = document.getElementById(elementId);
  if (!elem) return;

  // Extract pure code text (ignoring HTML tags)
  const codeContent = elem.innerText || elem.textContent;

  navigator.clipboard.writeText(codeContent).then(() => {
    const originalHtml = btn.innerHTML;
    btn.classList.add('copied');
    btn.innerHTML = `<span>✓</span> Copied!`;
    setTimeout(() => {
      btn.classList.remove('copied');
      btn.innerHTML = originalHtml;
    }, 2200);
  }).catch(err => {
    // Fallback for clipboard API
    const textArea = document.createElement('textarea');
    textArea.value = codeContent;
    document.body.appendChild(textArea);
    textArea.select();
    try {
      document.execCommand('copy');
      btn.classList.add('copied');
      btn.innerHTML = `<span>✓</span> Copied!`;
      setTimeout(() => {
        btn.classList.remove('copied');
        btn.innerHTML = originalHtml;
      }, 2200);
    } catch (e) {
      alert('Failed to copy: ' + e);
    }
    document.body.removeChild(textArea);
  });
};

// Utilities
function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function roundDec(val, dec = 1) {
  return Math.round(val * Math.pow(10, dec)) / Math.pow(10, dec);
}
