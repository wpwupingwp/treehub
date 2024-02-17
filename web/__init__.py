#!/usr/bin/python3

from flask import Flask, session, request
from flask_admin import Admin
from flask_bootstrap import Bootstrap4
from flask_babel import Babel
from flask_login import LoginManager

from pathlib import Path

app = Flask(__name__, static_folder='static', template_folder='templates')

def get_locale():
    stored_local = session.get('locale', False)
    if stored_local:
        return stored_local
    else:
        return request.accept_languages.best_match(['zh', 'en'])


babel = Babel(app)
babel.init_app(app, locale_selector=get_locale)
bootstrap = Bootstrap4(app)
lm = LoginManager()
lm.login_view = 'admin.login'
lm.init_app(app)
admin = Admin(app, template_mode='bootstrap4')
root = Path(app.root_path)
app.config.from_pyfile('config.py')

from web import config
from web import views
from web.database import db
