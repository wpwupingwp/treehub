#!/usr/bin/python3

from datetime import date
from functools import lru_cache
from io import StringIO
from pathlib import Path
from uuid import uuid4
import json
import re

from flask import g, request, session
from flask import flash
from flask_babel import gettext
from sqlalchemy import select, or_, and_
from werkzeug.utils import secure_filename
import dendropy
from Bio import Phylo
import flask as f
import flask_login as fl

from web import app, babel, lm, root
from web.database import Trees, Treefile, Study, Submit, Matrix, NcbiName
from web.database import Nodes, Visit, db
from web.auth import auth
from web.form import QueryForm, SubmitForm, SortQueryForm, TreeMatrixForm
from web.utils import nwk2auspice, compress_photo
# from web.form import LoginForm, UserForm


@babel.localeselector
def get_locale():
    stored_local = session.get('locale', False)
    if stored_local:
        return stored_local
    else:
        return request.accept_languages.best_match(['zh', 'en'])


@app.route('/locale/<loc>')
def set_locale(loc):
    session['locale'] = loc
    return f.redirect('/index')


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
    pass


@app.route('/favicon.ico')
def favicon():
    return f.send_from_directory(root/'static', 'favicon.ico',
                                 mimetype='image/vnd.microsoft.icon')


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return f.send_from_directory(app.config['UPLOADED_FILE_DEST'], filename)


@app.route('/tmp/<filename>')
def tmp_file(filename):
    return f.send_from_directory(app.config['TMP_FOLDER'], filename)


def upload(data) -> Path:
    """
    Upload uncompressed text file.
    Return '' if not exists.
    Return native path if ok.
    Old version return url.
    """
    length = 8
    upload_path = app.config.get('UPLOADED_FILE_DEST')
    if data is None or isinstance(data, str):
        return Path()
    # relative path
    filename = secure_filename(data.filename)
    unique_filename = str(uuid4())[:length] + data.filename
    native_path = upload_path / unique_filename
    # absolute path
    data.save(native_path)
    # return url
    return native_path


@app.route('/tree/list_all')
def tree_list():
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


@lru_cache(maxsize=100)
def query_taxonomy(taxonomy: str):
    # speed up
    species_tax_id = NcbiName.query.filter(
        NcbiName.name_txt==taxonomy).with_entities(NcbiName.tax_id).all()
    species_tax_id = [i[0] for i in species_tax_id]
    combine = NcbiName.query.filter(
        or_(NcbiName.genus_id.in_(species_tax_id),
            NcbiName.family_id.in_(species_tax_id),
            NcbiName.order_id.in_(species_tax_id))).with_entities(
        NcbiName.tax_id).all()
    combine = [i[0] for i in combine]
    tree_id = Nodes.query.filter(Nodes.designated_tax_id.in_(
        combine)).with_entities(Nodes.tree_id).all()
    tree_id = [i[0] for i in tree_id]
    node_condition = Trees.tree_id.in_(tree_id)
    return node_condition


@app.route('/tree/list', methods=('POST', 'GET'))
@app.route('/tree/list/<int:page>', methods=('POST', 'GET'))
def tree_result(page=1):
    name_to_field = {'ID': Trees.tree_id, 'Tree title': Trees.tree_title,
                     'Kind': Trees.tree_kind, 'Publish year': Study.year,
                     'Article title': Study.title, 'Journal': Study.journal,
                     'DOI': Study.doi}
    item = session.get('item', 'ID')
    order = session.get('order', 'Descend')
    sf = SortQueryForm()
    sf.item.choices = SortQueryForm.new_item_choices(item)
    sf.order.choices = SortQueryForm.new_order_choices(order)
    if sf.validate_on_submit():
        item = sf.item.data
        order = sf.order.data
        session['item'] = item
        session['order'] = order
        page = 1
    field = name_to_field[item]
    if order == 'Descend':
        order_by = field.desc()
    else:
        order_by = field.asc()
    query = session['dict']
    study_filters = []
    filters = []
    if query.get('taxonomy') and not query.get('species'):
        node_condition = query_taxonomy(query.get('taxonomy'))
        filters.append(node_condition)
    if query.get('species'):
        node_condition = Trees.tree_id.in_(select(Nodes.tree_id).where(
            Nodes.node_label.like(f'{query.get("species")}%')))
        filters.append(node_condition)
    if query.get('tree_type_new'):
        type_new = str(query.get('tree_type_new')).capitalize()
        filters.append(Trees.tree_type_new == type_new)
    if query.get('year'):
        study_filters.append(Study.year == int(query.get('year')))
    if query.get('author'):
        study_filters.append(Study.author.like(f'%{query.get("author")}%'))
    if query.get('title'):
        study_filters.append(Study.title.like(f'%{query.get("title")}%'))
    if query.get('keywords'):
        study_filters.append(Study.keywords.like(f'%{query.get("title")}%'))
    if query.get('doi'):
        study_filters.append(Study.doi == query.doi.data)
    if study_filters:
        study_condition = Trees.study_id.in_(
            select(Study.study_id).where(*study_filters))
        filters.append(study_condition)
        # studies = db.session.query(Study.study_id).filter(*study_filters).subquery()
        # filters.append(Trees.study_id.in_(studies))
    # trees = db.session.query(Trees.tree_id).filter(*filters).subquery()
    trees = Trees.tree_id.in_(select(Trees.tree_id).where(*filters))
    x = Trees.query.filter(trees)
    results = db.session.query(Study, Trees).with_entities(
        Study.title, Study.year, Study.journal, Study.doi,
        Trees.tree_id, Trees.tree_title, Trees.tree_type_new,).join(
        Study, Study.study_id == Trees.study_id).filter(
        trees).order_by(order_by)
    pagination = results.paginate(page=page, per_page=20)
    return f.render_template(f'tree_list.html', pagination=pagination, form=sf)


