#!/usr/bin/python3

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
import wtforms as m
from wtforms import validators as v
from wtforms.fields import DateField


# cannot use flask_upload, _uploads.uploaded_file is broken
# that photos.url() cannot be used, use flask instead
IMG = set('jpg jpe jpeg png gif svg bmp webp'.split())


class UserForm(FlaskForm):
    username = m.StringField('Email', validators=[
        v.input_required(), v.email(), v.length(max=100)])
    password = m.PasswordField('password', validators=[
        v.input_required(), v.length(min=4, max=100)])
    password2 = m.PasswordField('password again', validators=[
        v.input_required(), v.equal_to('password')])
    submit = m.SubmitField('Submit')


class LoginForm(FlaskForm):
    username = m.StringField('User name', validators=[v.input_required(),
                                                v.length(max=100)])
    password = m.PasswordField('Password', validators=[
        v.input_required(), v.length(min=4, max=100)])
    submit = m.SubmitField('Submit')


class GoodsForm(FlaskForm):
    name = m.StringField('名称', validators=[v.input_required(),
                                           v.length(max=100)])
    description = m.TextAreaField('描述', validators=[v.input_required()])
    # address for delivery
    address = m.StringField('地址', validators=[v.length(max=100)])
    original_price = m.FloatField('原价')
    lowest_price = m.FloatField('最低价', validators=[v.input_required()])
    highest_price = m.FloatField('最高价', validators=[v.input_required()])
    expired_date = DateField('截止时间')
    photo1 = FileField('照片1', validators=[FileAllowed(IMG, '不支持的格式')])
    photo2 = FileField('照片2', validators=[FileAllowed(IMG, '不支持的格式')])
    photo3 = FileField('照片3', validators=[FileAllowed(IMG, '不支持的格式')])
    submit = m.SubmitField('提交')




class StudyForm(FlaskForm):
    pass


class TreeForm(FlaskForm):
    pass


class MatrixForm(FlaskForm):
    pass