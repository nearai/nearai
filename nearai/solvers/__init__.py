from abc import ABC, ABCMeta, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from litellm import Choices, ModelResponse
from litellm.types.completion import ChatCompletionMessageParam

from nearai.agents.agent import Agent
from nearai.aws_runner.service import EnvironmentRun, start_with_environment
from nearai.config import CONFIG, get_hub_client
from nearai.shared.inference_client import InferenceClient
from nearai.shared.provider_models import get_provider_namespaced_model


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
    def __init__(self, agent, agent_params, model_full_path, client: InferenceClient, evaluation_name):
        self.agent = agent
        self.agent_params = agent_params
        self.model_full_path = model_full_path
        self.client = client
        self.evaluation_name = evaluation_name
        self.messages: List[ChatCompletionMessageParam] = []
        self.hub_client = get_hub_client()
        self.env_run: Optional[EnvironmentRun] = None

    def start_inference_session(self, task_id: str) -> "SolverInferenceSession":
        if self.agent:
            thread = self.hub_client.beta.threads.create()
            run = self.hub_client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.agent,
                extra_body={"delegate_execution": True},
            )
            auth = CONFIG.auth
            assert auth
            self.env_run = start_with_environment(
                self.agent,
                auth,
                thread.id,
                run.id,
                additional_path=self.agent,
                params=self.agent_params,
                print_system_log=False,
            )
            # Set an inference client with a cli client config.
            # This is needed to pass num_inference_retries.
            self.env_run.env.client = self.client
        return self

    def add_system_message(self, message: str) -> None:
        if self.agent:
            raise NotImplementedError("system messages for agent are not supported")
        self.messages.append({"role": "system", "content": message})

    def run_task(self, task: str) -> str:
        try:
            if self.agent:
                assert self.env_run
                self.env_run.run(task)
                message = self.env_run.env.get_last_message(role="assistant")
                return message.get("content") if message else ""
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
        except Exception as e:
            print(f"Error: {e}")
            return f"{e}"


class SolverStrategy(ABC, metaclass=SolverStrategyMeta):
    """Abstract class for solver strategies."""

    def __init__(self, model: str = "", agent: str = "") -> None:
        CONFIG.confirm_commands = False
        self.client_config = CONFIG.get_client_config()
        self.client = InferenceClient(self.client_config)
        assert model != "" or agent != ""
        self.dataset_evaluation_name = ""

        self.provider = ""
        self.model_namespace = ""
        self.model_full_path = ""
        self.model_name = ""
        if model != "":
            self.provider, self.model_full_path = self.client.provider_models.match_provider_model(model)
            self.provider, namespaced_model = get_provider_namespaced_model(self.model_full_path, self.provider)
            self.model_namespace = namespaced_model.namespace
            self.model_name = namespaced_model.name

        # If provider specified is a url, recreate a `client`.
        if self.provider.startswith("https://"):
            self.client_config.base_url = self.provider
            self.client_config.auth = None
            self.client_config.default_provider = self.provider
            print(self.client_config)
            self.client = InferenceClient(self.client_config)

        self.agent = agent
        self.agent_params = {
            "api_url": CONFIG.api_url,
            "data_source": "local_files",
            "temperature": 0.0,
            "record_run": False,
            "verbose": False,
            "change_to_agent_temp_dir": False,
        }
        if self.model_full_path:
            self.agent_params["model"] = self.model_full_path

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

    def agent_name(self) -> str:
        """Returns agent name that is evaluated."""
        if not self.agent:
            return ""
        path = Path(self.agent)
        return path.parent.name

    def agent_version(self) -> str:
        """Returns agent name that is evaluated."""
        if not self.agent:
            return ""
        path = Path(self.agent)
        return path.name

    def evaluated_entry_namespace(self) -> str:
        """Returns namespace of a model or agent to be evaluated."""
        if self.agent:
            path = Path(self.agent)
            return path.parent.parent.name
        return self.model_namespace

    def model_provider(self) -> str:
        """Returns model provider."""
        if self.provider != "":
            return self.provider
        if self.agent != "":
            agent_obj = Agent.load_agent(self.agent, self.client_config, local=True)
            return agent_obj.model_provider
        return ""

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
            self.agent, self.agent_params, self.model_full_path, self.client, self.evaluation_name()
        ).start_inference_session(task_id)


SolverStrategyRegistry: Dict[str, SolverStrategy] = {}

from nearai.solvers.ddot_v0_solver import DDOTSV0Solver  # noqa: E402
from nearai.solvers.gsm8k_solver import GSM8KSolverStrategy  # noqa: E402
from nearai.solvers.hellaswag_solver import HellaswagSolverStrategy  # noqa: E402
from nearai.solvers.livebench_solver import LiveBenchSolverStrategy  # noqa: E402
from nearai.solvers.mbpp_solver import MBPPSolverStrategy  # noqa: E402
from nearai.solvers.mmlu_solver import MMLUSolverStrategy  # noqa: E402

__all__ = [
    "DDOTSV0Solver",
    "GSM8KSolverStrategy",
    "HellaswagSolverStrategy",
    "LeanSolverStrategy",
    "LiveBenchSolverStrategy",
    "MBPPSolverStrategy",
    "MMLUSolverStrategy",
    "SolverStrategyRegistry",
]

try:
    from nearai.solvers.lean_solver import LeanSolverStrategy  # noqa: E402

    __all__.append("LeanSolverStrategy")
except ImportError:
    LeanSolverStrategy = None  # type: ignore
