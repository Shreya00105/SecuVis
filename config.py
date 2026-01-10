import os

class Config:
    # Flask settings
    SECRET_KEY = os.environ.get('SECUVIS_SECRET', 'replace-this-secret-in-prod')

    # Upload settings
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    UPLOAD_FOLDER = os.environ.get('SECUVIS_UPLOAD_FOLDER',
                                   os.path.join(BASE_DIR, 'data', 'uploads'))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload

    # MongoDB settings
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/secuvis')

    # Model paths (if used)
    MODEL_DIR = os.path.join(BASE_DIR, '..', 'models')
    ISOLATION_MODEL = os.path.join(MODEL_DIR, 'isolation_forest.pkl')
    VECTORIZER = os.path.join(MODEL_DIR, 'scaler.pkl')

    # Allowed upload extensions
    ALLOWED_EXTENSIONS = {'csv', 'json', 'log', 'txt'}

    # Rule runner settings
    RULES_COLLECTION = 'config_rules'
    RAW_LOGS_COLLECTION = 'raw_logs'
    NETWORK_EVENTS_COLLECTION = 'network_events'
    VISUAL_EVENTS_COLLECTION = 'visual_events'
    CORRELATED_ALERTS_COLLECTION = 'correlated_alerts'
