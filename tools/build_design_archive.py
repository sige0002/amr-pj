"""Create a deterministic, self-contained AMR design archive; no third-party packages."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "amr-01"


def main() -> None:
    config = json.loads((SOURCE / "design_parameters.json").read_text(encoding="utf-8"))
    version = config["version"]
    if not version or any(c not in "0123456789." for c in version):
        raise ValueError("Unsupported version format")
    stem = "amr_v" + version.replace(".", "_")
    output = ROOT / "archives" / (stem + ".zip")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Explicit text-only allowlist: never include generated images or caches.
    names = {"DESIGN.ja.md", "README.ja.md", "CHANGELOG.ja.md", "TEST_RESULTS.txt",
             "check_design.py", "test_check_design.py", "design_parameters.json", "calculation_results.json"}
    files = [SOURCE / name for name in sorted(names)]
    if any(not path.is_file() for path in files):
        raise FileNotFoundError("A required text/code file is missing")
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in files:
            info = zipfile.ZipInfo(stem + "/" + path.relative_to(SOURCE).as_posix(), (2026, 9, 20, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(output) as z:
        broken = z.testzip()
        if broken:
            raise ValueError("Corrupt ZIP member: " + broken)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".zip.sha256").write_text(digest + "  " + output.name + "\n", encoding="utf-8")
    print(f"Created {output.relative_to(ROOT)} ({len(files)} files, {output.stat().st_size} bytes)")
    print("SHA256: " + digest)


if __name__ == "__main__":
    main()
