import hashlib
import pathlib
from io import TextIOBase
from typing import Optional, List, Tuple, Set

from cincan.command_log import CommandLogIndex, CommandLog, quote_args


class FileDependency:
    """File dependency information for command log"""
    def __init__(self, file: pathlib.Path, digest: str, out:bool):
        self.file = file
        self.digest = digest
        self.out = out
        self.next: List['CommandDependency'] = []

    def __str__(self):
        file_string = self.file.as_posix() + (' ' + self.digest[:16] if self.digest else '/')
        next_strings = [str(s).replace('\n', '\n    ') for s in self.next]
        p = '\n|-- ' if self.out else '\n^-- '
        return file_string + (p + p.join(next_strings) if next_strings else '')


class CommandDependency:
    """Command dependency information for command log"""
    def __init__(self, command: CommandLog, out:bool):
        self.command = command
        self.out = out
        self.next: List[FileDependency] = []

    def __str__(self):
        cmd_string = " ".join(quote_args(self.command.command))
        next_strings = [str(s).replace('\n', '\n    ') for s in self.next]
        p = '\n|-->' if self.out else '\n^---'
        return cmd_string + (p + p.join(next_strings) if next_strings else '')


class CommandInspector:
    """Inspector for doing analysis based on command log"""
    def __init__(self, log: CommandLogIndex, work_dir: pathlib.Path):
        self.log = log
        self.work_dir = work_dir

    def __work_path(self, path: pathlib.Path) -> pathlib.Path:
        if path.as_posix().startswith('/dev/'):
            return path
        try:
            return path.relative_to(self.work_dir)
        except ValueError:
            return path.resolve()

    def fanin(self, file: pathlib.Path, depth: int, already_covered: Set[str] = None,
              digest: Optional[str] = None) -> FileDependency:
        file_digest = digest or self.hash_of(file)
        file_dep = FileDependency(self.__work_path(file), file_digest, out=False)
        file_check = file.as_posix() + ':' + file_digest
        already_covered = already_covered or set([])
        if depth < 1 or file_check in already_covered:
            return file_dep
        already_covered.add(file_check)

        for cmd in self.log.list_entries(reverse=True):
            output_here = any(filter(lambda f: f.digest == file_digest, cmd.out_files))
            if output_here:
                cmd_dep = CommandDependency(cmd, out=False)
                for file in cmd.in_files:
                    cmd_dep.next.append(self.fanin(file.path, depth - 1, already_covered, file.digest))
                file_dep.next.append(cmd_dep)
        return file_dep

    def fanout(self, file: pathlib.Path, depth: int, already_covered: Set[str] = None,
               digest: Optional[str] = None) -> FileDependency:
        file_digest = digest or self.hash_of(file)
        file_dep = FileDependency(self.__work_path(file), file_digest, out=True)
        file_check = file.as_posix() + ':' + file_digest
        already_covered = already_covered or set([])
        if depth < 1 or file_check in already_covered:
            return file_dep
        already_covered.add(file_check)

        for cmd in self.log.list_entries(reverse=True):
            input_here = any(filter(lambda f: f.digest == file_digest, cmd.in_files))
            if input_here:
                cmd_dep = CommandDependency(cmd, out=True)
                for file in cmd.out_files:
                    cmd_dep.next.append(self.fanout(file.path, depth -1, already_covered, file.digest))
                file_dep.next.append(cmd_dep)
        return file_dep

    @classmethod
    def hash_of(cls, file: pathlib.Path) -> str:
        if not file.is_file():
            return ''
        md = hashlib.sha256()
        with file.open("rb") as f:
            chunk = f.read(2048)
            while chunk:
                md.update(chunk)
                chunk = f.read(2048)
        return md.hexdigest()
