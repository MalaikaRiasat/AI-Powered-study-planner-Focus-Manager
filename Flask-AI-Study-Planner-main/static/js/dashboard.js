// dashboard.js
let weeklyChart = null;

async function loadDashboard() {
  const res = await fetch('/api/dashboard/stats');
  const d = await res.json();

  document.getElementById('statSubjects').textContent = d.subjects_count;
  document.getElementById('statCompleted').textContent = d.completed_hours + 'h';
  document.getElementById('statPlannedSub').textContent = `of ${d.planned_hours}h planned`;
  document.getElementById('statPomodoro').textContent = d.pomodoro_count;
  document.getElementById('statMissed').textContent = d.missed_count;

  // Missed banner
  if (d.missed_count > 0) {
    document.getElementById('missedBanner').classList.remove('hidden');
    document.getElementById('missedBannerText').textContent =
      `${d.missed_count} task(s) overdue. Let AI create a new plan.`;
  }

  // Upcoming exams
  const examsEl = document.getElementById('upcomingExams');
  if (!d.upcoming_exams.length) {
    examsEl.innerHTML = '<div class="text-muted text-sm">No exams in the next 7 days.</div>';
  } else {
    examsEl.innerHTML = d.upcoming_exams.map(e => `
      <div class="deadline-item">
        <div style="flex:1;">
          <span class="fw-bold text-sm">${escHtml(e.name)}</span>
          <span class="text-xs text-muted" style="margin-left:8px;">${fmtDate(e.exam_date)}</span>
        </div>
        <span class="missed-badge">Exam</span>
      </div>
    `).join('');
  }

  // Recent activity
  const actEl = document.getElementById('recentActivity');
  if (!d.recent_logs.length) {
    actEl.innerHTML = '<div class="text-muted text-sm">No sessions logged yet.</div>';
  } else {
    actEl.innerHTML = d.recent_logs.map(l => `
      <div class="deadline-item">
        <div style="flex:1;">
          <span class="fw-bold text-sm">${escHtml(l.subject)}</span>
          <span class="text-xs text-muted" style="margin-left:8px;">${fmtDate(l.date)}</span>
        </div>
        <span class="mono text-sm fw-bold" style="color:var(--maroon);">${l.hours}h</span>
      </div>
    `).join('');
  }

  // Chart
  renderWeeklyChart(d.chart_data);
}

function renderWeeklyChart(data) {
  const ctx = document.getElementById('weeklyChart').getContext('2d');
  if (weeklyChart) weeklyChart.destroy();

  weeklyChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.map(d => d.date),
      datasets: [
        {
          label: 'Planned',
          data: data.map(d => d.planned || 0),
          backgroundColor: '#F2EDE8',
          borderColor: '#e0d5cc',
          borderWidth: 1,
          borderRadius: 3,
        },
        {
          label: 'Completed',
          data: data.map(d => d.completed),
          backgroundColor: '#800020',
          borderColor: '#5c0016',
          borderWidth: 1,
          borderRadius: 3,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { font: { family: 'Lato', size: 12 }, color: '#6b6b6b' }
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { family: 'JetBrains Mono', size: 11 }, color: '#6b6b6b' } },
        y: { grid: { color: '#f0e8e0' }, ticks: { font: { family: 'JetBrains Mono', size: 11 }, color: '#6b6b6b' }, beginAtZero: true }
      }
    }
  });
}

async function loadSubjectsForDropdown() {
  const res = await fetch('/api/subjects');
  const subjects = await res.json();
  const sel = document.getElementById('logSubject');
  sel.innerHTML = '<option value="">Select subject…</option>' +
    subjects.map(s => `<option value="${s.id}">${escHtml(s.name)}</option>`).join('');
}

document.addEventListener('DOMContentLoaded', () => {
  // Set today's date as default
  document.getElementById('logDate').value = new Date().toISOString().split('T')[0];

  loadDashboard();
  loadSubjectsForDropdown();

  document.getElementById('logHoursForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const subject_id = document.getElementById('logSubject').value;
    const date = document.getElementById('logDate').value;
    const hours = document.getElementById('logHours').value;
    if (!subject_id || !hours) return;

    const res = await fetch('/api/study-logs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subject_id, date, hours: parseFloat(hours) })
    });
    if (res.ok) {
      showToast('✓ Study hours logged successfully.');
      document.getElementById('logHours').value = '';
      loadDashboard();
    } else {
      showToast('Failed to log hours.', true);
    }
  });
});
