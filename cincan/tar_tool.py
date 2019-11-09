from datetime import datetime
import hashlib
import io
import pathlib
import tarfile
import tempfile
import timeit
from logging import Logger
from typing import Dict, Optional, List, Iterable

from docker.models.containers import Container

from cincan.command_log import FileLog


class TarTool:
    def __init__(self, logger: Logger, container: Container, upload_stats: Dict[str, List]):
        self.logger = logger
        self.container = container
        self.upload_stats = upload_stats
        self.time_format_seconds = "%Y-%m-%dT%H:%M:%S"

    def upload(self, upload_files: Dict[str, str]):
        if not upload_files:
            return
        file_out = io.BytesIO()
        tar = tarfile.open(mode="w", fileobj=file_out)
        for name, arc_name in upload_files.items():
            self.logger.info("copy %s in", name)
            host_file = pathlib.Path(name)

            tar_file = tar.gettarinfo(name=name, arcname=arc_name)
            self.upload_stats[arc_name] = [tar_file.size, tar_file.mtime]  # [size, mtime]
            if host_file.is_file():
                with host_file.open("rb") as f:
                    tar.addfile(tar_file, fileobj=f)
            else:
                tar.addfile(tar_file)
        tar.close()

        put_arc_start = timeit.default_timer()
        self.container.put_archive(path='.', data=file_out.getvalue())
        self.logger.debug("put_archive time %.4f ms", timeit.default_timer() - put_arc_start)

    def download_files(self, explicit_output: Optional[Dict[str, str]]) -> List[FileLog]:
        # resolve files to download
        if explicit_output is not None:
            candidates = explicit_output  # explicitly given
        else:
            # check all modified (includes the ones we uploaded)
            candidates = sorted([d['Path'] for d in filter(lambda f: 'Path' in f, self.container.diff() or [])])
            # remove files which are paths to files
            for i, c in enumerate(candidates):
                if i < len(candidates) -1 and candidates[i+1].startswith(c):
                    candidates[i] = None
            candidates = list(filter(lambda s: s, candidates))
        out_files = []
        for f in candidates:
            log = self.__download_file_maybe(f, force_download=explicit_output is not None)
            out_files.extend(log)
        return out_files

    def __download_file_maybe(self, file_name: str, force_download: bool) -> List[FileLog]:
        # self.logger.debug(f"container file changed {file_name}")
        down_file = pathlib.Path(file_name)
        # all files come with leading '/' whether they are in home or in root :O
        # ... just strip it and put all to work dir
        host_file = pathlib.Path((file_name[1:] if file_name.startswith('/') else file_name).replace(':', '_'))

        # get the tar ball for the file
        get_arc_start = timeit.default_timer()
        chunks, stat = self.container.get_archive(file_name)
        check = self.__check_for_download(host_file, stat)

        if not check:
            return []  # do not attempt download

        # read the tarball into temp file
        tmp_tar = tempfile.TemporaryFile()
        for c in chunks:
            # self.logger.debug(f"chunk of {len(c)} bytes")
            tmp_tar.write(c)
        self.logger.debug("get_archive time %.4f ms", timeit.default_timer() - get_arc_start)

        tmp_tar.seek(0)
        down_tar = tarfile.open(fileobj=tmp_tar, mode="r|")
        out_files = []
        for tf in down_tar:
            cont_file = pathlib.Path(down_file).parent / tf.name
            if cont_file.as_posix() != file_name:
                # trim away leading directories
                continue
            md5 = ''
            timestamp = None
            if tf.isfile() and (force_download or not host_file.exists()):
                # no local file or explicit output asked, this is too easy
                self.logger.info(f"copy out {host_file.as_posix()}")
                tf_data = down_tar.extractfile(tf)
                if host_file.parent:
                    host_file.parent.mkdir(parents=True, exist_ok=True)
                with host_file.open("wb") as f:
                    md5 = self.read_with_hash(tf_data, f.write)
            elif tf.isfile() and host_file.is_dir():
                raise Exception(f"copy out {host_file.as_posix()} failed, a directory with that name exists")
            elif tf.isfile() and host_file.exists():
                # compare by hash, if should override local file
                tf_data = down_tar.extractfile(tf)
                temp_file = pathlib.Path(host_file.as_posix() + '_TEMP')
                self.logger.debug(f"creating temp file {temp_file.as_posix()}")

                # calculate hash for file from tar, copy it to temp file
                if host_file.parent:
                    host_file.parent.mkdir(parents=True, exist_ok=True)
                with temp_file.open("wb") as f:
                    md5 = self.read_with_hash(tf_data.read, f.write)

                # calculate hash for existing file
                with host_file.open("rb") as f:
                    host_digest = self.read_with_hash(f.read)

                if md5 == host_digest:
                    self.logger.debug(f"identical file {host_file.as_posix()} md5 {md5}, no action")
                    temp_file.unlink()
                else:
                    self.logger.debug(f"file {host_file.as_posix()} md5 in container {md5}, in host {host_digest}")
                    self.logger.info(f"copy out and replace {host_file.as_posix()}")
                    host_file.unlink()
                    temp_file.rename(host_file)
                    timestamp = datetime.fromtimestamp(host_file.stat().st_mtime)
            elif tf.isdir() and host_file.is_file():
                raise Exception(f"mkdir {host_file.as_posix()} failed, a file with that name exists")
            elif tf.isdir() and host_file.is_dir():
                pass  # no action required
            elif tf.isdir():
                self.logger.info(f"mkdir {host_file.as_posix()}")
                host_file.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.fromtimestamp(host_file.stat().st_mtime)
            out_files.append(FileLog(host_file.resolve(), md5, timestamp))
        tmp_tar.close()
        return out_files

    def __check_for_download(self, host_file: pathlib.Path, stat: Dict) -> bool:
        up_stat = self.upload_stats.get(host_file.as_posix())

        # NOTE: for directories (?) size from container is 4096 -> mismatch for directories!!!
        up_down_size_mismatch = False
        if up_stat and 'size' in stat:
            down_size = int(stat['size'])
            up_size = up_stat[0]
            up_down_size_mismatch = up_size != down_size
            if up_down_size_mismatch:
                self.logger.debug(f"size {host_file.as_posix()} change {up_size} -> {down_size}")

        if (not up_down_size_mismatch) and up_stat and 'mtime' in stat:
            down_time_s = stat['mtime']  # seconds + timezone
            up_time = datetime.fromtimestamp(int(up_stat[1]))
            up_time_s = up_time.strftime(self.time_format_seconds)  # seconds
            time_now_s = datetime.now().strftime(self.time_format_seconds)
            if down_time_s.startswith(up_time_s) and up_time_s != time_now_s:
                # down_time is seconds, up_time has more precision
                self.logger.debug(f"timestamp {host_file.as_posix()} not updated {down_time_s}")
                return False
            self.logger.debug(f"timestamp {host_file.as_posix()} updated {up_time_s} -> {down_time_s}")

        return True

    @classmethod
    def read_with_hash(cls, read_more, write_to: Optional = None) -> str:
        md5sum = hashlib.md5()
        chunk = read_more(2048)
        while chunk:
            md5sum.update(chunk)
            if write_to:
                write_to(chunk)
            chunk = read_more(2048)
        return md5sum.hexdigest()
