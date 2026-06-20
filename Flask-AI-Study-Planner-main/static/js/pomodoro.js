// pomodoro.js
const CIRCUMFERENCE = 2 * Math.PI * 95; // r=95
let workMin = 25, breakMin = 5;
let totalSeconds = workMin * 60;
let remainingSeconds = totalSeconds;
let isRunning = false;
let isBreak = false;
let timerInterval = null;
let currentSessionId = null;

const display = document.getElementById('timerDisplay');
const label = document.getElementById('timerLabel');
const ring = document.getElementById('progressRing');
const startBtn = document.getElementById('startStopBtn');
const sessionTag = document.getElementById('sessionTypeTag');

function setRing(fraction) {
  ring.style.strokeDashoffset = CIRCUMFERENCE * (1 - fraction);
}

function formatTime(s) {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`;
}

function updateDisplay() {
  display.textContent = formatTime(remainingSeconds);
  setRing(remainingSeconds / totalSeconds);
}

async function toggleTimer() {
  if (isRunning) {
    clearInterval(timerInterval);
    isRunning = false;
    startBtn.textContent = 'Resume';
    label.textContent = 'Paused';
  } else {
    isRunning = true;
    startBtn.textContent = 'Pause';
    label.textContent = isBreak ? 'On break…' : 'Focusing…';

    if (!currentSessionId && !isBreak) {
      await startBackendSession();
    }

    timerInterval = setInterval(async () => {
      remainingSeconds--;
      updateDisplay();
      if (remainingSeconds <= 0) {
        clearInterval(timerInterval);
        isRunning = false;
        await onPhaseEnd();
      }
    }, 1000);
  }
}

async function startBackendSession() {
  const subjectId = document.getElementById('pomoSubject').value || null;
  try {
    const res = await fetch('/api/pomodoro/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subject_id: subjectId, type: 'work', duration_minutes: workMin })
    });
    const data = await res.json();
    currentSessionId = data.session_id;
  } catch(e) { console.error('Failed to start session:', e); }
}

async function onPhaseEnd() {
  if (!isBreak) {
    // Work session ended
    if (currentSessionId) {
      await fetch('/api/pomodoro/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: currentSessionId })
      });
      currentSessionId = null;
    }
    notify('🎉 Work session complete! Take a break.');
    showToast('✓ Session complete! Break time.');
    // Switch to break
    isBreak = true;
    totalSeconds = breakMin * 60;
    remainingSeconds = totalSeconds;
    sessionTag.textContent = 'BREAK TIME';
    sessionTag.style.background = '#f0fdf4';
    sessionTag.style.color = '#15803d';
    label.textContent = 'Break ready — press Start';
    startBtn.textContent = 'Start Break';
  } else {
    // Break ended
    notify('⏰ Break over! Back to work.');
    showToast('Break ended. Ready to focus!');
    isBreak = false;
    totalSeconds = workMin * 60;
    remainingSeconds = totalSeconds;
    sessionTag.textContent = 'WORK SESSION';
    sessionTag.style.background = '';
    sessionTag.style.color = '';
    label.textContent = 'Ready — press Start';
    startBtn.textContent = 'Start';
  }
  updateDisplay();
  loadPomoHistory();
  loadPomoStats();
}

function resetTimer() {
  clearInterval(timerInterval);
  isRunning = false;
  isBreak = false;
  currentSessionId = null;
  totalSeconds = workMin * 60;
  remainingSeconds = totalSeconds;
  startBtn.textContent = 'Start';
  label.textContent = 'Ready to focus';
  sessionTag.textContent = 'WORK SESSION';
  sessionTag.style.background = '';
  sessionTag.style.color = '';
  updateDisplay();
}

function skipPhase() {
  clearInterval(timerInterval);
  isRunning = false;
  remainingSeconds = 0;
  onPhaseEnd();
}

function updateDurations() {
  workMin = parseInt(document.getElementById('customWork').value) || 25;
  breakMin = parseInt(document.getElementById('customBreak').value) || 5;
  document.getElementById('workDuration').textContent = workMin;
  document.getElementById('breakDuration').textContent = breakMin;
  if (!isRunning) {
    totalSeconds = (isBreak ? breakMin : workMin) * 60;
    remainingSeconds = totalSeconds;
    updateDisplay();
  }
}

function notify(msg) {
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification('StudyFlow', { body: msg, icon: '/static/favicon.ico' });
  }
}

async function loadPomoHistory() {
  const res = await fetch('/api/pomodoro/history');
  const sessions = await res.json();
  const el = document.getElementById('pomoHistory');
  if (!sessions.length) {
    el.innerHTML = '<div class="text-muted text-sm">No sessions yet.</div>';
    return;
  }
  el.innerHTML = sessions.map(s => `
    <div class="deadline-item">
      <span class="tag ${s.type === 'work' ? 'tag-maroon' : 'tag-neutral'}" style="min-width:44px;text-align:center;">${s.type}</span>
      <span class="text-sm" style="flex:1;">${s.subject_name ? escHtml(s.subject_name) : 'No subject'}</span>
      <span class="mono text-xs">${s.duration_minutes}m</span>
      <span class="tag ${s.completed ? 'tag-success' : 'tag-neutral'}">${s.completed ? '✓' : '—'}</span>
    </div>
  `).join('');
}

async function loadPomoStats() {
  const res = await fetch('/api/pomodoro/stats');
  const d = await res.json();
  document.getElementById('todaySessions').textContent = d.today_sessions;
  document.getElementById('totalSessions').textContent = d.total_sessions;
}

async function loadSubjectsDropdown() {
  const res = await fetch('/api/subjects');
  const subjects = await res.json();
  const sel = document.getElementById('pomoSubject');
  sel.innerHTML = '<option value="">No subject selected</option>' +
    subjects.map(s => `<option value="${s.id}">${escHtml(s.name)}</option>`).join('');
}

document.addEventListener('DOMContentLoaded', () => {
  ring.style.strokeDasharray = CIRCUMFERENCE;
  ring.style.strokeDashoffset = 0;
  updateDisplay();
  loadPomoHistory();
  loadPomoStats();
  loadSubjectsDropdown();

  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
  }
});
