import sys


class NavigateCursor:
    """Class for controlling cursor position of terminal with ANSI codes"""

    def __init__(self):
        """Hides cursor when instanced"""
        self.hide()

    def __del__(self):
        """Return visibility of cursor always in the end"""
        self.make_visible()

    @classmethod
    def hide(cls):
        """Hide cursor"""
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

    @classmethod
    def make_visible(cls):
        """Make cursor visible"""
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

    @classmethod
    def up(cls, n: int = 1):
        """Move cursor up n lines"""
        sys.stdout.write(f'\u001b[{n}A')
        sys.stdout.flush()

    @classmethod
    def down(cls, n: int = 1):
        """Move cursor down n lines"""
        sys.stdout.write(f'\u001b[{n}B')
        sys.stdout.flush()

    @classmethod
    def right(cls, n: int = 1):
        """Move cursor right n characters"""
        sys.stdout.write(f'\u001b[{n}C')
        sys.stdout.flush()

    @classmethod
    def left(cls, n: int = 1):
        """Move cursor left n characters"""
        sys.stdout.write(f'\u001b[{n}D')
        sys.stdout.flush()

    @classmethod
    def clear_line(cls):
        """Clear current line"""
        sys.stdout.write("\33[2K")
