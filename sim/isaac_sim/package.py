"""Bundle a standalone, relative-path URDF package; no source CAD required."""
from pathlib import Path
import hashlib
import json
import zipfile

HERE = Path(__file__).resolve().parent
FILES = ["README.ja.md", "amr_d62.urdf", "amr_d62_payload_10kg.urdf", "simulation_config.json",
         "export_manifest.json", "urdf_validation.json", "mujoco_smoke_validation.json", "urdf_preview_mujoco.png",
         "export_urdf.py", "drive.py", "import_isaac_sim.py", "validate_urdf.py", "smoke_mujoco.py", "package.py",
         "requirements-validation.txt", "render_motion_gif.py", "amr_d62_motion_mujoco.gif", "motion_gif_manifest.json"]


def main():
    manifest = json.loads((HERE / "export_manifest.json").read_text())
    files = sorted(FILES + [m["file"] for m in manifest["meshes"]])
    lines = [hashlib.sha256((HERE / f).read_bytes()).hexdigest()+"  "+f for f in files]
    (HERE / "SHA256SUMS").write_text("\n".join(lines)+"\n")
    path = HERE / "amr_d62_isaac5.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in files + ["SHA256SUMS"]:
            info = zipfile.ZipInfo("amr_d62_isaac5/"+name, date_time=(2026, 9, 22, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, (HERE / name).read_bytes())
    print(json.dumps(dict(file=path.name, files=len(files)+1, bytes=path.stat().st_size,
                         sha256=hashlib.sha256(path.read_bytes()).hexdigest())))


if __name__ == "__main__":
    main()
