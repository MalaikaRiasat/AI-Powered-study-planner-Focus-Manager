// subjects.js
let subjects = [];
let editingSubjectId = null;
let addingDeadlineForSubject = null;

async function loadSubjects() {
  const res = await fetch('/api/subjects');
  subjects = await res.json();
  renderSubjects();
}

function renderSubjects() {
  const grid = document.getElementById('subjectGrid');
  if (!subjects.length) {
    grid.innerHTML = `
      <div class="empty-state" style="grid-column:1/-1;">
        <h3>No subjects yet</h3>
        <p>Add your first subject to get started.</p>
      </div>`;
    return;
  }

  grid.innerHTML = subjects.map(s => {
    const now = new Date();
    const exam = s.exam_date ? new Date(s.exam_date) : null;
    const daysLeft = exam ? Math.ceil((exam - now) / 86400000) : null;
    const isMissed = exam && exam < now;

    const deadlinesHtml = s.deadlines && s.deadlines.length
      ? s.deadlines.map(d => {
          const past = !d.completed && new Date(d.due_date) < now;
          return `
            <div class="deadline-item ${d.completed ? 'done' : ''} ${past ? 'missed-card' : ''}" style="padding:6px 4px;">
              <input type="checkbox" class="deadline-check" ${d.completed ? 'checked' : ''}
                     onchange="toggleDeadline(${d.id}, this.checked)"/>
              <span class="deadline-title" style="flex:1;">${escHtml(d.title)}</span>
              ${past && !d.completed ? '<span class="missed-badge">Missed</span>' : ''}
              <span class="text-xs text-muted">${fmtDateShort(d.due_date)}</span>
              <button onclick="deleteDeadline(${d.id})" class="btn btn-ghost btn-sm" style="padding:2px 6px;font-size:0.7rem;">×</button>
            </div>`;
        }).join('')
      : '<div class="text-muted text-sm">No deadlines added.</div>';

    return `
      <div class="subject-card fade-in ${isMissed ? 'missed-card' : ''}">
        <div class="flex-between" style="margin-bottom:8px;">
          <div class="subject-name">${escHtml(s.name)}</div>
          <div class="flex gap-8">
            <button class="btn btn-ghost btn-sm" onclick="openSubjectModal(${s.id})">Edit</button>
            <button class="btn btn-danger btn-sm" onclick="deleteSubject(${s.id})">Delete</button>
          </div>
        </div>
        <div class="subject-meta">
          <span>📅 Exam: ${s.exam_date ? fmtDate(s.exam_date) : 'Not set'}</span>
          ${daysLeft !== null ? `<span class="${daysLeft < 0 ? 'text-maroon' : ''}">${daysLeft < 0 ? '⚠ Exam passed' : daysLeft === 0 ? '⚠ Exam today!' : daysLeft + ' days left'}</span>` : ''}
          <span>⏱ ${s.planned_hours_per_week}h/week</span>
        </div>

        <div style="margin-bottom:8px;">
          <div class="text-xs text-muted fw-bold" style="text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">Deadlines</div>
          ${deadlinesHtml}
        </div>

        <button class="btn btn-outline btn-sm" onclick="openDeadlineModal(${s.id})" style="width:100%;justify-content:center;">+ Add Deadline</button>
      </div>`;
  }).join('');
}

function openSubjectModal(id = null) {
  editingSubjectId = id;
  const modal = document.getElementById('subjectModal');
  document.getElementById('subjectModalTitle').textContent = id ? 'Edit Subject' : 'Add Subject';

  if (id) {
    const s = subjects.find(x => x.id === id);
    document.getElementById('subjectName').value = s.name;
    document.getElementById('subjectExamDate').value = s.exam_date || '';
    document.getElementById('subjectHours').value = s.planned_hours_per_week;
  } else {
    document.getElementById('subjectName').value = '';
    document.getElementById('subjectExamDate').value = '';
    document.getElementById('subjectHours').value = '';
  }
  modal.classList.add('open');
}

function closeSubjectModal() {
  document.getElementById('subjectModal').classList.remove('open');
  editingSubjectId = null;
}

async function saveSubject() {
  const name = document.getElementById('subjectName').value.trim();
  const exam_date = document.getElementById('subjectExamDate').value || null;
  const planned_hours_per_week = parseFloat(document.getElementById('subjectHours').value) || 0;
  if (!name) { showToast('Subject name is required.', true); return; }

  const url = editingSubjectId ? `/api/subjects/${editingSubjectId}` : '/api/subjects';
  const method = editingSubjectId ? 'PUT' : 'POST';
  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, exam_date, planned_hours_per_week })
  });
  if (res.ok) {
    closeSubjectModal();
    showToast(editingSubjectId ? '✓ Subject updated.' : '✓ Subject added.');
    loadSubjects();
  } else {
    showToast('Failed to save subject.', true);
  }
}

async function deleteSubject(id) {
  if (!confirm('Delete this subject and all its data?')) return;
  const res = await fetch(`/api/subjects/${id}`, { method: 'DELETE' });
  if (res.ok) { showToast('Subject deleted.'); loadSubjects(); }
}

function openDeadlineModal(subjectId) {
  addingDeadlineForSubject = subjectId;
  document.getElementById('deadlineTitle').value = '';
  document.getElementById('deadlineDue').value = '';
  document.getElementById('deadlineModal').classList.add('open');
}

function closeDeadlineModal() {
  document.getElementById('deadlineModal').classList.remove('open');
  addingDeadlineForSubject = null;
}

async function saveDeadline() {
  const title = document.getElementById('deadlineTitle').value.trim();
  const due_date = document.getElementById('deadlineDue').value;
  if (!title || !due_date) { showToast('Title and date required.', true); return; }

  const res = await fetch(`/api/subjects/${addingDeadlineForSubject}/deadlines`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, due_date })
  });
  if (res.ok) {
    closeDeadlineModal();
    showToast('✓ Deadline added.');
    loadSubjects();
  } else {
    showToast('Failed to add deadline.', true);
  }
}

async function toggleDeadline(id, completed) {
  await fetch(`/api/deadlines/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ completed })
  });
  loadSubjects();
}

async function deleteDeadline(id) {
  const res = await fetch(`/api/deadlines/${id}`, { method: 'DELETE' });
  if (res.ok) { showToast('Deadline removed.'); loadSubjects(); }
}

document.addEventListener('DOMContentLoaded', loadSubjects);
