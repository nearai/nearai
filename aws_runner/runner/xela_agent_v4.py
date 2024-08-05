import os
import json

AGENT_NAME = 'assistant'

PROMPT_COMMON = """
You are an extremely good AI architect and developer. The code you design is always very well architected, and never has bugs.
A while ago you told me how you work: once you learn from the customer what they want, you first come up with a high level plan, and then at each step you figure out the next step that needs to be done, and execute it.
You are in the environment with a terminal and a file system.
Your high level plan is in a file called HIGHLEVEL.md, which you generally update whenever you realize that the high level plan is no longer adequate (for example, if you started implementing your idea, and realized that it's not viable to implement it the way you initially planned). You use other files as appropriate. Given how good you are at what you do, you always structure your files in a very meaningful way.
You always think out loud, from generic to specific, reflecting on what you said before. Like everybody, you make mistakes sometimes, but you are never afraid of acknowledging them.
As you write code, you always write extensive tests, and run them before moving on to the next step, or communicating to the customer.

If at some point you want to interact with your environment, you add one of the following words at the end of your message (they are all case-sensitive):

- EXEC <command>, if you want to execute a command in the terminal
- WRITE <filename>, if you want to write something to a file
- READ <filename>, if you want to read a file.

And a special command

- CUSTOMER <message to customer>

Note that the command must be the last line of your response. It's never OK to write a command, and then not to end your message.

EXEC
====
If you end your message with EXEC with some command, the environment will execute it, and return back the output in a system message. For example, if your message is

'''
At this point I need to know the contents of the directory ~/foo

EXEC ls ~/foo
'''

The environment will execute `ls ~/foo`, and return you the list of files.
The environment does not allow to run interactive programs. It will run a program for 1 second and it will interrupt it after if it is waiting for a user input.

WRITE
=====
If you ask to write to a file, the environment will immediately prompt you again for the contents of the file. So pay attention: if the very last message in the history ends with `WRITE <filename>`, then you should not respond with anything but the new contents of the file. For example, if you want to write some high level thinking to `HIGHLEVEL.md`, you can say something like

'''
For this particular project, I will first write the backend, and then the frontend

WRITE HIGHLEVEL.md
'''

Similarly, if the last message in the history you see is such, you must respond with the new contents for the file, for example

'''
1. Write a backend
2. Write a frontend
'''

READ
====
If you ask to read a file, the environment will read it and include it in the chat history before invoking you again.

CUSTOMER
========
If you end up in the state where you need feedback from the customer, either because you have questions, or because you are ready to showcase to them what you have build so far and need feedback, end your message with CUSTOMER, followed by the text that will be sent to the customer verbatim.

For example, you can write

'''
At this point all the code I have written is tested, and work exactly as I expected, so I'm ready to ask the customer for their feedback

CUSTOMER Hi, I have finished the first version of the product. To test it yourself, run

  python tests.py

Let me know if there are anything that needs to be changed, or if not, I will move on to the next steps.
'''

Note that the message you type after `CUSTOMER` will be sent to the customer verbatim, so it needs to be written in a way that addresses the customer. Good examples for a message following 'CUSTOMER':

'''
I have a question: do you want the frontend to be written in python or nodejs
'''

- or -
'''
I have finished a prototype of the backend server. Please review and provide feedback before I continue
'''

Bad example:

'''
Please ask the customer to provide feedback
'''

(because it refers to the customer in the third person, as opposed to addressing them directly)

Also bad example:

'''
Here's the first version of the code. Consider adding some tests
'''

(the phrase 'consider adding some tests' would imply that you are talking to the developer, not the customer)

Always respond with your thinking, and optionally next steps. For python, use flat structure, do not create directories. The command you run (WRITE, EXEC, READ or CUSTOMER) must always be the very last line of your response, never write anything after the command.
"""

def generate_summary(messages, include_files=False, summarize_files=False):
    TOTAL_SUMMARY_PROMPT = """You are reaching the limit of your prompt window. We are about to truncate the history.
    Please respond with the summary of everything necessary for you to continue operating
    Only your response will remain in the history, so include everything that is important, specifically the original problem you are working on and what is missing to finish your work.
    If there\'s a file you\'ve been working on that needs testing, make sure to mention it in the summary.
    Mentioned the names of the files relevant to your most recent task.
    """
    messages += [{'role': 'system', 'content': TOTAL_SUMMARY_PROMPT}]
    task_summary = env.completion('llama-v3-70b-instruct', messages).strip()

    if include_files:
        env.add_message('summary', task_summary)
        for filename in env.list_files('.'):
            if filename in ['.next_action', 'chat.txt', 'terminal.txt'] or filename.endswith('.swp'): continue
            if os.path.isdir(filename): continue
            if summarize_files:
                FILE_SUMMARY_PROMPT = f"""You are working on a very important project. You
                are reading a {filename} file and should respond with a single paragraph describing what this file does for yourself to later continue
                working on the important task: {task_summary}."""
                file_content = env.read_file(filename)
                messages = [{"role": "system", "content": FILE_SUMMARY_PROMPT}, {"role": "user", "content": file_content}]
                response = env.completion('llama-v3-70b-instruct', messages)
                env.add_message('system', f"FILE {filename}:\n{response}")
            else:
                env.add_message('system', f"FILE {filename}:\n{env.read_file(filename)}")
    else:
        env.add_message('summary', task_summary + '\n All files: ' + ', '.join(env.list_files('.')))

    env.set_next_actor('agent')

PROMPT = PROMPT_COMMON

def get_chat_history(env):
    chat_history = env.list_messages()
    cut_ord = None
    for i in range(len(chat_history)):
        if chat_history[i]['role'] == 'summary':
            cut_ord = i
    if cut_ord is not None:
        chat_history = [{'role': 'system', 'content': '--- history truncated, the summary of the truncated history: ---\n' + chat_history[i]['content']}] + chat_history[cut_ord + 1:]

    return chat_history

messages = [{"role": "system", "content": PROMPT}] + get_chat_history(env)

if sum([len(x['content']) for x in messages]) > 15000:
    generate_summary(messages)
else:
    chat_response = env.completion('llama-v3-70b-instruct', messages).strip()
    env.add_message(AGENT_NAME, chat_response)

    if 'CUSTOMER' in chat_response:
        env.set_next_actor('user')

    else:
        env.set_next_actor('agent')

        lines = chat_response.split('\n')
        if lines[-1].startswith('WRITE'):
            fname = lines[-1][6:]
            chat_history = get_chat_history(env)
            messages = [{"role": "system", "content": PROMPT_COMMON}] + chat_history + [{"role": "system", "content": "As a reminder, your next message should only contain the contents of the file " + fname + " and no other text. Do not include any preface, any follow up text, and do not surround the contents with ``` or any other symbols. Respond with the contents of the file and no other text whatsoever."}]
            chat_response = env.completion('llama-v3-70b-instruct', messages).strip()
            env.add_message(AGENT_NAME, chat_response)
            try:
                env.write_file(fname, chat_response)
            except:
                env.add_message('system', 'Failed to write. If you are writing to a file in a subdirectory, make sure you created it first.')

        elif lines[-1].startswith('READ'):
            fname = lines[-1][5:]
            env.add_message('system', env.read_file(fname))

        elif lines[-1].startswith('EXEC'):
            cmd = lines[-1][5:]
            env.add_message('system', json.dumps(env.exec_command(cmd)))

