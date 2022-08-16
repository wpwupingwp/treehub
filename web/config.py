#!/usr/bin/python3

from web import root

# database
SQLALCHEMY_DATABASE_URI = 'sqlite:///mai.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False
# upload
# max filesize 100 mb
MAX_CONTENT_LENGTH = 100 * 1024 * 1024
CSRF_ENABLED = True
UPLOAD_FOLDER = root / 'upload'
UPLOADED_PHOTOS_DEST = UPLOAD_FOLDER / 'img'
for i in UPLOAD_FOLDER, UPLOADED_PHOTOS_DEST:
    if not i.exists():
        i.mkdir()
# safe
SECRET_KEY = '2022'
# bootstrap
BOOTSTRAP_SERVE_LOCAL = True
# login
MAX_LOGIN = 3
MAX_FAILED_BID = 3
