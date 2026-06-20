from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from database import get_db
from datetime import datetime, timedelta, date

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    return render_template('pages/dashboard.html')

@dashboard_bp.route('/api/dashboard/stats')
@login_required
def stats():
    db = get_db()
    uid = current_user.id
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    # Total subjects
    subjects_count = db.execute('SELECT COUNT(*) as c FROM subjects WHERE user_id=?', (uid,)).fetchone()['c']

    # This week completed hours
    completed_hours = db.execute(
        'SELECT COALESCE(SUM(hours),0) as h FROM study_logs WHERE user_id=? AND date BETWEEN ? AND ?',
        (uid, week_start.isoformat(), week_end.isoformat())
    ).fetchone()['h']

    # Planned hours this week
    planned_hours = db.execute(
        'SELECT COALESCE(SUM(planned_hours_per_week),0) as h FROM subjects WHERE user_id=?', (uid,)
    ).fetchone()['h']

    # Pomodoro sessions this week
    pomodoro_count = db.execute(
        "SELECT COUNT(*) as c FROM pomodoro_sessions WHERE user_id=? AND type='work' AND completed=1 AND date(started_at) BETWEEN ? AND ?",
        (uid, week_start.isoformat(), week_end.isoformat())
    ).fetchone()['c']

    # Upcoming exams (next 7 days)
    upcoming_exams = db.execute(
        "SELECT s.name, s.exam_date FROM subjects s WHERE s.user_id=? AND s.exam_date BETWEEN ? AND ? ORDER BY s.exam_date",
        (uid, today.isoformat(), (today + timedelta(days=7)).isoformat())
    ).fetchall()

    # Missed tasks
    missed_deadlines = db.execute(
        "SELECT d.title, d.due_date, s.name as subject FROM deadlines d JOIN subjects s ON d.subject_id=s.id WHERE d.user_id=? AND d.due_date < ? AND d.completed=0",
        (uid, datetime.now().isoformat())
    ).fetchall()

    # Weekly chart data (last 7 days)
    chart_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        hours_done = db.execute(
            'SELECT COALESCE(SUM(hours),0) as h FROM study_logs WHERE user_id=? AND date=?',
            (uid, day.isoformat())
        ).fetchone()['h']
        chart_data.append({'date': day.strftime('%a'), 'completed': round(hours_done, 2)})

    # Recent activity
    recent_logs = db.execute(
        """SELECT sl.hours, sl.date, sl.notes, s.name as subject
           FROM study_logs sl JOIN subjects s ON sl.subject_id=s.id
           WHERE sl.user_id=? ORDER BY sl.created_at DESC LIMIT 5""",
        (uid,)
    ).fetchall()

    db.close()

    return jsonify({
        'subjects_count': subjects_count,
        'completed_hours': round(completed_hours, 2),
        'planned_hours': round(planned_hours, 2),
        'pomodoro_count': pomodoro_count,
        'upcoming_exams': [dict(e) for e in upcoming_exams],
        'missed_count': len(missed_deadlines),
        'chart_data': chart_data,
        'recent_logs': [dict(r) for r in recent_logs]
    })
