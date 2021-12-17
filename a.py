from subprocess import run

tree_id = '10862615'
cmd = f'perl .\\write_trees.pl {tree_id}'
out = tree_id + '.nex'
err = tree_id + '.log'
with open(out, 'w') as o, open(err, 'w') as e:
    a = run(cmd, shell=True, stdout=o, stderr=e)
