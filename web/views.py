#!/usr/bin/python3

from uuid import uuid4
from datetime import date

from flask import g, request, session
from sqlalchemy import select
from werkzeug.utils import secure_filename
import dendropy
import flask as f
import flask_login as fl

from web import app, lm
from web.database import Trees, Treefile, Study, Submit, Matrix, NcbiName
from web.database import Nodes, Visit, db
from web.auth import auth
from web.form import LoginForm, UserForm
from web.form import QueryForm, SubmitForm



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
        session['user_id'] = user_id
        if request.headers.getlist('X-Forwarded-For'):
            ip = request.headers.getlist('X-Forwarded-For')[0]
        else:
            ip = request.remote_addr
        visit = Visit(user_id, ip, request.url, request.user_agent.string)
        db.session.add(visit)
        db.session.commit()
        session['visit_id'] = visit.visit_id


def login():
    '''
    {{ render_breadcrumb_item('auth.register', 'Register') }}
    {{ render_breadcrumb_item('auth.login', 'Login') }}
    '''



@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return f.send_from_directory(app.config['UPLOADED_FILE_DEST'], filename)


def upload(data) -> str:
    """
    Upload uncompressed text file.
    Return '' if not exists.
    Return native path if ok.
    Old version return url.
    """
    length = 8
    upload_path = app.config.get('UPLOADED_FILE_DEST')
    if data is None or isinstance(data, str):
        return ''
    # relative path
    filename = secure_filename(data.filename)
    unique_filename = str(uuid4())[:length] + data.filename
    native_path = upload_path / unique_filename
    # absolute path
    data.save(native_path)
    # relative path
    url = f.url_for('uploaded_file', filename=unique_filename)
    # return url
    return native_path


@app.route('/tree/list_all')
def tree_list():
    session['dict'] = {'is_dating': False}
    return f.redirect('/tree/list')


@app.route('/tree/query', methods=('POST', 'GET'))
def tree_query():
    qf = QueryForm()
    if qf.validate_on_submit():
        data = dict(qf.data)
        data.pop('submit')
        data.pop('csrf_token')
        session['dict'] = data
        return f.redirect('/tree/list')
    return f.render_template('tree_query.html', form=qf)


@app.route('/tree/list')
@app.route('/tree/list/<int:page>')
def tree_result(page=1):
    query = session['dict']
    study_filters = []
    filters = []
    if query.get("taxonomy"):
        node_condition = Trees.tree_id.in_(select(Nodes.tree_id).where(
            Nodes.node_label.like(f'{query.get("taxonomy")}%')))
        filters.append(node_condition)
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
        study_condition = Trees.study_id.in_(
            select(Study.study_id).where(*study_filters))
        filters.append(study_condition)
        # studies = db.session.query(Study.study_id).filter(*study_filters).subquery()
        # filters.append(Trees.study_id.in_(studies))
    # trees = db.session.query(Trees.tree_id).filter(*filters).subquery()
    trees = Trees.tree_id.in_(select(Trees.tree_id).where(*filters))
    results = db.session.query(Study, Trees).with_entities(
        Study.title, Study.year, Study.journal, Study.doi,
        Trees.tree_id, Trees.tree_title, Trees.tree_kind, Trees.is_dating).join(
        Study, Study.study_id == Trees.study_id).filter(
        trees).order_by(Trees.upload_date.desc())
    app.logger.debug(str(results))
    pagination = results.paginate(page=page, per_page=20)
    return f.render_template('tree_list.html', pagination=pagination)


@app.route('/tree/<int:tree_id>', methods=('POST', 'GET'))
def view_tree(tree_id):
    tree = Trees.query.get(tree_id)
    # todo: use auspice or other js
    return f.render_template('tree.html', tree=tree)


def get_nodes(raw_nodes: list) -> dict:
    # raw nodes: taxon_namespace
    label_taxon = {}
    name_list = [i.label for i in raw_nodes]
    node_exist = Nodes.query.filter(Nodes.node_label.in_(name_list)).all()
    for i in node_exist:
        label_taxon[i.node_label] = i.designated_tax_id
    new_nodes_name = [i for i in name_list if i not in label_taxon]
    for i in new_nodes_name:
        if i.count(' ') >= 1:
            if ' x ' not in i:
                short_name = ' '.join(i.split(' ')[:2])
            else:
                short_name = ' '.join(i.split(' ')[:3])
            retry = NcbiName.query.filter(
                NcbiName.name_class=='scientific name').filter(
                NcbiName.name_txt.like(f'{short_name}%')).all()
            if len(retry) != 0:
                label_taxon[i] = retry[0].tax_id
    return label_taxon


