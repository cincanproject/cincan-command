import sys
import logging
from docker.models.images import Image
from docker.client import DockerClient, APIClient
from docker.errors import ImageNotFound, NotFound
from typing import Dict
from shutil import get_terminal_size
from .utils import NavigateCursor
from .configuration import Configuration


class ImageFetcher:
    """Class for getting the correct tool image, possibly pulling it from remote"""

    def __init__(self, config: Configuration, client: DockerClient, low_level_client: APIClient,
                 logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.client = client
        self.low_level_client = low_level_client

    def get_image(self, image: str, pull: bool = False) -> Image:

        # Use defined default tag if tag not set
        name_tag = image.rsplit(':', 1) if ':' in image else (
            [image, self.config.default_stable_tag] if image.startswith("cincan/") else [image, "latest"])
        initial_tag = name_tag[1]

        if pull:
            self.logger.info(f"pulling image with tag '{name_tag[1]}'...")
            try:
                self.__pull_image(name_tag[0], tag=name_tag[1])
            except ImageNotFound:
                self.logger.error("Repository not found or no access into it. Is it typed correctly?")
                sys.exit(1)
            except NotFound:
                # Tag was initially set to custom, do not attempt other tag
                if initial_tag != self.config.default_stable_tag or not image.startswith("cincan/"):
                    self.logger.error(f"Tag '{name_tag[1]}' not found. Is it typed correctly?")
                    sys.exit(1)
                # Attempt to run 'cincan' tools with dev tag as well if no stable tag found
                self.logger.info(f"Tag '{name_tag[1]}' not found. Trying development tag "
                                 f"'{self.config.default_dev_tag}' instead.")
                name_tag[1] = self.config.default_dev_tag
                try:
                    # Attempt to use dev image without pull at first
                    image_obj = self.client.images.get(":".join(name_tag))
                    return image_obj
                except ImageNotFound:
                    try:
                        self.client.images.pull(name_tag[0], tag=name_tag[1])
                    except NotFound:
                        self.logger.error(
                            f"'{initial_tag}' or '{self.config.default_dev_tag}' tag not found for image "
                            f"{name_tag[0]} locally or remotely.")
                        sys.exit(1)
        try:
            image_obj = self.client.images.get(":".join(name_tag))
        except ImageNotFound:
            # If image not found when pull set False, try to pull it
            image_obj = self.get_image(image, pull=True)
        return image_obj

    def __pull_image(self, repository: str, tag: str):
        """
        Pull image. If lower API is available and logging level low enough, show progress bar.
        Progress bar is disabled, if input or output is not for 'tty'.
        """
        try:
            if isinstance(self.low_level_client, APIClient) \
                    and sys.stdin.isatty() and sys.stdout.isatty() \
                    and self.logger.getEffectiveLevel() < 30:
                self.__pull_image_with_progress(repository, tag)
            else:
                # No fancy progress bar
                self.client.images.pull(repository, tag)
        except KeyboardInterrupt:
            self.logger.info("\nKeyboard interrupt detected. Closing...")
            sys.exit(0)

    def __pull_image_with_progress(self, repository: str, tag: str):
        """Pulls image while logging in real time the progress"""

        def log_row(data: Dict):
            """Log single row of data"""
            layer_id = data.get("id", "")
            if layer_id:
                layer_id_padded = f'{layer_id:<12}: '
            else:
                layer_id_padded = layer_id
            status_ = data.get("status", "")
            progress = data.get("progress", "")
            t_width = get_terminal_size().columns
            line = f'{layer_id_padded}{status_:<{20}} {progress}'
            if len(f"{repository}: {line}") > t_width:
                diff = len(f"{repository}: {line}") - t_width
                self.logger.info(line[:-diff])
                return
            self.logger.info(line)

        position = NavigateCursor()
        first_time = True
        # Locations means the location of data row in terminal output
        loc = 0
        cur_loc = 0
        locations = {}
        for status in self.low_level_client.pull(repository, tag, stream=True, decode=True):
            s_id = status.get("id", "")
            if s_id and not first_time:
                position.up(cur_loc)
                cur_loc = 0
            elif not s_id:
                # Last responses do not contain id
                log_row(status)
                continue
            # Get status of each layer once at first
            if not locations.get(s_id):
                loc += 1
                locations[s_id] = {}
                locations[s_id]["state"] = status
                locations[s_id]["loc"] = loc
                cur_loc += 1
                log_row(locations[s_id].get("state"))
                first_time = True
            else:
                if first_time:
                    position.up(cur_loc)
                    cur_loc = 0
                first_time = False
                locations[s_id]["state"] = status
                for _id in sorted(locations, key=lambda item: locations[item].get("loc")):
                    log_row(locations[_id].get("state"))
                    cur_loc += 1