@app.route('/tree/phyloxml/<int:tree_id>')
def tree_phyloxml(tree_id):
    treefile = Treefile.query.filter_by(tree_id=tree_id).one_or_none()
    if treefile is None:
        flash(gettext('Tree not found.'))
    phyloxml = treefile.phyloxml.rstrip()
    phyloxml = phyloxml.replace('""', '"').replace("''", "'")
    return phyloxml


@app.route('/tree/newick/<int:tree_id>')
def tree_newick(tree_id):
    treefile = Treefile.query.filter_by(tree_id=tree_id).one_or_none()
    if treefile is None:
        flash(gettext('Treefile not found.'))
    newick = treefile.newick.rstrip()
    return newick


@app.route('/tree/newick_file/<int:tree_id>')
def tree_newick_file(tree_id):
    treefile = Treefile.query.filter_by(tree_id=tree_id).one_or_none()
    if treefile is None:
        flash(gettext('Treefile not found.'))
    newick = treefile.newick.rstrip()
    tmp_folder = app.config.get('TMP_FOLDER')
    filename = f'{tree_id}.nwk'
    tmp_file_ = tmp_folder / filename
    if not tmp_file_.exists():
        with open(tmp_file_, 'w', encoding='utf-8') as _:
            _.write(newick)
    return f.url_for('tmp_file', filename=filename)


@app.route('/tree/auspice_file/<int:tree_id>')
def tree_auspice_file(tree_id):
    tmp_folder = app.config.get('TMP_FOLDER')
    json_file = tmp_folder / f'{tree_id}.json'
    if json_file.exists():
        return f.url_for('tmp_file', filename=json_file)
    tree = Trees.query.get(tree_id)
    treefile = Treefile.query.filter_by(tree_id=tree_id).one_or_none()
    if treefile is None:
        flash(gettext('Treefile not found.'))
    newick = treefile.newick
    meta_file = root / 'static' / 'auspice_tree_meta.json'
    with open(meta_file, 'r', encoding='utf-8') as _:
        json_ = json.load(_)
    json_['meta']['title'] = tree.tree_title
    json_['meta']['panels'] = ['tree']
    json_['meta']['updated'] = str(treefile.upload_date)
    json_file = nwk2auspice(newick, json_file, json_)
    return f.url_for('tmp_file', filename=json_file)


@app.route('/tree/<int:tree_id>', methods=('POST', 'GET'))
def view_tree(tree_id):
    tree = Trees.query.get(tree_id)
    if tree is None:
        return f.abort(404)
    title = tree.tree_title
    tree_auspice_file(tree_id)
    return f.render_template('view_tree.html',
                             title=title, tree_id=tree_id)


@app.route('/tree/edit/<int:tree_id>', methods=('POST', 'GET'))
def edit_tree(tree_id):
    tree = Trees.query.get(tree_id)
    title = tree.tree_title
    return f.render_template('edit_tree.html',
                             title=title, tree_id=tree_id)


