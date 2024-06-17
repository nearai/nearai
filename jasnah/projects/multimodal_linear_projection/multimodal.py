from dataclasses import dataclass, field
from typing import List, Optional, Union

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from transformers import AutoTokenizer
from transformers.models.llama import LlamaConfig, LlamaForCausalLM
from transformers.tokenization_utils_base import PreTrainedTokenizerBase

PATCH_SIZE = 16
CHANNELS = 3


class LlamaMultimodalModel(LlamaForCausalLM):
    config: LlamaConfig

    def __init__(self, config: LlamaConfig):
        super().__init__(config)
        self.image_projection = torch.nn.Linear(CHANNELS * PATCH_SIZE**2, config.hidden_size)

    def freeze_lang_model(self):
        for param in self.model.parameters():
            param.requires_grad = False
        for param in self.lm_head.parameters():
            param.requires_grad = False

    def forward(
        self,
        n_ctx: int,
        tokens: torch.LongTensor,
        patches: torch.FloatTensor,
        tokens_pos: torch.LongTensor,
        patches_pos: torch.LongTensor,
        attention_mask: Optional[torch.Tensor] = None,
    ):
        batch_size = tokens.shape[0]

        embeds = torch.zeros((batch_size, n_ctx + 1, self.config.hidden_size), device=self.device, dtype=torch.bfloat16)

        if tokens_pos.numel() != 0:
            token_embeds: torch.FloatTensor = self.model.embed_tokens(tokens)
            embeds.scatter_add_(
                1,
                tokens_pos.unsqueeze(-1).expand(-1, -1, token_embeds.shape[-1]),
                token_embeds,
            )

        if patches_pos.numel() != 0:
            patch_embeds: torch.FloatTensor = self.image_projection(patches)
            embeds.scatter_add_(
                1,
                patches_pos.unsqueeze(-1).expand(-1, -1, patch_embeds.shape[-1]),
                patch_embeds,
            )

        embeds = embeds[:, :-1, :]

        return super().forward(inputs_embeds=embeds, attention_mask=attention_mask)


@dataclass
class ImageDescription:
    file_path: Optional[str] = None
    pil_image: Optional[Image.Image] = None

    def load(self) -> Image.Image:
        if self.file_path is not None:
            return Image.open(self.file_path).convert("RGB")
        elif self.pil_image is not None:
            return self.pil_image
        else:
            raise ValueError("No image source specified")


