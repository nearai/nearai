use std::fs::File;
use std::io::{self, Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::Path;
use std::sync::Arc;
use std::thread;

use axum::{
    extract::State,
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::post,
    Json, Router,
};
use bytes::Bytes;
use serde::{Deserialize, Serialize};
use thiserror::Error;
use tokio::net::TcpListener;
use tower_http::trace::TraceLayer;

// Re-export the ServerConfig for external use
#[derive(Clone, Debug)]
pub struct ServerConfig {
    pub kp_address: String,
    pub kp_port: u16,
    pub vm_dir: String,
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
    let mut stream = TcpStream::connect((address, port))?;

    let payload = serde_json::json!({
        "quote": quote,
    });

    let serialized = serde_json::to_vec(&payload)?;
    let length = serialized.len() as u32;

    // Send length as big-endian u32
    stream.write_all(&length.to_be_bytes())?;
    stream.write_all(&serialized)?;

    // Read response length
    let mut response_length_bytes = [0u8; 4];
    stream.read_exact(&mut response_length_bytes)?;
    let response_length = u32::from_be_bytes(response_length_bytes) as usize;

    // Read response data
    let mut response_data = Vec::with_capacity(response_length);
    let mut remaining = response_length;

    while remaining > 0 {
        let mut buffer = vec![0u8; std::cmp::min(4096, remaining)];
        let bytes_read = stream.read(&mut buffer)?;

        if bytes_read == 0 {
            return Err(QuoteError::ConnectionClosed);
        }

        response_data.extend_from_slice(&buffer[..bytes_read]);
        remaining -= bytes_read;
    }

    let response_json: serde_json::Value = serde_json::from_slice(&response_data)?;
    QuoteResponse::from_json(response_json)
}

async fn get_sealing_key(
    State(config): State<Arc<ServerConfig>>,
    Json(payload): Json<QuoteRequest>,
) -> Result<Json<KeyResponse>, QuoteError> {
    // Check if the request is too large (already handled by axum's default limits)

    let quote = hex::decode(&payload.quote)
        .map_err(|_| QuoteError::Data("Invalid hex in quote".to_string()))?;

    let response = get_key(quote, &config.kp_address, config.kp_port)?;

    Ok(Json(KeyResponse {
        encrypted_key: hex::encode(&response.encrypted_key),
        provider_quote: hex::encode(&response.provider_quote),
    }))
}

async fn notify(
    State(config): State<Arc<ServerConfig>>,
    Json(payload): Json<NotifyRequest>,
) -> Result<Json<serde_json::Value>, QuoteError> {
    // Check if the request is too large (already handled by axum's default limits)

    if payload.event == "instance.info" {
        let info_path = Path::new(&config.vm_dir)
            .join("shared")
            .join(".instance_info");
        let mut file = File::create(info_path)?;
        file.write_all(payload.payload.as_bytes())?;
    }

    Ok(Json(serde_json::json!(null)))
}

/// Starts the host API server with the given configuration
///
/// This function can be called from another binary to start the server in a thread.
pub async fn start_server(
    config: Arc<ServerConfig>,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    // Build our application with routes
    let app = Router::new()
        .route("/api/GetSealingKey", post(get_sealing_key))
        .route("/api/Notify", post(notify))
        .with_state(config.clone())
        .layer(TraceLayer::new_for_http());

    // Run the server
    let addr = SocketAddr::from(([127, 0, 0, 1], 0));
    let listener = TcpListener::bind(addr).await?;
    let server_addr = listener.local_addr()?;

    tracing::info!("Server listening on http://{}", server_addr);

    axum::serve(listener, app).await?;

    Ok(())
}

/// Starts the host API server in a new thread
///
/// Returns the server's address and a JoinHandle that can be used to wait for the server to finish
pub fn start_server_in_thread(
    config: ServerConfig,
) -> Result<(SocketAddr, thread::JoinHandle<()>), Box<dyn std::error::Error + Send + Sync>> {
    // Create a runtime for the server
    let rt = tokio::runtime::Runtime::new()?;

    // Create a TCP listener to get the address before spawning the thread
    let addr = SocketAddr::from(([127, 0, 0, 1], 0));
    let listener = rt.block_on(async { TcpListener::bind(addr).await })?;
    let server_addr = listener.local_addr()?;

    // Clone the config for the thread
    let config = Arc::new(config);

    // Spawn a thread to run the server
    let handle = thread::spawn(move || {
        rt.block_on(async {
            // Build our application with routes
            let app = Router::new()
                .route("/api/GetSealingKey", post(get_sealing_key))
                .route("/api/Notify", post(notify))
                .with_state(config.clone())
                .layer(TraceLayer::new_for_http());

            tracing::info!("Server listening on http://{}", server_addr);

            // Use the pre-created listener
            if let Err(e) = axum::serve(listener, app).await {
                eprintln!("Server error: {}", e);
            }
        });
    });

    Ok((server_addr, handle))
}
