# Use this script to create custom shell benchmark for ShellBenchmarkSolver.
# Data columns:
# - `input`: input task given to an agent.
# - `question`: the question in input; it's used by a solver to determine whether the question was answered,
#               and only if `response` is present.
# - `input_file`: a solver will add this file before running agent.
# - `input_file_content`: content of `input_file`.
# - `steps`: number of steps an agent is expected to take to solve this task.
# - `response`: expected response, if any.
# - `output_file`: expected output file, if any.
# - `output_file_content`: expected content of `output_file`.
#
# Run benchmark with --max_concurrent=1.

import random
from typing import List
from datasets import Dataset

def generate_dataset() -> List[dict]:
    data = []
    # 1  
    data.append({
        "input": "Create a file named 'hello.txt'.",
        "output_file": "hello.txt"
    })
    # 2
    data.append({
        "input": "Create a directory named 'test_dir', create a file named 'hello.txt' inside it",
        "steps": "2",
        "output_file": "test_dir/hello.txt"
    })
    # 3
    data.append({
        "input": "Create a directory named 'test_dir', create a file named 'hello.txt' inside it with the content 'Hello, World!'",
        "steps": "2",
        "output_file": "test_dir/hello.txt",
        "output_file_content": "Hello, World!"
    })
    # 4
    data.append({
        "input_file": "hello.txt",
        "input_file_content": "Hello, World!",
        "input": "There is a file 'hello.txt'. Read and return the content of the file. Respond only with the content of the file and nothing else.",
        "response": "Hello, World!"
    })
    # 5
    data.append({
        "input_file": "test_dir/hello.txt",
        "input_file_content": "Hello, World!",
        "input": "There is a directory 'test_dir', and a file 'hello.txt' inside it. Read and return the content of the file. Respond only with the content of the file and nothing else.",
        "response": "Hello, World!"
    })
    # 6
    data.append({
        "input": "What's the current date? You may take advantage of the system environment to determine that. Respond only with date and nothing else.",
        "question": "What's the current date?",
        "steps": "2",
        "response": "<date>"
    })
    # 7
    data.append({
        "input": "What's the current date? Respond only with date and nothing else.",
        "question": "What's the current date?",
        "steps": "2",
        "response": "<date>"
    })
    # 8
    data.append({
        "input": "What's the current day of the week? You may take advantage of the system environment to determine that. Respond only with day of the week and nothing else.",
        "question": "What's the current day of the week?",
        "steps": "2",
        "response": "<day_of_week>"
    })
    # 9
    data.append({
        "input": "What's the current day of the week? Respond only with day of the week and nothing else.",
        "question": "What's the current day of the week?",
        "steps": "2",
        "response": "<day_of_week>"
    })
    # 10
    data.append({
        "input": "What's the current UTC time hh:mm, 24h format? You may take advantage of the system environment to determine that. Respond only with time and nothing else.",
        "question": "What's the current UTC time hh:mm, 24h format?",
        "steps": "2",
        "response": "<utc_time>"
    })
    # 11
    data.append({
        "input": "What's the current UTC time hh:mm, 24h format? Respond only with time and nothing else.",
        "question": "What's the current UTC time hh:mm, 24h format?",
        "steps": "2",
        "response": "<utc_time>"
    })
    # 12
    data.append({
        "input": "What's the current local time hh:mm, 24h format? You may take advantage of the system environment to determine that. Respond only with time and nothing else.",
        "question": "What's the current local time hh:mm, 24h format?",
        "steps": "2",
        "response": "<local_time>"
    })
    # 13
    data.append({
        "input": "What's the current local time hh:mm, 24h format? Respond only with time and nothing else.",
        "question": "What's the current local time hh:mm, 24h format?",
        "steps": "2",
        "response": "<local_time>"
    })
    # 14
    data.append({
        "input": "Create a shell script that prints numbers from 1 to 5, one per line to a file 'five_numbers.txt'. Make it executable and run it.",
        "steps": "2",
        "output_file": "five_numbers.txt",
        "output_file_content": "1\n2\n3\n4\n5"
    })
    # 15
    random_value = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=8))
    data.append({
        "input": f"Set an environment variable named 'MY_VAR' with the value '{random_value}'. Then, create a shell script that prints the value of MY_VAR into 'my_sweet_recipe.yum', make it executable, and run it.",
        "steps": "3",
        "output_file": "my_sweet_recipe.yum",
        "output_file_content": random_value
    })
    # 16
    data.append({
        "input": "Create a Python script named 'factorial.py' that calculates the factorial of 5 and prints it into 'my_favorite_factorial.out'. Run the script.",
        "steps": "2",
        "output_file": "my_favorite_factorial.out",
        "output_file_content": "120"
    })
    # 17
    data.append({
        "input_file": "input.txt",
        "input_file_content": "7",
        "input": "Create a Python script named 'factorial.py' that reads single number from 'input.txt', calculates its factorial and prints it into 'my_favorite_factorial.out'. Run the script.",
        "steps": "3",
        "output_file": "my_favorite_factorial.out",
        "output_file_content": "5040"
    })
    # 18
    data.append({
        "input_file": "input.txt",
        "input_file_content": "apple banana cherry date elderberry",
        "input": "Create a program to count number of words in input.txt and output the count into 'out.txt'. Run it.",
        "steps": "3",
        "output_file": "out.txt",
        "output_file_content": "5"
    })

    # 19
    data.append({
        "input": "Create a directory named 'nested_dir' inside 'test_dir', then create an empty file named 'nested.txt' inside 'nested_dir'.",
        "steps": "2",
        "output_file": "test_dir/nested_dir/nested.txt"
    })
    # 20
    data.append({
        "input_file": "hello.txt",
        "input_file_content": "hello",
        "input": "Move the file 'hello.txt' from the current directory to the 'test_dir' directory.",
        "steps": "2",
        "output_file": "test_dir/hello.txt",
        "output_file_content": "hello"
    })
    # 21
    data.append({
        "input_file": "test_dir/hello.txt",
        "input_file_content": "hello",
        "input": "Copy the file 'hello.txt' from 'test_dir' to the current directory, naming the copy 'hello_copy.txt'",
        "output_file": "hello_copy.txt",
        "output_file_content": "hello",
    })
    # 22
    data.append({
        "input_file": "hello.txt",
        "input_file_content": "hello",
        "input": "Rename the file 'hello.txt' to 'greeting.txt'.",
        "output_file": "greeting.txt",
        "output_file_content": "hello",
    })
    # 23
    data.append({
        "input": "Create a file named 'numbers.txt' containing numbers from 1 to 10, one per line.",
        "output_file": "numbers.txt",
        "output_file_content": "1\n2\n3\n4\n5\n6\n7\n8\n9\n10"
    })

    # 24
    data.append({
        "input": "Sort the contents of 'numbers.txt' in reverse order and save the output to 'sorted_numbers.txt'.",
        "input_file": "numbers.txt",
        "input_file_content": "3\n2\n3\n5\n5\n6\n7\n8\n9\n10",
        "steps": "3",
        "output_file": "sorted_numbers.txt",
        "output_file_content": "10\n9\n8\n7\n6\n5\n5\n3\n3\n2"
    })
    # 25
    data.append({
        "input": "Sort the contents of 'numbers.txt' in ascending order and save the output to 'sorted_numbers.txt'.",
        "input_file": "numbers.txt",
        "input_file_content": "5 3 1 2 7 8 9",
        "steps": "3",
        "output_file": "sorted_numbers.txt",
        "output_file_content": "1 2 3 5 7 8 9"
    })

    return data

if __name__ == "__main__":
    data = generate_dataset()

    # Create a Hugging Face Dataset
    hf_dataset = Dataset.from_list([{
        "input": d["input"],
        "question": d.get("question", ""),
        "input_file": d.get("input_file", ""),
        "input_file_content": d.get("input_file_content", ""),
        "steps": d.get("steps", ""),
        "response": d.get("response", ""),
        "output_file": d.get("output_file", ""),
        "output_file_content": d.get("output_file_content", ""),
    } for d in data])

    # Save the dataset
    dir = "~/.nearai/registry/shell_benchmark"
    hf_dataset.save_to_disk(dir)

    print(f"Dataset generated and saved to {dir} directory.")