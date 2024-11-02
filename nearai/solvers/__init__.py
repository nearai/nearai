from abc import ABC, ABCMeta, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from litellm import Choices, ModelResponse
from litellm.types.completion import ChatCompletionMessageParam
from shared.agents.agent import Agent
from shared.client_config import ClientConfig
from shared.inference_client import InferenceClient
from shared.provider_models import get_provider_namespaced_model

from nearai.config import CONFIG


class SolverScoringMethod(Enum):
    # Scores each question with 'True' or 'False'.
    TrueOrFalseList = "TrueOrFalseList"
    # Custom dataset with custom answers.
    Custom = "Custom"


class SolverStrategyClassProperty:
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, _owner_self, owner_cls):
        return self.fget(owner_cls)


class SolverStrategyMeta(ABCMeta):
    """Metaclass that automatically registers subclasses in the SolverStrategyRegistry."""

    def __new__(cls, name: str, bases: tuple, namespace: dict) -> Any:
        new_class = super().__new__(cls, name, bases, namespace)
        if bases != (ABC,):  # Avoid registering the abstract base class itself
            SolverStrategyRegistry[new_class.__name__] = new_class  # type: ignore
        return new_class


class SolverInferenceSession:
    def __init__(self, agent_obj, model_full_path, client: InferenceClient, evaluation_name):
        self.agent = agent_obj
        self.model_full_path = model_full_path
        self.client = client
        self.evaluation_name = evaluation_name
        self.messages: List[ChatCompletionMessageParam] = []

    def start_inference_session(self, _task_id: str) -> "SolverInferenceSession":
        return self

    def add_system_message(self, message: str) -> None:
        self.messages.append({"role": "system", "content": message})

    def run_task(self, task: str) -> str:
        if self.agent:
            raise NotImplementedError()
            # output = ""
            # messages = self.client.threads_list_messages(self.run.thread_id)
            # for m in messages:
            #     if m.role == "assistant":
            #         output += m.content
            # return output
        else:
            self.messages.append({"role": "user", "content": task})
            completion_response = cast(
                ModelResponse,
                self.client.completions(
                    model=self.model_full_path,
                    messages=self.messages,
                    temperature=0.0,
                ),
            )
            response_content = str(cast(List[Choices], completion_response.choices)[0].message.content)
            self.messages.append({"role": "assistant", "content": response_content})
            return response_content


class SolverStrategy(ABC, metaclass=SolverStrategyMeta):
    """Abstract class for solver strategies."""

    def __init__(self, model: str = "", agent: str = "") -> None:
        CONFIG.confirm_commands = False
        client_config = ClientConfig(base_url=CONFIG.nearai_hub.base_url, auth=CONFIG.auth)
        self.client = InferenceClient(client_config)
        assert model != "" or agent != ""

        self.provider = ""
        self.model_namespace = ""
        self.model_full_path = ""
        self.model_name = ""
        if model != "":
            self.provider, self.model_full_path = self.client.provider_models.match_provider_model(model)
            self.provider, namespaced_model = get_provider_namespaced_model(self.model_full_path, self.provider)
            self.model_namespace = namespaced_model.namespace
            self.model_name = namespaced_model.name

        self.agent_obj = None
        if agent != "":
            self.agent_obj = Agent.load_agent(agent, client_config)

            self.agent_obj.model_temperature = 0.0
            if self.model_full_path != "":
                self.agent_obj.model = self.model_full_path
            if self.provider != "":
                self.agent_obj.model_provider = self.provider

    @property
    def name(self) -> str:
        """Returns the name of the solver strategy."""
        return type(self).__name__

    @SolverStrategyClassProperty
    def scoring_method(self) -> SolverScoringMethod:
        return SolverScoringMethod.TrueOrFalseList

    @abstractmethod
    def evaluation_name(self) -> str:
        """Returns a unique name for (benchmark, solver) tuple, e.g. 'mbpp' or 'live_bench' or 'mmlu-5-shot'."""
        ...

    @abstractmethod
    def compatible_datasets(self) -> List[str]:
        """Returns the list of datasets that the solver strategy is compatible with."""
        ...

    def model_metadata(self) -> Optional[Dict[str, Any]]:
        """Returns model metadata that is evaluated or used by an agent."""
        if self.model_name != "":
            return {"name": self.model_name}
        return {"name": cast(Agent, self.agent_obj).model}

    def agent_metadata(self) -> Optional[Dict[str, Any]]:
        """Returns agent metadata that is evaluated."""
        if self.agent_obj:
            return cast(Agent, self.agent_obj).metadata
        return None

    def evaluated_entry_namespace(self) -> str:
        """Returns namespace of a model or agent to be evaluated."""
        if self.agent_obj:
            return self.agent_obj.namespace
        return self.model_namespace

    def model_provider(self) -> str:
        """Returns model provider."""
        if self.provider != "":
            return self.provider
        return cast(Agent, self.agent_obj).model_provider

    @abstractmethod
    def solve(self, datum: dict) -> Union[bool, Tuple[bool, Any]]:
        """Solves the task for the given datum."""
        ...

    def get_custom_tasks(self) -> List[dict]:
        """Custom tasks for custom benchmark."""
        if self.scoring_method == SolverScoringMethod.Custom:
            raise NotImplementedError("get_custom_tasks must be implemented for Custom scoring method")
        else:
            raise AttributeError("get_custom_tasks is only applicable for Custom scoring method")

    def get_evaluation_metrics(self, tasks_results: List[Tuple[bool, Any]]) -> Dict[str, Any]:
        """Given results for all datums, returns evaluation metrics.

        Not used by TrueOrFalseList scoring method.
        Do not prepend with evaluation_name. If hierarchical, use slashes /.
        Expected metrics is a dict of scores, e.g.: {"average": <val>, "group/coding": <val>}.
        """
        raise NotImplementedError("get_evaluation_metrics not implemented")

    def start_inference_session(self, task_id: str) -> SolverInferenceSession:
        return SolverInferenceSession(
            self.agent_obj, self.model_full_path, self.client, self.evaluation_name()
        ).start_inference_session(task_id)


SolverStrategyRegistry: Dict[str, SolverStrategy] = {}

from nearai.solvers.ddot_v0_solver import DDOTSV0Solver  # noqa: E402
from nearai.solvers.gsm8k_solver import GSM8KSolverStrategy  # noqa: E402
from nearai.solvers.hellaswag_solver import HellaswagSolverStrategy  # noqa: E402
from nearai.solvers.livebench_solver import LiveBenchSolverStrategy  # noqa: E402
from nearai.solvers.mbpp_solver import MBPPSolverStrategy  # noqa: E402
from nearai.solvers.mmlu_solver import MMLUSolverStrategy  # noqa: E402

__all__ = [
    "SolverStrategyRegistry",
    "DDOTSV0Solver",
    "MBPPSolverStrategy",
    "MMLUSolverStrategy",
    "HellaswagSolverStrategy",
    "LiveBenchSolverStrategy",
    "GSM8KSolverStrategy",
]
