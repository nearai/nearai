# Host Runner

A CLI tool for managing QEMU instances for confidential computing environments.

## Overview

Host Runner provides a command-line interface for creating, managing, and stopping QEMU instances with support for confidential computing features like Intel TDX. It simplifies the process of setting up and running virtual machines with specific configurations for memory, CPU, disk, networking, and GPU passthrough.

## Installation

Build the host runner from source:

```bash
cargo build --bin host_runner
```

## Usage

The host runner provides several commands:

- `run`: Create and run a new instance
- `list`: List all running instances
- `stop`: Stop and remove an instance

### Global Options

- `-l, --log-level <LOG_LEVEL>`: Sets the level of verbosity (default: "info")

### Run Command

Create and run a new QEMU instance with the specified configuration.

```bash
host_runner run [OPTIONS] --image-path <IMAGE_PATH>
```

#### Options

- `-c, --compose-path <COMPOSE_PATH>`: Path to the compose file (default: "compose.yaml")
- `-i, --image-path <IMAGE_PATH>`: Path to the image directory (required)
- `-u, --cpus <CPUS>`: Number of CPUs to allocate (default: 12)
- `-m, --memory <MEMORY>`: Memory to allocate (e.g., "32G") (default: "32G")
- `-d, --disk <DISK>`: Disk size (e.g., "500G") (default: "500G")
- `-p, --ports <PORTS>`: Port mappings in format "tcp:host_ip:host_port:guest_port"
- `-g, --gpus <GPUS>`: GPU devices to pass through
- `--local-key-provider`: Use local key provider instead of remote (default: true)
- `--pin-numa`: Enable NUMA pinning (default: false)
- `--hugepage`: Enable hugepage support (default: false)

### List Command

List all running instances.

```bash
host_runner list
```

### Stop Command

Stop and remove an instance.

```bash
host_runner stop [OPTIONS]
```

#### Options

- `-i, --id <ID>`: Instance ID to stop
- `-a, --all`: Stop all instances

## Examples

### Running a Basic Instance

```bash
cargo run --bin host_runner -- run \
  -i /path/to/image/directory \
  -u 8 \
  -m "16G" \
  -d "250G"
```

### Running with Port Forwarding

```bash
cargo run --bin host_runner -- run \
  -i /path/to/image/directory \
  -p "tcp:0.0.0.0:443:443,tcp::10024:22"
```

### Running with GPU Passthrough

```bash
cargo run --bin host_runner -- run \
  -i /path/to/image/directory \
  -g "0000:01:00.0"
```

### Running with Custom Compose File

```bash
cargo run --bin host_runner -- run \
  -c /path/to/compose.yaml \
  -i /path/to/image/directory
```

### Complete Example

```bash
cargo run --bin host_runner -- run \
  -c /home/ubuntu/nearai/tee_infra/configs/runner.yaml \
  -i /home/ubuntu/private-ml-sdk/images/dstack-nvidia-dev-0.3.3 \
  -u 8 \
  -m "32G" \
  -d "500G" \
  -p "tcp:0.0.0.0:443:443,tcp::10024:22"
```

### Stopping an Instance

```bash
cargo run --bin host_runner -- stop --id <INSTANCE_ID>
```

### Stopping All Instances

```bash
cargo run --bin host_runner -- stop --all
```

## Notes

- The host runner requires QEMU to be installed on the system.
- For GPU passthrough, you may need to run the command with sudo privileges.
- Port mappings should follow the format "tcp:host_ip:host_port:guest_port" or "tcp::host_port:guest_port".
- The local key provider is enabled by default. To disable it, omit the `--local-key-provider` flag.
- Each host_runner process manages a single QEMU instance. Running multiple instances requires launching multiple host_runner processes.
- The `run` command blocks and keeps the QEMU process running until interrupted with Ctrl+C or a termination signal.
- To run instances in the background, you can use standard shell techniques like `nohup` or `&`:
  ```bash
  nohup cargo run --bin host_runner -- run -i /path/to/image > runner.log 2>&1 &
  ```

## Process Management

When you run the host_runner with the `run` command, it:

1. Creates a temporary directory for the instance
2. Starts a host API server in a separate thread
3. Sets up the QEMU instance with the specified configuration
4. Launches the QEMU process
5. Blocks and waits for either:
   - The QEMU process to exit
   - A termination signal (Ctrl+C or SIGTERM)
6. On termination, shuts down the QEMU instance gracefully

The host_runner captures QEMU's stdout and stderr to log files in the current directory:
- `qemu_stdout.log`
- `qemu_stderr.log`

This design ensures that each host_runner process is tied to a single QEMU instance. If the QEMU process exits for any reason, the host_runner will detect this and exit as well. This prevents orphaned host_runner processes when QEMU terminates unexpectedly.
