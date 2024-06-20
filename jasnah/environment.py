import os
import subprocess

CHAT_DELIMITER = '\n\n\n'
CHAT_FILENAME = 'chat.txt'

class Environment(object):

    def __init__(self, path):
        self._path = path
        os.makedirs(self._path, exist_ok=True)

    def add_message(self, role, message):
        with open(os.path.join(self._path, CHAT_FILENAME), 'a') as f:
            f.write(f'{role}: {message}{CHAT_DELIMITER}')

    def list_messages(self):
        with open(os.path.join(self._path, CHAT_FILENAME), 'r') as f:
            return [message.split(':', maxsplit=1) for message in f.read().split(CHAT_DELIMITER) if message]

    def exec_command(self, command):
        output = subprocess.run(command, shell=True)
        with open(os.path.join(self._path, 'terminal.txt'), 'a') as f:
            f.write(f'> {command}\n{output}\n')
        return output

    def is_done(self):
        return False
