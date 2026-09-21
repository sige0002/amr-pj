"""Download the retailer-linked original STEP to the ignored cache, verify SHA256."""
from pathlib import Path
from urllib.request import urlopen
import hashlib

HERE = Path(__file__).resolve().parent
URL = 'https://raw.githubusercontent.com/takasumasakazu/DirectDriveTech_test/main/STEPdata/M0601C_111.STEP'
SHA256 = '2f6fae044c768114fe4fbde16b974c9f787ec9e4716648a498a518ca207a8142'


def fetch():
    path = HERE/'vendor-cache/M0601C_111.STEP'
    data = path.read_bytes() if path.exists() else urlopen(URL, timeout=60).read()
    actual = hashlib.sha256(data).hexdigest()
    if actual != SHA256:
        raise ValueError('Vendor source changed; review its revision before rebuilding: '+actual)
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(data)
    print('Verified M0601C_111.STEP:', len(data), 'bytes;', actual)
    return path


if __name__ == '__main__':
    fetch()
