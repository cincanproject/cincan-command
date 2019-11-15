import pathlib
import re
from typing import List, Optional, Dict, Set


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

    def detect_upload_files(self) -> List[pathlib.Path]:
        sf = sorted(self.host_files)
        res = []
        # remove files which are just prefix directories
        for i, file in enumerate(sf):
            if file.is_file() or i == len(sf) - 1 or not sf[i + 1].as_posix().startswith(file.as_posix()):
                res.append(file)
        return res

    def archive_name_for(self, file: pathlib.Path) -> str:
        # - use absolute paths, if /../ used (ok, quite weak)
        b_name = file.as_posix()
        use_absolute = ".." in b_name or pathlib.Path(b_name).is_absolute()
        if use_absolute:
            f_name = file.resolve().as_posix().replace(':', '_')  # 'C:/jee' -> 'C_/jee'
            f_name = f_name[1:] if f_name.startswith('/') else f_name
        else:
            f_name = file.as_posix()
        return f_name
