#!/usr/bin/python3

from datetime import datetime
from flask import redirect
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy
import flask_login as fl

from web import app, admin

db = SQLAlchemy(app)


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
        self.register_date = datetime.utcnow()
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


class Matrix(db.Model):
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


class Study(db.Model):
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
    cover_img = db.Column(db.BINARY())
    for_news = db.Column(db.Boolean())
    lastmodifieddate = db.Column(db.Date)


class Trees(db.Model):
    __tablename__ = 'trees'
    tree_id = db.Column(db.Integer, primary_key=True)
    legacy_id = db.Column(db.String(255))
    root = db.Column(db.Integer, nullable=False)
    tree_label = db.Column(db.String(255))
    tree_title = db.Column(db.String(255))
    tree_type = db.Column(db.String(30))
    tree_kind = db.Column(db.String(30))
    tree_quality = db.Column(db.String(30))
    study_id = db.Column(db.Integer)
    is_dating = db.Column(db.Boolean, default=False)
    upload_date = db.Column(db.Date)
    file = db.relationship('Treefile', back_populates='tree')

    def __str__(self):
        return f'{self.tree_id} {self.root} {self.tree_title}'


class Treefile(db.Model):
    __tablename__ = 'treefile'
    treefile_id = db.Column(db.Integer, primary_key=True)
    tree_id = db.Column(db.Integer, db.ForeignKey('trees.tree_id'))
    nexus = db.Column(db.String())
    newick = db.Column(db.String())
    phyloxml = db.Column(db.String())
    upload_date = db.Column(db.Date)
    tree = db.relationship('Trees', back_populates='file')

    def __str__(self):
        return f'{self.treefile_id} {self.tree_id}'


class Submit(db.Model):
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

    def __init__(self, email, ip, date, user_id, tree_id, treefile_id, study_id,
                 matrix_id):
        self.email = email
        self.ip = ip
        self.date = date
        self.user_id = user_id
        self.tree_id = tree_id
        self.treefile_id =  treefile_id
        self.study_id = study_id
        self.matrix_id = matrix_id


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
