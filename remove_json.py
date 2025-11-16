from pathlib import Path
from time import sleep

folder = Path('/dev/shm/treehub/tmp')
session_ = folder / 'session'
limit = 50
while True:
    j = list(folder.glob('*.json'))
    s = list(session_.glob('*'))
    s = [i for i in s if not i.name.startswith('tmp')]
    j.sort(key=lambda x:x.stat().st_mtime, reverse=True)
    s.sort(key=lambda x:x.stat().st_mtime, reverse=True)
    for _ in j[limit:]:
        try:
            print('delete', _, _.stat().st_mtime)
            _.unlink()
        except Exception:
            pass
    for _ in s[limit:]:
        try:
            print('delete', _, _.stat().st_mtime)
            _.unlink()
        except Exception:
            pass
