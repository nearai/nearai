import openai

hub_url = "https://inference-api.phala.network/v1"


client = openai.OpenAI(base_url=hub_url, api_key="-")

# create a chat completion
chat_completion = client.chat.completions.create(
    model="meta-llama/meta-llama-3.1-8b-instruct",
    messages=[{"role": "user", "content": "Hello, world!"}],
)
print(chat_completion)
