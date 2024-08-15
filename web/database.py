#!/usr/bin/python3

import datetime

from sqlalchemy_serializer import SerializerMixin
from flask import redirect
from flask_admin.contrib.sqla import ModelView
from flask_restful_swagger_3 import Resource
import flask_login as fl

from web import db, admin, api


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
        self.date = datetime.now()

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


class Matrix(db.Model, Resource, SerializerMixin):
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

    @staticmethod
    def get(matrix_id: str):
        matrix_id = int(matrix_id)
        x = Matrix.query.filter_by(matrix_id=matrix_id).first_or_404()
        return x.to_dict()


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


class Study(db.Model, Resource, SerializerMixin):
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

    @staticmethod
    def get(study_id: str):
        study_id = int(study_id)
        x = Study.query.filter_by(study_id=study_id).first_or_404()
        return x.to_dict()


class Trees(db.Model, Resource, SerializerMixin):
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
                big += int(n) * base**bit
            else:
                big += (ord(n) - ord('A') + 10) * base**bit
        serial_id = big * 100_000 + int(numbers)
        return serial_id

    @staticmethod
    def get(tree_id: str):
        tree_id = int(tree_id)
        x = Trees.query.filter_by(tree_id=tree_id).first_or_404()
        return x.to_dict()


class Treefile(db.Model, Resource, SerializerMixin):
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

    @staticmethod
    def get(treefile_id: str):
        treefile_id = int(treefile_id)
        x = Treefile.query.filter_by(treefile_id=treefile_id).first_or_404()
        return x.to_dict()


class Submit(db.Model, Resource, SerializerMixin):
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

    @staticmethod
    def get(submit_id: str):
        submit_id = int(submit_id)
        x = Submit.query.filter_by(submit_id=submit_id).first_or_404()
        return x.to_dict()


class MyModelView(ModelView):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

    def is_accessible(self):
        return (fl.current_user.is_authenticated and
                fl.current_user.username=='admin')

    def is_accessible_callback(self):
        return redirect('/')


# for m in [User, Goods, Bid, Message]:
for m in [User, Matrix, NcbiName, Nodes, Study, Trees, Treefile, Visit]:
    admin.add_view(MyModelView(m, db.session))

api.add_resource(Trees, '/treehub/api/tree/<tree_id>')
api.add_resource(Matrix, '/treehub/api/matrix/<matrix_id>')
api.add_resource(Treefile, '/treehub/api/treefile/<treefile_id>')
api.add_resource(Study, '/treehub/api/study/<study_id>')
api.add_resource(Submit, '/treehub/api/submit/<submit_id>')
