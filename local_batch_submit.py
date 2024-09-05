import json
from pprint import pprint
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from time import sleep

import requests

# should clean bad submit before
URL1 = 'http://localhost:2022/treehub/submit'
# +n
URL2 = 'http://localhost:2022/treehub/submit/'
# result of tree cralwer
MERGE_JSON = Path(r'R:\submit\merge.json')
TREE_FOLDER = Path(r'R:\submit\trees')


def print_err(text):
    i = text.find('invalid-feedback')
    err = text[i:i+500].strip()
    if err:
        print(err)
    return


def prepare_form(old, csrf_token, with_tree=False) -> (dict, dict):
    new = dict(old)
    files = dict()
    new['csrf_token'] = csrf_token
    if with_tree:
        new['tree_type'] = 'Other'
        files = {'tree_file': new['tree_file'].read_bytes()}
    return new, files


def submit(record: dict, trees: list, session: requests.Session):
    print(record['doi'], len(trees))
    csrf_token = get_csrf_token(session)
    submit_form1 = record
    submit_form1['email'] = 'admin@example.org'
    submit_form1['root'] = submit_form1['lineage']
    submit_form1['journal'] = submit_form1['journal_name']
    submit_form1, files = prepare_form(submit_form1, csrf_token)
    r1 = session.post(URL1, data=submit_form1)
    if not r1.ok:
        raise Exception(r1.status_code)
    print_err(r1.text)
    for n, tree in enumerate(trees[:-1], start=1):
        submit_form2 = tree
        submit_form2['next'] = True
        submit_form2, files = prepare_form(submit_form2, csrf_token,
                                           with_tree=True)
        r2 = session.post(f'{URL2}{n}', data=submit_form2, files=files)
        if not r2.ok:
            print(r2.status_code)
            raise Exception
        else:
            print(submit_form2['tree_title'], 'ok')
        print_err(r2.text)
    submit_form3 = trees[-1]
    submit_form3['submit'] = True
    submit_form3, files = prepare_form(submit_form3, csrf_token,
                                       with_tree=True)
    r3 = session.post(f'{URL2}{n+1}', data=submit_form3, files=files)
    if r3.ok:
        print(submit_form3['tree_title'], 'ok')
    print_err(r3.text)
    return


def get_csrf_token(session):
    html = session.get(URL1).text
    index = html.find('csrf_token')
    line = html[index:index+200]
    token = line.split('=')[-1].split('"')[1]
    return token


def remove_old_submit(session):
    start = 91
    end = 100
    for i in range(start, end+1):
        r = session.get(f'{URL1}/remove/{i}')
        print(r.status_code)
    # raise Exception
    return


def wrap(record, trees):
    with requests.Session() as session:
        submit(record, trees, session)
    return


def main():
    data = json.load(open(MERGE_JSON, 'r'))
    with requests.Session() as session:
        remove_old_submit(session)
    with ThreadPoolExecutor(max_workers=16) as pool:
        # raise SystemExit()
        for key in data.keys():
            record = data[key]
            trees = list(record['tree_files'])
            record.pop('tree_files')
            print(record['doi'])
            for tree in trees:
                tree['tree_file'] = TREE_FOLDER / Path(tree['tree_file'])
                assert tree['tree_file'].exists(), tree['tree_file']
            pool.submit(wrap, record, trees)
        return


if __name__ == '__main__':
    main()