def get_nodes(raw_nodes: list) -> dict:
    # raw nodes: taxon_namespace
    label_taxon = {}
    name_list = [i.label for i in raw_nodes]
    node_exist = Nodes.query.filter(Nodes.node_label.in_(name_list)).all()
    for i in node_exist:
        label_taxon[i.node_label] = i.designated_tax_id
    not_found = [i for i in name_list if i not in label_taxon]
    new_names = {}
    pattern = re.compile(r'.*([A-Z][a-z]+)(_| )([a-z]+).*')
    for i in not_found:
        x = re.search(pattern, i)
        if x is not None:
            species = x.group(1) + ' ' + x.group(3)
            new_names[i] = species
    new_found = NcbiName.query.filter(and_(
        NcbiName.name_class=='scientific name',
        NcbiName.name_txt.in_(new_names.values()))).all()
    new_found_dict = {k.name_txt: k.tax_id for k in new_found}
    for j in new_names:
        j_species = new_names[j]
        if j_species in new_found_dict:
            label_taxon[j] = new_found_dict[j_species]
    return label_taxon


def newick_to_phyloxml(newick: str) -> str:
    # Phylo.convert do not support string
    tmp_in = StringIO()
    tmp_out = StringIO()
    tmp_in.write(newick)
    tmp_in.seek(0)
    Phylo.convert(tmp_in, 'newick', tmp_out, 'phyloxml')
    tmp_out.seek(0)
    phyloxml = tmp_out.read()
    return phyloxml


@app.route('/matrix/from_tree/<int:tree_id>')
def get_matrix_from_treeid(tree_id):
    f.abort(404)
    return


def handle_submit_info(info_form):
    upload_date = date.isoformat(date.today())
    study = Study()
    info_form.populate_obj(study)
    study.upload_date = upload_date
    db.session.add(study)
    # get id
    db.session.commit()
    if request.headers.getlist('X-Forwarded-For'):
        ip = request.headers.getlist('X-Forwarded-For')[0]
    else:
        ip = request.remote_addr
    submit_ = Submit(info_form.email.data, ip, upload_date, session['user_id'],
                     study.study_id)
    db.session.add(submit_)
    db.session.commit()
    return study, submit_


def handle_tree_info(tree_form, final=False):
    upload_date = date.isoformat(date.today())
    tree = Trees()
    treefile = Treefile()
    matrix = Matrix()
    for i in [tree, treefile, matrix]:
        tree_form.populate_obj(i)
    for j in [matrix, treefile, tree]:
        j.upload_date = upload_date
    tree.root = str(tree.root).strip()
    tree.tree_type_new = str(tree.tree_type_new).capitalize()
    # handle root id
    taxon = NcbiName.query.filter_by(name_txt=tree.root).all()
    # first or none
    if len(taxon) == 0:
        flash(gettext('Taxonomy name not found. '
                      'Currently only support accepted name.'))
        return f.render_template('submit_1.html', form=tree_form)
    else:
        tree.root = taxon[0].tax_id
    # handle matrix
    if tree_form.matrix_file.data:
        matrix_file_tmp = upload(tree_form.matrix_file.data)
        with open(matrix_file_tmp, 'r') as _:
            matrix.fasta = _.read()
        matrix_file_tmp.unlink()
        # dirty work
    matrix.analysisstep_id = '20222022'
    db.session.add(matrix)
    db.session.commit()
    # handle tree_text
    treefile_tmp = upload(tree_form.tree_file.data)
    try:
        with open(treefile_tmp, 'r') as _:
            line = _.readline()
            if line.startswith('#NEXUS'):
                schema = 'nexus'
            else:
                schema = 'newick'
            tree_content = dendropy.Tree.get(path=treefile_tmp,
                                             schema=schema)
            # different from original nexus
            # dendropy can handle abnormal nexus, biopython cannot
            nexus = tree_content.as_string(schema='nexus')
            newick = tree_content.as_string(schema='newick')
            phyloxml = newick_to_phyloxml(newick)
            treefile.nexus = nexus
            treefile.newick = newick
            treefile.phyloxml = phyloxml
            # handle nodes
            raw_nodes = tree_content.taxon_namespace
            label_taxon = get_nodes(raw_nodes)
            not_found = len(raw_nodes) - len(label_taxon)
            if not_found > 0:
                flash(gettext('%(not_found)s of %(total)s nodes have '
                              'invalid name.',
                              not_found=not_found, total=len(raw_nodes)))
                flash(gettext('Node name in tree file should be '
                              '"scientific name with other id" format '
                              '(eg. Oryza sativa id9999'))
        # dendropy error class is too long
    except Exception:
        flash(gettext('Bad tree file. The file should be UTF-8 encoding '
                      'nexus or newick format.'))
        return f.render_template('submit_2.html', form=tree_form)
    finally:
        treefile_tmp.unlink()
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
    # get id
    tree.study_id = session['study']
    db.session.commit()
    submit_ = Submit.query.get(session['submit_'])
    submit_.tree_id = tree.tree_id
    submit_.treefile_id = treefile.treefile_id
    submit_.matrix_id = matrix.matrix_id
    if tree_form.cover_img.data:
        img_tmp_big = upload(tree_form.cover_img.data)
        img_tmp = compress_photo(img_tmp_big)
        submit_.cover_img_name = str(img_tmp.name)
        with open(img_tmp, 'rb') as _:
            submit_.cover_img = _.read()
        img_tmp.unlink()
    db.session.commit()
    if not final:
        next_submit = Submit(submit_.email, submit_.ip, submit_.date,
                             submit_.user_id, submit_.study_id)
        db.session.add(next_submit)
        db.session.commit()
        session['submit_'] = next_submit.submit_id
    return


