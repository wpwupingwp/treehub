#!/usr/bin/python3

import flask as f
from flask import g, request, session
import flask_login as fl
from sqlalchemy import not_, and_

# import flask_mail

from web import app, lm, root
from web.database import Nodes, Trees, Treefile, Visit, db
from web.auth import auth
from web.form import LoginForm, UserForm

@app.before_request
def track():
    if session.get('tracked', False):
        return
    else:
        session['tracked'] = True
        if fl.current_user.is_anonymous:
            # guest.user_id=2
            user_id = 2
        else:
            user_id = fl.current_user.user_id
        if request.headers.getlist('X-Forwarded-For'):
            ip = request.headers.getlist('X-Forwarded-For')[0]
        else:
            ip = request.remote_addr
        visit = Visit(user_id, ip, request.url, request.user_agent.string)
        db.session.add(visit)
        db.session.commit()
        session['visit_id'] = visit.visit_id

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return f.send_from_directory(app.config['UPLOADED_PHOTOS_DEST'], filename)


# todo: temporary link redirect
@app.route('/view_trees')
def view_admin():
    return f.redirect('/admin')


@app.route('/')
@app.route('/index')
def index():
    return f.render_template('index.html')


app.register_blueprint(auth, url_prefix='/auth')