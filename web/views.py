#!/usr/bin/python3

import flask as f
from flask import g, request, session
import flask_login as fl
from sqlalchemy import not_, and_

# import flask_mail

from web import app, lm, root
from web.database import Nodes, Trees, Treefile, Study, Visit, db
from web.auth import auth
from web.form import LoginForm, UserForm, QueryForm


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
@app.route('/tree/list')
@app.route('/tree/list/<int:page>')
def tree_list(page=1):
    per_page = 10
    pagination = Trees.query.paginate(page=page, per_page=per_page)
    return f.render_template('tree_list.html', pagination=pagination)


@app.route('/tree/query/<string:query>/<int:page>')
def tree_result_list(query='', page=1):
    node = db.session.query(Nodes.tree_id).filter(
        Nodes.node_label.like(f'{query}%')).subquery()
    pagination = Trees.query.filter(Trees.tree_id.in_(node)).order_by(
        Trees.tree_id.desc()).paginate(page=page, per_page=10)
    return f.render_template('tree_list.html', pagination=pagination)


@app.route('/tree/result')
@app.route('/tree/result/<int:page>')
def tree_result(page=1):
    query = session['dict']
    study_filters = []
    filters = []
    if query.get("taxonomy"):
        node = db.session.query(Nodes.tree_id).filter(
            Nodes.node_label.like(f'{query.get("taxonomy")}%')).subquery()
        filters.append(Trees.tree_id.in_(node))
    if query.get("is_dating"):
        filters.append(Trees.is_dating == True)
    if query.get("year"):
        study_filters.append(Study.year == int(query.get("year")))
    if query.get("author"):
        study_filters.append(Study.author.like(f'%{query.get("author")}%'))
    if query.get("title"):
        study_filters.append(Study.title.like(f'%{query.get("title")}%'))
    if query.get("keywords"):
        study_filters.append(Study.keywords.like(f'%{query.get("title")}%'))
    if query.get("doi"):
        study_filters.append(Study.doi == query.doi.data)
    if study_filters:
        studies = db.session.query(Study.study_id).filter(*study_filters).subquery()
        filters.append(Trees.study_id.in_(studies))
    trees = db.session.query(Trees.tree_id).filter(*filters).subquery()
    results = Trees.query.filter(Trees.tree_id.in_(trees)).order_by(Trees.tree_title.asc())
    pagination = results.paginate(page=page, per_page=10)
    return f.render_template('tree_list.html', pagination=pagination)


    pass
@app.route('/tree/query', methods=('POST', 'GET'))
def tree_query():
    qf = QueryForm()
    if qf.validate_on_submit():
        data = dict(qf.data)
        data.pop('submit')
        data.pop('csrf_token')
        session['dict'] = data
        return f.redirect('/tree/result')
    return f.render_template('tree_query.html', form=qf)


@app.route('/tree/<int:tree_id>', methods=('POST', 'GET'))
def view_tree(tree_id):
    tree = Trees.query.get(tree_id)
    # todo: use auspice or other js
    return f.render_template('tree.html', tree=tree)


@app.route('/')
@app.route('/index')
def index():
    return f.render_template('index.html')


app.register_blueprint(auth, url_prefix='/auth')