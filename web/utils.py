from sys import argv
import json
from Bio import Phylo
from pathlib import Path
from io import StringIO


def nwk2auspice(newick: str, tmp: Path, file_stem: str, meta: dict):
    def get_auspice_json(node, name_format=False):
        # name format: Order_family_genus_species_others
        nonlocal branch_lengths, n
        if name_format:
            if node.name is None:
                order, family, genus, species, *_ = list('_' * 5)
            else:
                try:
                    order, family, genus, species, *_ = node.name.split('_')
                except Exception:
                    order, family, genus, species, *_ = list('_' * 5)
            organism = '_'.join([genus, species]) if genus else '_'
            order = order.strip("'")
            family = family.strip("'")
            organism = organism.strip("'")
            if organism in organisms:
                organism = f'{organism}_{n}'
                n += 1
            else:
                organisms.add(organism)
        else:
            if node.name is None:
                node.name = f'_{n}'
                n += 1
            organism = node.name
            order = family = ''
        organism = organism.replace(r"\'", '')
        length = float(
            node.branch_length) if node.branch_length is not None else 0
        branch_lengths.append(length)
        # length = max(length, 0.1)
        # print(organism, length)
        json_ = {'name': organism,
                 'node_attrs': {'div': -1 * length,
                                'num_date': {'value': -1 * length * 1000000}},
                 'branch_attrs': {'mutations': {}}}
        if name_format:
            json_['node_attrs']['order'] = {'value': order}
            json_['node_attrs']['family'] = {'value': family}
        if node.clades:
            json_['children'] = []
            for ch in node.clades:
                json_['children'].append(get_auspice_json(ch))
        return json_

    json_file = tmp / f'{file_stem}.json'
    with StringIO() as s:
        s.write(newick)
        s.seek(0)
        tree = Phylo.read(s, 'newick')
    root = tree.root
    n = 0
    organisms = set()
    branch_lengths = list()
    json_ = get_auspice_json(root)
    # wait time for loading
    wait = 2
    max_length = max(branch_lengths) * 1000000 + wait
    json_['node_attrs']['div'] = {'value': max_length * -1}
    json_['node_attrs']['num_date'] = {'value': max_length * -1}
    meta['tree'] = json_
    with open(json_file, 'w') as f:
        json.dump(meta, f)
    return json_file
