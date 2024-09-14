#!/usr/bin/python3

from datetime import date
from functools import lru_cache
from io import StringIO
from pathlib import Path
from uuid import uuid4
import json
import re

from flask import request, session
from flask import flash
from flask_babel import gettext
from sqlalchemy import select, or_, and_
from werkzeug.utils import secure_filename
# from werkzeug.urls import url_unquote_plus
import dendropy
from Bio import Phylo
import flask as f
import flask_login as fl

from web import app, babel, lm, root
from web.database import Trees, Treefile, Study, Submit, Matrix, NcbiName
from web.database import Nodes, Visit, db, query_taxonomy
from web.auth import auth
from web.form import QueryForm, SubmitForm, TreeMatrixForm
from web.form import SubscribeForm, SortQueryForm
from web.utils import nwk2auspice, compress_photo

# from web.form import LoginForm, UserForm

tid_func = Trees.tid


@app.route('/treehub/locale/<loc>')
def set_locale(loc):
    session['locale'] = loc
    return f.redirect('/treehub/index')


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


@app.route('/treehub/favicon.ico')
def favicon():
    return f.send_from_directory(root / 'static', 'favicon.ico',
                                 mimetype='image/vnd.microsoft.icon')


@app.route('/treehub/uploads/<filename>')
def uploaded_file(filename):
    return f.send_from_directory(app.config['UPLOADED_FILE_DEST'], filename)


@app.route('/treehub/tmp/<filename>')
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


@app.route('/treehub/tree/list_all', methods=('POST', 'GET'))
@app.route('/treehub/tree/list_all/<int:page>', methods=('POST', 'GET'))
def tree_list(page=1):
    session['dict'] = {}
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
    # x = Trees.query.filter(trees)
    # trees = Trees.tree_id.in_(select(Trees.tree_id).distinct(
    #     Trees.study_id).group_by(Trees.study_id, Trees.tree_id))
    results = db.session.query(
        Study, Trees, Submit, Matrix, NcbiName).with_entities(
        Study.title, Study.year, Study.journal, Study.doi,
        Trees.tree_id, NcbiName.name_txt, Trees.tree_title,
        Matrix.upload_date).join(
        Study, Study.study_id == Trees.study_id, isouter=True).join(
        Submit, Submit.tree_id == Trees.tree_id, isouter=True).join(
        Matrix, Matrix.matrix_id == Submit.matrix_id, isouter=True).join(
        NcbiName, NcbiName.tax_id == Trees.root, isouter=True).filter(
        and_(NcbiName.name_class == 'scientific name',
             Study.year > 0)).order_by(
        order_by)
    pagination = results.paginate(page=page, per_page=20)
    return f.render_template(f'tree_list.html', pagination=pagination,
                             form=sf,
                             tid_func=tid_func)


@lru_cache()
def root_id_to_name(root_id: int) -> str:
    record = NcbiName.get(root_id).first_or_none()
    if record is not None:
        return record.name_txt
    else:
        return 'Unknown'


@app.route('/treehub/tree/query', methods=('POST', 'GET'))
def tree_query():
    qf = QueryForm()
    if qf.validate_on_submit():
        data = dict(qf.data)
        data.pop('submit')
        data.pop('csrf_token')
        session['dict'] = data
        return f.redirect('/treehub/tree/list')
    return f.render_template('tree_query.html', form=qf)


