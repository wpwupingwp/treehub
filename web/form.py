#!/usr/bin/python3

from flask_babel import lazy_gettext as gettext
from flask_wtf import FlaskForm
from wtforms import validators as v
import wtforms as m

# cannot use flask_upload, _uploads.uploaded_file is broken
# that photos.url() cannot be used, use flask instead
IMG = set('jpg jpe jpeg png gif svg bmp webp'.split())


class UserForm(FlaskForm):
    username = m.StringField(gettext('Email'), validators=[
        v.input_required(), v.email(), v.length(max=100)])
    password = m.PasswordField(gettext('Password'), validators=[
        v.input_required(), v.length(min=4, max=100)])
    password2 = m.PasswordField(gettext('Password again'), validators=[
        v.input_required(), v.equal_to('password')])
    submit = m.SubmitField(gettext('Submit'))


class LoginForm(FlaskForm):
    username = m.StringField(gettext('Username'), validators=[v.input_required(),
                                                      v.length(max=100)])
    password = m.PasswordField(gettext('Password'), validators=[
        v.input_required(), v.length(min=4, max=100)])
    submit = m.SubmitField(gettext('Submit'))


class QueryForm(FlaskForm):
    # tree
    taxonomy = m.StringField(gettext('Taxonomy'), render_kw={
        'placeholder': 'eg. Rosales, Fabaceae, Zea'})
    species = m.StringField(gettext('Species'),
                            render_kw={'placeholder': 'eg. Oryza sativa'})
    tree_title = m.StringField(gettext('Tree title'),
                               validators=[v.length(max=255)], render_kw={
            'placeholder': 'eg. Bootstrap tree of Poaceae'})
    is_dating = m.BooleanField(gettext('Is dating tree'))
    # study
    year = m.StringField(gettext('Publish year'),
                         render_kw={'placeholder': 'eg. 2021'})
    author = m.StringField(gettext('Author'), validators=[v.length(max=100)],
                           render_kw={'placeholder': 'eg. Charles Darwin'})
    title = m.StringField(gettext('Title'), validators=[v.length(max=200)],
                          render_kw={'placeholder': 'Article title'})
    keywords = m.StringField(gettext('Keywords'), validators=[v.length(max=50)])
    doi = m.StringField(gettext('DOI'), validators=[v.length(max=100)],
                        render_kw={'placeholder': 'eg. 10.9999/123456789'})
    submit = m.SubmitField(gettext('Submit'))


class SortQueryForm(FlaskForm):
    item = m.SelectField('Sort by',
                         choices=['ID', 'Tree title', 'Kind', 'Publish year',
                                  'Article title', 'Journal', 'DOI'])
    order = m.SelectField('Order', choices=['Descend', 'Ascend'])
    submit = m.SubmitField(gettext('Sort'))

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


class SubmitForm(FlaskForm):
    # todo: currently support one file per submit
    # tree
    email = m.StringField(gettext('Email(*)'),
                          validators=[v.email(), v.input_required()],
                          render_kw={'placeholder': 'eg. alex@example.org'})
    root = m.StringField(gettext('Taxonomy(*)'), validators=[v.input_required()],
                         render_kw={'placeholder': 'root node or lineage name'})
    tree_title = m.StringField(gettext('Tree title'),
                               validators=[v.length(max=255)],
                               render_kw={'placeholder': 'eg. XXX tree of YYY'})
    is_dating = m.BooleanField(gettext('Dating tree'))
    tree_type = m.SelectField(gettext('Tree type'), default='Consensus',
                              choices=[('Consensus', 'Consensus'),
                                       ('Single', 'Single'),
                                       ('Other', 'Other')])
    tree_kind = m.RadioField(gettext('Tree kind'), default='Species Tree',
                             choices=[('Species Tree', 'Species Tree'),
                                      ('Gene Tree', 'Gene Tree'),
                                      ('Other', 'Other')])
    # tree_file = m.MultipleFileField('Tree file (NEXUS or newick format)')
    tree_file = m.FileField(gettext('Tree files (NEXUS or newick format) (*)'),
                            validators=[v.data_required()])
    # matrix
    matrix_title = m.StringField(gettext('Matrix title'),
                                 validators=[v.length(max=255)],
                                 render_kw={'placeholder':
                                                'eg. XXX matrix of tree YYY'})
    description = m.SelectField(gettext('Matrix type'), default='Nucleic Acid',
                                choices=[('Nucleic Acid', 'Nucleic Acid'),
                                         ('Amino Acid', 'Amino Acid'),
                                         ('Morphological', 'Morphological'),
                                         ('Combination', 'Combination'),
                                         ('Other', 'Other')])
    matrix_file = m.FileField(gettext('Matrix file (fasta format)'))
    # study
    journal = m.StringField(gettext('Journal'),
                            render_kw={'placeholder': 'eg. JSE'})
    year = m.IntegerField(gettext('Publish year'), default=2022)
    author = m.StringField(
        gettext('Author'), validators=[v.length(max=100)],
        render_kw={'placeholder': 'eg. Carl Linnaeus, Charles Robert Darwin'})
    title = m.StringField(gettext('Article title'),
                          validators=[v.length(max=200)],
                          render_kw={'placeholder': 'Article title'})
    abstract = m.TextAreaField(gettext('Abstract'),
                               validators=[v.length(max=2020)])
    keywords = m.StringField(gettext('Keywords'), validators=[v.length(max=50)],
                             render_kw={'placeholder': 'Article keywords'})
    doi = m.StringField(gettext('DOI'), validators=[v.length(max=100)],
                        render_kw={'placeholder': 'eg. 10.9999/1234567890'})
    cover_img = m.FileField(gettext('Cover image (.jpg or .png)'))
    news = m.BooleanField(gettext('Submit for news'), default=False)
    submit = m.SubmitField(gettext('Submit'))


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