@app.route('/submit', methods=('POST', 'GET'))
def submit_info():
    sf = SubmitForm()
    if sf.validate_on_submit():
        study, submit_ = handle_submit_info(sf)
        session['tree_n'] = 1
        session['study'] = study.study_id
        session['submit_'] = submit_.submit_id
        flash(gettext('Submit info ok.'))
        return f.redirect(f'/submit/{session["tree_n"]}')
    return f.render_template('submit_1.html', form=sf)


@app.route('/submit/<int:n>', methods=('POST', 'GET'))
def submit_data(n):
    sf = TreeMatrixForm()
    if sf.validate_on_submit():
        if sf.next.data:
            pass
        if sf.submit.data:
            pass
        handle_tree_info(sf)
        session['tree_n'] += 1
        flash(gettext('Submit tree ok.'))
        return f.redirect(f'/submit/{session["tree_n"]}')
    return f.render_template('submit_2.html', form=sf, n=session['tree_n'])


@app.route('/submit/remove/<int:submit_id>')
def remove_submit(submit_id):
    # todo: how to remove clean
    submit = Submit.query.get(submit_id)
    submit_id_list = [submit.submit_id]
    study = Study.query.get(submit.study_id)
    other_submits = Submit.query.filter(Submit.study_id==study.study_id).all()
    for i in other_submits:
        submit_id_list.append(i.submit_id)
    tree = Trees.query.filter(Trees.study_id==study.study_id).all()
    tree_id_list = [i.tree_id for i in tree]
    treefile = Treefile.query.filter(Treefile.tree_id.in_(tree_id_list))
    matrix_id_list = [i.matrix_id for i in other_submits]
    matrix_id_list.append(submit.matrix_id)
    matrix = Matrix.query.filter(Matrix.matrix_id.in_(matrix_id_list))
    nodes = Nodes.query.filter(Nodes.tree_id.in_(tree_id_list))
    # delete
    nodes.delete()
    matrix.delete()
    treefile.delete()
    for i in tree:
        db.session.delete(i)
    for j in other_submits:
        db.session.delete(j)
    db.session.delete(submit)
    db.session.delete(study)
    db.session.commit()
    flash(gettext('Remove ok.'))
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
    results = db.session.query(Submit, Study, Trees).with_entities(
        Submit.date, Submit.cover_img, Submit.cover_img_name,
        Study.upload_date, Study.title, Study.abstract, Study.doi,
        Trees.tree_title, Trees.tree_id).join(
        Submit, Submit.study_id==Study.study_id).join(
        Trees, Submit.tree_id==Trees.tree_id).filter(
        Submit.news==True).order_by(Submit.date.desc()).limit(3)
    tmp_imgs = []
    tmp_folder = app.config.get('TMP_FOLDER')
    for r in results:
        img = ''
        if r.cover_img_name is None:
            tmp_imgs.append(img)
            continue
        else:
            img = tmp_folder / r.cover_img_name
            if not img.exists():
                with open(img, 'wb') as _:
                    _.write(r.cover_img)
        url = f.url_for('tmp_file', filename=r.cover_img_name)
        tmp_imgs.append(url)
    cards = list(zip(results, tmp_imgs))
    return f.render_template('index.html', cards=cards)


app.register_blueprint(auth, url_prefix='/auth')