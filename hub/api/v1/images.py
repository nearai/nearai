import os
from typing import Protocol

from fireworks.client.image import Answer, ImageInference


class ImageGenerator(Protocol):
    def generate(self, **kwargs) -> dict:
        """Generates images"""
        ...


class FireworksImageGenerator:
    def __init__(self):
        """Initializes the Fireworks image generator."""
        api_key = os.environ.get("FIREWORKS_API_KEY")
        if not api_key:
            raise ValueError("FIREWORKS_API_KEY environment variable is not set")
        self.inference_client = ImageInference(model="playground-v2-1024px-aesthetic")

    def generate(self, **kwargs) -> dict:
        """Generate images using the Fireworks API.

        Args:
        ----
            **kwargs: Additional keyword arguments.

        Returns:
        -------
            dict: The response from the Fireworks API.

        """
        fireworks_params = {
            "prompt": kwargs.get("prompt"),
            "cfg_scale": kwargs.get("cfg_scale", 7.0),
            "height": kwargs.get("height", 1024),
            "width": kwargs.get("width", 1024),
            "sampler": kwargs.get("sampler"),
            "steps": kwargs.get("steps", 30),
            "seed": kwargs.get("seed"),
            "safety_check": kwargs.get("safety_check", False),
            "output_image_format": "JPG",
        }
        fireworks_params = {k: v for k, v in fireworks_params.items() if v is not None}

        try:
            answer: Answer = self.inference_client.text_to_image(**fireworks_params)
            if answer.image is None:
                raise RuntimeError(f"No return image, {answer.finish_reason}")

            import base64
            import io

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
