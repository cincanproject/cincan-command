import sys


class NavigateCursor:

    def __init__(self):
        # hide cursor
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

    def __del__(self):
        # return visibility of cursor in all cases
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

    def up(self, n: int = 1):
        sys.stdout.write(f'\u001b[{n}A')
        sys.stdout.flush()

    def down(self, n: int = 1):
        sys.stdout.write(f'\u001b[{n}B')
        sys.stdout.flush()

    def right(self, n: int = 1):
        sys.stdout.write(f'\u001b[{n}C')
        sys.stdout.flush()

    def left(self, n: int = 1):
        sys.stdout.write(f'\u001b[{n}D')
        sys.stdout.flush()

    def clear_line(self):
        sys.stdout.write("\33[2K")