@app.route('/submit', methods=('POST', 'GET'))
def submit():
    # todo: convert id format
    sf = SubmitForm()
    if sf.validate_on_submit():
        upload_date = date.isoformat(date.today())
        tree = Trees()
        treefile = Treefile()
        study = Study()
        matrix = Matrix()
        for i in [tree, treefile, study, matrix]:
            sf.populate_obj(i)
        for j in [matrix, treefile, tree]:
            j.upload_date = upload_date
        # handle root id
        taxon = NcbiName.query.filter_by(name_txt=tree.root).all()
        # first or none
        if len(taxon) == 0:
            f.flash('Taxonomy name not found. '
                    'Currently only support accepted name.')
            return f.render_template('submit.html', form=sf)
            # return f.redirect('/submit')
        else:
            tree.root = taxon[0].tax_id

        # handle tree_text
        treefile_tmp = upload(sf.tree_file.data)
        try:
            with open(treefile_tmp, 'r') as _:
                line = _.readline()
                if line.startswith('#NEXUS'):
                    schema = 'nexus'
                else:
                    schema = 'newick'
                    f.flash('Tree file is newick format, converted to nexus.')
                tree_content = dendropy.Tree.get(path=treefile_tmp,
                                                 schema=schema)
                # different from original nexus
                tree_text = tree_content.as_string(schema='nexus')
                treefile.tree_text = tree_text
                # handle nodes
                raw_nodes = tree_content.taxon_namespace
                label_taxon = get_nodes(raw_nodes)
                not_found = len(raw_nodes) - len(label_taxon)
                if not_found > 0:
                    f.flash(f'{not_found} of {len(raw_nodes)} '
                            'nodes have invalid name.')
                    f.flash('Node name in tree file should be '
                            '"scientific name with other id" format')
                    f.flash('eg. Oryza sativa id9999')
            # dendropy error class is too long
        except Exception:
            f.flash('Bad tree file.')
            f.flash('The file should be UTF-8 encoding nexus or newick format.')
            return f.render_template('submit.html', form=sf)
        # old tree id end at 118270
        db.session.add(tree)
        # get tree_id
        db.session.commit()
        treefile.tree_id = tree.tree_id
        for i in label_taxon:
            new_node = Nodes(i, label_taxon[i], tree.tree_id)
            db.session.add(new_node)
            db.session.commit()
        db.session.add(treefile)
        db.session.add(study)
        # dirty work
        matrix.analysisstep_id = '20222022'
        db.session.add(matrix)
        if request.headers.getlist('X-Forwarded-For'):
            ip = request.headers.getlist('X-Forwarded-For')[0]
        else:
            ip = request.remote_addr
        submit_ = Submit(sf.email.data, ip, upload_date, session['user_id'],
                         tree.tree_id, treefile.treefile_id, study.study_id,
                         matrix.matrix_id)
        db.session.add(submit_)
        db.session.commit()
        f.flash('Submit ok.')
        return f.redirect(f'/submit/list')
    return f.render_template('submit.html', form=sf)


@app.route('/submit/remove/<int:submit_id>')
def remove_submit(submit_id):
    submit = Submit.query.get(submit_id)
    tree = Trees.query.get(submit.tree_id)
    treefile = Treefile.query.get(submit.treefile_id)
    study = Study.query.get(submit.study_id)
    matrix = Matrix.query.get(submit.matrix_id)
    nodes = Nodes.query.filter(Nodes.tree_id==submit.tree_id).delete()
    for i in (matrix, study, treefile, tree, submit):
        db.session.delete(i)
    db.session.commit()
    f.flash('Remove ok.')
    return f.redirect('/submit/list')


@app.route('/submit/list')
@app.route('/submit/list/<int:page>')
def submit_list(page=1):
    pagination = Submit.query.order_by(Submit.date.desc()).paginate(page=page,
                                                                    per_page=10)
    return f.render_template('submit_list.html', pagination=pagination)


@app.route('/')
@app.route('/index')
def index():
    return f.render_template('index.html')


app.register_blueprint(auth, url_prefix='/auth')