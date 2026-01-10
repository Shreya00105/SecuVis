# tests/test_routes.py
import os
import tempfile
from app import create_app

def test_health_and_login_and_upload_no_file(tmp_path):
    # create app with test config
    upload_folder = tmp_path / "uploads"
    upload_folder.mkdir()
    app = create_app({
        'TESTING': True,
        'UPLOAD_FOLDER': str(upload_folder),
        'SECRET_KEY': 'test-secret-key',
        # keep MONGO_URI default or a harmless value; we won't call DB-dependent endpoints here
    })

    client = app.test_client()

    # Health endpoint should respond ok
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json == {'status': 'ok'}

    # Login page GET should return 200 (render template)
    r = client.get('/login')
    assert r.status_code == 200
    assert b"Login" in r.data or b"login" in r.data.lower()

    # Upload without file should return 400 error
    r = client.post('/upload/logs', data={})
    assert r.status_code == 400
    assert b'no file' in r.data.lower() or r.json.get('error')  # either HTML or JSON response
preprocessing.ipynb