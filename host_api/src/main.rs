use host_api::{start_server, ServerConfig};
use std::sync::Arc;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    // Initialize tracing
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::new(
            std::env::var("RUST_LOG").unwrap_or_else(|_| "info".into()),
        ))
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Example configuration - replace with actual config loading logic
    let config = Arc::new(ServerConfig {
        kp_address: "localhost".to_string(),
        kp_port: 8080,
        vm_dir: "/tmp".to_string(),
    });

    // Start the server
    start_server(config).await
}
