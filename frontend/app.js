/**
 * Universal AI Framework - Frontend Application Controller
 * Handles Key Pool Dashboard, SSE Streaming Playground, Arabic Benchmark, and Live Web Design Sandbox.
 */

// State
const state = {
  activeTab: 'tab-monitor',
  strategy: 'smart-adaptive',
  keys: [],
  events: [],
  models: {},
  chatHistory: [],
  isGeneratingChat: false,
  pollTimer: null
};

// DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initControls();
  initPlayground();
  initArabicBenchmark();
  initCodeBenchmark();
  
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

      // Update Header Indicator
      const available = data.available_keys || 0;
      const total = data.total_keys || 0;
      document.getElementById('activeKeysCount').textContent = `${available} / ${total} Keys Online`;
      document.getElementById('headerStrategyBadge').textContent = formatStrategy(state.strategy);

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
    let statusText = 'Active';
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
          <div class="key-num-badge">${idx + 1}</div>
          <div>
            <div class="key-name">${k.name}</div>
            <div class="key-masked">${k.masked_key}</div>
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
// 3. Playground & Live Streaming Chat
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
// 4. Arabic Video Script Benchmark Controller
// ========================================================
function initArabicBenchmark() {
  const topicInput = document.getElementById('arabicTopicInput');
  const runBtn = document.getElementById('runArabicBenchmarkBtn');
  const grid = document.getElementById('arabicBenchmarkGrid');

  // Preset chips
  document.querySelectorAll('.arabic-preset').forEach(btn => {
    btn.addEventListener('click', () => {
      topicInput.value = btn.getAttribute('data-topic');
    });
  });

  runBtn.addEventListener('click', async () => {
    const topic = topicInput.value.trim();
    if (!topic) return;

    runBtn.disabled = true;
    runBtn.innerHTML = `<span class="spinner"></span> جاري توليد السيناريو عبر كافة النماذج...`;

    grid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 3rem;">
        <span class="spinner" style="width: 32px; height: 32px; border-width: 3px;"></span>
        <p style="margin-top: 1rem; color: var(--text-secondary); font-family: var(--font-arabic);">جاري اختبار النماذج الأربعة وتدوير مفاتيح Groq آلياً...</p>
      </div>
    `;

    try {
      const res = await fetch('/api/inference/benchmark/arabic-script', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic })
      });
      const data = await res.json();
      renderArabicResults(data.results);
      fetchPoolStatus();
    } catch (err) {
      grid.innerHTML = `<div style="grid-column: 1 / -1; color: var(--accent-red); padding: 2rem;">خطأ في تشغيل الاختبار: ${err.message}</div>`;
    } finally {
      runBtn.disabled = false;
      runBtn.innerHTML = `<span>🚀</span> تشغيل الاختبار على جميع النماذج`;
    }
  });
}

function renderArabicResults(results) {
  const grid = document.getElementById('arabicBenchmarkGrid');
  grid.innerHTML = '';

  results.forEach(r => {
    const card = document.createElement('div');
    card.className = 'benchmark-card glass';

    if (!r.success) {
      card.innerHTML = `
        <div class="benchmark-card-header">
          <div class="model-title">${r.model}</div>
          <span class="pill-invalid">Failed</span>
        </div>
        <p style="color: var(--accent-red);">Error: ${r.error}</p>
      `;
      grid.appendChild(card);
      return;
    }

    card.innerHTML = `
      <div class="benchmark-card-header">
        <div>
          <div class="model-title">
            <span>🤖 ${r.model}</span>
          </div>
          <div style="margin-top: 4px;">
            <span class="model-badge-arabic">${r.score_badge}</span>
          </div>
        </div>
        <div class="perf-metrics-badge">
          <span>⚡ ${r.speed_tps} t/s</span>
          <span>•</span>
          <span>⏱️ ${r.duration_sec}s</span>
          <span>•</span>
          <span>🔑 ${r.key_name}</span>
        </div>
      </div>

      <div class="arabic-output-box">${escapeHtml(r.content)}</div>

      <div style="display: flex; justify-content: space-between; align-items: center; margin-top: auto; pt: 8px;">
        <span style="font-size: 0.8rem; color: var(--text-muted); font-family: var(--font-mono);">Tokens: ${r.tokens}</span>
        <button class="btn btn-sm" onclick="copyText(this, \`${escapeJs(r.content)}\`)">
          <span>📋</span> نسخ السيناريو
        </button>
      </div>
    `;
    grid.appendChild(card);
  });
}

// ========================================================
// 5. HTML/CSS/JS Web Design & Live Sandbox Controller
// ========================================================
function initCodeBenchmark() {
  const promptInput = document.getElementById('codePromptInput');
  const runBtn = document.getElementById('runCodeBenchmarkBtn');
  const grid = document.getElementById('codeBenchmarkGrid');

  // Preset challenges
  const challenges = {
    pomodoro: `Create a complete, modern, self-contained single-page interactive Pomodoro Focus Timer widget using pure HTML, CSS, and JavaScript.
Requirements:
1. Animated SVG circular countdown timer that smoothly updates every second.
2. Start, Pause, and Reset controls with micro-animations and glowing hover effects.
3. Mode switcher (25m Focus, 5m Short Break, 15m Long Break).
4. Premium dark glassmorphism styling with modern typography.
5. Sound notification synthesized using the Web Audio API when session ends.
Output ONLY complete valid HTML with embedded <style> and <script> inside an \`\`\`html code block.`,
    
    crypto: `Create a modern, self-contained interactive Crypto/AI Token Live Price Card using pure HTML, CSS, and JavaScript.
Requirements:
1. Displays Token Name ($GROQ), Current Price ($42.80), and 24h change (+18.4%).
2. Interactive HTML5 Canvas sparkline chart showing realistic animated sinusoidal upward wave line with gradient fill.
3. Timeframe toggles (1H, 24H, 7D, 1M) that redraw the canvas with smooth animation.
4. Dark glassmorphic neon aesthetic with glowing green borders.
Output ONLY complete valid HTML with embedded <style> and <script> inside an \`\`\`html code block.`,

    fireworks: `Create a breathtaking interactive particle fireworks animation on an HTML5 canvas using pure HTML, CSS, and JavaScript.
Requirements:
1. Full container Canvas with automatic resizing.
2. Fireworks launch automatically and burst into multicolored glowing particle explosions with gravity and trails.
3. Click or tap anywhere to launch a firework burst at the cursor position.
4. Particle speed and color variations (cyan, purple, gold, red).
5. Minimal UI controls at bottom (Pause/Play, Clear, Particle Count slider).
Output ONLY complete valid HTML with embedded <style> and <script> inside an \`\`\`html code block.`,

    kanban: `Create an interactive Drag-and-Drop Kanban Task Board using pure HTML, CSS, and JavaScript.
Requirements:
1. Three columns: To Do, In Progress, Done.
2. Ability to add new task card with title.
3. Native HTML5 drag and drop (dragstart, dragover, drop) to move task cards between columns.
4. Modern dark glassmorphism UI with vibrant badge tags.
Output ONLY complete valid HTML with embedded <style> and <script> inside an \`\`\`html code block.`
  };

  document.querySelectorAll('.code-preset').forEach(btn => {
    btn.addEventListener('click', () => {
      const c = btn.getAttribute('data-challenge');
      if (challenges[c]) promptInput.value = challenges[c];
    });
  });

  runBtn.addEventListener('click', async () => {
    const prompt = promptInput.value.trim();
    if (!prompt) return;

    runBtn.disabled = true;
    runBtn.innerHTML = `<span class="spinner"></span> جاري توليد الكود وبناء المعاينة الحية...`;

    grid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 3rem;">
        <span class="spinner" style="width: 32px; height: 32px; border-width: 3px;"></span>
        <p style="margin-top: 1rem; color: var(--text-secondary);">جاري تشغيل نماذج الذكاء الاصطناعي وبناء المعاينة الحية التفاعلية لكل نموذج...</p>
      </div>
    `;

    try {
      const res = await fetch('/api/inference/benchmark/web-design', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
      });
      const data = await res.json();
      renderCodeResults(data.results);
      fetchPoolStatus();
    } catch (err) {
      grid.innerHTML = `<div style="grid-column: 1 / -1; color: var(--accent-red); padding: 2rem;">Error: ${err.message}</div>`;
    } finally {
      runBtn.disabled = false;
      runBtn.innerHTML = `<span>🚀</span> تشغيل الاختبار ومعاينة الكود`;
    }
  });
}

function renderCodeResults(results) {
  const grid = document.getElementById('codeBenchmarkGrid');
  grid.innerHTML = '';

  results.forEach((r, idx) => {
    const card = document.createElement('div');
    card.className = 'benchmark-card glass';

    if (!r.success) {
      card.innerHTML = `
        <div class="benchmark-card-header">
          <div class="model-title">${r.model}</div>
          <span class="pill-invalid">Failed</span>
        </div>
        <p style="color: var(--accent-red);">Error: ${r.error}</p>
      `;
      grid.appendChild(card);
      return;
    }

    const uniqueId = `sandbox_${idx}_${Date.now()}`;
    const cleanHtml = r.extracted_html || '';

    card.innerHTML = `
      <div class="benchmark-card-header">
        <div>
          <div class="model-title">
            <span>🤖 ${r.model}</span>
          </div>
          <div style="margin-top: 4px;">
            <span class="model-badge-code">${r.code_badge}</span>
          </div>
        </div>
        <div class="perf-metrics-badge">
          <span>⚡ ${r.speed_tps} t/s</span>
          <span>•</span>
          <span>⏱️ ${r.duration_sec}s</span>
          <span>•</span>
          <span>🔑 ${r.key_name}</span>
        </div>
      </div>

      <!-- Live Runner Tabs -->
      <div class="code-runner-container">
        <div class="code-tabs-nav">
          <button class="code-tab-btn active" id="tab_prev_btn_${uniqueId}" onclick="switchCodeTab('${uniqueId}', 'preview')">Live Sandbox Preview</button>
          <button class="code-tab-btn" id="tab_src_btn_${uniqueId}" onclick="switchCodeTab('${uniqueId}', 'code')">HTML/CSS/JS Source</button>
        </div>

        <!-- Sandbox iframe -->
        <div id="prev_box_${uniqueId}">
          <iframe id="iframe_${uniqueId}" class="live-preview-iframe" sandbox="allow-scripts allow-modals"></iframe>
        </div>

        <!-- Code Viewer -->
        <div id="code_box_${uniqueId}" style="display: none;">
          <pre class="code-viewer-pre"><code>${escapeHtml(cleanHtml)}</code></pre>
        </div>
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center; margin-top: auto; pt: 8px;">
        <span style="font-size: 0.8rem; color: var(--text-muted); font-family: var(--font-mono);">Tokens: ${r.tokens}</span>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-sm" onclick="downloadHtmlFile('${r.model}', \`${escapeJs(cleanHtml)}\`)">
            <span>💾</span> Download .html
          </button>
          <button class="btn btn-sm btn-primary" onclick="copyText(this, \`${escapeJs(cleanHtml)}\`)">
            <span>📋</span> Copy Code
          </button>
        </div>
      </div>
    `;
    grid.appendChild(card);

    // Populate iframe safely
    setTimeout(() => {
      const iframe = document.getElementById(`iframe_${uniqueId}`);
      if (iframe) {
        iframe.srcdoc = cleanHtml;
      }
    }, 50);
  });
}

window.switchCodeTab = function(uniqueId, tab) {
  const prevBox = document.getElementById(`prev_box_${uniqueId}`);
  const codeBox = document.getElementById(`code_box_${uniqueId}`);
  const prevBtn = document.getElementById(`tab_prev_btn_${uniqueId}`);
  const codeBtn = document.getElementById(`tab_src_btn_${uniqueId}`);

  if (tab === 'preview') {
    prevBox.style.display = 'block';
    codeBox.style.display = 'none';
    prevBtn.classList.add('active');
    codeBtn.classList.remove('active');
  } else {
    prevBox.style.display = 'none';
    codeBox.style.display = 'block';
    prevBtn.classList.remove('active');
    codeBtn.classList.add('active');
  }
};

window.downloadHtmlFile = function(modelName, content) {
  const safeName = modelName.replace(/[^a-zA-Z0-9]/g, '_');
  const blob = new Blob([content], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${safeName}_widget.html`;
  a.click();
  URL.revokeObjectURL(url);
};

window.copySnippet = function(elemId) {
  const elem = document.getElementById(elemId);
  if (elem) {
    navigator.clipboard.writeText(elem.textContent);
    alert('Code snippet copied to clipboard!');
  }
};

window.copyText = function(btn, text) {
  navigator.clipboard.writeText(text);
  const original = btn.innerHTML;
  btn.innerHTML = `<span>✓</span> Copied!`;
  setTimeout(() => btn.innerHTML = original, 2000);
};

// Utilities
function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escapeJs(str) {
  if (!str) return '';
  return str.replace(/\\/g, '\\\\').replace(/`/g, '\\`').replace(/\$/g, '\\$');
}

function roundDec(val, dec = 1) {
  return Math.round(val * Math.pow(10, dec)) / Math.pow(10, dec);
}
