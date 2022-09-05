#!/usr/bin/python3

from datetime import datetime
from flask import redirect
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy
import flask_login as fl

from web import app, admin
from flask_wtf import FlaskForm

db = SQLAlchemy(app)


class User(db.Model, fl.UserMixin):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    # email
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
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
    visit_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    ip = db.Column(db.String(100))
    url = db.Column(db.String(200))
    useragent = db.Column(db.String(200))
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


class MyModelView(ModelView):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

    def is_accessible(self):
        return True
        return (fl.current_user.is_authenticated and
                fl.current_user.username=='admin')

    def is_accessible_callback(self):
        return redirect('/')


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
    filename = db.Column(db.String())
    # todo: pg_read_binary_file
    file_bin = db.Column(db.BLOB())


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


class Treefile(db.Model):
    __tablename__ = 'treefile'
    tree_id = db.Column(db.Integer, primary_key=True)
    tree_text = db.Column(db.String())


# for m in [User, Goods, Bid, Message]:
for m in [User, Matrix, Nodes, Trees, Treefile]:
    admin.add_view(MyModelView(m, db.session))
