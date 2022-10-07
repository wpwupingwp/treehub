from web.utils import nwk2auspice

with open(r'r:\test.nwk') as _:
    newick = _.read()
out = 'out.json'
meta = {}
nwk2auspice(newick, out, meta)
