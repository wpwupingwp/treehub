#!/usr/bin/python3

import datetime
from functools import lru_cache
from urllib.parse import unquote_plus as url_unquote_plus

import flask_login as fl
from flask import jsonify, redirect, request
from flask_admin.contrib.sqla import ModelView
from flask_restful import Resource
from sqlalchemy import or_, select
from sqlalchemy_serializer import SerializerMixin

from web import admin, db
from web import api as Api


class User(db.Model, fl.UserMixin):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    # email
    username = db.Column(db.VARCHAR(100), unique=True)
    password = db.Column(db.VARCHAR(100))
    register_date = db.Column(db.Date())
    # status
    failed_login = db.Column(db.Integer, default=0)

    def __init__(self, username, password, address=''):
        self.username = username
        self.password = password
        self.register_date = datetime.datetime.now(datetime.UTC)
        self.address = address

    def __repr__(self):
        return f'{self.username}'

    def get_id(self):
        return str(self.user_id)


class Visit(db.Model):
    __tablename__ = 'visits'
    visit_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    ip = db.Column(db.VARCHAR(100))
    url = db.Column(db.VARCHAR(200))
    useragent = db.Column(db.VARCHAR(200))
    date = db.Column(db.DateTime)
    user = db.relationship('User', backref='visit')

    def __init__(self, user_id, ip, url, useragent):
        self.user_id = user_id
        self.ip = ip
        self.url = url
        self.useragent = useragent
        self.date = datetime.datetime.now(datetime.UTC)

    def __str__(self):
        return (f'{self.date}:\t{self.user}\t{self.ip}'
                f'\t{self.url}\t{self.useragent}')


class Nodes(db.Model):
    __tablename__ = 'nodes'
    node_id = db.Column(db.Integer, primary_key=True)
    node_label = db.Column(db.String(255))
    left_id = db.Column(db.Integer)
    right_id = db.Column(db.Integer)
    tree_id = db.Column(db.Integer)
    taxon_variant_id = db.Column(db.Integer)
    legacy_id = db.Column(db.String(35))
    ncbi_map = db.Column(db.Integer)
    designated_tax_id = db.Column(db.Integer)
    db.relationship('Trees', backref='nodes')

    def __init__(self, node_label, designated_tax_id, tree_id):
        self.node_label = node_label
        self.designated_tax_id = designated_tax_id
        self.tree_id = tree_id
        self.left_id = self.right_id = self.taxon_variant_id = self.ncbi_map = 0


class Matrix(db.Model, SerializerMixin):
    __tablename__ = 'matrix'
    # is primary?
    matrix_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    nchar = db.Column(db.Integer)
    ntax = db.Column(db.Integer)
    analysisstep_id = db.Column(db.Integer)
    legacy_id = db.Column(db.String(35))
    description = db.Column(db.String(255))
    input = db.Column(db.Boolean)
    # todo: pg_read_binary_file
    fasta = db.Column(db.String())
    upload_date = db.Column(db.Date)


class NcbiName(db.Model):
    __tablename__ = 'ncbi_names'
    tax_id = db.Column(db.Integer, primary_key=True)
    name_txt = db.Column(db.String(255))
    unique_name = db.Column(db.String(255))
    # scientific name or not
    name_class = db.Column(db.String(32))
    genus_id = db.Column(db.Integer)
    family_id = db.Column(db.Integer)
    order_id = db.Column(db.Integer)


class Study(db.Model, SerializerMixin):
    __tablename__ = 'study'
    # is primary?
    study_id = db.Column(db.Integer, primary_key=True)
    pub_type = db.Column(db.String(30))
    author = db.Column(db.String())
    year = db.Column(db.Integer)
    title = db.Column(db.String())
    journal = db.Column(db.String(255))
    s_author = db.Column(db.String())
    s_title = db.Column(db.String())
    place_pub = db.Column(db.String(255))
    publisher = db.Column(db.String(255))
    volume = db.Column(db.String(50))
    number = db.Column(db.String(150))
    pages = db.Column(db.String(100))
    isbn = db.Column(db.String(35))
    keywords = db.Column(db.String(255))
    abstract = db.Column(db.String())
    legacy_id = db.Column(db.String(30))
    url = db.Column(db.String(255))
    doi = db.Column(db.String(100))
    upload_date = db.Column(db.Date)


