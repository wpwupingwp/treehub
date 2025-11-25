from pathlib import Path

folder = Path('/dev/shm/treehub/tmp')
session_ = folder / 'session'
session_.mkdir(parents=True, exist_ok=True)
limit = 100
j = list(folder.glob('*.json'))
s = list(session_.glob('*'))
s = [i for i in s if not i.name.startswith('tmp')]
j.sort(key=lambda x:x.stat().st_mtime, reverse=True)
s.sort(key=lambda x:x.stat().st_mtime, reverse=True)
m = 0
n = 0
for _ in j[limit:]:
    try:
        print('delete', _, _.stat().st_mtime)
        _.unlink()
        n += 1
    except Exception:
        pass
for _ in s[limit:]:
    try:
        print('delete', _, _.stat().st_mtime)
        _.unlink()
        m += 1
    except Exception:
        pass
print(f'Removed {m} sessions, {n} json files')
