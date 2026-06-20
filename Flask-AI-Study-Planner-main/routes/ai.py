from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from database import get_db
from config import Config
from datetime import date, timedelta
from google import genai
from google.genai import types
import json
import time

ai_bp = Blueprint('ai', __name__)
_client = genai.Client(api_key=Config.GEMINI_API_KEY)

# Models to try in order — 2.5-flash confirmed working, others as fallback
MODELS = ['models/gemini-2.5-flash', 'models/gemini-2.0-flash', 'models/gemini-2.0-flash-lite']

def call_gemini(prompt, retries=2):
    """Call Gemini with automatic model fallback and retry on quota errors."""
    last_err = None
    for model in MODELS:
        for attempt in range(retries):
            try:
                response = _client.models.generate_content(
                    model=model,
                    contents=prompt
                )
                return response.text, None
            except Exception as e:
                err_str = str(e)
                last_err = err_str
                if '429' in err_str or 'RESOURCE_EXHAUSTED' in err_str:
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)  # 1s, 2s backoff
                        continue
                    # This model quota exhausted — try next model
                    break
                else:
                    # Non-quota error, return immediately
                    return None, err_str
    return None, last_err


def get_user_context(uid):
    """Build context string for Gemini prompts."""
    db = get_db()
    today = date.today()

    subjects = db.execute(
        'SELECT * FROM subjects WHERE user_id=? ORDER BY exam_date', (uid,)
    ).fetchall()

    logs = db.execute(
        """SELECT sl.hours, sl.date, s.name as subject
           FROM study_logs sl JOIN subjects s ON sl.subject_id=s.id
           WHERE sl.user_id=? AND sl.date >= ? ORDER BY sl.date DESC""",
        (uid, (today - timedelta(days=14)).isoformat())
    ).fetchall()

    deadlines = db.execute(
        """SELECT d.title, d.due_date, d.completed, s.name as subject
           FROM deadlines d JOIN subjects s ON d.subject_id=s.id
           WHERE d.user_id=? AND d.completed=0 ORDER BY d.due_date""",
        (uid,)
    ).fetchall()

    db.close()

    ctx = f"Today's date: {today.isoformat()}\n\n"
    ctx += "SUBJECTS:\n"
    for s in subjects:
        ctx += f"  - {s['name']}: exam on {s['exam_date'] or 'N/A'}, {s['planned_hours_per_week']}h/week planned\n"

    ctx += "\nPENDING DEADLINES:\n"
    for d in deadlines:
        ctx += f"  - [{d['subject']}] {d['title']} due {d['due_date']}\n"

    ctx += "\nRECENT STUDY LOGS (last 14 days):\n"
    for l in logs:
        ctx += f"  - {l['date']} | {l['subject']} | {l['hours']}h\n"

    return ctx, [dict(s) for s in subjects]


@ai_bp.route('/api/ai/coach', methods=['POST'])
@login_required
def coach():
    data = request.json
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({'error': 'Message required'}), 400

    context, _ = get_user_context(current_user.id)

    prompt = f"""You are an expert AI Study Coach. You have the following student data:

{context}

The student asks: "{user_message}"

Give personalized, actionable advice based on their actual data. Be specific and encouraging. 
Keep your response concise (under 200 words) and well-structured. Use bullet points where helpful."""

    text, err = call_gemini(prompt)
    if err:
        if '429' in err or 'RESOURCE_EXHAUSTED' in err or 'quota' in err.lower():
            reply = ("⚠️ The Gemini API quota is currently exhausted for this key. "
                     "Please wait a minute and try again, or check your quota at "
                     "https://aistudio.google.com/app/apikey")
        else:
            reply = f"Connection error: {err[:120]}"
        return jsonify({'reply': reply})

    return jsonify({'reply': text})


@ai_bp.route('/api/ai/reschedule', methods=['POST'])
@login_required
def reschedule():
    db = get_db()
    uid = current_user.id
    today = date.today()
    from datetime import datetime

    # Get missed items
    missed_deadlines = db.execute(
        """SELECT d.id, d.title, d.due_date, s.name as subject, s.id as subject_id
           FROM deadlines d JOIN subjects s ON d.subject_id=s.id
           WHERE d.user_id=? AND d.due_date < ? AND d.completed=0""",
        (uid, datetime.now().isoformat())
    ).fetchall()

    missed_sessions = db.execute(
        """SELECT ss.id, ss.scheduled_date, ss.planned_hours, s.name as subject, s.id as subject_id
           FROM scheduled_sessions ss JOIN subjects s ON ss.subject_id=s.id
           WHERE ss.user_id=? AND ss.scheduled_date < ? AND ss.completed=0""",
        (uid, today.isoformat())
    ).fetchall()

    if not missed_deadlines and not missed_sessions:
        db.close()
        return jsonify({'message': 'No missed tasks found.', 'sessions': []})

    context, subjects = get_user_context(uid)

    missed_text = "MISSED TASKS:\n"
    for d in missed_deadlines:
        missed_text += f"  - Deadline: [{d['subject']}] {d['title']} was due {d['due_date']}\n"
    for s in missed_sessions:
        missed_text += f"  - Study Session: {s['subject']} ({s['planned_hours']}h) was scheduled {s['scheduled_date']}\n"

    subject_ids_str = ", ".join([f"{s['name']} (id:{s['id']})" for s in subjects])

    prompt = f"""You are an AI study planner. A student has missed some tasks and needs a rescheduled plan.

{context}

{missed_text}

AVAILABLE SUBJECTS: {subject_ids_str}

Create a realistic rescheduled plan for the next 7 days starting from {(today + timedelta(days=1)).isoformat()}.
Return ONLY a valid JSON array of sessions with this exact format (no markdown, no explanation):
[
  {{"subject_id": <integer id>, "subject_name": "<name>", "scheduled_date": "YYYY-MM-DD", "planned_hours": <float>, "reason": "<brief reason>"}},
  ...
]
Include at most 10 sessions total. Make realistic daily study loads (1-3 hours per session)."""

    db.close()

    text, err = call_gemini(prompt)
    if err:
        if '429' in err or 'RESOURCE_EXHAUSTED' in err or 'quota' in err.lower():
            return jsonify({'error': 'Gemini API quota exhausted. Please wait a minute and try again.'}), 429
        return jsonify({'error': f'AI error: {err[:200]}'}), 500

    raw = text.strip()
    # Clean up markdown code blocks if present
    if raw.startswith('```'):
        raw = raw.split('```')[1]
        if raw.startswith('json'):
            raw = raw[4:]
    try:
        sessions = json.loads(raw.strip())
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Could not parse AI response: {str(e)}'}), 500

    return jsonify({'sessions': sessions, 'missed_count': len(missed_deadlines) + len(missed_sessions)})
