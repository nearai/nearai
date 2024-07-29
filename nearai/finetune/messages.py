from typing import Any, Dict, List, Mapping, Optional

import numpy as np
from datasets import load_from_disk  # type: ignore
from torchtune.data import CROSS_ENTROPY_IGNORE_IDX, Message
from torchtune.modules.tokenizers import Tokenizer

from nearai.finetune.text_completion import TextCompletionDataset, truncate


class MessagesDataset(TextCompletionDataset):
    def __init__(self, tokenizer: Tokenizer, source: str, max_seq_len: Optional[int] = None) -> None:  # noqa: D107
        self._tokenizer = tokenizer
        self._data = load_from_disk(source)
        self.max_seq_len = max_seq_len

    def _prepare_sample(self, sample: Mapping[str, Any]) -> Dict[str, List[int]]:
        messages = [Message(role=message["role"], content=message["content"]) for message in sample["messages"]]
        tokens, mask = self._tokenizer.tokenize_messages(messages, max_seq_len=self.max_seq_len)

        if self.max_seq_len is not None:
            tokens = truncate(tokens, self.max_seq_len - 1)
            mask = truncate(mask, self.max_seq_len - 1)

        labels = list(np.where(mask, CROSS_ENTROPY_IGNORE_IDX, tokens))
        assert len(tokens) == len(labels)
        return {"tokens": tokens, "labels": labels}


def dataset(
    tokenizer: Tokenizer,
    source: str,
    max_seq_len: Optional[int] = None,
    **load_from_disk_kwargs: Dict[str, Any],
) -> MessagesDataset:
    return MessagesDataset(tokenizer=tokenizer, source=source, max_seq_len=max_seq_len)
