import json
import os
import tarfile
from typing import Any, List, Tuple

import streamlit as st  # type: ignore # TODO: Update pyproject to install streamlit


# Function to read file content
def read_file(file_path: str) -> str:
    with open(file_path, "r") as file:
        return file.read()


# Unpack everything
for file in os.listdir():
    if file.endswith(".tar.gz"):
        fdir = file[:-7]
        if not os.path.exists(fdir):
            tarfile.open(file).extractall(fdir)


def fetch_folders(path: str) -> List[str]:
    result = []
    for fdir in os.listdir(path):
        if os.path.isdir(f"{path}/{fdir}"):
            if os.path.exists(f"{path}/{fdir}/chat.txt"):
                result.append(f"{path}/{fdir}")
            result += fetch_folders(f"{path}/{fdir}")
    return result


# for fdir in os.listdir():
#     if os.path.isdir(fdir) and os.path.exists(f"{fdir}/chat.txt"):
#         dir_names.append(fdir)
dir_names = fetch_folders(".")

# List of directories to explore
directories = {fdir: fdir for fdir in dir_names}


# Function to get boilerplate chat messages based on the selected directory
def get_chat_messages(directory: str) -> List[Tuple[Any, Any]]:
    messages = []

    with open(f"{directory}/chat.txt", "r") as file:
        for line in file:
            if not line.strip(" "):
                continue
            message = json.loads(line.strip(" "))
            messages.append((message["role"], message["content"]))

    return messages


# Combo box to select directory
selected_directory = st.sidebar.selectbox("Select a folder", list(directories.keys()))


# Get the path of the selected directory
assert isinstance(selected_directory, str)
directory_path = directories[selected_directory]

# Get list of files in the selected directory (flat view)
file_list = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]

# Sidebar: List of files
st.sidebar.title("File Explorer")
selected_file = st.sidebar.radio("Select a file", file_list)

with st.expander("Chat Dialogue", expanded=True):
    # Main area: Display chat dialogue
    st.title("Chat Dialogue")
    chat_messages = get_chat_messages(selected_directory)
    for user, message in chat_messages:
        box = st.chat_message(user)
        box.write(message)

# Main area: Display file content
if selected_file:
    file_path = os.path.join(directory_path, selected_file)
    file_content = read_file(file_path)
    st.title(selected_file)
    st.code(file_content)
