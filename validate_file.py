from glob import glob
for i in glob('*.nex'):
    with open(i, encoding='utf-8') as f:
        print(i)
        _ = f.read()
        del(_)
