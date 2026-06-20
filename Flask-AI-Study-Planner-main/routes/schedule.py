from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from database import get_db
from datetime import datetime, date, timedelta

schedule_bp = Blueprint('schedule', __name__)

@schedule_bp.route('/schedule')
@login_required
def index():
    return render_template('pages/schedule.html')

@schedule_bp.route('/api/schedule', methods=['GET'])
@login_required
def get_schedule():
    db = get_db()
    uid = current_user.id
    today = date.today()
    two_weeks = today + timedelta(days=14)

    sessions = db.execute(
        """SELECT ss.*, s.name as subject_name, s.color as subject_color, s.exam_date
           FROM scheduled_sessions ss
           JOIN subjects s ON ss.subject_id=s.id
           WHERE ss.user_id=? AND ss.scheduled_date BETWEEN ? AND ?
           ORDER BY ss.scheduled_date""",
        (uid, today.isoformat(), two_weeks.isoformat())
    ).fetchall()
    db.close()
    return jsonify([dict(s) for s in sessions])

@schedule_bp.route('/api/schedule', methods=['POST'])
@login_required
def add_session():
    data = request.json
    db = get_db()
    subject = db.execute('SELECT id FROM subjects WHERE id=? AND user_id=?',
                         (data.get('subject_id'), current_user.id)).fetchone()
    if not subject:
        db.close()
        return jsonify({'error': 'Subject not found'}), 404

    cursor = db.execute(
        'INSERT INTO scheduled_sessions (user_id, subject_id, scheduled_date, planned_hours) VALUES (?,?,?,?)',
        (current_user.id, data['subject_id'], data['scheduled_date'], float(data.get('planned_hours', 1)))
    )
    db.commit()
    new_id = cursor.lastrowid
    session = dict(db.execute(
        'SELECT ss.*, s.name as subject_name FROM scheduled_sessions ss JOIN subjects s ON ss.subject_id=s.id WHERE ss.id=?',
        (new_id,)
    ).fetchone())
    db.close()
    return jsonify(session), 201

@schedule_bp.route('/api/schedule/<int:sid>/complete', methods=['POST'])
@login_required
def complete_session(sid):
    db = get_db()
    session = db.execute('SELECT * FROM scheduled_sessions WHERE id=? AND user_id=?', (sid, current_user.id)).fetchone()
    if not session:
        db.close()
        return jsonify({'error': 'Not found'}), 404
    db.execute('UPDATE scheduled_sessions SET completed=1 WHERE id=?', (sid,))
    db.commit()
    db.close()
    return jsonify({'success': True})

@schedule_bp.route('/api/schedule/<int:sid>', methods=['DELETE'])
@login_required
def delete_session(sid):
    db = get_db()
    session = db.execute('SELECT id FROM scheduled_sessions WHERE id=? AND user_id=?', (sid, current_user.id)).fetchone()
    if not session:
        db.close()
        return jsonify({'error': 'Not found'}), 404
    db.execute('DELETE FROM scheduled_sessions WHERE id=?', (sid,))
    db.commit()
    db.close()
    return jsonify({'success': True})

@schedule_bp.route('/api/missed-tasks')
@login_required
def missed_tasks():
    db = get_db()
    uid = current_user.id
    now = datetime.now().isoformat()
    today = date.today().isoformat()

    missed_deadlines = db.execute(
        """SELECT d.id, d.title, d.due_date, 'deadline' as task_type, s.name as subject_name
           FROM deadlines d JOIN subjects s ON d.subject_id=s.id
           WHERE d.user_id=? AND d.due_date < ? AND d.completed=0
           ORDER BY d.due_date""",
        (uid, now)
    ).fetchall()

    missed_sessions = db.execute(
        """SELECT ss.id, ss.scheduled_date || ' - Study Session' as title, ss.scheduled_date as due_date,
                  'session' as task_type, s.name as subject_name, ss.planned_hours
           FROM scheduled_sessions ss JOIN subjects s ON ss.subject_id=s.id
           WHERE ss.user_id=? AND ss.scheduled_date < ? AND ss.completed=0
           ORDER BY ss.scheduled_date""",
        (uid, today)
    ).fetchall()

    db.close()
    return jsonify({
        'missed_deadlines': [dict(d) for d in missed_deadlines],
        'missed_sessions': [dict(s) for s in missed_sessions],
        'total': len(missed_deadlines) + len(missed_sessions)
    })

@schedule_bp.route('/api/schedule/accept-ai', methods=['POST'])
@login_required
def accept_ai_schedule():
    data = request.json
    sessions = data.get('sessions', [])
    db = get_db()

    for s in sessions:
        subject = db.execute('SELECT id FROM subjects WHERE id=? AND user_id=?',
                             (s.get('subject_id'), current_user.id)).fetchone()
        if subject:
            db.execute(
                'INSERT INTO scheduled_sessions (user_id, subject_id, scheduled_date, planned_hours, ai_generated) VALUES (?,?,?,?,1)',
                (current_user.id, s['subject_id'], s['scheduled_date'], float(s.get('planned_hours', 1)))
            )

    db.commit()
    db.close()
    return jsonify({'success': True, 'added': len(sessions)})
