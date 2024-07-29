import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(base_url="http://127.0.0.1:8081/v1", api_key=os.getenv("ROUTER_API_KEY"))

response = client.completions.create(
    max_tokens=32,
    prompt="You are a brown fox, ",
    model="accounts/fireworks/models/mixtral-8x22b-instruct",
    frequency_penalty=0.1,
    n=1,
    stream=True,
)
for chunk in response:
    print(chunk)
    print("****************")

response2 = client.completions.create(
    max_tokens=32,
    prompt="You are a brown fox, ",
    model="accounts/fireworks/models/mixtral-8x22b-instruct",
    frequency_penalty=0.1,
    n=1,
)

print(response2)

r = client.chat.completions.create(
    messages=[
        {"role": "system", "content": "You are an AI assistant."},
        {"role": "user", "content": "My name is Y"},
        {"role": "assistant", "content": "Nice to meet you, Y."},
        {"role": "user", "content": "What is my name?"},
    ],
    model="accounts/fireworks/models/llama-v3-70b-instruct",
    max_tokens=256,
    frequency_penalty=0.1,
    temperature=0.1,
)

print(r)


response3 = client.chat.completions.create(
    messages=[
        {"role": "system", "content": "You are an AI assistant."},
        {"role": "user", "content": "My name is Y"},
        {"role": "assistant", "content": "Nice to meet you, Y."},
        {"role": "user", "content": "What is my name?"},
    ],
    model="accounts/fireworks/models/llama-v3-70b-instruct",
    max_tokens=256,
    frequency_penalty=0.1,
    temperature=0.1,
    stream=True,
)

for completion_chunk in response3:
    print(completion_chunk)
    print("****************")
