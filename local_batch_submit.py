import json
from pprint import pprint
from pathlib import Path

import requests

# should clean bad submit before
URL1 = 'http://localhost:2022/planttree/submit'
URL2 = 'http://localhost:2022/planttree/submit/' # +n
MERGE_JSON = Path(r'R:\submit\merge.json')
TREE_FOLDER = Path(r'R:\submit\trees')



def submit(record: dict, trees:dict, session: requests.Session):
    submit_form1 = record
    pprint(submit_form1)
    r1 = session.post(URL1, data=submit_form1)
    if r1.status_code != 200:
        pprint(r1.raw)
        raise Exception(r1.status_code)
    for n, tree in enumerate(trees[:-1]):
        submit_form2 = tree
        submit_form2['tree_file'] = submit_form2['tree_file'].read_bytes()
        r2 = session.post(f'{URL2}{n}', data=submit_form2)
        if r2.ok:
            pass
    submit_form3 = trees[-1]
    submit_form3['tree_file'] = submit_form3['tree_file'].read_bytes()
    submit_form3['submit'] = True
    r3 = session.post(f'{URL2}{n}', data=submit_form3)
    if r3.ok:
        print(r3.text)


def main():
    data = json.load(open(MERGE_JSON, 'r'))
    session = requests.Session()
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