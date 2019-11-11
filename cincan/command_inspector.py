import hashlib
import pathlib
from io import TextIOBase
from typing import Dict, Optional, List, Tuple, Set

from cincan.command_log import CommandLogIndex, CommandLog
from cincan.commands import quote_args


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

    def fanout(self, file: pathlib.Path, hashes: Set[str] = None, digest: Optional[str] = None) \
            -> List[Tuple[CommandLog, List]]:

        file_digest = digest or self.hash_of(file)
        if hashes and (file_digest in hashes):
            return []
        next_hashes = hashes.copy() if hashes else set([])
        next_hashes.add(file_digest)
        res = []
        for cmd in self.log.array:
            input_here = any(filter(lambda f: f.md5 == file_digest, cmd.in_files))
            if input_here:
                next_lvl = []
                for file in cmd.out_files:
                    next_lvl.extend(self.fanout(file.path, next_hashes, file.md5))
                res.append((cmd, next_lvl))
        return res

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