@app.route('/treehub/tree/list', methods=('POST', 'GET'))
@app.route('/treehub/tree/list/<int:page>', methods=('POST', 'GET'))
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
    if query.get('tree_id'):
        id_list_raw = query.get('tree_id').split(',')
        id_list = [Trees.tid2serial(i.strip()) for i in id_list_raw]
        filters.append(Trees.tree_id.in_(id_list))
    if query.get('taxonomy') and not query.get('species'):
        node_condition = query_taxonomy(query.get('taxonomy'))
        filters.append(node_condition)
    if query.get('species'):
        node_condition = Trees.tree_id.in_(select(Nodes.tree_id).where(
            Nodes.node_label.like(f'{query.get("species")}%')))
        filters.append(node_condition)
    if query.get('tree_type_new'):
        type_new = str(query.get('tree_type_new')).capitalize()
        if type_new != 'Any':
            filters.append(or_(Trees.tree_type_new == type_new,
                               Trees.tree_kind == type_new.title()))
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
    trees = Trees.tree_id.in_(select(Trees.tree_id).where(*filters))
    # x = Trees.query.filter(trees)
    # results = db.session.query(Study, Trees, Submit, Matrix).with_entities(
    #     Study.title, Study.year, Study.journal, Study.doi,
    #     Trees.tree_id, Trees.tree_title, Matrix.upload_date).join(
    #     Study, Study.study_id == Trees.study_id).join(
    #     Submit, Submit.tree_id == Trees.tree_id, isouter=True).join(
    #     Matrix, Matrix.matrix_id == Submit.matrix_id, isouter=True).filter(
    #     trees).order_by(order_by)
    results = db.session.query(
        Study, Trees, Submit, Matrix, NcbiName).with_entities(
        Study.title, Study.year, Study.journal, Study.doi,
        Trees.tree_id, NcbiName.name_txt, Trees.tree_title,
        Matrix.upload_date).join(
        Study, Study.study_id == Trees.study_id, isouter=True).join(
        Submit, Submit.tree_id == Trees.tree_id, isouter=True).join(
        Matrix, Matrix.matrix_id == Submit.matrix_id, isouter=True).join(
        NcbiName, NcbiName.tax_id == Trees.root, isouter=True).filter(
        and_(NcbiName.name_class == 'scientific name', trees)).order_by(
        order_by)
    pagination = results.paginate(page=page, per_page=20)
    return f.render_template(f'tree_list.html', pagination=pagination, form=sf,
                             tid_func=tid_func)


@app.route('/treehub/tree/phyloxml/<tid>')
def tree_phyloxml(tid):
    tree_id = Trees.tid2serial(tid)
    treefile = Treefile.query.filter_by(tree_id=tree_id).one_or_none()
    if treefile is None:
        flash(gettext('Tree not found.'), 'error')
    phyloxml = treefile.phyloxml.rstrip()
    phyloxml = phyloxml.replace('""', '"').replace("''", "'")
    return phyloxml


@app.route('/treehub/tree/newick/<tid>')
def tree_newick(tid):
    tree_id = Trees.tid2serial(tid)
    treefile = Treefile.query.filter_by(tree_id=tree_id).one_or_none()
    if treefile is None:
        flash(gettext('Treefile not found.'), 'error')
    newick = treefile.newick.rstrip()
    return newick


@app.route('/treehub/tree/newick_file/<tid>')
def tree_newick_file(tid):
    tree_id = Trees.tid2serial(tid)
    treefile = Treefile.query.filter_by(tree_id=tree_id).one_or_none()
    if treefile is None:
        flash(gettext('Treefile not found.'), 'error')
    newick = treefile.newick.rstrip()
    tmp_folder = app.config.get('TMP_FOLDER')
    filename = f'{tree_id}.nwk'
    tmp_file_ = tmp_folder / filename
    if not tmp_file_.exists():
        with open(tmp_file_, 'w', encoding='utf-8') as _:
            _.write(newick)
    return f.url_for('tmp_file', filename=filename)


@app.route('/treehub/tree/auspice_file/<tid>')
def tree_auspice_file(tid):
    tree_id = Trees.tid2serial(tid)
    tmp_folder = app.config.get('TMP_FOLDER')
    json_file = tmp_folder / f'{tree_id}.json'
    if json_file.exists():
        return f.url_for('tmp_file', filename=json_file)
    tree = Trees.query.get(tree_id)
    treefile = Treefile.query.filter_by(tree_id=tree_id).one_or_none()
    if treefile is None:
        flash(gettext('Treefile not found.'), 'error')
    newick = treefile.newick
    meta_file = root / 'static' / 'auspice_tree_meta.json'
    with open(meta_file, 'r', encoding='utf-8') as _:
        json_ = json.load(_)
    json_['meta']['title'] = tree.tree_title
    json_['meta']['panels'] = ['tree']
    json_['meta']['updated'] = str(treefile.upload_date)
    json_file = nwk2auspice(newick, json_file, json_)
    return f.url_for('tmp_file', filename=json_file)


@app.route('/treehub/tree/<tid>', methods=('POST', 'GET'))
def view_tree(tid):
    tree_id = Trees.tid2serial(tid)
    tree = Trees.query.get(tree_id)
    if tree is None:
        return f.abort(404)
    title = tree.tree_title
    tree_auspice_file(tid)
    return f.render_template('view_tree.html', title=title, tree_id=tree_id,
                             tid_func=tid_func)


