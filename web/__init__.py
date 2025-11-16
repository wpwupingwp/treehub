#!/usr/bin/python3

from flask import Flask, session, request
from flask_admin import Admin
from flask_bootstrap import Bootstrap4
from flask_babel import Babel
from flask_compress import Compress
from flask_login import LoginManager
from flask_restful import Api
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flasgger import Swagger

from pathlib import Path

app = Flask(__name__, static_folder='static', template_folder='templates')


def get_locale():
    stored_local = session.get('locale', False)
    if stored_local:
        return stored_local
    else:
        return request.accept_languages.best_match(['zh', 'en'])


swagger_config = {
    'headers': [],
    'specs':
        [
            {'endpoint': 'apispec_1',
             'route': '/treehub/apispec_1.json'}],
    'static_url_path': '/treehub/flasgger_static',
    # 'static_folder': 'static',
    'swagger_ui': True,
    'specs_route': '/treehub/apidocs/',
}
Compress(app)
api = Api(app,)
swagger = Swagger(app, config=swagger_config)
# swagger = Swagger(app)
babel = Babel(app)
babel.init_app(app, locale_selector=get_locale)
bootstrap = Bootstrap4(app)
lm = LoginManager()
lm.login_view = 'admin.login'
lm.init_app(app)
admin = Admin(app, template_mode='bootstrap4')
#root = Path(app.root_path)
root = Path('/dev/shm/treehub')
if not root.exists():
    root.mkdir()
app.config.from_pyfile('config.py')
db = SQLAlchemy(app)
session_ = Session(app)

from web import config
from web import views
from web.database import db
