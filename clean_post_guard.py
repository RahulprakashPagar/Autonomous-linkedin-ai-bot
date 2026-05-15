import json
from datetime import datetime, timedelta

data = json.load(open('post_guard.json'))

cutoff_s = datetime.now() - timedelta(days=3)
cutoff_h = datetime.now() - timedelta(days=14)

before_s = len(data.get('subjects', []))
before_h = len(data.get('headlines', []))

data['subjects'] = [
    e for e in data.get('subjects', [])
    if datetime.fromisoformat(e['date'][:19]) >= cutoff_s
]
data['headlines'] = [
    e for e in data.get('headlines', [])
    if datetime.fromisoformat(e['date'][:19]) >= cutoff_h
]

json.dump(data, open('post_guard.json', 'w'), indent=2)

print(f"Subjects:     {before_s} -> {len(data['subjects'])} (kept last 3 days only)")
print(f"Headlines:    {before_h} -> {len(data['headlines'])} (kept last 14 days only)")
print(f"Fingerprints: {len(data.get('fingerprints',[]))} (never deleted)")
print("Done - post_guard.json cleaned successfully")
