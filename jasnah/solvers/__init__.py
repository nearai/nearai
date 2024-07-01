import ast
import re
from abc import ABC, ABCMeta, abstractmethod
from itertools import islice
from typing import Any, Callable, Dict, List, Type, Union

from datasets import Dataset, DatasetDict
from jinja2 import Template
from openai.types.chat import ChatCompletion
from pydantic import BaseModel

from jasnah.config import PROMPTS_FOLDER


class SolverStrategyMeta(ABCMeta):
    """
    Metaclass that automatically registers subclasses in the SolverStrategyRegistry.
    """

    def __new__(cls, name: str, bases: tuple, namespace: dict) -> Any:
        new_class = super().__new__(cls, name, bases, namespace)
        if bases != (ABC,):  # Avoid registering the abstract base class itself
            SolverStrategyRegistry[new_class.__name__] = new_class  # type: ignore
        return new_class


class SolverStrategy(ABC, metaclass=SolverStrategyMeta):
    """
    Abstract class for solver strategies.
    """

    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return type(self).__name__

    @abstractmethod
    def compatible_datasets(self) -> List[str]: ...

    @abstractmethod
    def solve(self, datum: dict) -> bool: ...


SolverStrategyRegistry: Dict[str, Type[SolverStrategy]] = {}

from jasnah.solvers.mbpp_solver import MBPPSolverStrategy
