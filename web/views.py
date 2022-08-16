#!/usr/bin/python3

import flask as f
from flask import g, request, session
import flask_login as fl
from sqlalchemy import not_, and_

# import flask_mail

from web import app, lm, root
from web.database import Nodes, Trees, Treefile, db
from web.auth import auth
from web.form import BidForm



@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return f.send_from_directory(app.config['UPLOADED_PHOTOS_DEST'], filename)


# todo: temporary link redirect
@app.route('/view_trees')
def view_admin():
    return f.redirect('/admin')


@app.route('/')
@app.route('/index')
def index():
    return f.render_template('index.html')


