#!/usr/bin/python3

import uuid
import flask as f
import flask_login as fl
from werkzeug.utils import secure_filename
from sqlalchemy import not_
from pathlib import Path
from PIL import Image, ImageOps

from web import app, lm, root
from web.form import UserForm, LoginForm
from web.database import User, Study, Nodes, Trees, Treefile, Visit, db

auth = f.Blueprint('auth', __name__)
# cannot use photos.url
img_path = root / 'upload' / 'img'
# unread msg

@lm.user_loader
def load_user(user_id):
    user = User.query.get(user_id)
    return user


@auth.route('/login', methods=('POST', 'GET'))
def login():
    #if f.g.user is not None and f.g.user.is_authenticated():
    #    return f.redirect('/index')
    lf = LoginForm()
    if lf.validate_on_submit():
        user = User.query.filter_by(username=lf.username.data).first()
        if user is None:
            f.flash('User does not exist.')
        elif user.password != lf.password.data:
            print(user.password, lf.password.data)
            user.failed_login += 1
            db.session.commit()
            try_n = app.config["MAX_LOGIN"] - user.failed_login
            if try_n > 0:
                f.flash(f'Error password {user.failed_login} times，'
                        f'could try again {try_n} times.')
            else:
                f.flash('Too much failed login. Please contact administrator.')
        else:
            user.failed_login = 0
            fl.login_user(user)
            f.flash(f'Login success.')
            old_visit = Visit.query.get(f.session['visit_id'])
            if old_visit is not None:
                db.session.delete(old_visit)
            db.session.commit()
            f.session['tracked'] = False
            return f.redirect('/index')
    return f.render_template('login.html', form=lf)


@fl.login_required
@auth.route('/logout', methods=('POST', 'GET'))
def logout():
    f.session['tracked'] = False
    fl.logout_user()
    return f.redirect('/index')


@auth.route('/register', methods=('POST', 'GET'))
def register():
    uf = UserForm()
    if uf.validate_on_submit():
        username = User.query.filter_by(username=uf.username.data).first()
        if username is not None:
            f.flash('用户名已注册')
            return f.render_template('tree_query.html', form=uf)
        user = User(uf.username.data, uf.password.data, uf.address.data)
        db.session.add(user)
        db.session.commit()
        f.flash('注册成功')
        return f.redirect('/index')
    return f.render_template('tree_query.html', form=uf)


def compress_photo(old_path: Path) -> Path:
    """
    Compress and rotate image with PIL
    Args:
        old_path: Path
    """
    small = 1024 * 1024
    if old_path.stat().st_size <= small:
        return old_path
    old = Image.open(old_path)
    rotate = ImageOps.exif_transpose(old)
    rotate.thumbnail((1024, 1024))
    rotate.save(old_path, 'JPEG')
    return old_path



@auth.route('/message')
def sent_message(user_id, page=1):
    # import flask_mail
    # todo: send mail if submit
    return







