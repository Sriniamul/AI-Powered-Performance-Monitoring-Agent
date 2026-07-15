from pathlib import Path
import zipfile


def zip_files(files: list[str], output_path: str):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            p = Path(f)
            if p.exists() and p.is_file():
                zf.write(p, arcname=p.name)
    return output_path
