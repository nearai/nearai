# Host API

A Rust API server that provides endpoints for key management and VM instance notifications.

## Features

- `/api/GetSealingKey` endpoint for obtaining encrypted keys
- `/api/Notify` endpoint for handling VM instance events
- Can be used as a standalone binary or embedded in another application

## Usage

### As a Standalone Binary

```bash
cargo run
```

This will start the server on a random available port on localhost.

### As a Library in Another Application

You can use this API server in your own application by adding it as a dependency:

```toml
[dependencies]
host_api = { path = "path/to/host_api" }
```

#### Starting the Server in a Thread

```rust
use host_api::{ServerConfig, start_server_in_thread};

fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    // Create server configuration
    let config = ServerConfig {
        kp_address: "localhost".to_string(),
        kp_port: 8080,
        vm_dir: "/tmp".to_string(),
    };

    // Start the server in a thread
    let (server_addr, server_handle) = start_server_in_thread(config)?;
    
    println!("Server started on http://{}", server_addr);
    
    // Your application can continue doing other work...
    
    // Optionally wait for the server thread to complete
    // server_handle.join().unwrap();
    
    Ok(())
}
```

#### Starting the Server in an Async Context

If your application is already using Tokio, you can start the server in an async context:

```rust
use host_api::{ServerConfig, start_server};
use std::sync::Arc;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    // Create server configuration
    let config = Arc::new(ServerConfig {
        kp_address: "localhost".to_string(),
        kp_port: 8080,
        vm_dir: "/tmp".to_string(),
    });

    // Start the server (this will block until the server stops)
    start_server(config).await
}
```

## Examples

Check out the examples directory for more usage examples:

```bash
# Run the thread example
cargo run --example use_in_thread
```

## API Endpoints

### GET /api/GetSealingKey

Obtains an encrypted key using a provided attestation quote.

**Request:**
```json
{
  "quote": "hex_encoded_quote_data"
}
```

**Response:**
```json
{
  "encrypted_key": "hex_encoded_key",
  "provider_quote": "hex_encoded_provider_quote"
}
```

### POST /api/Notify

Handles event notifications, particularly for VM instance information.

**Request:**
```json
{
  "event": "instance.info",
  "payload": "instance_information_data"
}
```

**Response:**
```json
null
``` 