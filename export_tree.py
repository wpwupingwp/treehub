#!/usr/bin/python3

from csv import reader
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from sys import argv
from subprocess import run


def run_perl(folder, tree_id, root_id):
    # perl = 'perl'
    perl = r'C:\tools\Perl\perl\bin\perl.exe'
    cmd = f'{perl} write_trees.pl {root_id}'
    out = folder / (tree_id+'.nex')
    err = folder / (tree_id+'.log')
    with open(out, 'w') as o, open(err, 'w') as e:
        a = run(cmd, shell=True, stdout=o, stderr=e)
        print(a.returncode)
    print(tree_id)
    return out


def main():
    try:
        tree_node_list = Path(argv[1])
        folder = Path(argv[2])
    except IndexError:
        print('Usage: python3 export_tree.py tree_node.list out_folder')
        raise SystemExit(-1)
    if not folder.exists():
        folder.mkdir()
    tree_root = list()
    with open(tree_node_list, 'r', newline='', encoding='utf-8') as fp:
        # tree_id, root_node_id
        read = reader(fp, delimiter=';', quotechar='"')
        # head
        _ = next(read)
        for record in read:
            # tree_id, root_id = record
            tree_root.append(record)
    print(len(tree_root), 'records')
    with ProcessPoolExecutor(max_workers=8) as pool:
        all_task = [pool.submit(run_perl, folder, *i) for i in tree_root]
        for future in as_completed(all_task):
            print(future.result())
    print('Done')


if __name__ == '__main__':
    main()
