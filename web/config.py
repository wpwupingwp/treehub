#!/usr/bin/python3

from web import root

# session
SESSION_TYPE = 'filesystem'
SESSION_FILE_THRESHOLD = 5000
# database
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg://postgres:password@localhost:5432/treedb'
SQLALCHEMY_TRACK_MODIFICATIONS = False
# upload
# max filesize 100 mb
MAX_CONTENT_LENGTH = 100 * 1024 * 1024
CSRF_ENABLED = True
UPLOAD_FOLDER = root / 'upload'
TMP_FOLDER = root / 'tmp'
SESSION_FILE_DIR = TMP_FOLDER / 'session'
UPLOADED_FILE_DEST = UPLOAD_FOLDER / 'file'
for d in UPLOAD_FOLDER, UPLOADED_FILE_DEST, TMP_FOLDER, SESSION_FILE_DIR:
    if not d.exists():
        d.mkdir()
# safe
SECRET_KEY = '2022'
WTF_CSRF_TIME_LIMIT = 3600 * 100
# bootstrap
BOOTSTRAP_SERVE_LOCAL = True
# login
MAX_LOGIN = 3
# locale
BABEL_DEFAULT_LOCALE = 'en'
BABEL_DEFAULT_TIMEZONE = 'UTC'
