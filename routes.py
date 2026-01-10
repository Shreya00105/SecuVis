import os
import uuid
import json
import pandas as pd
from datetime import datetime
from flask import (
    Blueprint, current_app, request,
    render_template, redirect, url_for, flash, session, jsonify
)
from werkzeug.utils import secure_filename

from . import mongo

# Local utils - you should implement these modules as per project structure
# - utils/log_parser.py -> parse_uploaded_file(file_path, source, log_type) -> list of docs
# - rules/runner.py -> run_rules_on_ingest(ingest_id) -> list of events (or summary)
try:
    from app.utils.log_parser import parse_uploaded_file
except Exception:
    # safe fallback if module not present yet
    def parse_uploaded_file(*args, **kwargs):
        raise RuntimeError("log_parser.parse_uploaded_file not implemented")

try:
    from app.rules.runner import run_rules_on_ingest
except Exception:
    def run_rules_on_ingest(*args, **kwargs):
        # placeholder: actual implementation should execute configured rules against raw_logs in DB
        return []

main_bp = Blueprint('main', __name__, template_folder='templates', static_folder='static')

# ---------------------
# Helper functions
# ---------------------
def allowed_file(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in current_app.config['ALLOWED_EXTENSIONS']

def save_uploaded_file(upload, dest_folder):
    filename = secure_filename(upload.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    path = os.path.join(dest_folder, unique_name)
    upload.save(path)
    return path, unique_name

# ---------------------
# UI Routes
# ---------------------
@main_bp.route('/')
def index():
    # Simple landing / redirect to dashboard
    if session.get('user'):
        return render_template('dashboard.html', user=session.get('user'))
    return redirect(url_for('main.login'))

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Very simple login for demo. In production, use Flask-Login and hashed passwords.
    """
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # For demo: check against a users collection in MongoDB
        users_coll = mongo.db.users
        user = users_coll.find_one({'username': username})
        if user and user.get('password') == password:
            # NOTE: store hashed passwords in production; this is simplified for demo
            session['user'] = {'username': username, 'role': user.get('role', 'admin')}
            return redirect(url_for('main.index'))
        else:
            error = 'Invalid credentials'
            flash(error, 'danger')
    return render_template('login.html', error=error)

@main_bp.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('main.login'))

@main_bp.route('/alerts')
def alerts_page():
    if not session.get('user'):
        return redirect(url_for('main.login'))
    return render_template('alerts.html')

# ---------------------
# API Routes
# ---------------------
@main_bp.route('/upload/logs', methods=['GET', 'POST'])
def upload_logs():
    """
    Upload CSV/JSON/LOG files via form (multipart). Saves file and triggers parsing + rule runner.
    Returns JSON with ingest_id and summary.
    """
    if request.method == 'GET':
        # render a basic upload form if desired
        return render_template('upload.html')

    # POST flow
    if 'file' not in request.files:
        return jsonify({'error': 'no file part in request'}), 400

    file = request.files['file']
    source = request.form.get('source', 'manual_upload')
    log_type = request.form.get('log_type', 'auth')  # default to auth logs

    if file.filename == '':
        return jsonify({'error': 'no selected file'}), 400

    if file and allowed_file(file.filename):
        upload_folder = current_app.config['UPLOAD_FOLDER']
        saved_path, saved_name = save_uploaded_file(file, upload_folder)

        # create ingest record
        ingest_id = uuid.uuid4().hex
        ingest_doc = {
            'ingest_id': ingest_id,
            'file_name': saved_name,
            'source': source,
            'log_type': log_type,
            'uploaded_by': session.get('user', {}).get('username') if session.get('user') else 'anonymous',
            'uploaded_at': datetime.utcnow(),
            'raw_path': saved_path,
            'status': 'uploaded'
        }
        mongo.db[ current_app.config['RAW_LOGS_COLLECTION'] ].insert_one(ingest_doc)

        # Parse file into structured documents (synchronous for demo; switch to background job in prod)
        try:
            parsed_docs = parse_uploaded_file(saved_path, source=source, log_type=log_type)
            if parsed_docs:
                # insert parsed docs into raw_logs collection (or separate collection)
                # each parsed doc should contain normalized timestamp and 'parsed' object
                for doc in parsed_docs:
                    doc.update({'ingest_id': ingest_id, 'ingested_at': datetime.utcnow()})
                mongo.db[ current_app.config['RAW_LOGS_COLLECTION'] ].insert_many(parsed_docs)
            # Run rule engine to produce network_events
            events = run_rules_on_ingest(ingest_id=ingest_id)
            # update ingest status
            mongo.db[ current_app.config['RAW_LOGS_COLLECTION'] ].update_many(
                {'ingest_id': ingest_id},
                {'$set': {'parse_status': 'parsed'}}
            )
            return jsonify({
                'ingest_id': ingest_id,
                'parsed_count': len(parsed_docs) if parsed_docs else 0,
                'generated_events': len(events) if events else 0
            })
        except Exception as e:
            current_app.logger.exception("Parsing or rule execution failed")
            return jsonify({'error': 'parsing_failed', 'details': str(e)}), 500
    else:
        return jsonify({'error': 'file type not allowed', 'allowed': list(current_app.config['ALLOWED_EXTENSIONS'])}), 400

@main_bp.route('/api/alerts', methods=['GET'])
def api_alerts():
    """
    Return recent correlated alerts for UI consumption (paginated).
    Query params: ?limit=20&status=new
    """
    try:
        limit = int(request.args.get('limit', 20))
        status = request.args.get('status', None)
        query = {}
        if status:
            query['status'] = status
        cursor = mongo.db[ current_app.config['CORRELATED_ALERTS_COLLECTION'] ].find(query).sort('created_at', -1).limit(limit)
        alerts = list(cursor)
        # convert ObjectId to str and datetime to ISO
        for a in alerts:
            a['_id'] = str(a.get('_id'))
            if isinstance(a.get('created_at'), datetime):
                a['created_at'] = a['created_at'].isoformat()
        return jsonify(alerts)
    except Exception as e:
        current_app.logger.exception("Failed to fetch alerts")
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/visual_events', methods=['GET'])
def api_visual_events():
    """
    Return visual events (YOLO detections). Params: camera_id, since (ISO)
    """
    try:
        camera = request.args.get('camera', None)
        since = request.args.get('since', None)
        query = {}
        if camera:
            query['camera_id'] = camera
        if since:
            try:
                since_dt = datetime.fromisoformat(since)
                query['frame_ts'] = {'$gte': since_dt}
            except Exception:
                pass
        docs = list(mongo.db[ current_app.config['VISUAL_EVENTS_COLLECTION'] ].find(query).sort('frame_ts', -1).limit(500))
        for d in docs:
            d['_id'] = str(d.get('_id'))
            if isinstance(d.get('frame_ts'), datetime):
                d['frame_ts'] = d['frame_ts'].isoformat()
        return jsonify(docs)
    except Exception as e:
        current_app.logger.exception("Failed to fetch visual events")
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/network_events', methods=['GET'])
def api_network_events():
    """
    Return network events (rule engine outputs).
    """
    try:
        limit = int(request.args.get('limit', 100))
        docs = list(mongo.db[ current_app.config['NETWORK_EVENTS_COLLECTION'] ].find({}).sort('first_seen', -1).limit(limit))
        for d in docs:
            d['_id'] = str(d.get('_id'))
            if isinstance(d.get('first_seen'), datetime):
                d['first_seen'] = d['first_seen'].isoformat()
        return jsonify(docs)
    except Exception as e:
        current_app.logger.exception("Failed to fetch network events")
        return jsonify({'error': str(e)}), 500

# ---------------------
# Admin endpoints (protected) - simple example
# ---------------------
def require_admin():
    user = session.get('user')
    return user and user.get('role') == 'admin'

@main_bp.route('/api/rules', methods=['GET', 'POST'])
def manage_rules():
    """
    GET: list rules
    POST: add/update a rule (expects JSON rule doc)
    In production protect this endpoint with real auth.
    """
    if not require_admin():
        return jsonify({'error': 'unauthorized'}), 403

    if request.method == 'GET':
        rules = list(mongo.db[ current_app.config['RULES_COLLECTION'] ].find({}))
        for r in rules:
            r['_id'] = str(r.get('_id'))
        return jsonify(rules)

    data = request.json
    if not data:
        return jsonify({'error': 'missing rule payload'}), 400

    # simple upsert by rule_id
    rule_id = data.get('rule_id') or f"R-{uuid.uuid4().hex[:8]}"
    data['rule_id'] = rule_id
    data['updated_at'] = datetime.utcnow()
    mongo.db[ current_app.config['RULES_COLLECTION'] ].update_one({'rule_id': rule_id}, {'$set': data}, upsert=True)
    return jsonify({'status': 'ok', 'rule_id': rule_id})

# ---------------------
# Utility endpoint (optional) - trigger correlation manually
# ---------------------
@main_bp.route('/api/correlate', methods=['POST'])
def trigger_correlation():
    """
    Manual trigger to run correlation engine. This should be moved to a background worker.
    """
    if not require_admin():
        return jsonify({'error': 'unauthorized'}), 403

    # correlation logic should be implemented in correlator module
    try:
        from app.correlator.correlator import run_correlation
    except Exception:
        return jsonify({'error': 'correlator_not_implemented'}), 500

    result = run_correlation()
    return jsonify({'status': 'ok', 'created_alerts': result})

