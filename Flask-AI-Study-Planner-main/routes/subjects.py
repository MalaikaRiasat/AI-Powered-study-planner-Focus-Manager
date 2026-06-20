from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from database import get_db
from datetime import datetime

subjects_bp = Blueprint('subjects', __name__)

@subjects_bp.route('/subjects')
@login_required
def index():
    return render_template('pages/subjects.html')

@subjects_bp.route('/api/subjects', methods=['GET'])
@login_required
def get_subjects():
    db = get_db()
    subjects = db.execute(
        'SELECT * FROM subjects WHERE user_id=? ORDER BY created_at DESC', (current_user.id,)
    ).fetchall()
    result = []
    for s in subjects:
        s_dict = dict(s)
        deadlines = db.execute(
            'SELECT * FROM deadlines WHERE subject_id=? ORDER BY due_date', (s['id'],)
        ).fetchall()
        s_dict['deadlines'] = [dict(d) for d in deadlines]
        result.append(s_dict)
    db.close()
    return jsonify(result)

@subjects_bp.route('/api/subjects', methods=['POST'])
@login_required
def create_subject():
    data = request.json
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    exam_date = data.get('exam_date') or None
    planned_hours = float(data.get('planned_hours_per_week', 0))
    color = data.get('color', '#800020')

    db = get_db()
    cursor = db.execute(
        'INSERT INTO subjects (user_id, name, exam_date, planned_hours_per_week, color) VALUES (?,?,?,?,?)',
        (current_user.id, name, exam_date, planned_hours, color)
    )
    db.commit()
    new_id = cursor.lastrowid
    subject = dict(db.execute('SELECT * FROM subjects WHERE id=?', (new_id,)).fetchone())
    subject['deadlines'] = []
    db.close()
    return jsonify(subject), 201

@subjects_bp.route('/api/subjects/<int:sid>', methods=['PUT'])
@login_required
def update_subject(sid):
    db = get_db()
    subject = db.execute('SELECT * FROM subjects WHERE id=? AND user_id=?', (sid, current_user.id)).fetchone()
    if not subject:
        db.close()
        return jsonify({'error': 'Not found'}), 404

    data = request.json
    db.execute(
        'UPDATE subjects SET name=?, exam_date=?, planned_hours_per_week=?, color=? WHERE id=?',
        (data.get('name', subject['name']),
         data.get('exam_date') or subject['exam_date'],
         float(data.get('planned_hours_per_week', subject['planned_hours_per_week'])),
         data.get('color', subject['color']),
         sid)
    )
    db.commit()
    updated = dict(db.execute('SELECT * FROM subjects WHERE id=?', (sid,)).fetchone())
    deadlines = db.execute('SELECT * FROM deadlines WHERE subject_id=? ORDER BY due_date', (sid,)).fetchall()
    updated['deadlines'] = [dict(d) for d in deadlines]
    db.close()
    return jsonify(updated)

@subjects_bp.route('/api/subjects/<int:sid>', methods=['DELETE'])
@login_required
def delete_subject(sid):
    db = get_db()
    subject = db.execute('SELECT id FROM subjects WHERE id=? AND user_id=?', (sid, current_user.id)).fetchone()
    if not subject:
        db.close()
        return jsonify({'error': 'Not found'}), 404
    db.execute('DELETE FROM subjects WHERE id=?', (sid,))
    db.commit()
    db.close()
    return jsonify({'success': True})

# Deadlines CRUD
@subjects_bp.route('/api/subjects/<int:sid>/deadlines', methods=['POST'])
@login_required
def add_deadline(sid):
    db = get_db()
    subject = db.execute('SELECT id FROM subjects WHERE id=? AND user_id=?', (sid, current_user.id)).fetchone()
    if not subject:
        db.close()
        return jsonify({'error': 'Subject not found'}), 404

    data = request.json
    title = data.get('title', '').strip()
    due_date = data.get('due_date')
    if not title or not due_date:
        db.close()
        return jsonify({'error': 'Title and due date required'}), 400

    cursor = db.execute(
        'INSERT INTO deadlines (subject_id, user_id, title, due_date) VALUES (?,?,?,?)',
        (sid, current_user.id, title, due_date)
    )
    db.commit()
    new_id = cursor.lastrowid
    deadline = dict(db.execute('SELECT * FROM deadlines WHERE id=?', (new_id,)).fetchone())
    db.close()
    return jsonify(deadline), 201

@subjects_bp.route('/api/deadlines/<int:did>', methods=['PUT'])
@login_required
def update_deadline(did):
    db = get_db()
    deadline = db.execute('SELECT * FROM deadlines WHERE id=? AND user_id=?', (did, current_user.id)).fetchone()
    if not deadline:
        db.close()
        return jsonify({'error': 'Not found'}), 404

    data = request.json
    completed = data.get('completed', deadline['completed'])
    title = data.get('title', deadline['title'])
    due_date = data.get('due_date', deadline['due_date'])
    db.execute('UPDATE deadlines SET completed=?, title=?, due_date=? WHERE id=?',
               (1 if completed else 0, title, due_date, did))
    db.commit()
    updated = dict(db.execute('SELECT * FROM deadlines WHERE id=?', (did,)).fetchone())
    db.close()
    return jsonify(updated)

@subjects_bp.route('/api/deadlines/<int:did>', methods=['DELETE'])
@login_required
def delete_deadline(did):
    db = get_db()
    deadline = db.execute('SELECT id FROM deadlines WHERE id=? AND user_id=?', (did, current_user.id)).fetchone()
    if not deadline:
        db.close()
        return jsonify({'error': 'Not found'}), 404
    db.execute('DELETE FROM deadlines WHERE id=?', (did,))
    db.commit()
    db.close()
    return jsonify({'success': True})
