#!/usr/bin/python3
import json
from Bio import Phylo
from pathlib import Path
from io import StringIO


def parse_newick(nwk: str):
    with StringIO() as s:
        s.write(nwk)
        s.seek(0)
        tree = Phylo.read(s, 'newick')
    return tree


def phylo_to_json(tree) -> dict:
    json_ = {'name': tree.name,
             'node_attrs': {'div': tree.branch_length}}
    if tree.clades:
        json_['children'] = []
        for ch in tree.clades:
            json_['children'].append(phylo_to_json(ch))
    return json_


def add_node_attr(node: dict, count: int, node_names: dict):
    # add node attributes, first node is root
    if node['name'] is None:
        node['name'] = f'Node_{count}'
        count += 1
    # not in -> 0
    if node['name'] in node_names:
        n = node_names[node['name']] + 1
        node['name'] = f'{node["name"]}_{n}'
        node_names[node['name']] = n
    else:
        node_names[node['name']] = 1
    if node['node_attr']['div'] is None:
        node['node_attr']['div'] = 0
    if 'children' in node:
        for ch in node['children']:
            add_node_attr(ch, count, node_names)
    return node


def set_branch(node, depth):
    node['node_attr']['div'] = depth
    if 'children' in node:
        for ch in node['children']:
            set_branch(ch, depth + 1)
    pass


def get_tree(nwk: str):
    def cumulative_divs(node: dict, so_far=0):
        node['node_attr']['div'] += so_far
        if so_far:
            nonlocal all_branch_zero
            all_branch_zero = False
        if 'children' in node:
            for ch in node['children']:
                cumulative_divs(ch, node['node_attr']['div'])
        return so_far

    count = 0
    node_names = {}
    all_branch_zero = True
    tree = parse_newick(nwk)
    add_node_attr(tree, count, node_names)
    cumulative_divs(tree)
    if all_branch_zero:
        set_branch(tree, 0)
    return tree


def nwk2auspice(newick: str, tmp: Path, file_stem: str):
    json_file = tmp / f'{file_stem}.json'
    tree = get_tree(newick)
    json_dict = {'version': '2.0',
                 'meta': {'title': file_stem,
                          'panels': ['tree'],
                          'description': ''},
                 'tree': tree}
    with open(json_file, 'w', encoding='utf-8') as out:
        json.dump(json_dict, out)
    return json_file