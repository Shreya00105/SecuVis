# app/__init__.py
from flask import Flask
from pymongo import MongoClient
import os

mongo_client = None
db = None

def create_app(config_object=None):
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECUVIS_SECRET", "change_this_secret"),
        MONGO_URI=os.environ.get("MONGO_URI", "mongodb://localhost:27017/"),
        MONGO_DBNAME=os.environ.get("MONGO_DBNAME", "secuvis")
    )

    # Initialize MongoDB client and attach to app context
    global mongo_client, db
    mongo_client = MongoClient(app.config['MONGO_URI'])
    db = mongo_client[app.config['MONGO_DBNAME']]

    # Create indexes if not exist
    try:
        db.raw_logs.create_index([("parsed.src_ip", 1)])
        db.network_events.create_index([("first_seen", -1)])
        db.visual_events.create_index([("frame_ts", -1)])
        db.correlated_alerts.create_index([("created_at", -1)])
    except Exception:
        pass

    # Register blueprints
    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app
