import base64
import io
import os
from typing import Protocol

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

    def _decode_image(self, base64_image: str) -> io.BytesIO:
        image_buffer = io.BytesIO(base64.b64decode(base64_image))
        image_buffer.seek(0)
        return image_buffer

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
            "init_image": kwargs.get("init_image"),
            "image_strength": kwargs.get("image_strength"),
            "cfg_scale": kwargs.get("cfg_scale", 7.0),
            "height": kwargs.get("height", 1024),
            "width": kwargs.get("width", 1024),
            "sampler": kwargs.get("sampler"),
            "steps": kwargs.get("steps", 30),
            "seed": kwargs.get("seed"),
            "safety_check": kwargs.get("safety_check", False),
            "output_image_format": "JPG",
            "control_image": kwargs.get("control_image"),
            "control_net_name": kwargs.get("control_net_name"),
            "conditioning_scale": kwargs.get("conditioning_scale"),
        }

        fireworks_params = {k: v for k, v in fireworks_params.items() if v is not None}

        try:
            answer: Answer
            if kwargs.get("init_image"):
                # run image to image if init_image is found
                # decode the init_image (fireworks expects bytes, PIL or a file -- not base64)
                base64_image = str(kwargs.get("init_image"))
                init_image = self._decode_image(base64_image)
                fireworks_params.update({"init_image": init_image})

                # set the image strength to 0.7 if it is not provided
                if kwargs.get("image_strength") is None:
                    fireworks_params.update({"image_strength": 0.7})

                # also check if control_image is received
                if kwargs.get("control_image"):
                    base64_image = str(kwargs.get("control_image"))
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
