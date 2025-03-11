use axum::{
    Json, Router,
    extract::State,
    http::StatusCode,
    routing::{get, post},
};
use bollard::Docker;
use guest_manager::{Manager, RunConfig};
use near_auth::{AuthData, verify_signed_message};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::signal;
use tokio::sync::{Mutex, oneshot};
use tower_http::trace::TraceLayer;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

// Shared application state
struct AppState {
    manager: Mutex<Manager>,
    shutdown_tx: Mutex<Option<oneshot::Sender<()>>>,
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

    // Create a channel for shutdown signal
    let (shutdown_tx, shutdown_rx) = oneshot::channel();

    // Create shared state
    let state = Arc::new(AppState {
        manager: Mutex::new(manager),
        shutdown_tx: Mutex::new(Some(shutdown_tx)),
    });

    // Clone state for shutdown handler
    let shutdown_state = Arc::clone(&state);

    // Build the router
    let app = Router::new()
        .route("/health", get(health_check))
        .route("/assign_cvm", post(assign_cvm))
        .with_state(state)
        .layer(TraceLayer::new_for_http());

    // Run the server
    let addr = SocketAddr::from(([0, 0, 0, 0], 3001));
    tracing::info!("Listening on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await?;
    tracing::info!("Server started, press Ctrl+C to stop");

    // Spawn a task to handle shutdown signals
    tokio::spawn(async move {
        handle_shutdown_signals(shutdown_state).await;
    });

    // Start the server with graceful shutdown
    axum::serve(listener, app)
        .with_graceful_shutdown(async {
            let _ = shutdown_rx.await;
            tracing::info!("Shutdown signal received, starting graceful shutdown");
        })
        .await?;

    Ok(())
}

// Handle various shutdown signals (SIGINT, SIGTERM)
async fn handle_shutdown_signals(state: Arc<AppState>) {
    // Wait for either Ctrl+C or SIGTERM
    tokio::select! {
        _ = signal::ctrl_c() => {
            tracing::info!("Received Ctrl+C signal");
        }
        _ = async {
            let mut term_signal = signal::unix::signal(signal::unix::SignalKind::terminate())
                .expect("Failed to install SIGTERM handler");
            term_signal.recv().await;
            tracing::info!("Received SIGTERM signal");
        } => {}
    }

    // Perform cleanup
    tracing::info!("Starting cleanup process...");

    // Get a lock on the manager and call shutdown
    let mut manager = state.manager.lock().await;
    if let Err(e) = manager.shutdown().await {
        tracing::error!("Error during manager shutdown: {}", e);
    }

    // Send shutdown signal to the server
    let mut shutdown_tx = state.shutdown_tx.lock().await;
    if let Some(tx) = shutdown_tx.take() {
        let _ = tx.send(());
    }
}

// Health check endpoint
async fn health_check() -> StatusCode {
    StatusCode::OK
}

// Assign CVM endpoint
#[axum::debug_handler]
async fn assign_cvm(
    State(state): State<Arc<AppState>>,
    // auth: AuthData,
    Json(payload): Json<AssignCvmRequest>,
) -> Result<Json<AssignCvmResponse>, (StatusCode, String)> {
    // Verify the signature
    // if !verify_signed_message(&auth).await {
    //     return Err((StatusCode::UNAUTHORIZED, "Invalid auth token".to_string()));
    // }

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