class ImageTokenizer:
    def encode(self, image_d: ImageDescription) -> torch.FloatTensor:
        pil_image = image_d.load()
        pil_image = pil_image.resize((pil_image.width // 4, pil_image.height // 4))

        image = torch.tensor(np.array(pil_image, dtype=np.float32) / 255.0)

        if len(image.shape) == 2:
            image = image.unsqueeze(2).expand(-1, -1, 3)

        image = image.permute(2, 0, 1)

        if image.shape[0] == 4:
            # TODO: Make sure we are removing the alpha channel correctly
            image = image[:3]

        C, H, W = image.shape

        # Calculate required padding
        pad_height = (PATCH_SIZE - H % PATCH_SIZE) % PATCH_SIZE
        pad_width = (PATCH_SIZE - W % PATCH_SIZE) % PATCH_SIZE

        # Pad the image
        # Here padding is applied symmetrically, but you can adjust it as needed
        padded_image = F.pad(
            image,
            (
                pad_width // 2,
                pad_width - pad_width // 2,
                pad_height // 2,
                pad_height - pad_height // 2,
            ),
            mode="constant",
            value=0,
        )

        # Unfold the image into patches
        # Unfold dimension 1 (height)
        patches = padded_image.unfold(1, PATCH_SIZE, PATCH_SIZE)
        # Unfold dimension 2 (width), after unfolding the height
        patches = patches.unfold(2, PATCH_SIZE, PATCH_SIZE)

        patches = patches.permute(1, 2, 0, 3, 4).contiguous()
        return patches


@dataclass
class MultimodalInput:
    ctx: int = 0
    tokens: List[int] = field(default_factory=list)
    tokens_pos: List[int] = field(default_factory=list)
    patches: List[torch.FloatTensor] = field(default_factory=list)
    patches_pos: List[int] = field(default_factory=list)
    weight: List[float] = field(default_factory=list)
    label: List[int] = field(default_factory=list)
    eos_id: int = 0

    def _get_pos(self, size):
        pos = list(range(self.ctx, self.ctx + size))
        self.ctx += size
        return pos

    def _add_labels(self, labels: List[int], encode_only: bool):
        assert isinstance(encode_only, bool)
        weight = 0.0 if encode_only else 1.0

        if self.label:
            self.label[-1] = labels[0]
            self.weight[-1] = weight

        self.label += labels[1:] + [self.eos_id]
        self.weight += [weight] * len(labels)

    def add_text(self, tokens: List[int], encode_only: bool = False):
        self.tokens += tokens
        self.tokens_pos += self._get_pos(len(tokens))
        self._add_labels(tokens, encode_only)

    def add_patches(self, patches: torch.FloatTensor, separator: List[int]):
        h, w, *_ = patches.shape

        self.patches.append(patches.view(h * w, -1))
        self.tokens += separator * h

        before = self.ctx

        for _ in range(h):
            self.patches_pos += self._get_pos(w)
            self.tokens_pos += self._get_pos(len(separator))

        new_tokens = self.ctx - before
        self._add_labels([0] * new_tokens, encode_only=True)

    def get_tokens(self, size, n_ctx):
        assert len(self.tokens) == len(self.tokens_pos)
        assert size >= len(self.tokens)
        tokens = torch.zeros(size, dtype=torch.long)
        tokens[: len(self.tokens)] = torch.tensor(self.tokens)
        tokens_pos = torch.full((size,), n_ctx, dtype=torch.long)
        tokens_pos[: len(self.tokens_pos)] = torch.tensor(self.tokens_pos)
        return tokens, tokens_pos

    def get_patches(self, size, n_ctx):
        if not self.patches:
            patches = torch.zeros((size, 0), dtype=torch.float)
            patches_pos = torch.full((size,), n_ctx, dtype=torch.long)
            return patches, patches_pos

        patches = torch.cat(self.patches)
        assert patches.size(0) == len(self.patches_pos)
        assert size >= patches.size(0)
        patches_pos = torch.full((size,), n_ctx, dtype=torch.long)
        patches_pos[: len(self.patches_pos)] = torch.tensor(self.patches_pos)
        patches = F.pad(patches, (0, 0, 0, size - patches.size(0)), value=0)
        return patches, patches_pos

    def get_labels(self, size):
        assert size >= len(self.label)
        assert len(self.label) == len(self.weight)
        label = torch.zeros(size, dtype=torch.long)
        weight = torch.zeros(size, dtype=torch.float)
        label[: len(self.label)] = torch.tensor(self.label)
        weight[: len(self.weight)] = torch.tensor(self.weight)
        return label, weight


class EncodeOnly:
    """
    Objects wrapped in this class will be masked out during training.
    Loss will not be computed against them.
    """

    def __init__(self, inner):
        self.inner = inner


def encode_only(inner):
    return EncodeOnly(inner)


ItemType = Union[str, ImageDescription, EncodeOnly]


class MultimodalTokenizer:
    def __init__(
        self,
        text_tokenizer: PreTrainedTokenizerBase,
        img_tokenizer: ImageTokenizer,
        eos_id: int = 0,
    ):
        self.text_tokenizer = text_tokenizer
        self.img_tokenizer = img_tokenizer
        self.separator = self.text_tokenizer.encode("\n")
        self.eos_id = eos_id

    def get_item(self, item: ItemType):
        if isinstance(item, EncodeOnly):
            item, type_, kwargs = self.get_item(item.inner)
            kwargs["encode_only"] = True
            return item, type_, kwargs

        if isinstance(item, str):
            return self.text_tokenizer(item)["input_ids"], str, {}

        if isinstance(item, ImageDescription):
            return (
                self.img_tokenizer.encode(item),
                ImageDescription,
                {"separator": self.separator},
            )

        raise ValueError(f"Unknown type: {type(item)}")

    def encode(self, data: List[List[ItemType]], include_labels=False, context_size=None):
        inputs: List[MultimodalInput] = []

        for row in data:
            input = MultimodalInput(eos_id=self.eos_id)

            for item in row:
                item, type_, kwargs = self.get_item(item)

                if type_ is str:
                    input.add_text(item, **kwargs)
                elif type_ is ImageDescription:
                    input.add_patches(item, **kwargs)
                else:
                    raise ValueError(f"Unknown type: {type_}")

            inputs.append(input)

        # Prepare the input tensors
        n_ctx = max(i.ctx for i in inputs)

        if isinstance(context_size, int):
            assert context_size >= n_ctx
            n_ctx = context_size

        max_tokens = max(len(i.tokens) for i in inputs)
        max_patches = max(sum(p.size(0) for p in i.patches) for i in inputs)

        tokens = []
        tokens_pos = []
        patches = []
        patches_pos = []
        labels = []
        weights = []

        for i in inputs:
            i_tokens, i_tokens_pos = i.get_tokens(max_tokens, n_ctx)
            tokens.append(i_tokens)
            tokens_pos.append(i_tokens_pos)

            i_patches, i_patches_pos = i.get_patches(max_patches, n_ctx)
            patches.append(i_patches)
            patches_pos.append(i_patches_pos)

            if include_labels:
                i_label, i_weights = i.get_labels(n_ctx)
                labels.append(i_label)
                weights.append(i_weights)

        return_dict = {
            "n_ctx": n_ctx,
            "tokens": torch.stack(tokens),
            "patches": torch.stack(patches),
            "tokens_pos": torch.stack(tokens_pos),
            "patches_pos": torch.stack(patches_pos),
            "labels": torch.stack(labels),
            "weights": torch.stack(weights),
        }

        if include_labels:
            return_dict["labels"] = return_dict.pop("labels")
            return_dict["weights"] = return_dict.pop("weights")

        return return_dict


def test_reconstruct_image():
    img_tokenizer = ImageTokenizer()
    tokens = img_tokenizer.encode(ImageDescription("0.jpg"))
    w, h, _, _, _ = tokens.shape

    reconstructed = torch.zeros((3, w * PATCH_SIZE, h * PATCH_SIZE))
    for i in range(w):
        for j in range(h):
            reconstructed[
                :,
                i * PATCH_SIZE : (i + 1) * PATCH_SIZE,
                j * PATCH_SIZE : (j + 1) * PATCH_SIZE,
            ] = tokens[i, j]

    plt.imsave("r.jpg", reconstructed.permute(1, 2, 0).numpy())


MODEL_PATH = "/home/setup/.jasnah/models/llama-3-8b-instruct"


def test_next_token():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

    tokens = tokenizer.encode("The name of the wizard is Harry", return_tensors="pt")
    print(tokens)

    model: LlamaMultimodalModel = LlamaMultimodalModel.from_pretrained(MODEL_PATH)

    output = super(LlamaMultimodalModel, model).forward(tokens)
    print(output.loss)
    print(output.logits.shape)

    result = torch.topk(output.logits, 5)

    for i, t in enumerate(tokens[0]):
        print()
        print(i, f"<{tokenizer.decode([t])}>")
        for nt, nv in zip(result.indices[0, i], result.values[0, i]):
            print(f"- {repr(tokenizer.decode([nt]))} ({nv:.2f})")


def test_multimodal():
    text_tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    image_tokenizer = ImageTokenizer()
    tokenizer = MultimodalTokenizer(text_tokenizer, image_tokenizer)

    model_input = tokenizer.encode(
        [
            [
                "Describe the following image:",
                ImageDescription("0.jpg"),
                "The image shows",
            ],
            [
                "Describe the following image:",
                ImageDescription("1.jpg"),
                "The image shows",
            ],
        ],
    )

    print("context length:", model_input["n_ctx"])

    model = LlamaMultimodalModel.from_pretrained(MODEL_PATH, device_map="auto")
    # model.to("cuda")

    # model_input = {
    #     k: v if k == "n_ctx" else v.to("cuda") for k, v in model_input.items()
    # }

    output = model.forward(**model_input)

    last_logits = output.logits[:, -1, :]
    result = torch.topk(last_logits, 5)

    batch_size = last_logits.shape[0]
    for i in range(batch_size):
        print()
        for nt, nv in zip(result.indices[i], result.values[i]):
            print(f"- {repr(text_tokenizer.decode([nt]))} ({nv:.2f})")

    # print(output.loss)
    # print(output.logits.shape)


def test_include_labels():
    text_tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    image_tokenizer = ImageTokenizer()
    tokenizer = MultimodalTokenizer(text_tokenizer, image_tokenizer, eos_id=128001)

    model_input = tokenizer.encode(
        [
            [
                encode_only("Task description:"),
                "You should add two numbers",
                encode_only("Thinking step by step"),
                "I add the numbers in python",
            ],
        ],
        include_labels=True,
    )

    labels = model_input.pop("labels")
    weights = model_input.pop("weights")

    print(labels.shape)
    print(weights.shape)

    print(labels)
    print(weights)


def test_attention_mask():
    model = LlamaForCausalLM.from_pretrained(MODEL_PATH)

    tokens = torch.tensor([[0, 1, 2, 3], [0, 2, 1, 3]], dtype=torch.long)
    attention_mask = torch.tensor(
        [
            [
                [
                    [1, 0, 0, 0],
                    [1, 1, 1, 0],
                    [1, 1, 1, 0],
                    [1, 1, 1, 1],
                ]
            ],
            [
                [
                    [1, 0, 0, 0],
                    [1, 1, 1, 0],
                    [1, 1, 1, 0],
                    [1, 1, 1, 1],
                ]
            ],
        ],
        dtype=torch.float,
    )
    positions_ids = torch.tensor([[0, 1, 1, 2], [0, 1, 1, 2]], dtype=torch.long)

    output = model.forward(tokens, attention_mask=attention_mask, position_ids=positions_ids)
    print(output.logits)


if __name__ == "__main__":
    # test_next_token()
    # test_multimodal()
    # test_attention_mask()
    test_include_labels()
