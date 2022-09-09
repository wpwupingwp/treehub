#!/usr/bin/python3

from web import root

# database
SQLALCHEMY_DATABASE_URI = 'postgresql://root:password@localhost:5432/treedb'
SQLALCHEMY_TRACK_MODIFICATIONS = False
# upload
# max filesize 100 mb
MAX_CONTENT_LENGTH = 100 * 1024 * 1024
CSRF_ENABLED = True
UPLOAD_FOLDER = root / 'upload'
UPLOADED_FILE_DEST = UPLOAD_FOLDER / 'file'
if not UPLOADED_FILE_DEST.exists():
    UPLOADED_FILE_DEST.mkdir()
# safe
SECRET_KEY = '2022'
# bootstrap
BOOTSTRAP_SERVE_LOCAL = True
# login
MAX_LOGIN = 3
