from sys import argv
from Bio import Phylo

tree_file = argv[1]
table_file = argv[2]
with open(tree_file, 'r') as _:
    first_line = _.readline()
    if first_line.startswith('#NEXUS'):
        fmt = 'nexus'
    else:
        fmt = 'newick'
tree = Phylo.read(tree_file, fmt)
label_name = dict()
with open(table_file, 'r') as _:
    for line in _:
        label, name = line.strip().split()
        label_name[label] = name

for i in tree.get_terminals():
    i.name = label_name[i.name]
Phylo.write(tree, 'rename-' + tree_file, fmt)