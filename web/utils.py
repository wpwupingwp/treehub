#!/usr/bin/python3
import json
from pathlib import Path
from io import StringIO

from Bio import Phylo
from PIL import Image, ImageOps


meta = {'title': '',
        'panels': ['tree'],
        'colorings': [{'key': 'subgroup', 'title': 'subgroup',
                       'type': 'categorical'}],
        'updated': '',
}

def parse_newick(nwk: str):
    with StringIO() as s:
        s.write(nwk)
        s.seek(0)
        tree = Phylo.read(s, 'newick')
    return tree


def phylo_to_json(tree) -> dict:
    div = getattr(tree, 'branch_length', None)
    json_ = {'name': tree.name,
             'node_attrs': {'div': div}}
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
        node_names[node['name']] = n
        node['name'] = f'{node["name"]}_{n}'
    else:
        node_names[node['name']] = 1
    if node['node_attrs']['div'] is None:
        node['node_attrs']['div'] = 0
    if 'children' in node:
        for ch in node['children']:
            add_node_attr(ch, count, node_names)
    return node


def set_branch(node, depth):
    node['node_attrs']['div'] = depth
    if 'children' in node:
        for ch in node['children']:
            set_branch(ch, depth + 1)
    pass


def get_tree(nwk: str):
    def cumulative_divs(node: dict, so_far=0):
        node['node_attrs']['div'] += so_far
        if so_far:
            nonlocal all_branch_zero
            all_branch_zero = False
        if 'children' in node:
            for ch in node['children']:
                cumulative_divs(ch, node['node_attrs']['div'])
        return so_far

    count = 0
    node_names = {}
    all_branch_zero = True
    tree = parse_newick(nwk)
    root = tree.root
    tree_dict = phylo_to_json(root)
    add_node_attr(tree_dict, count, node_names)
    cumulative_divs(tree_dict)
    if all_branch_zero:
        set_branch(tree_dict, 0)
    return tree_dict


def nwk2auspice(newick: str, json_file: Path, json_: dict) -> Path:
    tree = get_tree(newick)
    json_['tree'] = tree
    with open(json_file, 'w', encoding='utf-8') as out:
        json.dump(json_, out)
    return json_file


def compress_photo(old_path: Path) -> Path:
    """
    Compress and rotate image with PIL
    Args:
        old_path: Path
    """
    small = 1024 * 1024
    if old_path.stat().st_size <= small:
        return old_path
    old = Image.open(old_path)
    old = old.convert('RGB')
    rotate = ImageOps.exif_transpose(old)
    rotate.thumbnail((1024, 1024))
    rotate.save(old_path, 'JPEG')
    return old_path