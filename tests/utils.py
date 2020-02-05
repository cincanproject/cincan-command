import shutil
import pathlib
from typing import List


def prepare_work_dir(name: str, with_files: List['str']) -> pathlib.Path:
    src_root = pathlib.Path('samples')
    root = pathlib.Path(name)
    if root.is_dir():
        shutil.rmtree(root, ignore_errors=True)
    root.mkdir()
    for f_name in with_files:
        src = src_root / f_name
        dst = root / f_name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
        shutil.copystat(src, dst)
    return root
