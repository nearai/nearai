import os
from functools import cached_property
from typing import Any, Dict, List, Optional

from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_openai import ChatOpenAI
from pydantic import Field

from nearai.shared.client_config import ClientConfig
from nearai.shared.provider_models import ProviderModels


class LangchainChatModel(BaseChatModel):
    """NEAR AI chat model adapter for Langchain BaseChatModel interface."""

    metadata_provider: str = Field(default="")
    metadata_model: str = Field(default="")

    # TODO(#796): don't expose this data to agent
    config: ClientConfig = Field(exclude=True)
    auth: str = Field(default="", exclude=True)

    @cached_property
    def provider_models(self) -> ProviderModels:  # noqa: D102
        return ProviderModels(self.config)

    @cached_property
    def inference_model(self) -> str:
        """Returns 'provider::model_full_path'."""
        _, model_for_inference = self.provider_models.match_provider_model(self.metadata_model, self.metadata_provider)
        return model_for_inference

    @cached_property
    def chat_open_ai_model(self) -> ChatOpenAI:  # noqa: D102
        os.environ["OPENAI_API_KEY"] = self.auth
        return ChatOpenAI(model=self.inference_model, base_url=self.config.base_url)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate chat model outputs."""
        return self.chat_open_ai_model._generate(messages=messages, stop=stop, run_manager=run_manager, **kwargs)

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Asynchronously generate chat model outputs."""
        return await self.chat_open_ai_model._agenerate(messages=messages, stop=stop, run_manager=run_manager, **kwargs)

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Get the identifying parameters."""
        return {
            "metadata_provider": self.metadata_provider,
            "metadata_model": self.metadata_model,
        }

    @property
    def _llm_type(self) -> str:
        """Get the type of LLM."""
        return "nearai-chat"
