## v0.1.11 (2025-02-11)

### Feat

- Ensure the user is authenticated on agent local run (#822)

### Fix

- Removed unnecessary retries in HUB (#827)

## v0.1.10 (2025-02-01)

### Feat

- update agent quickstart guide (#782)

## v0.1.9 (2025-01-31)

## v0.1.8 (2025-01-31)

## v0.1.7 (2025-01-31)

### Feat

- env methods to interact with NEAR Blockchain (#748)
- easy agent creation (#723)
- cli to respect `verbose` param (#716)
- run_scheduler (#703)
- format verbose printed statements (#709)
- Expose user's NEAR account_id to agent (#700)
- borsh serializer to support dicts (#677)
- get_signed_completion to use messages as list, not string
fix: user auth removed from runner's logs
- hub to derive a private key for every agent and generate a veri… (#662)
- faster (#665)

### Fix

- set num_retries to avoid extra requests with slow completions (#755)
- set DEFAULT_TIMEOUT and remove MAX_RETRIES to avoid multiple paid requests on slow completions (#754)
- add format_check and update lint/type check filename (#710)
- enable `FASTNEAR_APIKEY` (#699)
- cached_property for runner properties (#692)
- add project dependencies section for pip install support (#683)
- protected auth (#670)

## v0.1.6 (2024-12-19)

### Feat

- hub to read commands in EVENT_JSON logs in NEAR blocks and run … (#655)
- env.completion to support `temperature` and `max_tokens` parameter for a specific request. (#652)
- web-agent-framework updated packages (#481)

### Fix

- yield/resume compatibility (#663)
- add /tmp folder as an option for `DATA_FOLDER` (#576)
- service default model (#562)

## v0.1.5 (2024-11-09)

## v0.1.4 (2024-11-08)

### Feat

- iframe to allow popups (#415)

### Fix

- file read to ignore non-supported tokens instead of breaking (#513)
- read_file to not break agent if file not exists (#486)
- `updated` to have default field to support `local_files` mode (#478)
- max_iterations default set to 1 (#466)
- run_with_environment call to respect new `additional_path` value (#454)
- remove unused parameter (#386)

## v0.1.2 (2024-10-11)
