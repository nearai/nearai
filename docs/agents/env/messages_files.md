# Messages and Files

Agents interact with the users through messages, and can also access and create files. This page provides an overview of how agents can work with messages and files.

??? tip "Quick Overview"
    * Each run of an agent is executed in a separate thread, which contains messages and files.
    * The agent can access the messages in the current thread using `env.list_messages()`.
    * The agent can save temporary files to track the progress of a task.
    * By default, the entire message history is stored in a file named `chat.txt`. The agent can add messages there by using `env.add_reply()`.
    * During its operation, the agent creates a file named `.next_agent`, which stores the role of the next participant expected in the dialogue (either `user` or `agent`) during the next iteration of the loop. The agent can control this value using `env.set_next_actor()`.
    * The agent can use local imports from the home folder or its subfolders. It is executed from a temporary folder within a temporary environment.

---

## Thread Messages

The environment provides methods for agents to access and interact with the messages in the current thread. Messages are stored in a list, with each message containing an `id`, `content`, and `role` field.

### Accessing Messages

Agents can access the messages from the current thread using the `list_messages` method:

```python title="agent.py"
def run(env: Environment):
  messages = env.list_messages()
  print(messages)
```

??? note "Example Output"
    ```python
    [{'id': 'msg_9b676ae4ad324ca58794739d', 'content': 'Hi', 'role': 'user'},
      {'id': 'msg_58693367bcee42669a85cb69', 'content': "Hello! It's nice to meet you. Is there something I can help you with or would you like to chat?", 'role': 'assistant'},
      {'id': 'msg_16acda223c294213bc3c814e', 'content': 'help me decide how to decorate my house!', 'role': 'user'}]
    ```

### Adding Messages

Agents can add new messages to the thread using the `add_reply` method:

```python title="agent.py"
def run(env: Environment):
  env.add_reply("I have finished")
```

----

## Files 

Agents have access to two types of files through the environment:

  1. Those created within the current [conversation thread](../threads.md)
  2. Those uploaded with the agent [to the registry](../registry.md#uploading-an-agent)

### Storing Data

To create a new file in the thread we can use the `write_file` method from the environment:

```python title="agent.py"
def run(env: Environment):
  env.write_file('file.txt', 'hello thread')
```

??? tip "Where is the file stored?"

    When running the agent locally, a temporary folder will be created to store each thread data. We can check exactly where the file is stored by using the `python debugger`:

    ```python title="agent.py"
    def run(env: Environment):
      env.write_file('file.txt', 'hello thread')
      import ipdb; ipdb.set_trace()  # Call the ipdb debugger
    ```

    After running the agent, we will be dropped into the debugger, where we can check the current working directory:

    ```bash
    nearai agent interactive ~/.nearai/registry/<your-account.near>/hello-ai/0.0.1 --local --thread_id thread_43c64803c0a948bc9a8eb8e8

    ipdb> import os; os.getcwd() # Check the current working directory
    '/private/var/folders/v6/pw4e3e3r5t6h8i9oihtd9d7d1234df/T/agent_7e312s678b987sa4vc4s2zxs2s1w1345'
    ```

    We can see that the current working directory is a temporary folder. Go ahead and start the `agent` again without the `--thread_id` parameter, you will see that the working directory changes.

<hr class="subsection">

### Accessing Files

To list the files in the thread storage, we can use the `list_files_from_thread` method from the environment:

```python title="agent.py"
def run(env: Environment):
  files = env.list_files_from_thread()
  content = env.read_file('file.txt')

  print('Files:', files)
  print('Content of file.txt:', content)
```

??? example "Example Output"
    ```python
    Files [FileObject(id='file_31aab645e3214a13b402e321', bytes=12, created_at=1734733634, filename='file.txt', object='file', purpose='assistants', status='uploaded', status_details='File information retrieved successfully')]

    Content of file.txt hello thread
    ```

---

## Logging

You can turn on agent logging by passing an environment variable of `DEBUG` with a value of true. 
In the UI this is set on the Run page of an agent while logged in as the agent author. Once this is set, 
logs from either of the methods below will be written to the thread. The 'show logs' button (next to send message)
toggles whether the logs show in the thread.


* [`add_system_log`](../../api.md#nearai.agents.environment.Environment.add_system_log): adds a system or environment log that is then saved into "system_log.txt".
* [`add_agent_log`](../../api.md#nearai.agents.environment.Environment.add_system_log): any agent logs may go here. Saved into "agent_log.txt".
