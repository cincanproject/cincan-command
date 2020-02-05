from cincan.frontend import ToolImage
import pytest
import io


def test_option_user():
    tool = ToolImage(image='busybox', rm=False)
    out = tool.run_get_string(['id'])
    assert out == 'uid=0(root) gid=0(root) groups=10(wheel)\n'

    tool = ToolImage(image='busybox', rm=False)
    tool.user = 'root'
    out = tool.run_get_string(['id'])
    assert out.startswith('uid=0(root) gid=0(root)')
