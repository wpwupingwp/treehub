#!/usr/bin/python3

from flask import Flask
from flask_admin import Admin
from flask_bootstrap import Bootstrap4
from flask_login import LoginManager

from pathlib import Path


app = Flask(__name__)
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
