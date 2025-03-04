use std::fs::File;
use std::io::{self, Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::thread;

use anyhow;
use axum::{
    body::Bytes,
    extract::State,
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::post,
    Json, Router,
};
use serde::{Deserialize, Serialize};
use thiserror::Error;
use tokio::net::TcpListener;
use tower_http::trace::TraceLayer;

#[derive(Clone, Debug)]
pub struct ServerConfig {
    pub kp_address: String,
    pub kp_port: u16,
    pub vm_dir: PathBuf,
}

impl ServerConfig {
    pub fn new(vm_dir: impl AsRef<Path>) -> Self {
        let config = Self {
            kp_address: "localhost".to_string(),
            kp_port: 3443,
            vm_dir: vm_dir.as_ref().to_path_buf(),
        };
        tracing::debug!("Created new ServerConfig: {:?}", config);
        config
    }
}

#[derive(Error, Debug)]
pub enum QuoteError {
    #[error("IO error: {0}")]
    Io(#[from] io::Error),

    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),

    #[error("Connection closed prematurely")]
    ConnectionClosed,

    #[error("Request body too large")]
    RequestTooLarge,

    #[error("Not found")]
    NotFound,

    #[error("Data error: {0}")]
    Data(String),
}

impl IntoResponse for QuoteError {
    fn into_response(self) -> Response {
        let (status, error_message) = match self {
            QuoteError::RequestTooLarge => (
                StatusCode::BAD_REQUEST,
                "Request body too large".to_string(),
            ),
            QuoteError::NotFound => (StatusCode::NOT_FOUND, "Not found".to_string()),
            err => (
                StatusCode::INTERNAL_SERVER_ERROR,
                format!("Internal server error: {}", err),
            ),
        };

        let body = Json(serde_json::json!({
            "error": error_message,
        }));

        (status, body).into_response()
    }
}

#[derive(Debug, Serialize, Deserialize)]
struct QuoteResponse {
    encrypted_key: Vec<u8>,
    provider_quote: Vec<u8>,
}

impl QuoteResponse {
    fn from_json(data: serde_json::Value) -> Result<Self, QuoteError> {
        let encrypted_key = data["encrypted_key"]
            .as_array()
            .ok_or_else(|| QuoteError::Data("encrypted_key not an array".to_string()))?
            .iter()
            .map(|v| v.as_u64().unwrap_or(0) as u8)
            .collect();

        let provider_quote = data["provider_quote"]
            .as_array()
            .ok_or_else(|| QuoteError::Data("provider_quote not an array".to_string()))?
            .iter()
            .map(|v| v.as_u64().unwrap_or(0) as u8)
            .collect();

        Ok(QuoteResponse {
            encrypted_key,
            provider_quote,
        })
    }
}

#[derive(Debug, Deserialize)]
struct QuoteRequest {
    quote: String,
}

#[derive(Debug, Deserialize)]
struct NotifyRequest {
    event: String,
    payload: String,
}

#[derive(Debug, Serialize)]
struct KeyResponse {
    encrypted_key: String,
    provider_quote: String,
}

fn get_key(quote: Vec<u8>, address: &str, port: u16) -> Result<QuoteResponse, QuoteError> {
    tracing::debug!("Connecting to key provider at {}:{}", address, port);
    let mut stream = match TcpStream::connect((address, port)) {
        Ok(stream) => stream,
        Err(err) => {
            tracing::error!("Failed to connect to key provider: {}", err);
            return Err(QuoteError::Io(err));
        }
    };

    let payload = serde_json::json!({
        "quote": quote,
    });

    let serialized = serde_json::to_vec(&payload)?;
    let length = serialized.len() as u32;
    tracing::trace!("Sending quote data of length {} bytes", length);

    // Send length as big-endian u32
    if let Err(err) = stream.write_all(&length.to_be_bytes()) {
        tracing::error!("Failed to send length to key provider: {}", err);
        return Err(QuoteError::Io(err));
    }

    if let Err(err) = stream.write_all(&serialized) {
        tracing::error!("Failed to send payload to key provider: {}", err);
        return Err(QuoteError::Io(err));
    }
    tracing::debug!("Successfully sent quote data to key provider");

    // Read response length
    let mut response_length_bytes = [0u8; 4];
    if let Err(err) = stream.read_exact(&mut response_length_bytes) {
        tracing::error!("Failed to read response length from key provider: {}", err);
        return Err(QuoteError::Io(err));
    }

    let response_length = u32::from_be_bytes(response_length_bytes) as usize;
    tracing::debug!("Expecting response of length {} bytes", response_length);

    // Read response data
    let mut response_data = Vec::with_capacity(response_length);
    let mut remaining = response_length;

    while remaining > 0 {
        let mut buffer = vec![0u8; std::cmp::min(4096, remaining)];
        let bytes_read = match stream.read(&mut buffer) {
            Ok(0) => {
                tracing::error!("Connection closed prematurely by key provider");
                return Err(QuoteError::ConnectionClosed);
            }
            Ok(n) => n,
            Err(err) => {
                tracing::error!("Error reading from key provider: {}", err);
                return Err(QuoteError::Io(err));
            }
        };

        tracing::trace!("Read {} bytes from key provider", bytes_read);
        response_data.extend_from_slice(&buffer[..bytes_read]);
        remaining -= bytes_read;
    }

    tracing::debug!("Successfully received complete response from key provider");
    let response_json: serde_json::Value = match serde_json::from_slice(&response_data) {
        Ok(json) => json,
        Err(err) => {
            tracing::error!("Failed to parse JSON response from key provider: {}", err);
            return Err(QuoteError::Json(err));
        }
    };

    match QuoteResponse::from_json(response_json) {
        Ok(response) => {
            tracing::debug!("Successfully parsed QuoteResponse");
            Ok(response)
        }
        Err(err) => {
            tracing::error!("Failed to parse QuoteResponse: {}", err);
            Err(err)
        }
    }
}

// Custom handler for GetSealingKey that accepts raw bytes
async fn get_sealing_key(
    State(config): State<Arc<ServerConfig>>,
    body: Bytes,
) -> Result<Json<KeyResponse>, QuoteError> {
    tracing::info!("Received GetSealingKey request");
    tracing::trace!("Request body size: {} bytes", body.len());

    // Parse the request body manually
    let payload: QuoteRequest = match serde_json::from_slice(&body) {
        Ok(payload) => {
            tracing::debug!("Successfully parsed QuoteRequest");
            payload
        }
        Err(err) => {
            tracing::error!("Failed to parse QuoteRequest: {}", err);
            return Err(QuoteError::Json(err));
        }
    };

    tracing::debug!(
        "Decoding hex quote string of length {}",
        payload.quote.len()
    );
    let quote = match hex::decode(&payload.quote) {
        Ok(quote) => quote,
        Err(err) => {
            tracing::error!("Invalid hex in quote: {}", err);
            return Err(QuoteError::Data("Invalid hex in quote".to_string()));
        }
    };

    tracing::debug!(
        "Requesting key from provider at {}:{}",
        config.kp_address,
        config.kp_port
    );
    let response = match get_key(quote, &config.kp_address, config.kp_port) {
        Ok(response) => response,
        Err(err) => {
            tracing::error!("Failed to get key from provider: {}", err);
            return Err(err);
        }
    };

    let encrypted_key_hex = hex::encode(&response.encrypted_key);
    let provider_quote_hex = hex::encode(&response.provider_quote);
    tracing::debug!(
        "Successfully obtained encrypted key (length: {}) and provider quote (length: {})",
        encrypted_key_hex.len(),
        provider_quote_hex.len()
    );

    tracing::info!("GetSealingKey request completed successfully");
    Ok(Json(KeyResponse {
        encrypted_key: encrypted_key_hex,
        provider_quote: provider_quote_hex,
    }))
}

// Custom handler for Notify that accepts raw bytes
async fn notify(
    State(config): State<Arc<ServerConfig>>,
    body: Bytes,
) -> Result<Json<serde_json::Value>, QuoteError> {
    tracing::info!("Received Notify request");
    tracing::trace!("Request body size: {} bytes", body.len());

    // Parse the request body manually with explicit type annotation
    let payload: NotifyRequest = match serde_json::from_slice::<NotifyRequest>(&body) {
        Ok(payload) => {
            tracing::debug!(
                "Successfully parsed NotifyRequest with event: {}",
                payload.event
            );
            payload
        }
        Err(err) => {
            tracing::error!("Failed to parse NotifyRequest: {}", err);
            return Err(QuoteError::Json(err));
        }
    };

    if payload.event == "instance.info" {
        let info_path = config.vm_dir.join("shared").join(".instance_info");
        tracing::debug!("Writing instance.info to {}", info_path.display());

        let mut file = match File::create(&info_path) {
            Ok(file) => file,
            Err(err) => {
                tracing::error!(
                    "Failed to create instance info file at {}: {}",
                    info_path.display(),
                    err
                );
                return Err(QuoteError::Io(err));
            }
        };

        if let Err(err) = file.write_all(payload.payload.as_bytes()) {
            tracing::error!("Failed to write to instance info file: {}", err);
            return Err(QuoteError::Io(err));
        }

        tracing::debug!(
            "Successfully wrote instance info to {}",
            info_path.display()
        );
    } else {
        tracing::debug!("Ignoring unknown event type: {}", payload.event);
    }

    tracing::info!("Notify request completed successfully");
    Ok(Json(serde_json::json!(null)))
}

/// Starts the host API server with the given configuration
///
/// This function can be called from another binary to start the server in a thread.
pub async fn start_server(config: Arc<ServerConfig>) -> anyhow::Result<()> {
    tracing::info!("Starting host API server with config: {:?}", config);

    // Build our application with routes
    let app = Router::new()
        .route("/api/GetSealingKey", post(get_sealing_key))
        .route("/api/Notify", post(notify))
        .with_state(config.clone())
        .layer(TraceLayer::new_for_http());
    tracing::debug!("Router configured with endpoints: /api/GetSealingKey, /api/Notify");

    // Run the server
    let addr = SocketAddr::from(([127, 0, 0, 1], 0));
    tracing::debug!("Attempting to bind to address: {}", addr);

    let listener = match TcpListener::bind(addr).await {
        Ok(listener) => listener,
        Err(err) => {
            tracing::error!("Failed to bind to address {}: {}", addr, err);
            return Err(err.into());
        }
    };

    let server_addr = listener.local_addr()?;
    tracing::info!("Server listening on http://{}", server_addr);

    tracing::info!("Starting to serve requests");
    if let Err(err) = axum::serve(listener, app).await {
        tracing::error!("Server error: {}", err);
        return Err(err.into());
    }

    tracing::info!("Server shutdown complete");
    Ok(())
}

/// Starts the host API server in a new thread
///
/// Returns the server's address and a JoinHandle that can be used to wait for the server to finish
pub fn start_server_in_thread(
    config: ServerConfig,
) -> anyhow::Result<(SocketAddr, thread::JoinHandle<()>)> {
    tracing::info!(
        "Starting host API server in a new thread with config: {:?}",
        config
    );

    // Create a runtime for the server
    let rt = match tokio::runtime::Runtime::new() {
        Ok(rt) => rt,
        Err(err) => {
            tracing::error!("Failed to create Tokio runtime: {}", err);
            return Err(err.into());
        }
    };
    tracing::debug!("Created Tokio runtime for server thread");

    // Create a TCP listener to get the address before spawning the thread
    let addr = SocketAddr::from(([127, 0, 0, 1], 0));
    tracing::debug!("Attempting to bind to address: {}", addr);

    let listener = match rt.block_on(async { TcpListener::bind(addr).await }) {
        Ok(listener) => listener,
        Err(err) => {
            tracing::error!("Failed to bind to address {}: {}", addr, err);
            return Err(err.into());
        }
    };

    let server_addr = listener.local_addr()?;
    tracing::info!("Server will listen on http://{}", server_addr);

    // Clone the config for the thread
    let config = Arc::new(config);

    // Spawn a thread to run the server
    let handle = thread::spawn(move || {
        tracing::debug!("Server thread started");
        rt.block_on(async {
            // Build our application with routes
            let app = Router::new()
                .route("/api/GetSealingKey", post(get_sealing_key))
                .route("/api/Notify", post(notify))
                .with_state(config.clone())
                .layer(TraceLayer::new_for_http());
            tracing::debug!("Router configured with endpoints: /api/GetSealingKey, /api/Notify");

            tracing::info!("Server listening on http://{}", server_addr);

            // Use the pre-created listener
            tracing::info!("Starting to serve requests in thread");
            if let Err(e) = axum::serve(listener, app).await {
                tracing::error!("Server error in thread: {}", e);
            }
            tracing::info!("Server thread shutdown complete");
        });
    });

    tracing::info!("Server thread spawned successfully");
    Ok((server_addr, handle))
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::http::StatusCode;
    use axum::response::Response;
    use serde_json::json;

    #[test]
    fn test_quote_response_from_json() {
        let test_data = json!({
            "encrypted_key": [1, 2, 3, 4],
            "provider_quote": [5, 6, 7, 8]
        });

        let response = QuoteResponse::from_json(test_data).unwrap();
        assert_eq!(response.encrypted_key, vec![1, 2, 3, 4]);
        assert_eq!(response.provider_quote, vec![5, 6, 7, 8]);
    }

    #[test]
    fn test_quote_response_from_json_error() {
        // Missing encrypted_key
        let test_data = json!({
            "provider_quote": [5, 6, 7, 8]
        });

        let result = QuoteResponse::from_json(test_data);
        assert!(result.is_err());

        // Missing provider_quote
        let test_data = json!({
            "encrypted_key": [1, 2, 3, 4]
        });

        let result = QuoteResponse::from_json(test_data);
        assert!(result.is_err());
    }

    #[test]
    fn test_quote_error_into_response() {
        // Test RequestTooLarge error
        let error = QuoteError::RequestTooLarge;
        let response: Response = error.into_response();
        assert_eq!(response.status(), StatusCode::BAD_REQUEST);

        // Test NotFound error
        let error = QuoteError::NotFound;
        let response: Response = error.into_response();
        assert_eq!(response.status(), StatusCode::NOT_FOUND);

        // Test other errors (should be internal server error)
        let error = QuoteError::Data("Test error".to_string());
        let response: Response = error.into_response();
        assert_eq!(response.status(), StatusCode::INTERNAL_SERVER_ERROR);
    }

    #[test]
    fn test_server_config() {
        let config = ServerConfig {
            kp_address: "localhost".to_string(),
            kp_port: 8080,
            vm_dir: PathBuf::from("/tmp"),
        };

        assert_eq!(config.kp_address, "localhost");
        assert_eq!(config.kp_port, 8080);
        assert_eq!(config.vm_dir, PathBuf::from("/tmp"));
    }
}
