import hashlib
import pathlib
from typing import Dict, Optional, List

from cincan.command_log import CommandLogIndex, CommandLog


class CommandInspector:
    def __init__(self, log: CommandLogIndex):
        self.log = log

    def fanout(self, file: pathlib.Path, digest: Optional[str] = None) -> List[CommandLog]:
        file_digest = digest or self.hash_of(file)
        res = []
        for cmd in self.log.array:
            found = any(filter(lambda f: f.md5 == file_digest, cmd.in_files))
            if found:
                res.append(cmd)
        return res

    @classmethod
    def hash_of(cls, file: pathlib.Path) -> str:
        md5sum = hashlib.md5()
        with file.open("rb") as f:
            chunk = f.read(2048)
            while chunk:
                md5sum.update(chunk)
                chunk = f.read(2048)
        return md5sum.hexdigest()
