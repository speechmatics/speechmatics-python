import copy
import os.path
import logging
import yaml

LOGGER = logging.getLogger(__name__)
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/speechmatics/config.yaml")


class ConfigurationFormatError(ValueError):
    pass


def load_config(path=None):
    """
    Loads configuration yaml file into python dict object

    Args:
        path (Union[str, None]): File path to a config to load. Can be None, in
            that case DEFAULT_CONFIG_PATH is used.

    Returns:
        dict: Config representation as a dict.

    Raises:
        FileNotFoundError: If configuration file does not exists. Note, that if
            no `path` is passed and DEFAULT_CONFIG_PATH does not exist, this
            function silently returns empty dict.
        ConfigurationFormatError: If configuration file has unexpected format.
    """
    orig_path = path
    if path is None:
        path = DEFAULT_CONFIG_PATH

    try:
        with open(path, 'r') as config_file:
            config = yaml.safe_load(config_file)
            if config is None:
                return dict()
            if not isinstance(config, dict):
                raise ConfigurationFormatError(
                    "Configuration format is invalid"
                )
            LOGGER.debug("Configuration loaded from file: {path}")
            return config
    except FileNotFoundError as exc:
        if orig_path is None:
            LOGGER.debug("Ignoring non existing configuration file: {path}")
            return dict()
        raise exc


def merge_configs(orig_config, update_config):
    """
    Merges two configuration dictionaries together. If configurations are not
    flat, the behaviour is undefined.

    Args:
        orig_config (dict): Original configuration.
        update_config (dict): Overwriting configuration. If it contains None and
            `orig_config` is not None, the result is not overwritten

    Returns:

    """
    result = copy.deepcopy(orig_config)
    for key in update_config.keys():
        if update_config.get(key) is not None or orig_config.get(key) is None:
            result[key] = update_config[key]
    return result
