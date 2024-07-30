from random import randint

from openai import OpenAI

client = OpenAI(
    base_url="http://ai.nearspace.info/chat/api/v1",
    api_key="token-abc123",
)

for models in client.models.list():
    print(models)

hard_sum = []

for _ in range(3):
    x = randint(1, 3)
    y = randint(1, 3)
    t = int("1" + "0" * x + "1" + "0" * y)
    a = randint(1, t - 1)
    b = t - a
    hard_sum.append(f"What is the sum of {a} and {b}?")

questions = [
    f"What is the sum of {randint(1, 100)} and {randint(1, 100)}?",
    f"What is the product of {randint(1, 10)} times {randint(1, 10)}?",
    *hard_sum,
    "What are the best three cities on the north of Africa to host a hackathon for a small team?",
]

for question in questions:
    print()
    print()
    print("===================================")
    print(question)
    print("===================================")

    completion = client.chat.completions.create(
        model="/home/setup/.nearai/models/llama-3-8b-instruct/",
        messages=[
            {
                "role": "user",
                "content": question,
            }
        ],
        max_tokens=2048,
        stop=["<|eot_id|>"],
    )

    print(completion.choices[0].message.content)
