from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from database import get_db

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings')
@login_required
def index():
    return render_template('pages/settings.html')

@settings_bp.route('/api/settings/profile', methods=['PUT'])
@login_required
def update_profile():
    data = request.json
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400

    db = get_db()
    db.execute('UPDATE users SET name=? WHERE id=?', (name, current_user.id))
    db.commit()
    db.close()
    current_user.name = name
    return jsonify({'success': True, 'name': name})

@settings_bp.route('/api/settings/password', methods=['PUT'])
@login_required
def change_password():
    from werkzeug.security import check_password_hash, generate_password_hash
    data = request.json
    current_pw = data.get('current_password', '')
    new_pw = data.get('new_password', '')

    db = get_db()
    user = db.execute('SELECT password_hash FROM users WHERE id=?', (current_user.id,)).fetchone()
    if not check_password_hash(user['password_hash'], current_pw):
        db.close()
        return jsonify({'error': 'Current password is incorrect'}), 400
    if len(new_pw) < 6:
        db.close()
        return jsonify({'error': 'New password must be at least 6 characters'}), 400

    db.execute('UPDATE users SET password_hash=? WHERE id=?',
               (generate_password_hash(new_pw), current_user.id))
    db.commit()
    db.close()
    return jsonify({'success': True})
