import os, codecs, re
from collections import defaultdict

res = defaultdict(set)
directory = "/home/kr/mydev/eht_office/IDF"
for f in os.listdir(directory):
    if not f.endswith(".idf"): continue
    path = os.path.join(directory, f)
    try:
        content = codecs.open(path, "r", "utf-16-le").read()
    except Exception:
        content = codecs.open(path, "r", "utf-8").read()
    lines = content.splitlines()
    for line in lines:
        line = line.strip().replace('\x00', '')
        if not line: continue
        m = re.match(r"^\s*([+-]?\d+)", line)
        if m:
            id_ = int(m.group(1))
            if id_ < 0:
                text = line[len(str(id_)):].strip()
                if len(res[id_]) < 3:
                     res[id_].add(text)

for k in sorted(res.keys()):
    print(f"{k}: {list(res[k])}")
