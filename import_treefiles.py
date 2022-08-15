# /usr/bin/python3

import psycopg2
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from timeit import default_timer as timer


def insert(tree_id, treefile):
    # print(treefile)
    with open(treefile, 'r', encoding='utf-8') as f:
        text = f.read()
    new_text = text.replace("'", "''")
    conn = psycopg2.connect(host='::1', port=5432, user='root',
                            password='password', database='treedb')
    cursor = conn.cursor()
    cmd = (f"INSERT INTO treefile (tree_id, tree_text) "
           f"VALUES ({tree_id}, '{new_text}')")
    cursor.execute(cmd)
    cursor.close()
    conn.commit()
    conn.close()
    print(treefile, 'ok')
    return treefile


def main():
    start = timer()
    tree_files = list(Path('trees').glob('*.nex'))
    with ThreadPoolExecutor(max_workers=50) as pool:
        futures = [pool.submit(insert, treefile.stem, treefile)
                   for treefile in tree_files]
        pool.shutdown(wait=True)
        # for future in (futures):
        #     print(future.result())
    end = timer()
    print(len(tree_files), 'trees')
    print(len(futures), 'insertion')
    print(end-start, 'seconds')


if __name__ == '__main__':
    main()