import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'study-planner-secret-key-2024')
    DATABASE = os.path.join(os.path.dirname(__file__), 'study_planner.db')
    GEMINI_API_KEY = 'AIzaSyADE3qaWyWn50XCUUqtfGUvluiqP4CxyZw'
