from pathlib import Path

import toml

CONFIG_PATH = Path.home().resolve() / ".speechmatics/config"


def read_config_from_home(profile: str = "default"):
    if CONFIG_PATH.exists():
        cli_config = {"default": {}}
        with CONFIG_PATH.open("r", encoding="UTF-8") as file:
            cli_config = toml.load(file)
        if profile not in cli_config:
            raise SystemExit(
                f"Cannot unset config for profile {profile}. Profile does not exist."
            )
        return cli_config[profile]

    return None
