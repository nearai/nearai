# NEAR AI

Manage dataset and model registry.
Run and explore tasks on the experiment platform.

All data created by `nearai` is stored at `~/.nearai`

## Experiment Platform

There are two components:

- Server: Deployed on one node with ssh access to every host
- Supervisors: One deployed on every host

### Deployment

1. Install `nearai` first. See [README.md](README.md).
2. Create the host files with all hosts you want to use. See for example [etc/hosts_lambda.txt](etc/hosts_lambda.txt).
3. Install the supervisor on every host by running: `nearai server install_supervisors path/to/hosts.txt`. This command is idempotent, so it is ok if it is re-run multiple times.
4. Start server by running: `nearai server start path/to/hosts.txt`.

### Experiment flow

After the server is started it creates a new entry in the `Supervisors` dataset with all hosts, and set Available status `False`.
Only the supervisor can set themselves as available. The server pings every supervisor so they can set themselves available.
The server will check if there is a pending experiment and an available supervisor, if that is the case it changes the status of the supervisor and the experiment to `Running` and not available, and send the experiment id to the supervisor.
When the supervisor finishes the task it sets itself as available again and pings the server.