@app.route('/treehub/tree/edit/<tid>', methods=('POST', 'GET'))
def edit_tree(tid):
    tree_id = Trees.tid2serial(tid)
    tree = Trees.query.get(tree_id)
    title = tree.tree_title
    return f.render_template('edit_tree.html', title=title, tree_id=tree_id,
                             tid_func=tid_func)


def get_nodes(raw_nodes: list) -> dict:
    # raw nodes: taxon_namespace
    label_taxon = {}
    name_list = [i.label for i in raw_nodes]
    node_exist = Nodes.query.filter(Nodes.node_label.in_(name_list)).all()
    for i in node_exist:
        label_taxon[i.node_label] = i.designated_tax_id
    not_found = [i for i in name_list if i not in label_taxon]
    new_names = {}
    # todo: test
    pattern = re.compile(r'.*([A-Z][a-z]+)([_ ])([a-z]+)[_ ].*')
    for i in not_found:
        x = re.search(pattern, i)
        if x is not None:
            species = x.group(1) + ' ' + x.group(3)
            new_names[i] = species
    new_found = NcbiName.query.filter(and_(
        NcbiName.name_class == 'scientific name',
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


@app.route('/treehub/matrix/from_tree/<tid>')
def get_matrix_from_treeid(tid):
    tree_id = Trees.tid2serial(tid)
    submit = Submit.query.filter(Submit.tree_id == tree_id).first_or_404()
    matrix_id = submit.matrix_id
    matrix = Matrix.query.filter(Matrix.matrix_id == matrix_id).first_or_404()
    if matrix.fasta is None:
        f.abort(404)
    else:
        tmp_folder = app.config.get('TMP_FOLDER')
        fasta_file = tmp_folder / f'{matrix_id}.fasta'
        with open(fasta_file, 'w') as _:
            _.write(matrix.fasta)
        return f.send_file(fasta_file, mimetype='text/plain',
                           as_attachment=True)


def handle_submit_info(info_form) -> bool:
    root = str(info_form.root.data).strip()
    # handle root id
    taxon = NcbiName.query.filter_by(name_txt=root).all()
    # first or none
    if len(taxon) == 0:
        # danger
        # for batch submit only
        # todo
        return False
        root = 'root'
        root_id = 1
        session['root_id'] = root_id
        # return False
    else:
        root_id = taxon[0].tax_id
    session['root_id'] = root_id
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
    session['study'] = study.study_id
    session['submit_'] = submit_.submit_id
    return True


def handle_tree_info(tree_form, final=False) -> bool:
    upload_date = date.isoformat(date.today())
    tree = Trees()
    treefile = Treefile()
    matrix = Matrix()
    for i in [tree, treefile, matrix]:
        tree_form.populate_obj(i)
    for j in (treefile, tree):
        j.upload_date = upload_date
    tree.tree_type_new = str(tree.tree_type_new).capitalize()
    tree.root = session['root_id']
    # handle matrix
    if tree_form.matrix_file.data:
        matrix_file_tmp = upload(tree_form.matrix_file.data)
        with open(matrix_file_tmp, 'r') as _:
            matrix.fasta = _.read()
        matrix_file_tmp.unlink()
        matrix.upload_date = upload_date
        # dirty work
    matrix.analysisstep_id = '20222022'
    db.session.add(matrix)
    db.session.commit()
    session['matrix_id_list'].append(matrix.matrix_id)
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
                              not_found=not_found, total=len(raw_nodes)),
                      'error')
                flash(gettext('Node name in tree file should be '
                              '"scientific name with other id" format '
                              '(eg. Oryza sativa id9999'))
        # dendropy error class is too long
    except Exception:
        flash(gettext('Bad tree file. The file should be UTF-8 encoding '
                      'nexus or newick format.'), 'error')
        session['matrix_id_list'].pop()
        db.session.delete(matrix)
        db.session.commit()
        return False
    finally:
        treefile_tmp.unlink()
    # old tree id end at 118270
    db.session.add(tree)
    # get tree_id
    db.session.commit()
    session['tree_id_list'].append(tid_func(tree.tree_id))
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
    return True


