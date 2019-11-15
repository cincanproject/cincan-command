import argparse
import hashlib
import io
import select
import struct
import threading
import time
from datetime import datetime
import json
import logging
import pathlib
import sys
import socket
from io import IOBase
from typing import List, Set, Dict, Optional, Tuple

import docker
import docker.errors

from cincan import registry
from cincan.command_inspector import CommandInspector
from cincan.command_log import CommandLog, FileLog, CommandLogWriter, CommandLogIndex
from cincan.commands import quote_args
from cincan.file_tool import FileResolver
from cincan.tar_tool import TarTool


class ToolStream:
    def __init__(self, stream: IOBase):
        self.data_length = 0
        self.md5 = hashlib.md5()
        self.raw = bytearray()  # when collected
        self.stream = stream

    def update(self, data: bytes):
        self.data_length += len(data)
        self.md5.update(data)


class ToolImage:
    """A tool wrapped to docker image"""

    def __init__(self, name: str = None, path: Optional[str] = None,
                 image: Optional[str] = None,
                 pull: bool = False,
                 tag: Optional[str] = None,
                 rm: bool = True):
        self.logger = logging.getLogger(name)
        self.client = docker.from_env()
        self.loaded_image = False  # did we load the image?
        if path is not None:
            self.name = name or path
            if tag is not None:
                self.image, log = self.client.images.build(path=path, tag=tag, rm=rm)
            else:
                self.image, log = self.client.images.build(path=path, rm=rm)
            self.context = path
            self.__log_dict_values(log)
        elif image is not None:
            self.name = name or image
            self.loaded_image = True
            if pull:
                # pull first
                self.logger.info(f"pulling image...")
                self.__get_image(image, pull=True)
            else:
                # just get the image
                try:
                    self.__get_image(image, pull=False)
                except docker.errors.ImageNotFound:
                    # image not found, try to pull it
                    self.logger.info(f"pulling image...")
                    self.__get_image(image, pull=True)
            self.context = '.'  # not really correct, but will do
        else:
            raise Exception("No file nor image specified")
        self.input_files: Optional[List[str]] = None  # Explicit tool input files
        self.upload_stats: Dict[str, List] = {} # upload file stats
        self.output_files: Optional[List[str]] = None  # Explicit tool input files

        # more test-oriented attributes...
        self.upload_files: List[str] = []
        self.download_files: List[str] = []
        self.buffer_output = False

    def get_tags(self) -> List[str]:
        """List image tags"""
        return self.image.tags

    def get_id(self) -> str:
        return self.image.id

    def get_creation_time(self) -> datetime:
        """Get image creation time"""
        return registry.parse_json_time(self.image.attrs['Created'])

    def __get_image(self, image: str, pull: bool = False):
        """Get Docker image, possibly pulling it first"""
        if pull:
            self.client.images.pull(image)
        self.image = self.client.images.get(image)

    def __create_container(self, upload_files: Dict[str, str]):
        """Create a container from the image here"""
        # override entry point to just keep the container running
        container = self.client.containers.create(self.image, auto_remove=True, entrypoint="sh",
                                                  stdin_open=True, tty=True)
        container.start()

        # upload files to container
        tar_tool = TarTool(self.logger, container, self.upload_stats)
        tar_tool.upload(upload_files)

        return container

    def __unpack_container_stream(self, c_socket) -> Tuple[int, bytes]:
        buf = bytearray()
        while len(buf) < 8:
            r = c_socket.read(8 - len(buf))
            if not r:
                return 0, bytes([])  # EOF
            buf.extend(r)
        s_len = struct.unpack('>Q', buf)[0]
        s_type = s_len >> 56
        s_len = s_len & 0xffffffffffffff

        self.logger.debug(f"container input type={s_type} length={s_len}")
        buf.clear()
        while len(buf) < s_len:
            r = c_socket.read(s_len - len(buf))
            if not r:
                raise Exception('Failed to read all data from the container')
            buf.extend(r)
        return s_type, buf

    def __container_exec(self, container, cmd_args: List[str]) -> CommandLog:
        """Execute a command in the container"""
        # create the full command line and run with exec
        entry_point = self.image.attrs['Config'].get('Entrypoint')
        if not entry_point:
            entry_point = []
        cmd = self.image.attrs['Config'].get('Cmd')
        if not cmd:
            cmd = []  # 'None' value observed
        user_cmd = (cmd_args if cmd_args else cmd)
        full_cmd = entry_point + user_cmd

        log = CommandLog([self.name] + user_cmd)

        stdin_s = ToolStream(sys.stdin)
        stdout_s = ToolStream(sys.stdout.buffer)
        stderr_s = ToolStream(sys.stderr.buffer)

        # execute the command, collect stdin and stderr
        exec = self.client.api.exec_create(container.id, cmd=full_cmd, stdin=True)
        exec_id = exec['Id']
        c_socket = self.client.api.exec_start(exec_id, detach=False, socket=True)
        c_socket_sock = c_socket._sock  # NOTE: c_socket itself is not writeable???, but this is :O

        buffer_size = 1024 * 1024

        self.logger.debug("enter stdin/container io loop...")
        active_streams = [c_socket_sock, sys.stdin]  # prefer socket to limit the amount of data in the container (?)
        c_socket_open = True
        while c_socket_open:
            try:
                # FIXME: Using select, which is known not to work with Windows!
                select_in, _, _ = select.select(active_streams, [], [])
            except io.UnsupportedOperation as e:
                if sys.stdin in active_streams:
                    # pytest stdin is somehow fundamentally dysfunctional
                    active_streams.remove(sys.stdin)
                    continue
                raise e

            for sel in select_in:
                if sel == sys.stdin:
                    s_data = sys.stdin.buffer.read(buffer_size)
                    if not s_data:
                        self.logger.debug(f"received eof from stdin")
                        active_streams.remove(sel)
                        c_socket_sock.shutdown(socket.SHUT_WR)
                    else:
                        self.logger.debug(f"received {len(s_data)} bytes from stdin")
                        stdin_s.update(s_data)

                        out_off = 0
                        while out_off < len(s_data):
                            out_off += c_socket_sock.send(s_data[out_off:])
                            self.logger.debug(f"wrote ...{out_off} bytes to container stdin")

                elif sel == c_socket_sock:
                    s_type, s_data = self.__unpack_container_stream(c_socket)
                    if not s_data:
                        self.logger.debug(f"received eof from container")
                        c_socket_open = False
                        continue
                    if s_type == 1:
                        self.logger.debug(f"received {len(s_data)} bytes from stdout")
                        std_s = stdout_s
                    elif s_type == 2:
                        self.logger.debug(f"received {len(s_data)} bytes from stderr")
                        std_s = stderr_s
                    else:
                        self.logger.warning(f"received {len(s_data)} bytes from ???, discarding")
                        continue
                    std_s.update(s_data)
                    if self.buffer_output:
                        std_s.raw.extend(s_data)
                    else:
                        std_s.stream.write(s_data)

        # inspect execution result
        inspect = self.client.api.exec_inspect(exec_id)
        log.exit_code = inspect.get('ExitCode', 0)

        # collect raw data
        if self.buffer_output:
            log.stdin = bytes(stdin_s.raw)
            log.stdout = bytes(stdout_s.raw)
            log.stderr = bytes(stderr_s.raw)

        if log.exit_code == 0:
            # collect stdin, stdout, stderr hash codes
            if stdin_s.data_length:
                log.in_files.append(FileLog(pathlib.Path('/dev/stdin'), stdin_s.md5.hexdigest()))
            if stdout_s.data_length:
                log.out_files.append(FileLog(pathlib.Path('/dev/stdout'), stdout_s.md5.hexdigest()))
            if stderr_s.data_length:
                log.out_files.append(FileLog(pathlib.Path('/dev/stderr'), stderr_s.md5.hexdigest()))

        return log

    def __run(self, args: List[str]) -> CommandLog:
        """Run native tool in container with given arguments"""
        # resolve files to upload
        resolver = FileResolver(args, pathlib.Path(), input_files=self.input_files)
        in_files = []
        upload_files = {}
        for up_file in resolver.detect_upload_files():
            arc_name = resolver.archive_name_for(up_file)
            if up_file.is_file():
                with up_file.open("rb") as f:
                    file_md5 = TarTool.read_with_hash(f.read)
                in_files.append(FileLog(up_file.resolve(), file_md5, datetime.fromtimestamp(up_file.stat().st_mtime)))
            upload_files[up_file.as_posix()] = arc_name
            self.logger.debug(f"{up_file.as_posix()} -> {arc_name}")
        cmd_args = resolver.command_args
        self.logger.debug("args: %s", ' '.join(quote_args(cmd_args)))

        container = self.__create_container(upload_files)
        log = CommandLog([])
        try:
            log = self.__container_exec(container, cmd_args)
            log.in_files.extend(in_files)
            if log.exit_code == 0:
                # download results
                tar_tool = TarTool(self.logger, container, self.upload_stats)
                log.out_files.extend(tar_tool.download_files(self.output_files))
        finally:
            self.logger.debug("killing the container")
            container.kill()
            # if we created the image, lets also remove it (intended for testing)
            if not self.loaded_image:
                self.logger.info(f"removing the docker image {self.get_id()}")
                try:
                    self.remove_image()
                except docker.errors.APIError as e:
                    self.logger.warning(e)

        work_dir = pathlib.Path().cwd()
        self.upload_files = list(upload_files.keys())
        self.download_files = [f.path.relative_to(work_dir).as_posix() for f in
                               filter(lambda f: not f.path.as_posix().startswith('/dev/'), log.out_files)]
        return log

    def run(self, args: List[str]) -> CommandLog:
        """Run native tool in container, return output"""
        self.buffer_output = False  # we stream it
        return self.__run(args)

    def run_get_string(self, args: List[str]) -> str:
        """Run native tool in container, return output as a string"""
        self.buffer_output = True  # we return it
        log = self.__run(args)
        return log.stdout.decode('utf8') + log.stderr.decode('utf8')

    def __log_dict_values(self, log: Set[Dict[str, str]]) -> None:
        """Log values from a dict as debug"""
        for i in log:
            v = i.values()
            self.logger.debug("{}".format(*v).strip())

    def file_to_copy_from_context(self, file: str) -> str:
        """Create path for sample file inside docker context (for unit testing) """
        return str(pathlib.Path(self.context) / file)

    def remove_image(self):
        """Remove this image"""
        self.client.images.remove(self.get_id())

