import json
from pprint import pprint
from pathlib import Path

import requests

# should clean bad submit before
URL1 = 'http://localhost:2022/planttree/submit'
URL2 = 'http://localhost:2022/planttree/submit/' # +n
MERGE_JSON = Path(r'R:\submit\merge.json')
TREE_FOLDER = Path(r'R:\submit\trees')


def print_err(text):
    i = text.find('invalid-feedback')
    print(text[i:i+500])
    return


def submit(record: dict, trees: list, session: requests.Session):
    pprint(len(trees))
    submit_form1 = record
    submit_form1['email'] = 'admin@example.org'
    submit_form1['root'] = submit_form1['lineage']
    submit_form1['csrf_token'] = csrf_token
    pprint(submit_form1)
    r1 = session.post(URL1, data=submit_form1)
    if not r1.ok:
        raise Exception(r1.status_code)
    print_err(r1.text)
    for n, tree in enumerate(trees[:-1], start=1):
        submit_form2 = tree
        submit_form2['tree_file'] = submit_form2['tree_file'].read_bytes()
        submit_form2['tree_type'] = 'Other'
        submit_form2['csrf_token'] = csrf_token
        r2 = session.post(f'{URL2}{n}', data=submit_form2)
        if not r2.ok:
            print(r2.status_code)
            pprint(submit_form2)
            raise Exception
        else:
            print(submit_form2['tree_title'], 'ok')
        print_err(r2.text)
    submit_form3 = trees[-1]
    submit_form3['tree_file'] = submit_form3['tree_file'].read_bytes()
    submit_form3['submit'] = True
    submit_form3['csrf_token'] = csrf_token
    submit_form3['tree_type'] = 'Other'
    r3 = session.post(f'{URL2}{n+1}', data=submit_form3)
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
    start = 103
    end = 104
    for i in range(start, end+1):
        r = session.get(f'{URL1}/remove/{i}')
        print(r.status_code)
    return


def main():
    data = json.load(open(MERGE_JSON, 'r'))
    session = requests.Session()
    remove_old_submit(session)
    # raise SystemExit()
    global csrf_token
    csrf_token = get_csrf_token(session)
    for key in data.keys():
        record = data[key]
        trees = list(record['tree_files'])
        record.pop('tree_files')
        for tree in trees:
            tree['tree_file'] = TREE_FOLDER / Path(tree['tree_file'])
            assert tree['tree_file'].exists(), tree['tree_file']
        submit(record, trees, session)
        break
    return


if __name__ == '__main__':
    main()