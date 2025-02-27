# NearAI `submit`

The `nearai submit` command allows a user to submit a 'job' to be executed on the NearAI platform. A 'job' can be a single model inference request, training a neural network, or any other task that can be represented as a single unit of work.

## Usage

The simplest way to submit a job is to run the command:

```bash
nearai submit <job-directory> --worker-kind GPU_8_A100
```

## Job Directory

A job directory is a directory that contains all the files and metadata required to run a job. The directory should contain a `metadata.json` file so the job directory can be uploaded to the registry and executed on the platform.

The only other requirement is that the job directory contains a `run.sh` script that will be executed on the worker acting as the job's entrypoint.

## An example job directory

In this section we will walk through a minimal example of a job directory and submitting it to the platform.

For our example we will be training a simple neural network on random data. Our job directory will contain the following files:

```
job-directory/
├── metadata.json
├── run.sh
└── run.py
```

Our `metadata.json` file will look like this:

```json
{
  "name": "test_job",
  "version": "0.0.1",
  "description": "trains a simple neural network on random data",
  "category": "test",
  "tags": [],
  "details": {},
  "show_entry": true
}
```

Our `run.sh` file will look like this:

```bash
#!/usr/bin/env bash
python3 run.py
```

Our `run.py` file will look like this:

```python
#!/usr/bin/env python3
import nearai.log
import torch
import torch.nn as nn
import torch.optim as optim

log_cli = nearai.log.LogCLI()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
assert device == "cuda", "Device must be cuda"

class SimpleNet(nn.Module):
    def __init__(self):  # noqa: D107
        super(SimpleNet, self).__init__()
        self.fc1 = nn.Linear(10, 50)
        self.fc2 = nn.Linear(50, 1)

    def forward(self, x):  # noqa: D102
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        return x


model = SimpleNet().to(device)
criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

num_batches = 100
batch_size = 16
for batch in range(num_batches):
    inputs = torch.randn(batch_size, 10).to(device)
    targets = torch.randn(batch_size, 1).to(device)

    outputs = model(inputs)
    loss = criterion(outputs, targets)

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    log_cli.push("simple_train", batch=batch, loss=loss.item())
    print(f"Batch {batch} loss: {loss.item()}")
```

Now we can submit our job directory to the platform with the following command:

```bash
nearai submit job-directory --worker-kind GPU_8_A100
```

Once our job is submitted, we can see the status of our job by tailing the logs like so:

```bash
nearai log track simple_train --follow --max-wait-time 1
```

which we should see output like:

```
...
No new logs found.
Waiting for 1 seconds...
Log:  439
{'batch': 0, 'loss': 0.8657659292221069}
Log:  440
{'batch': 1, 'loss': 0.4572370946407318}
Waiting for 1 seconds...
Log:  441
{'batch': 2, 'loss': 1.1624698638916016}
...
```