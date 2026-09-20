"""One-time import of a locally validated design package (no external downloads)."""
import base64
import hashlib
import io
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[2]
staging = root / '.github/amr-transfer'
parts = sorted(staging.glob('amr_v0_2_1.zip.part*'))
expected_names = [f'amr_v0_2_1.zip.part{i:02d}' for i in range(13)]
if [p.name for p in parts] != expected_names:
    raise SystemExit('Incomplete package: expected exactly 13 numbered parts')
chunks = [p.read_bytes() for p in parts]
# Correct one known base64 transport omission, not the package contents.
# Both the received part and the complete restored package are hash-checked.
if hashlib.sha1(b'blob ' + str(len(chunks[11])).encode() + b'\0' + chunks[11]).hexdigest() == '9079d972ddf830f0c9bb37caebe61008070976d3':
    encoded = base64.b64encode(chunks[11]).decode('ascii').rstrip('=')
    encoded = encoded[:862] + 'f' + encoded[862:]
    chunks[11] = base64.b64decode(encoded[:-1] + 'j', validate=True)
if hashlib.sha1(b'blob ' + str(len(chunks[11])).encode() + b'\0' + chunks[11]).hexdigest() != '28267d02072f3b0538f70e104ccd8968aee8128b':
    raise SystemExit('Part 11 integrity check failed')
data = b''.join(chunks)
expected_hash = '3397e306bc1f5262bd8ad301b10a44d38229a83763a7e5b78d787ecb26cc340e'
if len(data) != 78654 or hashlib.sha256(data).hexdigest() != expected_hash:
    raise SystemExit('ZIP size or SHA-256 mismatch; no files extracted')
files = [
    'CHANGELOG.ja.md', 'DESIGN.ja.md', 'README.ja.md', 'TEST_RESULTS.txt',
    'assets/amr_internal_structure.webp', 'calculation_results.json',
    'check_design.py', 'design_parameters.json', 'test_check_design.py',
]
with zipfile.ZipFile(io.BytesIO(data)) as archive:
    if archive.namelist() != ['amr_v0_2_1/' + name for name in files]:
        raise SystemExit('Unexpected ZIP members')
    if archive.testzip() is not None:
        raise SystemExit('ZIP CRC validation failed')
    for name in files:
        destination = root / 'docs/amr-01' / name
        if destination.exists():
            raise SystemExit(f'Refusing to overwrite existing design file: {name}')
    for name in files:
        destination = root / 'docs/amr-01' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(archive.read('amr_v0_2_1/' + name))
output = root / 'archives/amr_v0_2_1.zip'
output.parent.mkdir(parents=True, exist_ok=True)
if output.exists():
    raise SystemExit('Refusing to overwrite an existing ZIP')
output.write_bytes(data)
output.with_suffix('.zip.sha256').write_text(expected_hash + '  ' + output.name + '\n', encoding='utf-8')
for part in parts:
    part.unlink()
Path(__file__).unlink()
print(f'Imported {len(files)} files; ZIP SHA-256 {expected_hash}')
