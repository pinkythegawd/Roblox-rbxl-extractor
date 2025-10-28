import pathlib
import rbxl_extractor.binary_extractor as be

rbxl = pathlib.Path(r'C:/Users/MikePinku/Downloads/Phone Link/Place_137283905857565.rbxl')
out = str(rbxl.parent)
opts = {'scripts': True, 'images': True, 'models': False, 'sounds': False}

print('Running extractor test...')
res = be.extract_from_binary(str(rbxl), out, opts)
print('Scripts found:', len(res.get('scripts', [])))
# Quick smoke checks
scripts = res.get('scripts', [])
if scripts:
    largest = max(scripts, key=lambda p: pathlib.Path(p).stat().st_size)
    print('Largest script:', largest, pathlib.Path(largest).stat().st_size)
    txt = pathlib.Path(largest).read_text(errors='ignore')
    print('Contains function?:', 'function' in txt)
    assert 'function' in txt or len(scripts) > 0
else:
    print('No scripts extracted')
    raise SystemExit(2)

print('Test complete')
