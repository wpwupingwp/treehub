#!/usr/bin/python3

from web import root

# database
SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:password@localhost:5432/treedb'
SQLALCHEMY_TRACK_MODIFICATIONS = False
# upload
# max filesize 100 mb
MAX_CONTENT_LENGTH = 100 * 1024 * 1024
CSRF_ENABLED = True
UPLOAD_FOLDER = root / 'upload'
TMP_FOLDER = root / 'tmp'
UPLOADED_FILE_DEST = UPLOAD_FOLDER / 'file'
for d in UPLOADED_FILE_DEST, TMP_FOLDER:
    if not d.exists():
        d.mkdir()
# safe
SECRET_KEY = '2022'
# bootstrap
BOOTSTRAP_SERVE_LOCAL = True
# login
MAX_LOGIN = 3
# locale
BABEL_DEFAULT_LOCALE = 'en'
BABEL_DEFAULT_TIMEZONE = 'UTC'
