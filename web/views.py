#!/usr/bin/python3

import flask as f
from flask import g, request, session
import flask_login as fl
from sqlalchemy import not_, and_

# import flask_mail

from web import app, lm, root
from web.database import Nodes, Trees, Treefile, Study, Visit, db
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
    return f.send_from_directory(app.config['UPLOADED_FILE_DEST'], filename)


# todo: temporary link redirect
@app.route('/treelist')
@app.route('/treelist/<int:page>')
def tree_list(page=1):
    per_page = 10
    pagination = Trees.query.paginate(page=page, per_page=per_page)
    return f.render_template('tree_list.html', pagination=pagination)


@app.route('/tree/<int:tree_id>', methods=('POST', 'GET'))
def view_goods(tree_id):
    tree = Trees.query.get(tree_id)
    node = db.session.query(Trees, Nodes).join(
        Trees, Trees.tree_id==Nodes.node_id).filter_by(
        tree_id=tree_id).limit(10)
    return f.render_template('tree.html', tree=tree, node=node)


@app.route('/')
@app.route('/index')
def index():
    return f.render_template('index.html')


app.register_blueprint(auth, url_prefix='/auth')