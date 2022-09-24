from io import StringIO
from dendropy import Tree

tree = './10862615.nex'
# tree = './47158.nex'
x = Tree.get(path=tree, schema='nexus')
with open(tree, 'r', encoding='utf-8') as _:
    a = StringIO()
    a.write(_.read())
    a.seek(0)

with open('47158.nex.2', 'w') as out:
    out.write(x.as_string(schema='nexus'))
for i in x.taxon_namespace:
    print(dir(i))
    print(i.taxon_label)