def tool_with_file(file: str, use_tag: Optional[bool] = True) -> ToolImage:
    path = pathlib.Path(file).parent.name
    tag = None
    if use_tag:
        tag = 'test_{}'.format(path)
    return ToolImage(name=path, path=path, tag=tag)


def image_default_args(sub_parser):
    """Default arguments for sub commands which load docker image"""
    sub_parser.add_argument('tool', help="the tool and possible arguments", nargs=argparse.REMAINDER)
    sub_parser.add_argument('-p', '--path', help='path to Docker context')
    sub_parser.add_argument('-u', '--pull', action='store_true', help='Pull image from registry')


def main():
    m_parser = argparse.ArgumentParser()
    m_parser.add_argument("-l", "--log", dest="log_level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                          help="Set the logging level", default=None)
    m_parser.add_argument('-q', '--quiet', action='store_true', help='Be quite quiet')
    subparsers = m_parser.add_subparsers(dest='sub_command')

    run_parser = subparsers.add_parser('run')
    image_default_args(run_parser)
    run_parser.add_argument('-i', '--in', dest='input_files', default=None, help='Explicitly list tool input files')
    run_parser.add_argument('-o', '--out', dest='output_files', default=None, help='Explicitly list tool output files')

    list_parser = subparsers.add_parser('list')
    list_parser.add_argument('-i', '--in', dest='input', action='store_true', help='Show input formats')
    list_parser.add_argument('-o', '--out', action='store_true', help='Show output formats')
    list_parser.add_argument('-t', '--tags', action='store_true', help='Show tags')

    mani_parser = subparsers.add_parser('manifest')
    image_default_args(mani_parser)

    fanin_parser = subparsers.add_parser('fanin', help='Show fan-in to the given file')
    fanin_parser.add_argument('file', help="File to analyze")
    fanout_parser = subparsers.add_parser('fanout', help='Show fan-out from the given file')
    fanout_parser.add_argument('file', help="File to analyze")

    help_parser = subparsers.add_parser('help')

    if len(sys.argv) > 1:
        args = m_parser.parse_args(args=sys.argv[1:])
    else:
        args = m_parser.parse_args(args=['help'])

    log_level = args.log_level if args.log_level else ('WARNING' if args.quiet else 'INFO')
    logging.basicConfig(format='%(name)s: %(message)s', level=getattr(logging, log_level))
    if args.sub_command == 'help':
        m_parser.print_help()
        sys.exit(1)
    elif args.sub_command in {'run'}:
        if len(args.tool) == 0:
            raise Exception('Missing tool name argument')
        name = args.tool[0]
        if args.path is None:
            tool = ToolImage(name, image=name, pull=args.pull)
        elif args.path is not None:
            tool = ToolImage(name, path=args.path)
        else:
            tool = ToolImage(name)  # should raise exception
        tool.input_files = list(filter(
            lambda s: s, args.input_files.split(","))) if args.input_files is not None else None
        tool.output_files = list(filter(
            lambda s: s, args.output_files.split(","))) if args.output_files is not None else None
        all_args = args.tool[1:]

        log = tool.run(all_args)
        if log.exit_code == 0:
            log_writer = CommandLogWriter()
            log_writer.write(log)
        if log.stdout:
            sys.stdout.buffer.write(log.stdout)
        if log.stderr:
            sys.stderr.buffer.write(log.stderr)
        sys.exit(log.exit_code)  # exit code
    elif args.sub_command in {'fanin', 'fanout'}:
        inspector = CommandInspector(CommandLogIndex(), pathlib.Path().resolve())
        if args.sub_command == 'fanout':
            res = inspector.fanout(pathlib.Path(args.file).resolve())
        else:
            res = inspector.fanin(pathlib.Path(args.file).resolve())
        print(res)
    elif args.sub_command == 'manifest':
        # sub command 'manifest'
        if len(args.tool) == 0:
            raise Exception('Missing tool name argument')
        name = args.tool[0]
        reg = registry.ToolRegistry()
        info = reg.fetch_manifest(name)
        print(json.dumps(info, indent=2))
    else:
        format_str = "{0:<25}"
        if args.input:
            format_str += " {2:<30}"
        if args.out:
            format_str += " {3:<30}"
        if args.tags:
            format_str += " {4:<20}"
        format_str += " {1}"
        reg = registry.ToolRegistry()
        tool_list = reg.list_tools()
        for tool in sorted(tool_list):
            lst = tool_list[tool]
            print(format_str.format(lst.name, lst.description, ",".join(lst.input), ",".join(lst.output),
                                    ",".join(lst.tags)))
