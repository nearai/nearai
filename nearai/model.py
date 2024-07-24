from pathlib import Path

from nearai.registry import model


def get_model(name: str) -> Path:
    """
    Download the model from the registry and download it locally if it hasn't been downloaded yet.

    :param name: The name of the model to download
    :return: The path to the downloaded model
    """
    return model.download(name)
