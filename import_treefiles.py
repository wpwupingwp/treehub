# /usr/bin/python3

import psycopg2
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from timeit import default_timer as timer
from datetime import date

upload_date = date.isoformat(date.today())


def insert(treefile: Path):
    tree_id = treefile.stem
    nexus = treefile.with_suffix('.nex')
    newick = treefile.with_suffix('.nwk')
    phyloxml = treefile.with_suffix('.xml')
    with open(nexus, 'r', encoding='utf-8') as f:
        nexus_ = f.read()
        # handle quotation marks in string for INSERT
        nexus_ = nexus_.replace("'", "''")
        nexus_ = nexus_.replace('"', '""')
    with open(newick, 'r', encoding='utf-8') as f:
        newick_ = f.read()
        newick_ = newick_.replace("'", "''")
        newick_ = newick_.replace('"', '""')
    with open(phyloxml, 'r', encoding='utf-8') as f:
        phyloxml_ = f.read()
        phyloxml_ = phyloxml_.replace("'", "''")
        phyloxml_ = phyloxml_.replace('"', '""')
    conn = psycopg2.connect(host='::1', port=5432, user='root',
                            password='password', database='treedb')
    cursor = conn.cursor()
    cmd = (f"""INSERT INTO treefile 
           (tree_id, upload_date, nexus, newick, phyloxml) VALUES 
           ({tree_id}, '{upload_date}', '{nexus_}', '{newick_}', '{phyloxml_}');""")
    cursor.execute(cmd)
    cursor.close()
    conn.commit()
    conn.close()
    return treefile


def main():
    start = timer()
    tree_files = list(Path('trees').glob('*.nex'))
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(insert, treefile) for treefile in tree_files]
        pool.shutdown(wait=True)
        # for future in (futures):
        #     print(future.result())
    end = timer()
    print(len(tree_files), 'trees')
    print(len(futures), 'insertion')
    print(end-start, 'seconds')
    return


if __name__ == '__main__':
    main()
