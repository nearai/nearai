# In local interactive mode, the first user input is collected before the agent runs.
prompt = {"role": "system", "content": "You are a travel agent that helps users plan trips."}
result = env.completion("llama-v3p1-405b-instruct-long", [prompt] + env.list_messages())
env.add_message("agent", result)
env.request_user_input()
