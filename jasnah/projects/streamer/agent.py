import litellm

def run_agent(env, task):
    print(f"Running task: {task}")

    history = []

    while True:
        PROMPT = f"""You are an AGI agent working on the task: {task}

        You approach to a task should be:
          - always thinking outloud
          - understand the environment you are working
          - writing specification
          - writing required code
          - testing that code works correctly
        """
        PROMPT2 = f"""You should think about the next steps outloud and at the end output ||||| and one of the following commands:
        - run <command> to execute command in the terminal
        - list <path> to list files in the given path
        - write <filename> and from new line content of the file you want to write
        - read <filename> to read a file named filename

        There should be nothing else after you output this command.
        """
        messages = [{"role": "system", "content": PROMPT}]
        messages += history
        messages += [{"role": "user", "content": PROMPT2}]
        stream = env.completions('llama-v3-70b-instruct', messages, stream=True)

        output = ""

        chunks = []
        for chunk in stream:
            chunks.append(chunk)
            print(chunk.choices[0].delta.content or "", end="")
        print()

        output = litellm.stream_chunk_builder(chunks, messages=messages).choices[0].message.content
        history.append({"role": "assistant", "content": output})
        env.add_message("assistant", output)
        command = output.split('|||||', maxsplit=1)[1].strip()

        print(f"Executing {command[:10]}")
        command_outcome = ""
        try:
            if command.startswith('run'):
                command = command.split('run ')[1]
                result = env.exec_command(command)
                print(result)
                if 'returncode' in result and result['returncode'] != 0:
                    command_outcome = f'Command {command} failed with error: {result["stderr"]}'
                else:
                    command_outcome = result["stdout"]
            elif command.startswith('write'):
                filename, content = command.split('write ')[1].split('\n', maxsplit=1)
                filename = filename.strip()
                content = content.strip(' \n`')
                env.write_file(filename, content)
                command_outcome = "Done"
            elif command.startswith('read'):
                filename = command.split('read ')[1]
                content = env.read_file(filename)
                command_outcome = f'Read file {filename} with content: {content}'
            elif command.startswith('list'):
                path = command.split('list ')[1].strip()
                files = env.list_files(path)
                command_outcome = f'Listed files in path {path}: {files}'
        except Exception as e:
            command_outcome = f'Error: {e}'
        history.append({"role": "user", "content": command_outcome})
        env.add_message("user", command_outcome)
        print(history[-1])
        input(f'Press Enter to continue...')
