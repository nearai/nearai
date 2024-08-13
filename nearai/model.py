from pathlib import Path

from nearai.registry import registry


def get_model(name: str) -> Path:
    """Download the model from the registry and download it locally if it hasn't been downloaded yet.

    :param name: The name of the entry to download the model. The format should be namespace/name/version.
    :return: The path to the downloaded model
    """
    return registry.download(name)
