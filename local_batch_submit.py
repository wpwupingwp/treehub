import json

import requests

# should clean bad submit before
URL1 = 'http://localhost:2022/planttree/submit'
URL2 = 'http://localhost:2022/planttree/submit/' # +n
PAPER_JSON = 'new.json'
TREE_JSON = 'tree.json'
def submit(record: dict):
    submit_form1 = {}
    with requests.Session() as s:
        r1 = s.post(URL1, data=submit_form1)
        if r1.status_code == 200:
            pass
        for n, tree in enumerate(record['trees'][:-1]):
            submit_form2 = {}
            r2 = s.post(f'{URL2}{n}', data=submit_form2)
            if r2.ok:
                pass
        submit_form2 = record['trees'][-1]
        submit_form2['submit'] = True
    r3 = s.post(f'{URL2}{n}', data=submit_form2)
    if r3.ok:
        print(r3.text)


def main():
    papers = json.load(open(PAPER_JSON, 'r'))
    trees = json.load(open(TREE_JSON, 'r'))
    for paper in papers:
        pass
    return


if __name__ == '__main__':
    main()