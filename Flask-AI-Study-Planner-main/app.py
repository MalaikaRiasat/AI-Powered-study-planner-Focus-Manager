from flask import Flask, redirect, url_for
from flask_login import LoginManager, UserMixin
from flask_cors import CORS
from config import Config
from database import get_db, init_db

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to continue.'
login_manager.login_message_category = 'info'

class User(UserMixin):
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    user_row = db.execute('SELECT * FROM users WHERE id=?', (int(user_id),)).fetchone()
    db.close()
    if user_row:
        return User(user_row['id'], user_row['name'], user_row['email'])
    return None

# Register blueprints
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.subjects import subjects_bp
from routes.tracking import tracking_bp
from routes.pomodoro import pomodoro_bp
from routes.schedule import schedule_bp
from routes.notifications import notifications_bp
from routes.ai import ai_bp
from routes.settings import settings_bp

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(subjects_bp)
app.register_blueprint(tracking_bp)
app.register_blueprint(pomodoro_bp)
app.register_blueprint(schedule_bp)
app.register_blueprint(notifications_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(settings_bp)

@app.route('/')
def root():
    return redirect(url_for('dashboard.index'))

# Initialize DB on first run
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
