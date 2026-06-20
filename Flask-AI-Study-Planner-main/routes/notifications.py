from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from database import get_db
from datetime import datetime, date, timedelta

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('/notifications')
@login_required
def index():
    return render_template('pages/notifications.html')

def generate_notifications(uid):
    """Generate dynamic notifications based on current state."""
    db = get_db()
    now = datetime.now()
    today = date.today()
    notifications = []

    # Upcoming exams within 3 days
    exams = db.execute(
        "SELECT name, exam_date FROM subjects WHERE user_id=? AND exam_date BETWEEN ? AND ?",
        (uid, today.isoformat(), (today + timedelta(days=3)).isoformat())
    ).fetchall()
    for e in exams:
        exam_dt = datetime.strptime(e['exam_date'], '%Y-%m-%d')
        days_left = (exam_dt.date() - today).days
        notifications.append({
            'type': 'exam',
            'message': f"Exam: {e['name']} in {days_left} day{'s' if days_left != 1 else ''}",
            'priority': 'high'
        })

    # Deadlines within 24 hours
    soon = (now + timedelta(hours=24)).isoformat()
    deadlines = db.execute(
        """SELECT d.title, d.due_date, s.name as subject FROM deadlines d
           JOIN subjects s ON d.subject_id=s.id
           WHERE d.user_id=? AND d.due_date BETWEEN ? AND ? AND d.completed=0""",
        (uid, now.isoformat(), soon)
    ).fetchall()
    for d in deadlines:
        notifications.append({
            'type': 'deadline',
            'message': f"Deadline in 24hrs: {d['title']} ({d['subject']})",
            'priority': 'high'
        })

    # Today's scheduled sessions
    today_sessions = db.execute(
        """SELECT ss.planned_hours, s.name as subject FROM scheduled_sessions ss
           JOIN subjects s ON ss.subject_id=s.id
           WHERE ss.user_id=? AND ss.scheduled_date=? AND ss.completed=0""",
        (uid, today.isoformat())
    ).fetchall()
    for s in today_sessions:
        notifications.append({
            'type': 'session',
            'message': f"Study session today: {s['subject']} ({s['planned_hours']}h planned)",
            'priority': 'medium'
        })

    # Missed tasks
    missed_deadlines = db.execute(
        """SELECT d.title, s.name as subject FROM deadlines d
           JOIN subjects s ON d.subject_id=s.id
           WHERE d.user_id=? AND d.due_date < ? AND d.completed=0""",
        (uid, now.isoformat())
    ).fetchall()
    for m in missed_deadlines:
        notifications.append({
            'type': 'missed',
            'message': f"Missed deadline: {m['title']} ({m['subject']})",
            'priority': 'urgent'
        })

    missed_sessions = db.execute(
        """SELECT s.name as subject, ss.scheduled_date FROM scheduled_sessions ss
           JOIN subjects s ON ss.subject_id=s.id
           WHERE ss.user_id=? AND ss.scheduled_date < ? AND ss.completed=0""",
        (uid, today.isoformat())
    ).fetchall()
    for m in missed_sessions:
        notifications.append({
            'type': 'missed',
            'message': f"Missed session: {m['subject']} on {m['scheduled_date']}",
            'priority': 'urgent'
        })

    db.close()
    return notifications


@notifications_bp.route('/api/notifications')
@login_required
def get_notifications():
    dynamic = generate_notifications(current_user.id)

    db = get_db()
    stored = db.execute(
        'SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 20',
        (current_user.id,)
    ).fetchall()
    db.close()

    return jsonify({
        'dynamic': dynamic,
        'stored': [dict(n) for n in stored],
        'unread_count': len([n for n in dynamic if n['priority'] in ('high', 'urgent')]) +
                        sum(1 for n in stored if not n['read'])
    })

@notifications_bp.route('/api/notifications/<int:nid>/read', methods=['POST'])
@login_required
def mark_read(nid):
    db = get_db()
    db.execute('UPDATE notifications SET read=1 WHERE id=? AND user_id=?', (nid, current_user.id))
    db.commit()
    db.close()
    return jsonify({'success': True})

@notifications_bp.route('/api/notifications/read-all', methods=['POST'])
@login_required
def mark_all_read():
    db = get_db()
    db.execute('UPDATE notifications SET read=1 WHERE user_id=?', (current_user.id,))
    db.commit()
    db.close()
    return jsonify({'success': True})