class Trees(db.Model, SerializerMixin):
    __tablename__ = 'trees'
    tree_id = db.Column(db.Integer, primary_key=True)
    legacy_id = db.Column(db.String(255))
    root = db.Column(db.Integer, nullable=False)
    tree_label = db.Column(db.String(255))
    tree_title = db.Column(db.String(255))
    tree_type = db.Column(db.String(30))
    tree_type_new = db.Column(db.String(50))
    tree_kind = db.Column(db.String(30))
    tree_quality = db.Column(db.String(30))
    study_id = db.Column(db.Integer)
    upload_date = db.Column(db.Date)
    serialize_rules = ('-file.tree',)
    file = db.relationship('Treefile', back_populates='tree')

    def __str__(self):
        return f'{self.tree_id} {self.root} {self.tree_title}'

    @staticmethod
    def tid(tree_id: int) -> str:
        """
        Generate TreeID from tree_id in database
        Since postgresql serial is 4*8 bit, if id is too big,
        alter table and return raw number.
        TID format: 'T00A100000'
            first letter, 'T'
            2-4, digit or capital letter, 0-9 and A-Z
            5-10, digit
        Args:
            tree_id: tree_id, postgresql serial number

        Returns:
            tid: str
        """
        max_n = min(36 ** 3 * 100_000, 2 ** (8 * 4 - 1))
        prefix = 'T'
        n = 1_000_00
        if tree_id >= max_n:
            return 'T' + str(tree_id)
        # 0-9 and A-Z
        base = 26 + 10

        a, b = divmod(tree_id, n)
        letters = ''
        while a > 0:
            a, digit = divmod(a, base)
            if digit < 10:
                letters = str(digit) + letters
            else:
                letters = chr(ord('A') + (digit - 10)) + letters
        return prefix + f'{letters:>03}' + f'{b:05d}'

    @staticmethod
    def tid2serial(tid: str) -> int:
        # convert TreeID to database's serial id
        # return -1 for error
        # test case
        base = 36
        # T ABC 00000
        length = 9
        _ = [1, 28, 200, 3000, 40000, 5000000, 5000001, 10000000,
             36 * 1000_00 - 1, 36 * 100_000,
             36 * 35 * 1000_00 - 1, 36 * 35 * 100_000, 36 ** 3 * 100000 - 1,
             36 ** 3 * 100_000, 36 ** 3 * 100_000 + 1,
             800000000038, 1000000000738]
        if tid[0] != 'T' or len(tid) < length:
            return -1
        if len(tid) > length:
            return int(tid[1:])
        letters = tid[1:4]
        numbers = tid[4:]
        big = 0
        # bit start from 0
        for bit, n in enumerate(reversed(letters)):
            if n.isdigit():
                big += int(n) * base ** bit
            else:
                big += (ord(n) - ord('A') + 10) * base ** bit
        serial_id = big * 100_000 + int(numbers)
        return serial_id


class Treefile(db.Model, SerializerMixin):
    __tablename__ = 'treefile'
    treefile_id = db.Column(db.Integer, primary_key=True)
    tree_id = db.Column(db.Integer, db.ForeignKey('trees.tree_id'))
    nexus = db.Column(db.String())
    newick = db.Column(db.String())
    phyloxml = db.Column(db.String())
    upload_date = db.Column(db.Date)
    serialize_rules = ('-tree.file',)
    tree = db.relationship('Trees', back_populates='file')

    def __str__(self):
        return f'{self.treefile_id} {self.tree_id}'


class Submit(db.Model, SerializerMixin):
    __tablename__ = 'submit'
    submit_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255))
    ip = db.Column(db.VARCHAR(100))
    date = db.Column(db.DateTime)
    user_id = db.Column(db.Integer)
    tree_id = db.Column(db.Integer)
    treefile_id = db.Column(db.Integer)
    study_id = db.Column(db.Integer)
    matrix_id = db.Column(db.Integer)
    cover_img = db.Column(db.BINARY())
    cover_img_name = db.Column(db.String())
    news = db.Column(db.Boolean())

    def __init__(self, email, ip, date, user_id, study_id):
        self.email = email
        self.ip = ip
        self.date = date
        self.user_id = user_id
        self.study_id = study_id


class MyModelView(ModelView):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

    def is_accessible(self):
        return (fl.current_user.is_authenticated and
                fl.current_user.username == 'admin')

    def is_accessible_callback(self):
        return redirect('/')


