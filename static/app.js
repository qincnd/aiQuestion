// SPDX-FileCopyrightText: 2026 qincnd <qincnd@qq.com>
// SPDX-FileCopyrightText: 2026 Xue Zicheng <xuezicheng842@outlook.com>
// SPDX-License-Identifier: MIT
//
// Original code created by qincnd <qincnd@qq.com>
// Modified by Xue Zicheng <xuezicheng842@outlook.com>
const startButton = document.querySelector('#startButton');
const stopButton = document.querySelector('#stopButton');
const saveButton = document.querySelector('#saveButton');
const reloadButton = document.querySelector('#reloadButton');
const rawToggle = document.querySelector('#rawToggle');
const rawPanel = document.querySelector('#rawPanel');
const rawEditor = document.querySelector('#rawEditor');
const rawSave = document.querySelector('#rawSave');
const rawBack = document.querySelector('#rawBack');
const saveStatus = document.querySelector('#saveStatus');
const statusPill = document.querySelector('#statusPill');
const message = document.querySelector('#message');
const screenText = document.querySelector('#screenText');
const aiLog = document.querySelector('#aiLog');
const configForm = document.querySelector('#configForm');
const tabRun = document.querySelector('#tab-run');
const tabSettings = document.querySelector('#tab-settings');

let aiLogRendered = [];

/* ---------- 工具函数 ---------- */
function getByPath(obj, path) {
  return path.split('.').reduce((o, k) => (o == null ? undefined : o[k]), obj);
}
function setByPath(obj, path, value) {
  const keys = path.split('.');
  let cur = obj;
  for (let i = 0; i < keys.length - 1; i++) {
    if (cur[keys[i]] == null || typeof cur[keys[i]] !== 'object') cur[keys[i]] = {};
    cur = cur[keys[i]];
  }
  cur[keys[keys.length - 1]] = value;
}

/* ---------- 表单 -> config 对象 ---------- */
function formToConfig() {
  const config = { ai: {}, bot: {} };
  const data = new FormData(configForm);
  for (const [key, value] of data.entries()) {
    if (!key.includes('.')) continue;
    const field = configForm.elements[key];
    let v = value;
    if (field && field.type === 'number') {
      v = value === '' ? '' : Number(value);
    }
    setByPath(config, key, v);
  }
  // checkbox 单独处理（未勾选时 FormData 不含该 key）
  const notify = configForm.elements['bot.notify_on_submit'];
  if (notify) setByPath(config, 'bot.notify_on_submit', notify.checked);
  return config;
}

/* ---------- config 对象 -> 表单 ---------- */
function configToForm(config) {
  const fields = configForm.querySelectorAll('input[name], textarea[name], select[name]');
  fields.forEach((field) => {
    const path = field.name;
    if (!path.includes('.')) return;
    const value = getByPath(config, path);
    if (value === undefined || value === null) {
      if (field.type === 'checkbox') field.checked = false;
      else field.value = '';
      return;
    }
    if (field.type === 'checkbox') field.checked = Boolean(value);
    else field.value = value;
  });
}

/* ---------- 加载 / 保存 ---------- */
async function loadConfig() {
  const resp = await fetch('/api/config');
  const data = await resp.json();
  if (!resp.ok) {
    saveStatus.textContent = data.error || 'config.json 不存在';
    saveStatus.className = 'save-status error';
    return;
  }
  configToForm(data.config);
  rawEditor.value = JSON.stringify(data.config, null, 2);
}

async function saveFormConfig() {
  const config = formToConfig();
  saveButton.disabled = true;
  saveStatus.textContent = '正在保存...';
  saveStatus.className = 'save-status';
  try {
    const resp = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ config }),
    });
    const data = await resp.json();
    if (resp.ok) {
      saveStatus.textContent = '配置已保存';
      saveStatus.className = 'save-status success';
      rawEditor.value = JSON.stringify(config, null, 2);
    } else {
      saveStatus.textContent = data.error || '保存失败';
      saveStatus.className = 'save-status error';
    }
  } catch {
    saveStatus.textContent = '网络错误，保存失败';
    saveStatus.className = 'save-status error';
  } finally {
    saveButton.disabled = false;
  }
}

/* ---------- 运行监视 ---------- */
function renderLog(events) {
  if (!Array.isArray(events)) return;
  if (events.length === aiLogRendered.length) return;
  aiLogRendered = events;
  const lines = events.map((e) => {
    if (e.type === 'tool_call') return `→ ${e.name}(${e.arguments})`;
    if (e.type === 'tool_result') return `← ${e.name}: ${e.result}`;
    if (e.type === 'assistant') return `AI: ${e.content}`;
    return JSON.stringify(e);
  });
  aiLog.textContent = lines.join('\n') || '暂无';
}

function update(data) {
  message.textContent = data.message || '等待开始';
  screenText.textContent = data.last_screen_text || '暂无';
  renderLog(data.ai_log || []);
  statusPill.className = `status-pill ${data.running ? 'running' : (data.message || '').startsWith('错误') ? 'error' : 'idle'}`;
  statusPill.innerHTML = `<span></span>${data.running ? '运行中' : '未运行'}`;
  startButton.disabled = data.running;
}

async function refresh() {
  const response = await fetch('/api/status');
  update(await response.json());
}

/* ---------- 事件绑定 ---------- */
startButton.addEventListener('click', async () => {
  // 启动前保存一次表单
  await saveFormConfig();
  const resp = await fetch('/api/start', { method: 'POST' });
  const data = await resp.json();
  if (!resp.ok) alert(data.error || '启动失败');
  await refresh();
});

stopButton.addEventListener('click', async () => {
  await fetch('/api/stop', { method: 'POST' });
  await refresh();
});

saveButton.addEventListener('click', saveFormConfig);

reloadButton.addEventListener('click', loadConfig);

rawToggle.addEventListener('click', async () => {
  // 打开 raw 前，先把表单内容同步过去
  rawEditor.value = JSON.stringify(formToConfig(), null, 2);
  configForm.hidden = true;
  rawPanel.hidden = false;
});

rawBack.addEventListener('click', async () => {
  // 返回表单前，把 raw 内容解析回表单
  try {
    const parsed = JSON.parse(rawEditor.value);
    configToForm(parsed);
  } catch (e) {
    alert('JSON 格式错误，无法返回表单：' + e.message);
    return;
  }
  configForm.hidden = false;
  rawPanel.hidden = true;
});

rawSave.addEventListener('click', async () => {
  let parsed;
  try {
    parsed = JSON.parse(rawEditor.value);
  } catch (e) {
    saveStatus.textContent = 'JSON 格式错误：' + e.message;
    saveStatus.className = 'save-status error';
    return;
  }
  const resp = await fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ config: parsed }),
  });
  const data = await resp.json();
  if (resp.ok) {
    saveStatus.textContent = 'JSON 已保存';
    saveStatus.className = 'save-status success';
    configToForm(parsed);
  } else {
    saveStatus.textContent = data.error || '保存失败';
    saveStatus.className = 'save-status error';
  }
});

loadConfig().then(refresh);
setInterval(refresh, 1000);