// settings.js
async function saveProfile() {
  const name = document.getElementById('settingName').value.trim();
  if (!name) { showToast('Name is required.', true); return; }
  const res = await fetch('/api/settings/profile', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name })
  });
  const data = await res.json();
  if (res.ok) {
    showToast('✓ Profile updated.');
    document.getElementById('userAvatar').textContent = name[0].toUpperCase();
  } else {
    showToast(data.error || 'Failed to update.', true);
  }
}

async function changePassword() {
  const current_password = document.getElementById('currentPw').value;
  const new_password = document.getElementById('newPw').value;
  const confirm = document.getElementById('confirmPw').value;

  if (!current_password || !new_password) { showToast('All fields required.', true); return; }
  if (new_password !== confirm) { showToast('New passwords do not match.', true); return; }
  if (new_password.length < 6) { showToast('Password must be at least 6 characters.', true); return; }

  const res = await fetch('/api/settings/password', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ current_password, new_password })
  });
  const data = await res.json();
  if (res.ok) {
    showToast('✓ Password changed.');
    document.getElementById('currentPw').value = '';
    document.getElementById('newPw').value = '';
    document.getElementById('confirmPw').value = '';
  } else {
    showToast(data.error || 'Failed to change password.', true);
  }
}
