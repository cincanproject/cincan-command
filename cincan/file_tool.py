import pathlib
import re
from datetime import datetime
from typing import List, Optional, Dict, Set, Tuple, Iterable

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

                o_is_file = o_file.exists()
                if not o_is_file and not o_file.is_absolute() and '..' not in o_file.as_posix():
                    # the file does not exist, but it is relative path to a file/directory...
                    o_parent = o_file.parent
                    while not o_is_file and o_parent and o_parent.as_posix() != '.':
                        if o_parent.is_dir() and o_parent not in self.host_files:
                            o_is_file = True  # ...and there is existing parent directory, perhaps for output
                        o_parent = o_parent.parent

                if o_is_file:
                    h_file, a_name = self.__archive_name_for(o_file)
                    self.host_files.append(h_file)
                    c_args.append(a_name)
                else:
                    c_args.append(part)
            self.command_args.append(''.join(c_args))

    def resolve_upload_files(self, in_files: List[FileLog], upload_files: Dict[pathlib.Path, str]):
        for up_file in self.detect_upload_files():
            host_file, arc_name = self.__archive_name_for(up_file)
            if up_file.is_file():
                with up_file.open("rb") as f:
                    file_md5 = read_with_hash(f.read)
                in_files.append(FileLog(host_file.resolve(), file_md5, datetime.fromtimestamp(up_file.stat().st_mtime)))
            upload_files[host_file] = arc_name
        cmd_args = self.command_args
        return cmd_args

    def detect_upload_files(self, files: Optional[Iterable[pathlib.Path]] = None) -> List[pathlib.Path]:
        it_files = sorted(self.host_files) if files is None else files
        res = []
        for file in it_files:
            if file.exists():
                res.append(file)
            if file.is_dir():
                sub_res = self.detect_upload_files(file.iterdir())
                res.extend(sub_res)
        if files is None:
            # make sure also paths leading to output files are uploaded
            all_dirs = set()
            for file in res:
                all_dirs.add(file)
                for p in file.parents:
                    all_dirs.add(p)
            for file in filter(lambda f: not f.exists(), it_files):
                # file not exists, but marked for upload - must mean some sub directory for output
                p = file.parent
                while not p.exists():
                    p = p.parent
                if p not in all_dirs:
                    res.append(p)
        return res

    @classmethod
    def __archive_name_for(cls, file: pathlib.Path) -> Tuple[pathlib.Path, str]:
        if cls.__use_absolute_path(file):
            h_file = file.resolve()
            a_file = file.resolve().as_posix().replace(':', '_')  # 'C:/jee' -> 'C_/jee'
            a_file = a_file[1:] if a_file.startswith('/') else a_file
        else:
            h_file = file
            a_file = file.as_posix()
        return h_file, a_file

    @classmethod
    def __use_absolute_path(cls, file: pathlib.Path) -> bool:
        # - use absolute paths, if /../ used (ok, quite weak)
        return file.is_absolute() or (".." in file.as_posix())
