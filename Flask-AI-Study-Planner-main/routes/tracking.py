from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from database import get_db
from datetime import date, timedelta

tracking_bp = Blueprint('tracking', __name__)

@tracking_bp.route('/api/study-logs', methods=['GET'])
@login_required
def get_logs():
    db = get_db()
    logs = db.execute(
        """SELECT sl.*, s.name as subject_name, s.color as subject_color
           FROM study_logs sl JOIN subjects s ON sl.subject_id=s.id
           WHERE sl.user_id=? ORDER BY sl.date DESC""",
        (current_user.id,)
    ).fetchall()
    db.close()
    return jsonify([dict(l) for l in logs])

@tracking_bp.route('/api/study-logs', methods=['POST'])
@login_required
def log_hours():
    data = request.json
    subject_id = data.get('subject_id')
    log_date = data.get('date', date.today().isoformat())
    hours = float(data.get('hours', 0))
    notes = data.get('notes', '')

    if not subject_id or hours <= 0:
        return jsonify({'error': 'Subject and hours > 0 required'}), 400

    db = get_db()
    subject = db.execute('SELECT id FROM subjects WHERE id=? AND user_id=?',
                         (subject_id, current_user.id)).fetchone()
    if not subject:
        db.close()
        return jsonify({'error': 'Subject not found'}), 404

    cursor = db.execute(
        'INSERT INTO study_logs (user_id, subject_id, date, hours, notes) VALUES (?,?,?,?,?)',
        (current_user.id, subject_id, log_date, hours, notes)
    )
    db.commit()
    new_id = cursor.lastrowid
    log = dict(db.execute(
        'SELECT sl.*, s.name as subject_name FROM study_logs sl JOIN subjects s ON sl.subject_id=s.id WHERE sl.id=?',
        (new_id,)
    ).fetchone())
    db.close()
    return jsonify(log), 201

@tracking_bp.route('/api/study-logs/<int:lid>', methods=['DELETE'])
@login_required
def delete_log(lid):
    db = get_db()
    log = db.execute('SELECT id FROM study_logs WHERE id=? AND user_id=?', (lid, current_user.id)).fetchone()
    if not log:
        db.close()
        return jsonify({'error': 'Not found'}), 404
    db.execute('DELETE FROM study_logs WHERE id=?', (lid,))
    db.commit()
    db.close()
    return jsonify({'success': True})

@tracking_bp.route('/api/weekly-chart')
@login_required
def weekly_chart():
    db = get_db()
    uid = current_user.id
    today = date.today()

    subjects = db.execute('SELECT * FROM subjects WHERE user_id=?', (uid,)).fetchall()

    chart_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_data = {'date': day.strftime('%a'), 'full_date': day.isoformat(), 'completed': 0, 'planned': 0}

        hours_done = db.execute(
            'SELECT COALESCE(SUM(hours),0) as h FROM study_logs WHERE user_id=? AND date=?',
            (uid, day.isoformat())
        ).fetchone()['h']
        day_data['completed'] = round(hours_done, 2)

        # Planned is daily avg (weekly planned / 7)
        planned_total = sum(s['planned_hours_per_week'] for s in subjects) / 7
        day_data['planned'] = round(planned_total, 2)

        chart_data.append(day_data)

    db.close()
    return jsonify(chart_data)
