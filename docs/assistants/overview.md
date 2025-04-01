# Assistants/Agents API overview

The Assistants API allows you to build AI assistants within your own applications. An Assistant has instructions and can leverage models, tools, and files to respond to user queries. 

## How Assistants work

The Assistants API is designed to help developers build powerful AI assistants capable of performing a variety of tasks.

The Assistants API is in beta and we are actively working on adding more functionality.

1. Assistants can call various models with specific instructions to tune their personality and capabilities.
2. Assistants can access multiple tools.
3. Assistants can access persistent Threads. Threads simplify AI application development by storing message history and truncating it when the conversation gets too long for the model’s context length. You create a Thread once, and simply append Messages to it as your users reply.
4. Assistants can access files in several formats — either as part of their creation or as part of Threads between Assistants and users. When using tools, Assistants can also create files (e.g., images, spreadsheets, etc) and cite files they reference in the Messages they create.

## Key Concepts

| Object        | What it represents                                                                                                                                                                                                           |
|---------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Assistant     | Purpose-built AI that uses various models and calls tools.                                                                                                                                                                   |
| Thread        | A conversation session between an Assistant and a user. Threads store Messages and automatically handle truncation to fit content into a model’s context.                                                                    |
| Message       | A message created by an Assistant or a user. Messages can include text, images, and other files. Messages stored as a list on the Thread.                                                                                    |
| Run           | An invocation of an Assistant on a Thread. The Assistant uses its configuration and the Thread’s Messages to perform tasks by calling models and tools. As part of a Run, the Assistant appends Messages to the Thread.      |
| Run Step      | A detailed list of steps the Assistant took as part of a Run. An Assistant can call tools or create Messages during its run. Examining Run Steps allows you to introspect how the Assistant is getting to its final results. |
| Service Agent | A specialized Agent called by the Assistant to accomplish a task such as purchasing, undertaking a swap, or generating a smart contract.                                                                                     |

## Next Steps
[Integrate an Assistant into your application](./integrate.md)