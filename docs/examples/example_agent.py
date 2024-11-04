# In local interactive mode, the first user input is collected before the agent runs.
prompt = {"role": "system", "content": "You are a travel agent that helps users plan trips."}
result = env.completion([prompt] + env.list_messages())
env.add_reply(result)
env.request_user_input()
