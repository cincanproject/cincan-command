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


class ANSIEscapes:

    BLACK = "\033[30m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    DARKCYAN = "\033[36m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    GREEN_BACKGROUND = "\033[102m"
    YELLOW = "\033[93m"
    GRAY = "\033[90m"
    GRAY_BACKGROUND = "\033[100m"
    RED = "\033[31m"
    RED_BACKGROUND = "\033[41m"
    BOLD_RED = "\033[1m\033[31m"
    BOLD = "\033[1m"
    BOLD_YELLOW = "\033[1m\033[33m"
    UNDERLINE = "\033[4m"
    WHITE_BACKGROUND = "\033[47m"
    END = "\033[0m"
