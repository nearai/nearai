# CVM Client

A Rust client for interacting with the Confidential Virtual Machine (CVM) service.

## Features

- Secure communication with CVM service
- TDX attestation support
- Agent assignment and management
- Run execution

## Usage

### Creating a Client

```rust
use cvm_client::{AuthData, CvmClient};

// Create auth data
let auth = AuthData {
    token: "your_token".to_string(),
};

// Create client
let mut client = CvmClient::new("https://your-cvm-service.com", Some(auth))?;
```

### Attestation

Before using the CVM service, you need to perform attestation to verify the identity of the CVM:

```rust
// Perform attestation
let quote_response = client.attest().await?;
println!("Attestation successful, quote: {}", quote_response.quote);
```

### Checking Assignment

Check if an agent is already assigned to the CVM:

```rust
let is_assigned = client.is_assigned().await?;
if is_assigned.is_assigned {
    println!("Agent is assigned: {:?}", is_assigned.agent_id);
} else {
    println!("No agent assigned");
}
```

### Assigning an Agent

Assign an agent to the CVM:

```rust
use cvm_client::AssignRequest;

let assign_request = AssignRequest {
    agent_id: "your-agent-id".to_string(),
};

let response = client.assign(assign_request).await?;
println!("Assignment successful: {}", response);
```

### Running an Agent

Run an agent on the CVM:

```rust
use cvm_client::RunRequest;
use std::collections::HashMap;

let mut env_vars = HashMap::new();
env_vars.insert("API_KEY".to_string(), "your-api-key".to_string());

let run_request = RunRequest {
    run_id: "your-run-id".to_string(),
    thread_id: "your-thread-id".to_string(),
    provider: "openai".to_string(),
    model: "gpt-4".to_string(),
    temperature: 0.7,
    max_tokens: 1000,
    max_iterations: 5,
    env_vars,
};

let response = client.run(run_request).await?;
println!("Run successful: {}", response);
```

## Security Considerations

- The client verifies the CVM's identity through TDX attestation
- All communication is encrypted using TLS
- The client stores the server's certificate in a temporary file

## Dependencies

- `reqwest`: HTTP client
- `tokio`: Async runtime
- `serde`: Serialization/deserialization
- `anyhow`: Error handling
- `openssl`: Certificate handling
- `sha2`: Cryptographic hashing
- `tracing`: Logging

## Building and Testing

```bash
# Build the project
cargo build

# Run the example
cargo run

# Run tests
cargo test
``` 