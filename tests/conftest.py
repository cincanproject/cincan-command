import pytest
import io


@pytest.fixture(autouse=True, scope="function")
def disable_tty_interactive(monkeypatch):
    """Mock stdin to make tty part of tests to complete"""
    monkeypatch.setattr('sys.stdin', io.StringIO(''))
    monkeypatch.setattr('sys.stdin.fileno', lambda : 0)