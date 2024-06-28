

def run_agent(env, task):
    print(f"Running task: {task}")

    # PROMPT = f"""You are AGI agent working on a given task.

    # You can use the following commands as you are working on the task:
    #  - <thinking> to start thinking step by step and ending it with </thinking>
    #  - <code filename> to start writing code in a file named filename and ending it with </code>
    #  - <run> following with command line you want to execute and ending it with </run> which will be succeeded by output of that command line coming from the environment
    
    # The objective: {task}
    # """
    history = ""

    while True:
        PROMPT = f"""You are an AGI agent working on the task: {task}

        You approach to a task should be:
          - always thinking outloud
          - understand the environment you are working
          - writing specification
          - writing required code
          - testing that code works correctly

        Here is the history of your work:
        f{history}
        ==== END OF HISTORY ====

        You should think about the next steps outloud and at the end output # and one of the following commands:
        - run <command> to execute command in the terminal
        - list <path> to list files in the given path
        - write <filename> and from new line content of the file you want to write
        - read <filename> to read a file named filename

        There should be nothing else after you output this command.
        """
        messages = [{"role": "system", "content": PROMPT}]
        stream = env.completions('llama-v3-70b-instruct', messages, stream=True)

        output = ""
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                next_token = chunk.choices[0].delta.content
                output += next_token
                print(next_token, end="")
        print()
        history += output
        command = output.split('#')[1].strip()
        if command.startswith('run'):
            command = command.split('run')[1]
            result = env.exec_command(command)
            if 'returncode' in result and result['returncode'] != 0:
                history += f'\nCommand {command} failed with error: {result["stderr"]}'
            else:
                history += result["stdout"]
        elif command.startswith('write'):
            filename, content = command.split('write')[1].split('\n')
            print(filename, content)
            env.write_file(filename, content)
            # history += f'Wrote file {filename} with content: {content}'
        elif command.startswith('read'):
            filename = command.split('read')[1]
            content = env.read_file(filename)
            history += f'\nRead file {filename} with content: {content}'
        elif command.startswith('list'):
            path = command.split('list')[1]
            files = env.list_files(path)
            history += f'\nListed files in path {path}: {files}'
        input(f'Press Enter to continue... {len(history)}')
