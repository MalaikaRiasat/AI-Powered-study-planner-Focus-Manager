// schedule.js
let scheduleData = [];

async function loadSchedule() {
  const [sessRes, missedRes] = await Promise.all([
    fetch('/api/schedule'),
    fetch('/api/missed-tasks')
  ]);
  scheduleData = await sessRes.json();
  const missed = await missedRes.json();

  renderWeekGrid(scheduleData);
  renderSessionsTable(scheduleData);
  renderMissed(missed);
}

function renderWeekGrid(sessions) {
  const grid = document.getElementById('scheduleGrid');
  const days = [];
  const today = new Date();
  for (let i = 0; i < 7; i++) {
    const d = new Date(today);
    d.setDate(today.getDate() - today.getDay() + i);
    days.push(d);
  }

  grid.innerHTML = days.map(day => {
    const iso = day.toISOString().split('T')[0];
    const isToday = iso === today.toISOString().split('T')[0];
    const daySessions = sessions.filter(s => s.scheduled_date === iso);
    return `
      <div class="schedule-day ${isToday ? 'today' : ''}">
        <div class="schedule-day-label">${day.toLocaleDateString('en-US',{weekday:'short'})} ${day.getDate()}</div>
        ${daySessions.map(s => `
          <div class="schedule-session ${s.completed ? 'opacity-50' : ''}">
            <div class="fw-bold" style="font-size:0.7rem;">${escHtml(s.subject_name)}</div>
            <div style="font-size:0.65rem;color:var(--text-muted);">${s.planned_hours}h</div>
          </div>
        `).join('') || '<div style="font-size:0.65rem;color:var(--text-muted);margin-top:4px;">—</div>'}
      </div>`;
  }).join('');
}

function renderSessionsTable(sessions) {
  const tbody = document.getElementById('sessionsBody');
  if (!sessions.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-muted text-sm" style="text-align:center;padding:24px;">No scheduled sessions. Add one or use AI Reschedule.</td></tr>';
    return;
  }
  tbody.innerHTML = sessions.map(s => `
    <tr>
      <td class="mono text-sm">${fmtDate(s.scheduled_date)}</td>
      <td><span class="fw-bold">${escHtml(s.subject_name)}</span></td>
      <td class="mono">${s.planned_hours}h</td>
      <td>${s.ai_generated ? '<span class="tag tag-maroon">AI</span>' : '<span class="tag tag-neutral">Manual</span>'}</td>
      <td>${s.completed ? '<span class="tag tag-success">Done</span>' : '<span class="tag tag-neutral">Pending</span>'}</td>
      <td>
        <div class="flex gap-8">
          ${!s.completed ? `<button class="btn btn-ghost btn-sm" onclick="completeSession(${s.id})">✓ Done</button>` : ''}
          <button class="btn btn-danger btn-sm" onclick="deleteSession(${s.id})">×</button>
        </div>
      </td>
    </tr>
  `).join('');
}

function renderMissed(missed) {
  const sec = document.getElementById('missedSection');
  const list = document.getElementById('missedList');
  if (missed.total === 0) { sec.classList.add('hidden'); return; }
  sec.classList.remove('hidden');

  const allMissed = [
    ...missed.missed_deadlines.map(m => ({ ...m, kind: 'Deadline' })),
    ...missed.missed_sessions.map(m => ({ ...m, kind: 'Session' }))
  ];

  list.innerHTML = allMissed.map(m => `
    <div class="deadline-item">
      <span class="missed-badge">${m.kind}</span>
      <span class="text-sm" style="flex:1;">${escHtml(m.subject_name)} — ${escHtml(m.title)}</span>
      <span class="text-xs text-muted">${fmtDate(m.due_date)}</span>
    </div>
  `).join('');
}

async function completeSession(id) {
  const res = await fetch(`/api/schedule/${id}/complete`, { method: 'POST' });
  if (res.ok) { showToast('✓ Session marked complete.'); loadSchedule(); }
}

async function deleteSession(id) {
  if (!confirm('Remove this session?')) return;
  const res = await fetch(`/api/schedule/${id}`, { method: 'DELETE' });
  if (res.ok) { showToast('Session removed.'); loadSchedule(); }
}

async function openAddSessionModal() {
  const res = await fetch('/api/subjects');
  const subjects = await res.json();
  const sel = document.getElementById('sessionSubject');
  sel.innerHTML = subjects.map(s => `<option value="${s.id}">${escHtml(s.name)}</option>`).join('');
  document.getElementById('sessionDate').value = new Date().toISOString().split('T')[0];
  document.getElementById('sessionHours').value = '2';
  document.getElementById('addSessionModal').classList.add('open');
}

async function addSession() {
  const subject_id = document.getElementById('sessionSubject').value;
  const scheduled_date = document.getElementById('sessionDate').value;
  const planned_hours = document.getElementById('sessionHours').value;
  if (!subject_id || !scheduled_date || !planned_hours) { showToast('All fields required.', true); return; }

  const res = await fetch('/api/schedule', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subject_id, scheduled_date, planned_hours: parseFloat(planned_hours) })
  });
  if (res.ok) {
    document.getElementById('addSessionModal').classList.remove('open');
    showToast('✓ Session added.');
    loadSchedule();
  } else {
    showToast('Failed to add session.', true);
  }
}

document.addEventListener('DOMContentLoaded', loadSchedule);
