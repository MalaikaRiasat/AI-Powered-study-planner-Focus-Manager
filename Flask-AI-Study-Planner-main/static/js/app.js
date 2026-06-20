// ── app.js — Global utilities, notifications, AI coach ──────────────────

// ── Notification Bell ───────────────────────────────────────────────────
let notifOpen = false;

async function loadNotifications() {
  try {
    const res = await fetch('/api/notifications');
    const data = await res.json();
    const badge = document.getElementById('bellBadge');
    const list = document.getElementById('notifList');

    const count = data.unread_count || 0;
    if (count > 0) {
      badge.style.display = 'flex';
      badge.textContent = count > 9 ? '9+' : count;
    } else {
      badge.style.display = 'none';
    }

    const all = data.dynamic || [];
    if (all.length === 0) {
      list.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:0.82rem;">All clear — no notifications.</div>';
      return;
    }

    list.innerHTML = all.map(n => `
      <div class="notif-item">
        <div class="notif-dot ${n.priority}"></div>
        <div style="flex:1;">
          <div style="font-size:0.82rem;">${n.message}</div>
          <div class="text-xs text-muted" style="margin-top:2px;text-transform:uppercase;letter-spacing:.06em;">${n.type}</div>
        </div>
      </div>
    `).join('');
  } catch(e) {
    console.error('Notif load error:', e);
  }
}

function toggleNotifDropdown() {
  const dd = document.getElementById('notifDropdown');
  notifOpen = !notifOpen;
  dd.classList.toggle('open', notifOpen);
  if (notifOpen) loadNotifications();
}

async function markAllRead() {
  await fetch('/api/notifications/read-all', { method: 'POST' });
  document.getElementById('bellBadge').style.display = 'none';
  loadNotifications();
}

document.addEventListener('click', (e) => {
  if (notifOpen && !e.target.closest('#notifDropdown') && !e.target.closest('#bellBtn')) {
    document.getElementById('notifDropdown').classList.remove('open');
    notifOpen = false;
  }
});

// ── AI Coach Panel ───────────────────────────────────────────────────────
let aiPanelOpen = false;

function toggleAIPanel() {
  aiPanelOpen = !aiPanelOpen;
  document.getElementById('aiPanel').classList.toggle('open', aiPanelOpen);
  document.getElementById('aiToggle').classList.toggle('panel-open', aiPanelOpen);
  if (aiPanelOpen) document.getElementById('aiInput').focus();
}

async function sendAIMessage() {
  const input = document.getElementById('aiInput');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';

  const msgBox = document.getElementById('aiMessages');
  msgBox.innerHTML += `<div class="ai-msg user fade-in">${escHtml(msg)}</div>`;
  msgBox.innerHTML += `<div class="ai-msg assistant typing fade-in" id="aiTyping">✦ Thinking…</div>`;
  msgBox.scrollTop = msgBox.scrollHeight;

  try {
    const res = await fetch('/api/ai/coach', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    });
    const data = await res.json();
    document.getElementById('aiTyping').remove();
    const reply = data.reply || 'Sorry, I could not get a response.';
    msgBox.innerHTML += `<div class="ai-msg assistant fade-in">${markdownToHtml(reply)}</div>`;
  } catch(e) {
    document.getElementById('aiTyping').remove();
    msgBox.innerHTML += `<div class="ai-msg assistant fade-in">Connection error. Please try again.</div>`;
  }
  msgBox.scrollTop = msgBox.scrollHeight;
}

// ── AI Reschedule Modal ──────────────────────────────────────────────────
let aiScheduleSessions = [];

async function openRescheduleModal() {
  const modal = document.getElementById('rescheduleModal');
  const body = document.getElementById('rescheduleBody');
  const btn = document.getElementById('acceptAIBtn');
  modal.classList.add('open');
  body.innerHTML = '<div class="pulse" style="text-align:center;padding:32px;color:var(--text-muted);">✦ Gemini is generating your reschedule…</div>';
  btn.disabled = true;
  aiScheduleSessions = [];

  try {
    const res = await fetch('/api/ai/reschedule', { method: 'POST', headers: {'Content-Type':'application/json'}, body: '{}' });
    const data = await res.json();
    if (data.error) {
      body.innerHTML = `<div class="flash error">${escHtml(data.error)}</div>`;
      return;
    }
    if (!data.sessions || data.sessions.length === 0) {
      body.innerHTML = '<div class="empty-state"><h3>No missed tasks</h3><p>Nothing to reschedule right now.</p></div>';
      return;
    }
    aiScheduleSessions = data.sessions;
    body.innerHTML = `
      <p class="text-sm text-muted mb-16">Gemini has rescheduled <strong>${data.missed_count}</strong> missed task(s) across the next 7 days:</p>
      <div style="display:flex;flex-direction:column;gap:8px;">
        ${data.sessions.map(s => `
          <div class="card card-sm" style="border-left:3px solid var(--maroon);border-radius:0 4px 4px 0;">
            <div class="flex-between">
              <div>
                <div class="fw-bold text-sm">${escHtml(s.subject_name)}</div>
                <div class="text-xs text-muted">${s.scheduled_date} · ${s.planned_hours}h</div>
              </div>
              <div class="text-xs text-muted" style="max-width:160px;text-align:right;">${escHtml(s.reason || '')}</div>
            </div>
          </div>
        `).join('')}
      </div>
    `;
    btn.disabled = false;
  } catch(e) {
    body.innerHTML = `<div class="flash error">Failed to get AI response: ${escHtml(e.message)}</div>`;
  }
}

function closeRescheduleModal() {
  document.getElementById('rescheduleModal').classList.remove('open');
}

async function acceptAISchedule() {
  if (!aiScheduleSessions.length) return;
  const btn = document.getElementById('acceptAIBtn');
  btn.disabled = true;
  btn.textContent = 'Saving…';

  try {
    const res = await fetch('/api/schedule/accept-ai', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sessions: aiScheduleSessions })
    });
    const data = await res.json();
    if (data.success) {
      closeRescheduleModal();
      showToast(`✓ ${data.added} sessions added to your schedule.`);
      if (typeof loadSchedule === 'function') loadSchedule();
    }
  } catch(e) {
    showToast('Error saving schedule. Please try again.', true);
  }
  btn.disabled = false;
  btn.textContent = 'Accept Plan';
}

// ── Utilities ────────────────────────────────────────────────────────────
function escHtml(str) {
  const d = document.createElement('div');
  d.textContent = str || '';
  return d.innerHTML;
}

function markdownToHtml(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    .replace(/\n/g, '<br/>');
}

function showToast(msg, isError = false) {
  const t = document.createElement('div');
  t.className = `flash ${isError ? 'error' : 'success'} fade-in`;
  t.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:999;min-width:260px;';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

function fmtDate(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function fmtDateShort(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Load notification badge on every page
window.addEventListener('DOMContentLoaded', () => {
  loadNotifications();
  setInterval(loadNotifications, 60000);
});
