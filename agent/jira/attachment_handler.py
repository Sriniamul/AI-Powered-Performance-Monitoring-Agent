def filter_existing_files(files: list[str]):
    from pathlib import Path
    return [f for f in files if Path(f).exists() and Path(f).is_file()]