@app.route('/treehub/submit', methods=('POST', 'GET'))
def submit_info():
    sf = SubmitForm()
    if sf.validate_on_submit():
        if not handle_submit_info(sf):
            flash(gettext('Taxonomy name not found. '
                          'Currently only support accepted name.'), 'error')
            return f.redirect('/treehub/submit')
        session['tree_n'] = 1
        session['matrix_id_list'] = list()
        session['tree_id_list'] = list()
        flash(gettext('Submit info ok.'))
        return f.redirect(f'/treehub/submit/{session["tree_n"]}')
    return f.render_template('submit_1.html', form=sf)


@app.route('/treehub/submit/<int:n>', methods=('POST', 'GET'))
def submit_data(n):
    # todo: test
    tf = TreeMatrixForm()
    if tf.validate_on_submit():
        if tf.next.data:
            ok = handle_tree_info(tf)
            if not ok:
                return f.redirect(f'/treehub/submit/{session["tree_n"]}')
            flash(gettext('Submit No.%(n)s tree ok.', n=n))
            session['tree_n'] += 1
            return f.redirect(f'/treehub/submit/{session["tree_n"]}')
        if tf.submit.data:
            ok = handle_tree_info(tf, final=True)
            if not ok:
                return f.redirect(f'/treehub/submit/{session["tree_n"]}')
            flash(gettext('Submit No.%(n)s trees ok.', n=n))
            flash(gettext('Submit finished. Your study ID is %(study_id)s',
                          study_id=session['study']))
            flash(gettext('Your TreeID are %(tree_id_list)s',
                          tree_id_list=', '.join(session['tree_id_list'])))
            return f.redirect(f'/treehub/submit/list')
    return f.render_template('submit_2.html', form=tf)


@app.route('/treehub/submit/cancel')
def cancel_submit():
    submit_ = Submit.query.get(session['submit_'])
    return f.redirect(f'/treehub/submit/remove/{submit_.submit_id}')


@app.route('/treehub/submit/remove/<int:submit_id>')
def remove_submit(submit_id):
    # todo: how to remove clean
    submit = Submit.query.get(submit_id)
    if submit is None:
        flash(gettext('Submit not found.'), 'error')
        return f.redirect('/treehub/submit/list')
    submit_id_list = [submit.submit_id]
    study = Study.query.get(submit.study_id)
    other_submits = Submit.query.filter(Submit.study_id == study.study_id).all()
    for i in other_submits:
        submit_id_list.append(i.submit_id)
    tree = Trees.query.filter(Trees.study_id == study.study_id).all()
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
    return f.redirect('/treehub/submit/list')


@app.route('/treehub/submit/list')
@app.route('/treehub/submit/list/<int:page>')
def submit_list(page=1):
    pagination = Submit.query.order_by(Submit.submit_id.desc()).paginate(
        page=page, per_page=10)
    return f.render_template('submit_list.html', pagination=pagination)


@app.route('/treehub/node/<tid>')
def redirect_to_node(tid):
    return f.redirect(f'/planttreenode/{tid}')
    # return f.redirect(f'/treehub/{tree_id}')
    # tree_id = Trees.tid2serial(tid)
    # return f.redirect(f'http://localhost:4000/{tree_id}')


@app.route('/treehub/tid/<tid>')
def goto_tid(tid: str):
    tree_id = Trees.tid2serial(tid)
    if tree_id == -1:
        error_msg = 'Bad TreeID, a valid TreeID looks like "T00118334"'
        return f.abort(404, description=error_msg)
    tree_ = Trees.query.get(tree_id)
    if tree_ is None:
        error_msg = 'TreeID not found'
        return f.abort(404, description=error_msg)
    else:
        return f.redirect(f'/treehub/tree/edit/{tree_id}')


@app.route('/treehub/subscribe')
def subscribe():
    sf = SubscribeForm()
    if sf.validate_on_submit():
        # todo: subscribe and notice by email
        flash(gettext('Subscribe ok.'))
    return f.render_template('subscribe.html', form=sf)


@app.route('/')
@app.route('/treehub/')
@app.route('/treehub/index')
def index():
    results = db.session.query(Submit, Study, Trees).with_entities(
        Submit.date, Submit.cover_img, Submit.cover_img_name,
        Study.upload_date, Study.title, Study.abstract, Study.doi,
        Trees.tree_title, Trees.tree_id).join(
        Submit, Submit.study_id == Study.study_id).join(
        Trees, Submit.tree_id == Trees.tree_id).filter(
        Submit.news == True).order_by(Submit.date.desc()).limit(3)
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
    return f.render_template('index.html', cards=cards, tid=tid_func)


app.register_blueprint(auth, url_prefix='/auth')