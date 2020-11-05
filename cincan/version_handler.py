from os.path import basename
import asyncio
import logging
from typing import List
from docker.models.images import Image
from cincan.configuration import Configuration
from cincanregistry import ToolRegistry
from cincan.utils import ANSIEscapes


class VersionHandler:
    """Class for handling version information from 'cincan-registry' on image runtime"""

    def __init__(self, config: Configuration, registry: ToolRegistry, image: Image, tool_name: str,
                 logger: logging.Logger):
        self.config = config
        self.registry = registry
        self.image = image
        self.tool_name = tool_name
        self.logger = logger
        self.current_version = ""
        self.data_available: bool = False
        self.latest_local: str = ""
        self.local_tags: List = []
        self.local_updates: bool = False
        self.latest_remote: str = ""
        self.remote_tags: List = []
        self.remote_updates: bool = False
        self.latest_origin: str = ""
        self.origin_provider: str = ""

    def _get_version_information(self):
        """
        Get version status of image from remote and origin,
        including local current version
        """
        self.current_version = self.registry.local_registry.get_version_by_image_id(self.image.id)
        loop = asyncio.get_event_loop()
        try:
            version_info = loop.run_until_complete(
                self.registry.list_versions(basename(self.tool_name), only_updates=False))
        except FileNotFoundError as e:
            # FileNotFoundError is raised if origin check is not implemented
            self.logger.debug(f"Version check failed for {self.tool_name}: {e}")
            return
        if version_info:
            version_data = version_info.get("versions", {})
            local_data = version_data.get("local", {})
            remote_data = version_data.get("remote", {})
            origin_data = version_data.get("origin", {})
            if local_data:
                self.latest_local = local_data.get("version", "")
                self.local_tags = local_data.get("tags", [])
            if remote_data:
                self.latest_remote = remote_data.get("version", "")
                self.remote_tags = remote_data.get("tags", [])
            if origin_data:
                self.latest_origin = origin_data.get("version", "")
                self.origin_provider = origin_data.get("details", {}).get("provider", "")
            available_updates = version_info.get("updates", {})
            self.local_updates = available_updates.get("local")
            self.remote_updates = available_updates.get("remote")
            if version_data and available_updates:
                self.data_available = True

    def compare_versions(self):
        """
        Compare version information, log details. Versions are colored with ANSI escapes
        RED - direct update available
        YELLOW - not latest version, but cant change immediately. Exception in current tool case.
        GREEN - All good.
        """

        if not self.tool_name.startswith(f'{self.registry.remote_registry.full_prefix}/'):
            self.logger.debug("Version information disabled for non-cincan tools.")
            return

        self._get_version_information()
        if self.data_available:
            other = ""
            if not self.local_updates:
                if self.current_version != self.latest_local:
                    color_current = ANSIEscapes.YELLOW
                    color_local = ANSIEscapes.GREEN
                    other = f"Latest local is available with tags '{','.join(self.local_tags)}'"
                else:
                    color_current = ANSIEscapes.GREEN
                    color_local = ANSIEscapes.GREEN
            else:
                color_current = ANSIEscapes.YELLOW
                color_local = ANSIEscapes.RED
                if self.config.default_stable_tag in self.remote_tags:
                    other = f"Update available in remote: ('{self.latest_local}' vs. '{self.latest_remote}')" \
                            f" Use 'docker pull {self.tool_name}:{self.config.default_stable_tag}' to update."
                else:
                    other = f"Newer development version available in remote: " \
                            f"'{self.latest_local}' vs. '{self.latest_remote}' with tags '{','.join(self.remote_tags)}'"
            color_remote = ANSIEscapes.YELLOW if self.remote_updates else ANSIEscapes.GREEN
            currentV = f"{ANSIEscapes.BOLD}Current:{ANSIEscapes.END} {color_current}{self.current_version}{ANSIEscapes.END}"
            localV = f"{ANSIEscapes.BOLD}Latest Local:{ANSIEscapes.END} {color_local}{self.latest_local}{ANSIEscapes.END}"
            remoteV = f"{ANSIEscapes.BOLD}Latest Remote:{ANSIEscapes.END} {color_remote}{self.latest_remote}{ANSIEscapes.END}"
            originV = f"{ANSIEscapes.BOLD}Origin:{ANSIEscapes.END} {self.latest_origin}"
            ver_info = f"Version information - {currentV} {localV} {remoteV} {originV}"
            self.logger.info(ver_info)
            if other:
                self.logger.info(other)
        else:
            self.logger.info(f"No version information available for {self.tool_name}\n")
