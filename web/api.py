from urllib.parse import unquote_plus as url_unquote_plus

import flask as f
from sqlalchemy import select

from web import app
from web.database import Matrix, Nodes, Study, Submit, Trees, db
from web.views import query_taxonomy


@app.route('/treehub/tree/query_api/<taxon>')
def tree_query_api(taxon: str):
    host = f.request.host_url
    results_list = [['Tree title', 'Year', 'Title', 'Journal', 'View', 'Edit',
                     'DOI', 'Matrix']]
    taxon_str = url_unquote_plus(taxon)
    if len(taxon_str) == 0:
        return f.jsonify(results_list)
    # species
    if ' ' in taxon_str:
        condition = Trees.tree_id.in_(select(Nodes.tree_id).where(
            Nodes.node_label.like(taxon_str)))
    else:
        condition = query_taxonomy(taxon_str)
    results = db.session.query(Study, Trees, Submit, Matrix).with_entities(
        Study.title, Study.year, Study.journal, Study.doi,
        Trees.tree_id, Trees.tree_title, Matrix.upload_date).join(
        Study, Study.study_id == Trees.study_id).join(
        Submit, Submit.tree_id==Trees.tree_id, isouter=True).join(
        Matrix, Matrix.matrix_id==Submit.matrix_id, isouter=True).filter(
        condition).order_by(Study.year.desc()).all()
    for r in results:
        record = [Trees.tid(r.tree_id), r.tree_title,
                  r.year, r.title, r.journal,
                  f'{host}treehub/tree/{r.tree_id}',
                  f'{host}treehub/tree/edit/{r.tree_id}',
                  f'https://doi.org/{r.doi}' if r.doi is not None else '',
                  (f'{host}treehub/matrix/from_tree/{r.tree_id}'
                   if r.upload_date is not None else '')]
        results_list.append(record)
    return f.jsonify(results_list)