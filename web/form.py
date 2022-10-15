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


class QueryForm(FlaskForm):
    # tree
    taxonomy = m.StringField('Taxonomy',
                             render_kw={'placeholder': 'Oryza sativa'})
    tree_title = m.StringField('Tree title', validators=[v.length(max=255)],
                               render_kw={'placeholder': 'Poaceae'})
    is_dating = m.BooleanField('Is dating tree')
    # study
    year = m.StringField('Publish year',  render_kw={'placeholder': 2022})
    author = m.StringField('Author', validators=[v.length(max=100)],
                           render_kw={'placeholder': 'eg. Charles Darwin'})
    title = m.StringField('Title', validators=[v.length(max=200)],
                          render_kw={'placeholder': 'Article title'})
    keywords = m.StringField('Keywords', validators=[v.length(max=50)])
    doi = m.StringField('DOI', validators=[v.length(max=100)],
                        render_kw={'placeholder': 'eg. 10.9999/123456789'})
    submit = m.SubmitField('Submit')


class SortQueryForm(FlaskForm):
    item = m.SelectField('Sort by',
                         choices=['ID', 'Tree title', 'Kind', 'Publish year',
                                  'Article title', 'Journal', 'DOI'])
    order = m.SelectField('Order', choices=['Descend', 'Ascend'])
    submit = m.SubmitField('Sort')

    @staticmethod
    def new_item_choices(key=None):
        old = ['ID', 'Tree title', 'Kind', 'Publish year', 'Article title',
               'Journal', 'DOI']
        if key is None:
            return old
        else:
            index = old.index(key)
            new = [key, *old[:index], *old[index+1:]]
            return new

    @staticmethod
    def new_order_choices(key=None):
        old = ['Descend', 'Ascend']
        if key is None or key == 'Descend':
            return old
        else:
            return list(reversed(old))




class TreeForm(FlaskForm):
    # outdated
    taxonomy = m.StringField('Taxonomy', validators=[v.input_required()],
                             render_kw={'placeholder': 'Asteraceae'})
    tree_title = m.StringField('Tree title', validators=[v.length(max=255)],
                               render_kw={'placeholder': 'XXX tree of YYY'})
    is_dating = m.BooleanField('Dating tree')
    tree_type = m.SelectField('Tree type', default='Consensus',
                              choices=[('Consensus', 'Consensus'),
                                       ('Single', 'Single'),
                                       ('Other', 'Other')])
    tree_kind = m.RadioField('Tree kind', default='Species Tree',
                             choices=[('Species Tree', 'Species Tree'),
                                      ('Gene Tree', 'Gene Tree'),
                                      ('Other', 'Other')])
    # todo
    # tree_file = m.MultipleFileField('Tree file (NEXUS or newick format)')
    tree_file = m.FileField('Tree files (NEXUS format)',
                                    validators=[v.data_required()])


class MatrixForm(FlaskForm):
    # outdated
    matrix_title = m.StringField('Matrix title', validators=[v.length(max=255)])
    description = m.SelectField('Matrix type', default='Nucleic Acid',
                                choices=[('Nucleic Acid', 'Nucleic Acid'),
                                         ('Amino Acid', 'Amino Acid'),
                                         ('Morphological', 'Morphological'),
                                         ('Combination', 'Combination'),
                                         ('Other', 'Other')])
    matrix_file = m.FileField('Matrix file (fasta format)')


class StudyForm(FlaskForm):
    # outdated
    year = m.StringField('Publish year')
    author = m.StringField('Author', validators=[v.length(max=100)])
    title = m.StringField('Title', validators=[v.length(max=200)])
    keywords = m.StringField('Keywords', validators=[v.length(max=50)])
    doi = m.StringField('DOI', validators=[v.length(max=100)])


class OutdatedSubmitForm(FlaskForm):
    # todo
    email = m.StringField('Email', validators=[v.email(), v.input_required()])
    study = m.FormField(StudyForm)
    matrix = m.FormField(MatrixForm)
    tree = m.FormField(TreeForm)
    submit = m.SubmitField('Submit')


class SubmitForm(FlaskForm):
    # todo: currently support one file per submit
    # tree
    email = m.StringField('Email', validators=[v.email(), v.input_required()],
                          render_kw={'placeholder': 'eg. alex@example.org'})
    root = m.StringField('Taxonomy', validators=[v.input_required()],
                         render_kw={'placeholder': 'root node or lineage name'})
    tree_title = m.StringField('Tree title', validators=[v.length(max=255)],
                               render_kw={'placeholder': 'eg. XXX tree of YYY'})
    is_dating = m.BooleanField('Dating tree')
    tree_type = m.SelectField('Tree type', default='Consensus',
                              choices=[('Consensus', 'Consensus'),
                                       ('Single', 'Single'),
                                       ('Other', 'Other')])
    tree_kind = m.RadioField('Tree kind', default='Species Tree',
                             choices=[('Species Tree', 'Species Tree'),
                                      ('Gene Tree', 'Gene Tree'),
                                      ('Other', 'Other')])
    # tree_file = m.MultipleFileField('Tree file (NEXUS or newick format)')
    tree_file = m.FileField('Tree files (NEXUS or newick format)',
                            validators=[v.data_required()])
    # matrix
    matrix_title = m.StringField(
        'Matrix title', validators=[v.length(max=255)],
        render_kw={'placeholder': 'eg. XXX matrix of tree YYY'})
    description = m.SelectField('Matrix type', default='Nucleic Acid',
                                choices=[('Nucleic Acid', 'Nucleic Acid'),
                                         ('Amino Acid', 'Amino Acid'),
                                         ('Morphological', 'Morphological'),
                                         ('Combination', 'Combination'),
                                         ('Other', 'Other')])
    matrix_file = m.FileField('Matrix file (fasta format)')
    # study
    year = m.IntegerField('Publish year', default=2022)
    author = m.StringField(
        'Author', validators=[v.length(max=100)],
        render_kw={'placeholder': 'eg. Carl Linnaeus, Charles Robert Darwin'})
    title = m.StringField('Title', validators=[v.length(max=200)],
                          render_kw={'placeholder': 'Article title'})
    keywords = m.StringField('Keywords', validators=[v.length(max=50)],
                             render_kw={'placeholder': 'Article keywords'})
    doi = m.StringField('DOI', validators=[v.length(max=100)],
                        render_kw={'placeholder': 'eg. 10.9999/1234567890'})
    submit = m.SubmitField('Submit')


tmp2 = '''
<form method="post">
    {{ form.csrf_token() }}
    <div class="row ">
        <div class="col">
            {{ render_field(form.root, form_type='horizontal') }}
        </div>
        <div class="col">
            {{ render_field(form.submit, form_type='horizontal') }}
        </div>
    </div>
</form>

'''
