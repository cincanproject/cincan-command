import hashlib
import pathlib
from io import TextIOBase
from typing import Dict, Optional, List, Tuple, Set

from cincan.command_log import CommandLogIndex, CommandLog, JSON_TIME_FORMAT
from cincan.commands import quote_args


class FileDependency:
    def __init__(self, file: pathlib.Path, digest: str):
        self.file = file
        self.digest = digest
        self.next: List['CommandDependency'] = []

    def __str__(self):
        file_string = self.file.as_posix() + ' ' + self.digest[:16]
        next_strings = [str(s).replace('\n', '\n  ') for s in self.next]
        return file_string + ('\n|-->' + '\n|-->'.join(next_strings) if next_strings else '')


class CommandDependency:
    def __init__(self, command: CommandLog):
        self.command = command
        self.next: List[FileDependency] = []

    def __str__(self):
        cmd_string = " ".join(quote_args(self.command.command)) + \
                     ' # ' + self.command.timestamp.strftime(JSON_TIME_FORMAT)
        next_strings = [str(s).replace('\n', '\n  ') for s in self.next]
        return cmd_string + ('\n|-->' + '\n|-->'.join(next_strings) if next_strings else '')


class CommandInspector:
    def __init__(self, log: CommandLogIndex):
        self.log = log

    def fanin(self, file: pathlib.Path, digest: Optional[str] = None) -> List[CommandLog]:
        file_digest = digest or self.hash_of(file)
        res = []
        for cmd in self.log.array:
            found = any(filter(lambda f: f.md5 == file_digest, cmd.out_files))
            if found:
                res.append(cmd)
        return res

    def fanout(self, file: pathlib.Path, already_covered: Set[str] = None, digest: Optional[str] = None) -> FileDependency:
        file_digest = digest or self.hash_of(file)
        file_dep = FileDependency(file, file_digest)
        already_covered = already_covered.copy() if already_covered else set([])
        already_covered.add(file_digest)

        covered: Set[str] = set()
        for cmd in self.log.list_entries(reverse=True):
            cmd_string = cmd.command_string()
            if cmd_string in already_covered:
                continue
            input_here = any(filter(lambda f: f.md5 == file_digest, cmd.in_files))
            if input_here:
                new_output = any(filter(lambda f: f.md5 not in covered, cmd.out_files))
                if not new_output:
                    continue  # does not add new files to
                cmd_dep = CommandDependency(cmd)
                for file in cmd.out_files:
                    covered.add(file.md5)
                    if file.md5 in already_covered:
                        continue
                    cmd_covered = already_covered.copy()
                    cmd_covered.add(cmd_string)
                    cmd_dep.next.append(self.fanout(file.path, cmd_covered, file.md5))
                file_dep.next.append(cmd_dep)
        return file_dep

    def print_fanout(self, writer: TextIOBase, fanout: List[Tuple[CommandLog, List]]):
        self.__print_fans(writer, fanout, fanout=True, indent='')

    def __print_fans(self, writer: TextIOBase, fans: List[Tuple[CommandLog, List]], fanout: bool, indent: str):
        for cmd, next in fans:
            cmd_string = " ".join(quote_args(cmd.command))
            writer.write(f"{indent}{cmd_string}\n")
            if isinstance(next, List):
                self.__print_fans(writer, next, fanout, indent + '  ')

    @classmethod
    def hash_of(cls, file: pathlib.Path) -> str:
        md5sum = hashlib.md5()
        with file.open("rb") as f:
            chunk = f.read(2048)
            while chunk:
                md5sum.update(chunk)
                chunk = f.read(2048)
        return md5sum.hexdigest()
