from cincan.frontend import ToolImage
import pytest
import io

@pytest.fixture(autouse=True)
def disable_tty_interactive(monkeypatch):
    """Mock stdin to make tty part of tests to complete"""
    monkeypatch.setattr('sys.stdin', io.StringIO(''))
    monkeypatch.setattr('sys.stdin.fileno', lambda : 0)

def test_option_user():
    tool = ToolImage(image='busybox', rm=False)
    out = tool.run_get_string(['id'])
    assert out == 'uid=0(root) gid=0(root) groups=10(wheel)\n'

    tool = ToolImage(image='busybox', rm=False)
    tool.user = 'root'
    out = tool.run_get_string(['id'])
    assert out.startswith('uid=0(root) gid=0(root)')
