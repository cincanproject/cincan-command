import pytest
import pathlib
from typing import List
import shutil
import io
from cincan.frontend import ToolImage

@pytest.fixture(autouse=True, scope="function")
def disable_tty_interactive(monkeypatch):
    """Mock stdin to make tty part of tests to complete"""
    monkeypatch.setattr('sys.stdin', io.StringIO(''))
    monkeypatch.setattr('sys.stdin.fileno', lambda : 0)


@pytest.fixture(scope='function')
def tool(request):
    tool = ToolImage(image='busybox', rm=False)
    yield tool


@pytest.fixture(scope="session", autouse=True)
def delete_temporary_files(request, tmp_path_factory):
    """Cleanup a testing directory once we are finished."""
    _tmp_path_factory = tmp_path_factory
    def cleanup():
        tmp_path = _tmp_path_factory.getbasetemp()
        if pathlib.Path(tmp_path).exists() and pathlib.Path(tmp_path).is_dir():
            shutil.rmtree(tmp_path)
    request.addfinalizer(cleanup)


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