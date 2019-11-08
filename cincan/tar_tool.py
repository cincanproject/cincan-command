import datetime
import hashlib
import io
import pathlib
import tarfile
import tempfile
import timeit
from logging import Logger
from typing import Dict, Optional, List

from docker.models.containers import Container


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

    def download_files(self, explicit_output: Optional[Dict[str, str]]):
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
        for f in candidates:
            self.__download_file_maybe(f, force_download=explicit_output is not None)

    def __download_file_maybe(self, file_name: str, force_download: bool):
        # self.logger.debug(f"container file changed {file_name}")
        down_file = pathlib.Path(file_name)
        # all files come with leading '/' whether they are in home or in root :O
        # ... just strip it and put all to work dir
        host_file = pathlib.Path((file_name[1:] if file_name.startswith('/') else file_name).replace(':', '_'))

        get_arc_start = timeit.default_timer()
        chunks, stat = self.container.get_archive(file_name)

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
            up_time = datetime.datetime.fromtimestamp(int(up_stat[1]))
            up_time_s = up_time.strftime(self.time_format_seconds)  # seconds
            time_now_s = datetime.datetime.now().strftime(self.time_format_seconds)
            if down_time_s.startswith(up_time_s) and up_time_s != time_now_s:
                # down_time is seconds, up_time has more precision
                self.logger.debug(f"timestamp {host_file.as_posix()} not updated {down_time_s}")
                return
            self.logger.debug(f"timestamp {host_file.as_posix()} updated {up_time_s} -> {down_time_s}")

        tmp_tar = tempfile.TemporaryFile()
        for c in chunks:
            # self.logger.debug(f"chunk of {len(c)} bytes")
            tmp_tar.write(c)
        self.logger.debug("get_archive time %.4f ms", timeit.default_timer() - get_arc_start)

        tmp_tar.seek(0)
        down_tar = tarfile.open(fileobj=tmp_tar, mode="r|")
        for tf in down_tar:
            cont_file = pathlib.Path(down_file).parent / tf.name
            if cont_file.as_posix() != file_name:
                # trim away leading directories
                continue
            if tf.isfile() and (force_download or not host_file.exists()):
                # no local file or explicit output asked, this is too easy
                self.logger.info(f"copy out {host_file.as_posix()}")
                tf_data = down_tar.extractfile(tf)
                if host_file.parent:
                    host_file.parent.mkdir(parents=True, exist_ok=True)
                with host_file.open("wb") as f:
                    f_chunk = tf_data.read(2048)
                    while f_chunk:
                        f.write(f_chunk)
                        f_chunk = tf_data.read(2048)
            elif tf.isfile() and host_file.is_dir():
                raise Exception(f"copy out {host_file.as_posix()} failed, a directory with that name exists")
            elif tf.isfile() and host_file.exists():
                # compare by hash, if should override local file
                tf_data = down_tar.extractfile(tf)
                candi_file = pathlib.Path(host_file.as_posix() + '_TEMP')
                self.logger.debug(f"creating temp file {candi_file.as_posix()}")
                if host_file.parent:
                    host_file.parent.mkdir(parents=True, exist_ok=True)
                candi_f = candi_file.open("wb")
                md5sum = hashlib.md5()
                f_chunk = tf_data.read(2048)
                while f_chunk:
                    candi_f.write(f_chunk)
                    md5sum.update(f_chunk)
                    f_chunk = tf_data.read(2048)
                candi_f.close()
                tf_digest = md5sum.hexdigest()

                # calculate hash for existing file
                with host_file.open("rb") as f:
                    md5sum = hashlib.md5()
                    f_chunk = f.read(2048)
                    while f_chunk:
                        md5sum.update(f_chunk)
                        f_chunk = f.read(2048)
                    candi_digest = md5sum.hexdigest()

                if tf_digest == candi_digest:
                    self.logger.debug(f"identical file {host_file.as_posix()} md5 {tf_digest}, no action")
                    candi_file.unlink()
                    continue

                self.logger.debug(f"file {host_file.as_posix()} md5 in container {tf_digest}, in host {candi_digest}")
                self.logger.info(f"copy out and replace {host_file.as_posix()}")
                host_file.unlink()
                candi_file.rename(host_file)
            elif tf.isdir() and host_file.is_file():
                raise Exception(f"mkdir {host_file.as_posix()} failed, a file with that name exists")
            elif tf.isdir() and host_file.is_dir():
                pass  # no action required
            elif tf.isdir():
                self.logger.info(f"mkdir {host_file.as_posix()}")
                host_file.mkdir(parents=True, exist_ok=True)
        tmp_tar.close()