@lru_cache(maxsize=1000)
def query_taxonomy(taxonomy: str):
    # speed up
    species_tax_id = NcbiName.query.filter(
        NcbiName.name_txt == taxonomy).with_entities(NcbiName.tax_id).all()
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


class MatrixGet(Resource):
    @staticmethod
    def get(matrix_id: str):
        """
        get matrix record
        ---
        parameters:
            - in: path
              name: matrix_id
              type: integer
              required: true
        responses:
            200:
                description: A single matrix item
                schema:
                    id: Matrix
                    properties:
                        matrix_id:
                            type: integer
                            description: The ID of the matrix
                        title:
                            type: string
                            description: The title of the matrix
                        nchar:
                            type: integer
                            description: The number of characters in the matrix
                        ntax:
                            type: integer
                            description: The number of taxa in the matrix
                        analysisstep_id:
                            type: integer
                            description: The ID of the analysis step associated with the matrix
                        legacy_id:
                            type: string
                            description: The legacy ID of the matrix
                        description:
                            type: string
                            description: The description of the matrix
                        input:
                            type: boolean
                            description: Whether the matrix is an input to an analysis step
                        fasta:
                            type: string
                            description: The FASTA format of the matrix
                        upload_date:
                            type: string
                            format: date
                            description: The upload date of the matrix
        """
        matrix_id = int(matrix_id)
        x = Matrix.query.filter_by(matrix_id=matrix_id).first_or_404()
        return x.to_dict()


class StudyGet(Resource):
    @staticmethod
    def get(study_id: str):
        """
        get study record
        ---
        parameters:
            - in: path
              name: study_id
              type: integer
              required: true
        responses:
            200:
                description: A single study item
                schema:
                    id: Study
                    properties:
                        study_id:
                            type: integer
                            description: The ID of the study
                        pub_type:
                            type: string
                            description: The publication type of the study
                        author:
                            type: string
                            description: The author of the study
                        year:
                            type: integer
                            description: The year of publication of the study
                        title:
                            type: string
                            description: The title of the study
                        journal:
                            type: string
                            description: The journal in which the study was published
                        s_author:
                            type: string
                            description: The second author of the study
                        s_title:
                            type: string
                            description: The second title of the study
                        place_pub:
                            type: string
                            description: The place of publication of the study
                        publisher:
                            type: string
                            description: The publisher of the study
                        volume:
                            type: string
                            description: The volume of the publication containing the study
                        number:
                            type: string
                            description: The number of the issue containing the study
                        pages:
                            type: string
                            description: The page numbers of the study in the publication
                        isbn:
                            type: string
                            description: The ISBN of the publication containing the study
                        keywords:
                            type: string
                            description: The keywords associated with the study
                        abstract:
                            type: string
                            description: The abstract of the study
                        legacy_id:
                            type: string
                            description: The legacy ID of the study
                        url:
                            type: string
                            description: The URL of the study
                        doi:
                            type: string
                            description: The DOI of the study
                        upload_date:
                            type: string
                            format: date
                            description: The upload date of the study
        """
        study_id = int(study_id)
        x = Study.query.filter_by(study_id=study_id).first_or_404()
        return x.to_dict()


class TreesGet(Resource):
    def get(self, tree_id: str):
        """
        get tree record
        ---
        parameters:
            - in: path
              name: tree_id
              type: integer
              required: true
        responses:
            200:
                description: a Tree record
                schema:
                    id: Trees
                    properties:
                        tree_id:
                            type: integer
                            description: The ID of the tree
                        legacy_id:
                            type: string
                            description: The legacy ID of the tree
                        root:
                            type: integer
                            description: The root of the tree
                        tree_label:
                            type: string
                            description: The label of the tree
                        tree_title:
                            type: string
                            description: The title of the tree
                        tree_type:
                            type: string
                            description: The type of the tree
                        tree_type_new:
                            type: string
                            description: The new type of the tree
                        tree_kind:
                            type: string
                            description: The kind of the tree
                        tree_quality:
                            type: string
                            description: The quality of the tree
                        study_id:
                            type: integer
                            description: The ID of the study
                        upload_date:
                            type: string
                            format: date
                            description: The upload date of the tree
        """
        tree_id = int(tree_id)
        x = Trees.query.filter_by(tree_id=tree_id).first_or_404()
        return x.to_dict()


