from pathlib import Path
from typing import Union

from datasets import Dataset, DatasetDict, load_from_disk

from nearai.registry import dataset


def get_dataset(alias_or_name: str) -> Path:
    """
    Download the dataset from the registry and download it locally if it hasn't been downloaded yet.

    :param name: The name of the dataset to download
    :return: The path to the downloaded dataset
    """
    return dataset.download(alias_or_name)


def load_dataset(alias_or_name: str) -> Union[Dataset, DatasetDict]:
    path = get_dataset(alias_or_name)
    return load_from_disk(path.as_posix())
