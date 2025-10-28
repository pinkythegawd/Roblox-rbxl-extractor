import re
from pathlib import Path
p=Path(r'C:/Users/MikePinku/Downloads/Phone Link/extracted/Scripts/script_28.lua')
if not p.exists():
    print('FILE_NOT_FOUND', p)
    raise SystemExit(1)

b=p.read_bytes()
print('file bytes:', len(b))
indices=[m.start() for m in re.finditer(b'function', b)]
print('function occurrences:', len(indices))
if indices:
    idx=indices[0]
    print('first function index:', idx)
    start=max(0, idx-120)
    end=min(len(b), idx+400)
    snippet=b[start:end]
    print('\n---RAW BYTES AROUND (latin1 decoded)---')
    print(snippet.decode('latin1'))

print('\n---LONG PRINTABLE SEQUENCES (min 30 chars)---')
text=b.decode('latin1')
for s in re.findall(r'[ -~]{30,}', text)[:40]:
    print(s)