class TreesQuery(Resource):
    @staticmethod
    def get(taxon: str):
        """
        Query by taxon name
        ---
        parameters:
            - name: taxon
              in: path
              type: string
              required: true
              default: Poa
        responses:
            200:
                description: A list of tree records
                schema:
                type: array
                items:
                    - type: string
                    - type: string
                    - type: string
                    - type: string
                    - type: string
                    - type: string
                    - type: string
                    - type: string
                    - type: string
                examples:
                    - ['Tree title', 'Year', 'Title', 'Journal', 'View', 'Edit',
                         'DOI', 'Matrix']
        """
        host = request.host_url
        results_list = [
            ['Tree title', 'Year', 'Title', 'Journal', 'View', 'Edit',
             'DOI', 'Matrix']]
        taxon_str = url_unquote_plus(taxon)
        if len(taxon_str) == 0:
            return jsonify(results_list)
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
            Submit, Submit.tree_id == Trees.tree_id, isouter=True).join(
            Matrix, Matrix.matrix_id == Submit.matrix_id, isouter=True).filter(
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
        return jsonify(results_list)


class TreefileGet(Resource):
    @staticmethod
    def get(treefile_id: str):
        """
        get treefile record
        ---
        parameters:
            - in: path
              name: treefile_id
              type: integer
              required: true
              description: ID of the treefile
        responses:
            200:
                description: A single treefile item
                schema:
                    id: Treefile
                    properties:
                        treefile_id:
                            type: integer
                            description: The ID of the treefile
                        tree_id:
                            type: integer
                            description: The ID of the tree associated with the
                                treefile
                        nexus:
                            type: string
                            description: The nexus format of the treefile
                        newick:
                            type: string
                            description: The newick format of the treefile
                        phyloxml:
                            type: string
                            description: The phyloxml format of the treefile
                        upload_date:
                            type: string
                            format: date
                            description: The upload date of the treefile
        """
        treefile_id = int(treefile_id)
        x = Treefile.query.filter_by(treefile_id=treefile_id).first_or_404()
        return x.to_dict()


class SubmitGet(Resource):
    @staticmethod
    def get(submit_id: str):
        """
        get submit record
        ---
        parameters:
            - in: path
              name: submit_id
              type: integer
              required: true
        responses:
            200:
                description: A single submit item
                schema:
                    id: Submit
                    properties:
                        submit_id:
                            type: integer
                            description: The ID of the submit
                        email:
                            type: string
                            description: The email of the submitter
                        ip:
                            type: string
                            description: The IP address of the submitter
                        date:
                            type: string
                            format: date-time
                            description: The date and time of the submission
                        user_id:
                            type: integer
                            description: The ID of the user who submitted the
                                data
                        tree_id:
                            type: integer
                            description: The ID of the tree associated with the
                                submission
                        treefile_id:
                            type: integer
                            description: The ID of the treefile associated with
                                the submission
                        study_id:
                            type: integer
                            description: The ID of the study associated with the
                                submission
                        matrix_id:
                            type: integer
                            description: The ID of the matrix associated with
                                the submission
                        cover_img:
                            type: string
                            format: binary
                            description: The cover image associated with the
                                submission
                        cover_img_name:
                            type: string
                            description: The name of the cover image associated
                                with the submission
                        news:
                            type: boolean
                            description: Whether or not the submission is news
        """
        submit_id = int(submit_id)
        x = Submit.query.filter_by(submit_id=submit_id).first_or_404()
        return x.to_dict()


Api.add_resource(TreesGet, '/treehub/api/tree/get/<tree_id>')
Api.add_resource(TreesQuery, '/treehub/api/tree/query/<taxon>')
Api.add_resource(MatrixGet, '/treehub/api/matrix/get/<matrix_id>')
Api.add_resource(TreefileGet, '/treehub/api/treefile/get/<treefile_id>')
Api.add_resource(StudyGet, '/treehub/api/study/get/<study_id>')
Api.add_resource(SubmitGet, '/treehub/api/submit/get/<submit_id>')

# for m in [User, Goods, Bid, Message]:
for m in [User, Matrix, NcbiName, Nodes, Study, Trees, Treefile, Visit]:
    admin.add_view(MyModelView(m, db.session))



