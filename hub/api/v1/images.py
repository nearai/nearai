import base64
import io
import os
import time
from typing import Optional, Protocol

import requests
from fireworks.client.image import Answer, ImageInference


class ImageGenerator(Protocol):
    def generate(self, **kwargs) -> dict:
        """Generates images."""
        ...


class FireworksImageGenerator:
    def __init__(self):
        """Initializes the Fireworks image generator."""
        api_key = os.environ.get("FIREWORKS_API_KEY")
        if not api_key:
            raise ValueError("FIREWORKS_API_KEY environment variable is not set")
        self.inference_client = ImageInference(model="playground-v2-1024px-aesthetic")
        self.api_key = api_key

    def _decode_image(self, base64_image: str) -> io.BytesIO:
        image_buffer = io.BytesIO(base64.b64decode(base64_image))
        image_buffer.seek(0)
        return image_buffer

    def _is_workflow_model(self, model: str) -> bool:
        """Detect whether the model should use Fireworks workflows (polling) API.

        Currently supports Flux family and Kontext variants that require polling.
        """
        # Explicit allowlist from TODO with a broader guard for future variants
        allowlist = (
            # "accounts/fireworks/models/flux-1-dev-fp8",  # FIXME: not found
            "accounts/fireworks/models/flux-kontext-max",
            "accounts/fireworks/models/flux-1-schnell-fp8",
            "accounts/fireworks/models/flux-kontext-pro",
        )
        return model in allowlist or ("flux" in model or "kontext" in model)

    def _get_workflow_url(self, model: str, is_i2i: bool) -> str:
        """Return the correct workflow URL for a given model and mode.

        Some Flux variants require a sub-route:
        - text-only:   /text_to_image
        - image-to-image (init/control): /image_to_image
        Kontext models use the base workflow path.
        """
        base = f"https://api.fireworks.ai/inference/v1/workflows/{model}"
        if "flux-1-schnell" in model or "flux-1-dev-fp8" in model:
            return base + ("/image_to_image" if is_i2i else "/text_to_image")
        return base

    def _submit_workflow(self, model: str, payload: dict, is_i2i: bool) -> tuple[str, str]:
        """Submit a workflow request and return (base_url, request_id)."""
        # Base model workflow URL (used for polling)
        base_url = f"https://api.fireworks.ai/inference/v1/workflows/{model}"
        # Some Flux variants require sub-routes for submission
        if "flux-1-schnell" in model or "flux-1-dev-fp8" in model:
            submit_url = base_url + ("/image_to_image" if is_i2i else "/text_to_image")
        else:
            submit_url = base_url
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        # For most workflow models (e.g., kontext), request JSON; for special flux endpoints, omit Accept
        if not ("flux-1-schnell" in model or "flux-1-dev-fp8" in model):
            headers["Accept"] = "application/json"
        resp = requests.post(submit_url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        request_id = data.get("request_id") or data.get("id")
        if not request_id:
            raise RuntimeError(f"No request_id in workflow submission response: {data}")
        # Return base model URL for polling
        return base_url, request_id

    def _poll_workflow(self, base_url: str, request_id: str, timeout_seconds: int = 60) -> bytes:
        """Poll a workflow result endpoint until completion or timeout. Returns JPEG bytes."""
        result_endpoint = f"{base_url}/get_result"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        deadline = time.time() + timeout_seconds
        attempt = 0
        while time.time() < deadline:
            attempt += 1
            time.sleep(1)
            r = requests.post(result_endpoint, headers=headers, json={"id": request_id}, timeout=60)
            # Allow non-2xx to propagate meaningfully
            r.raise_for_status()
            try:
                result = r.json()
            except Exception:
                # If server returned raw bytes (e.g., image/jpeg), just use them
                return r.content

            status = (result.get("status") or result.get("state") or "").lower()
            if status in {"ready", "complete", "finished", "succeeded", "success"}:
                # Fireworks may return a direct sample (base64 or URL) in various shapes
                out = result.get("result") or {}
                sample = out.get("sample") or out.get("image") or (out.get("samples") or [None])[0] or out.get("output")

                if isinstance(sample, str):
                    if sample.startswith("http"):
                        img_resp = requests.get(sample, timeout=60)
                        img_resp.raise_for_status()
                        return img_resp.content
                    if sample.startswith("data:image") and "," in sample:
                        b64 = sample.split(",", 1)[1]
                        return base64.b64decode(b64)
                    # Assume base64
                    try:
                        return base64.b64decode(sample)
                    except Exception:
                        # Some APIs may return JSON with bytes field; fallback
                        pass

                # If still no luck, try known keys for raw bytes
                if isinstance(out, dict):
                    maybe_b64 = out.get("b64") or out.get("b64_json")
                    if isinstance(maybe_b64, str):
                        return base64.b64decode(maybe_b64)

                raise RuntimeError(f"Workflow completed but no image found in response: {result}")

            if status in {"failed", "error"}:
                details = result.get("details") or result
                raise RuntimeError(f"Image generation failed: {details}")

        raise TimeoutError("Timed out waiting for image generation result")

    def generate(self, **kwargs) -> dict:
        """Generate images using the Fireworks API.

        Args:
        ----
            **kwargs: Additional keyword arguments.

        Returns:
        -------
            dict: The response from the Fireworks API.

        """
        if kwargs.get("model"):
            # model arrives without provider prefix, e.g. "accounts/fireworks/models/<model_name>"
            model = kwargs.get("model", "")
            # For playground models, use the SDK client; for flux/kontext, use workflows with polling
            if self._is_workflow_model(model):
                # Build payload strictly from user-specified fields (no defaults)
                def to_data_url(img_b64: Optional[str]) -> Optional[str]:
                    if not img_b64:
                        return None
                    return img_b64 if img_b64.startswith("data:image") else f"data:image/jpeg;base64,{img_b64}"

                payload: dict = {}
                for k, v in kwargs.items():
                    if v is None:
                        continue
                    if k in ("model", "provider", "timeout"):
                        # handled elsewhere or internal-only
                        continue
                    if k == "init_image":
                        data_url = to_data_url(str(v))
                        if data_url:
                            payload["input_image"] = data_url
                        continue
                    if k == "control_image":
                        data_url = to_data_url(str(v))
                        if data_url:
                            payload["control_image"] = data_url
                        continue
                    # pass-through all other fields as-is (e.g., prompt, steps, cfg_scale, etc.)
                    payload[k] = v

                # For certain Flux endpoints, only allow prompt and optional images
                if ("flux-1-dev-fp8" in model) or ("flux-1-schnell" in model):
                    allowed_keys = {"prompt", "input_image", "control_image"}
                    payload = {k: v for k, v in payload.items() if k in allowed_keys}

                try:
                    is_i2i = bool(payload.get("input_image") or payload.get("control_image"))
                    base_url, request_id = self._submit_workflow(model, payload, is_i2i)
                    img_bytes = self._poll_workflow(base_url, request_id, timeout_seconds=kwargs.get("timeout", 60))
                    img_str = base64.b64encode(img_bytes).decode()
                    return {
                        "data": [
                            {
                                "b64_json": img_str,
                                "url": None,
                                "revised_prompt": None,
                            }
                        ]
                    }
                except Exception as e:
                    raise RuntimeError(f"Image generation failed: {str(e)}") from e

            # Otherwise, fall back to non-workflow image inference (playground family)
            playground_model = model.split("/")[-1]
            self.inference_client = ImageInference(model=playground_model)

        # Build SDK params from only user-specified fields by default.
        whitelisted_keys = [
            "prompt",
            "init_image",
            "image_strength",
            "cfg_scale",
            "height",
            "width",
            "sampler",
            "steps",
            "seed",
            "safety_check",
            "output_image_format",
            "control_image",
            "control_net_name",
            "conditioning_scale",
        ]
        fireworks_params = {k: kwargs[k] for k in whitelisted_keys if k in kwargs and kwargs[k] is not None}

        # Only for the default playground aesthetic models, fill in defaults when not provided.
        default_playground_models = {
            "playground-v2-1024px-aesthetic",
            "playground-v2-5-1024px-aesthetic",
        }
        if playground_model in default_playground_models:
            fireworks_params.setdefault("cfg_scale", 7.0)
            fireworks_params.setdefault("height", 1024)
            fireworks_params.setdefault("width", 1024)
            fireworks_params.setdefault("steps", 30)
            fireworks_params.setdefault("safety_check", False)
            fireworks_params.setdefault("output_image_format", "JPG")

        try:
            answer: Answer
            if fireworks_params.get("init_image") is not None:
                # run image to image if init_image is found
                # decode the init_image (fireworks expects bytes, PIL or a file -- not base64)
                base64_image = str(fireworks_params.get("init_image"))
                init_image = self._decode_image(base64_image)
                fireworks_params.update({"init_image": init_image})

                # For default playground models only, set a sensible default image_strength for i2i
                if playground_model in default_playground_models and fireworks_params.get("image_strength") is None:
                    fireworks_params.update({"image_strength": 0.7})

                # also check if control_image is received
                if fireworks_params.get("control_image") is not None:
                    base64_image = str(fireworks_params.get("control_image"))
                    control_image = self._decode_image(base64_image)
                    fireworks_params.update({"control_image": control_image})

                answer = self.inference_client.image_to_image(**fireworks_params)
            else:
                answer = self.inference_client.text_to_image(**fireworks_params)
            if answer.image is None:
                raise RuntimeError(f"No return image, {answer.finish_reason}")

            buffered = io.BytesIO()
            answer.image.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

            return {
                "data": [
                    {
                        "b64_json": img_str,
                        "url": None,
                        "revised_prompt": None,
                    }
                ]
            }
        except Exception as e:
            raise RuntimeError(f"Image generation failed: {str(e)}") from e


def get_images_ai(provider: str) -> ImageGenerator:
    if provider == "fireworks":
        return FireworksImageGenerator()
    raise NotImplementedError(f"Provider {provider} not supported")
