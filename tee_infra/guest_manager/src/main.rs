use axum::{
    Json, Router,
    extract::State,
    http::StatusCode,
    routing::{get, post},
};
use bollard::Docker;
use guest_manager::{Manager, RunConfig};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::sync::Mutex;
use tower_http::trace::TraceLayer;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

// Shared application state
struct AppState {
    manager: Mutex<Manager>,
}

// Request payload for assigning a CVM
#[derive(Deserialize)]
struct AssignCvmRequest {
    run_id: String,
    thread_id: String,
    agent_id: String,
    provider: String,
    model: String,
    temperature: f32,
    max_tokens: u32,
    max_iterations: u32,
    env_vars: HashMap<String, String>,
}

// Response for the assign_cvm endpoint
#[derive(Serialize)]
struct AssignCvmResponse {
    port: u16,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::new(
            std::env::var("RUST_LOG").unwrap_or_else(|_| "info".into()),
        ))
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Connect to Docker
    let docker = Docker::connect_with_socket_defaults()?;

    // Create the Manager with a pool size of 5
    let manager = Manager::new(docker, 5).await?;

    // Create shared state
    let state = Arc::new(AppState {
        manager: Mutex::new(manager),
    });

    // Build the router
    let app = Router::new()
        .route("/health", get(health_check))
        .route("/assign_cvm", post(assign_cvm))
        .with_state(state)
        .layer(TraceLayer::new_for_http());

    // Run the server
    let addr = SocketAddr::from(([0, 0, 0, 0], 3000));
    tracing::info!("Listening on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await?;
    tracing::info!("Server started, press Ctrl+C to stop");
    axum::serve(listener, app).await?;

    Ok(())
}

// Health check endpoint
async fn health_check() -> StatusCode {
    StatusCode::OK
}

// Assign CVM endpoint
async fn assign_cvm(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<AssignCvmRequest>,
) -> Result<Json<AssignCvmResponse>, (StatusCode, String)> {
    // Create RunConfig from the request
    let run_config = RunConfig::new(
        payload.provider,
        payload.model,
        payload.temperature,
        payload.max_tokens,
        payload.max_iterations,
        payload.env_vars,
    );

    // Get a lock on the manager
    let mut manager = state.manager.lock().await;

    // Assign a CVM
    match manager
        .assign_cvm(
            payload.run_id,
            payload.thread_id,
            payload.agent_id,
            run_config,
        )
        .await
    {
        Ok(port) => Ok(Json(AssignCvmResponse { port })),
        Err(e) => {
            tracing::error!("Failed to assign CVM: {}", e);
            Err((StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))
        }
    }
}
