import openai
import json
import nearai
import base64

# Load NEAR AI Hub configuration
config = nearai.config.load_config_file()
base_url = config.get("api_url", "https://api.near.ai/") + "v1"
auth = config["auth"]

client = openai.OpenAI(base_url=base_url, api_key=json.dumps(auth))


# Generate images
response = client.images.generate(
    prompt="A serene forest landscape with a misty lake at sunrise.",
    n=2,
    size="1024x1024",
    response_format="b64_json",
    model="fireworks::accounts/fireworks/models/playground-v2-5-1024px-aesthetic",
)


image_data = json.loads(response.model_dump_json())
base64_image = image_data['data'][0]['b64_json']

# Decode the base64 string and save it as an image file
image_bytes = base64.b64decode(base64_image)
with open('generated_image.jpg', 'wb') as f:
    f.write(image_bytes)

print("Image generated and saved as 'generated_image.jpg'")
