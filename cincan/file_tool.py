import pathlib
import re
from datetime import datetime
from typing import List, Optional, Dict, Set, Tuple

from cincan.command_log import FileLog
from cincan.tar_tool import TarTool


class FileResolver:
    def __init__(self, args: List[str], directory: pathlib.Path, input_files: List[str] = None):
        self.original_args = args
        self.directory = directory

        # NOTE: Not good for Windows paths!
        self.arg_pattern = re.compile("([a-zA-Z_0-9-/.~]+)")

        self.host_files: List[pathlib.Path] = []
        self.command_args = []
        self.arg_parts: List[str] = []
        if input_files is not None:
            # input files specified
            self.host_files = [pathlib.Path(p) for p in input_files]
            self.arg_parts = args
            self.command_args = args
        else:
            # autodetect input files
            self.__analyze()

    def __analyze(self):
        for o_arg in self.original_args:
            split = list(filter(lambda s: s, self.arg_pattern.split(o_arg)))
            c_args = []
            for part in split:
                self.arg_parts.append(part)
                o_file = pathlib.Path(part)

                #if not o_file.is_absolute():
                #    o_file = self.directory / o_file

                if o_file.exists():
                    self.host_files.append(o_file)
                    c_args.append(part)
                else:
                    c_args.append(part)
            self.command_args.append(''.join(c_args))

    def resolve_upload_files(self, in_files: List[FileLog], upload_files: Dict[pathlib.Path, str]):
        for up_file in self.detect_upload_files():
            host_file, arc_name = self.archive_name_for(up_file)
            if up_file.is_file():
                with up_file.open("rb") as f:
                    file_md5 = TarTool.read_with_hash(f.read)
                in_files.append(FileLog(host_file.resolve(), file_md5, datetime.fromtimestamp(up_file.stat().st_mtime)))
            upload_files[host_file] = arc_name
        cmd_args = self.command_args
        return cmd_args


    def detect_upload_files(self) -> List[pathlib.Path]:
        sf = sorted(self.host_files)
        res = []
        # remove files which are just prefix directories
        for i, file in enumerate(sf):
            if file.is_file() or i == len(sf) - 1 or not sf[i + 1].as_posix().startswith(file.as_posix()):
                res.append(file)
        return res

    def archive_name_for(self, file: pathlib.Path) -> Tuple[pathlib.Path, str]:
        # - use absolute paths, if /../ used (ok, quite weak)
        b_name = file.as_posix()
        use_absolute = ".." in b_name or pathlib.Path(b_name).is_absolute()
        if use_absolute:
            h_file = file.resolve()
            a_file = file.resolve().as_posix().replace(':', '_')  # 'C:/jee' -> 'C_/jee'
            a_file = a_file[1:] if a_file.startswith('/') else a_file
        else:
            h_file = file
            a_file = file.as_posix()
        return h_file, a_file
