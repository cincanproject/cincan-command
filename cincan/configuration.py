import json
import pathlib


class Configuration:
    """Configuration options"""

    def __init__(self, file: pathlib.Path = pathlib.Path.home() / '.cincan' / 'config.json'):
        self.file = file
        if self.file.is_file():
            with file.open() as f:
                self.values = json.load(f)
        else:
            self.values = {}
        self.show_updates = self.values.get("show_updates", True)
        self.default_stable_tag = self.values.get("stable_tag", "latest")
        self.default_dev_tag = self.values.get("dev_tag", "dev")

    def is_command_log(self) -> bool:
        return self.values.get('command_log', False)
