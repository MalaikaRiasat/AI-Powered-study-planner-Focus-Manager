// notifications.js
async function loadNotificationsPage() {
  const res = await fetch('/api/notifications');
  const data = await res.json();
  const all = data.dynamic || [];

  const urgent = all.filter(n => n.priority === 'urgent');
  const high = all.filter(n => n.priority === 'high');
  const sessions = all.filter(n => n.type === 'session');
  const stored = data.stored || [];

  renderGroup('urgentNotifs', urgent, 'No missed tasks. You\'re on track!');
  renderGroup('highNotifs', high, 'No upcoming exams or deadlines.');
  renderGroup('sessionNotifs', sessions, 'No sessions scheduled for today.');
  renderStoredGroup('storedNotifs', stored);
}

function renderGroup(elId, items, emptyMsg) {
  const el = document.getElementById(elId);
  if (!items.length) {
    el.innerHTML = `<div class="text-muted text-sm">${emptyMsg}</div>`;
    return;
  }
  el.innerHTML = items.map(n => `
    <div class="notif-item" style="padding:10px 0;border-bottom:1px solid var(--border);">
      <div class="notif-dot ${n.priority}"></div>
      <div style="flex:1;">
        <div class="text-sm">${escHtml(n.message)}</div>
        <div class="text-xs text-muted" style="margin-top:2px;text-transform:uppercase;letter-spacing:.06em;">${n.type}</div>
      </div>
    </div>
  `).join('');
}

function renderStoredGroup(elId, items) {
  const el = document.getElementById(elId);
  if (!items.length) {
    el.innerHTML = '<div class="text-muted text-sm">No system messages.</div>';
    return;
  }
  el.innerHTML = items.map(n => `
    <div class="notif-item ${n.read ? 'opacity-70' : ''}" style="padding:10px 0;border-bottom:1px solid var(--border);">
      <div class="notif-dot medium"></div>
      <div style="flex:1;">
        <div class="text-sm">${escHtml(n.message)}</div>
        <div class="text-xs text-muted">${fmtDate(n.created_at)}</div>
      </div>
      ${!n.read ? `<button class="btn btn-ghost btn-sm" onclick="markRead(${n.id})">Read</button>` : ''}
    </div>
  `).join('');
}

async function markRead(id) {
  await fetch(`/api/notifications/${id}/read`, { method: 'POST' });
  loadNotificationsPage();
  loadNotifications(); // Update bell
}

document.addEventListener('DOMContentLoaded', loadNotificationsPage);
