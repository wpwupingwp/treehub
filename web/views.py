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

@app.route('/tree/query_result/<int:page>')
def tree_result_list2(results: db.session.query, page=1):
    print('call')
    print(str(results))
    per_page = 10
    pagination = results.paginate(page=page, per_page=10)
    return f.render_template('tree_list.html', pagination=pagination)


def tree_result(query: QueryForm):
    study_filters = []
    filters = []
    if query.taxonomy.data:
        node = db.session.query(Nodes.tree_id).filter(
            Nodes.node_label.like(f'{query.taxonomy.data}%')).subquery()
        filters.append(Trees.tree_id.in_(node))
    if query.is_dating.data:
        filters.append(Trees.is_dating == True)
    if query.year.data:
        study_filters.append(Study.year == int(query.year.data))
    if query.author.data:
        study_filters.append(Study.author.like(f'%{query.author.data}%'))
    if query.title.data:
        study_filters.append(Study.title.like(f'%{query.title.data}%'))
    if query.keywords.data:
        study_filters.append(Study.keywords.like(f'%{query.title.data}%'))
    if query.doi.data:
        study_filters.append(Study.doi == query.doi.data)
    if study_filters:
        studies = db.session.query(Study.study_id).filter(*study_filters).subquery()
        filters.append(Trees.study_id.in_(studies))
    trees = db.session.query(Trees.tree_id).filter(*filters).subquery()
    results = Trees.query.filter(Trees.tree_id.in_(trees)).order_by(Trees.tree_title.asc())
    pagination = results.paginate(page=1, per_page=10)
    print(str(trees))
    if 1 < 0:
        f.flash('Not found')
        return f.redirect('/tree/query')
    return tree_result_list2(results)
    pagination = Trees.query.filter(Trees.tree_id.in_(trees)).order_by(
        Trees.tree_id.desc()).paginate(page=1, per_page=10)
    # todo: test
    return f.render_template('tree_list.html', pagination=pagination)


    pass
@app.route('/tree/query', methods=('POST', 'GET'))
def tree_query():
    qf = QueryForm()
    if qf.validate_on_submit():
        print(qf.data)
        return tree_result(qf)
        taxonomy = qf.taxonomy.data
        test = Nodes.query.filter(
            Nodes.node_label.like(f'{taxonomy}%')).first()
        if test is None:
            f.flash('Not found.')
            return f.redirect('/tree/query')
        node = db.session.query(Nodes.tree_id).filter(
            Nodes.node_label.like(f'{taxonomy}%')).subquery()
        have_treefile = db.session.query(Treefile.tree_id).filter(
            Trees.tree_id.in_(node)).subquery()
        pagination = Trees.query.filter(
            Trees.tree_id.in_(have_treefile)).order_by(
            Trees.tree_id.desc()).paginate(page=1, per_page=10)
        return f.redirect(f'/tree/query/{taxonomy}/1')
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