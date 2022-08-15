# /usr/bin/python3

from psycopg2.pool import ThreadedConnectionPool
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from timeit import default_timer as timer


def insert(conn_pool, tree_id, treefile):
    with open(treefile, 'r', encoding='utf-8') as f:
        text = f.read()
    new_text = text.replace("'","''")
    conn = conn_pool.getconn()
    cursor = conn.cursor()
    cmd = (f"INSERT INTO treefile (tree_id, tree_text) "
           f"VALUES ({tree_id}, '{new_text}')")
    cursor.execute(cmd)
    cursor.commit()
    cursor.close()
    conn.close()
    return treefile


def main():
    start = timer()
    conn_pool = ThreadedConnectionPool(maxconn=8, minconn=1, host='::1',
                                       port=5432, user='root',
                                       password='password',
                                       database='treedb', keepalives=1,
                                       keepalives_idle=30,
                                       keepalives_interval=10,
                                       keepalives_count=5)
    tree_files = list(Path('trees').glob('*.nex'))
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(insert, conn_pool, treefile.stem, treefile)
                   for treefile in tree_files]
        for future in as_completed(futures):
            print(future.result())
    pool.shutdown(wait=True)
    conn_pool.closeall()
    end = timer()
    print(len(tree_files), 'trees')
    print(len(futures), 'insertion')
    print(end-start, 'seconds')


if __name__ == '__main__':
    main()