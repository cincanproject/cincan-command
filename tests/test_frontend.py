import pathlib
import shutil
from typing import List

from cincan.frontend import ToolImage


def prepare_work_dir(name: str, with_files: List['str']) -> pathlib.Path:
    root = pathlib.Path(name)
    if root.is_dir():
        shutil.rmtree(root, ignore_errors=True)
    root.mkdir()
    for f_name in with_files:
        f = pathlib.Path(f_name)
        shutil.copy(f, root / f.name)
    return root


def test_run_get_string():
    tool = ToolImage(image='cincan/env', rm=False)
    out = tool.run_get_string(['echo', 'Hello'])
    assert out == 'Hello\n'

    out = tool.run_get_string(['echxo', 'Hello'])
    assert 'No such file or directory' in out


def test_magic_file_io():
    tool = ToolImage(image='cincan/env', rm=False)
    work_dir = prepare_work_dir('_test', ['samples/source-a.txt'])
    out = tool.run_get_string(['cat', '_test/source-a.txt'])
    assert out == 'Source A\n'
    assert tool.upload_files == ['_test/source-a.txt']
    assert tool.download_files == []

    work_dir = prepare_work_dir('_test', ['samples/source-b.txt'])
    out = tool.run_get_string(['cat', '_test/source-b.txt'])
    assert out == 'Source B\n'
    assert tool.upload_files == ['_test/source-b.txt']
    assert tool.download_files == []
