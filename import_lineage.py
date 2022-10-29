import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from concurrent.futures import ThreadPoolExecutor


tcp = ThreadedConnectionPool(minconn=1, maxconn=16, host='::1', port=5432,
                             user='root', password='password',
                             database='treedb')
def to_int(s):
    if s == '':
        i = -1
    else:
        i = int(s)
    return i


def insert(cmd):
    #conn = psycopg2.connect(host='::1', port=5432, user='root', password='password', database='treedb')
    conn = tcp.getconn()
    cursor = conn.cursor()
    cursor.execute(cmd)
    cursor.close()
    conn.commit()
    tcp.putconn(conn)
    return


def main():
    pool = ThreadPoolExecutor(max_workers=16)
    info = open('species_info', 'r')
    # skip header
    info.readline()
    for i, line in enumerate(info):
        if i % 5000 == 0: print(i)
        raw = line.rstrip().split('|')
        tax_id, genus_id, family_id, order_id = [to_int(i) for i in raw]
        cmd = (f'UPDATE ncbi_names SET genus_id={genus_id}, '
               f'family_id={family_id}, order_id={order_id} '
               f'WHERE tax_id={tax_id};')
        pool.submit(insert, cmd)
    pool.shutdown(wait=True)


main()