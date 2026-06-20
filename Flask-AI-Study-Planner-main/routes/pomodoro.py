from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from database import get_db
from datetime import datetime

pomodoro_bp = Blueprint('pomodoro', __name__)

@pomodoro_bp.route('/timer')
@login_required
def timer_page():
    from flask import render_template
    return render_template('pages/timer.html')

@pomodoro_bp.route('/api/pomodoro/start', methods=['POST'])
@login_required
def start_session():
    data = request.json
    subject_id = data.get('subject_id') or None
    session_type = data.get('type', 'work')
    duration = int(data.get('duration_minutes', 25))

    db = get_db()
    cursor = db.execute(
        'INSERT INTO pomodoro_sessions (user_id, subject_id, started_at, duration_minutes, type, completed) VALUES (?,?,?,?,?,0)',
        (current_user.id, subject_id, datetime.now().isoformat(), duration, session_type)
    )
    db.commit()
    session_id = cursor.lastrowid
    db.close()
    return jsonify({'session_id': session_id})

@pomodoro_bp.route('/api/pomodoro/complete', methods=['POST'])
@login_required
def complete_session():
    data = request.json
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    db = get_db()
    session = db.execute(
        'SELECT * FROM pomodoro_sessions WHERE id=? AND user_id=?',
        (session_id, current_user.id)
    ).fetchone()
    if not session:
        db.close()
        return jsonify({'error': 'Session not found'}), 404

    db.execute('UPDATE pomodoro_sessions SET completed=1 WHERE id=?', (session_id,))
    db.commit()

    # If it's a work session, auto-log study hours
    if session['type'] == 'work' and session['subject_id']:
        hours = session['duration_minutes'] / 60.0
        log_date = datetime.now().strftime('%Y-%m-%d')
        db.execute(
            'INSERT INTO study_logs (user_id, subject_id, date, hours, notes) VALUES (?,?,?,?,?)',
            (current_user.id, session['subject_id'], log_date, round(hours, 2), 'Pomodoro session')
        )
        db.commit()

    db.close()
    return jsonify({'success': True})

@pomodoro_bp.route('/api/pomodoro/history')
@login_required
def history():
    db = get_db()
    sessions = db.execute(
        """SELECT ps.*, s.name as subject_name
           FROM pomodoro_sessions ps
           LEFT JOIN subjects s ON ps.subject_id=s.id
           WHERE ps.user_id=? ORDER BY ps.started_at DESC LIMIT 20""",
        (current_user.id,)
    ).fetchall()
    db.close()
    return jsonify([dict(s) for s in sessions])

@pomodoro_bp.route('/api/pomodoro/stats')
@login_required
def pomo_stats():
    db = get_db()
    uid = current_user.id
    total = db.execute(
        "SELECT COUNT(*) as c FROM pomodoro_sessions WHERE user_id=? AND completed=1 AND type='work'", (uid,)
    ).fetchone()['c']
    today_count = db.execute(
        "SELECT COUNT(*) as c FROM pomodoro_sessions WHERE user_id=? AND completed=1 AND type='work' AND date(started_at)=date('now')",
        (uid,)
    ).fetchone()['c']
    db.close()
    return jsonify({'total_sessions': total, 'today_sessions': today_count})
