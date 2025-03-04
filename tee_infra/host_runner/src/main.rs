use anyhow::Context;
use ctrlc;
use std::fs;
use std::panic;
use std::path::{Path, PathBuf};
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc,
};
use tempfile::tempdir;
use tracing::{debug, error, info, Level};

/// Check if a file exists and is readable
fn check_file(path: &Path, description: &str) -> anyhow::Result<()> {
    if !path.exists() {
        error!("{} not found at: {}", description, path.display());
        return Err(anyhow::anyhow!(
            "{} not found at: {}",
            description,
            path.display()
        ));
    }

    if !path.is_file() {
        error!("{} is not a file: {}", description, path.display());
        return Err(anyhow::anyhow!(
            "{} is not a file: {}",
            description,
            path.display()
        ));
    }

    // Try to read the file to ensure it's accessible
    fs::read_to_string(path)
        .with_context(|| format!("Failed to read {} at: {}", description, path.display()))?;

    info!("{} found and readable at: {}", description, path.display());
    Ok(())
}

fn main() -> anyhow::Result<()> {
    // Initialize tracing with more verbose output
    tracing_subscriber::fmt()
        .with_max_level(Level::TRACE)
        .init();

    info!("Starting host runner");

    let manager = Arc::new(host_runner::DStackManager::new());
    debug!("Manager created");

    // Set up panic hook to ensure cleanup
    let manager_for_panic = Arc::clone(&manager);
    panic::set_hook(Box::new(move |panic_info| {
        error!("Panic occurred: {:?}", panic_info);
        error!("Shutting down QEMU instances before exiting...");
        if let Err(e) = manager_for_panic.shutdown_instances() {
            error!("Error shutting down instances: {:?}", e);
        }
        error!("Cleanup complete after panic");
    }));

    let dir = tempdir().unwrap();
    debug!("Tempdir created at: {}", dir.path().display());

    tracing::info!("Starting host API server");
    let config = host_api::ServerConfig::new(dir.path());
    let (server_addr, _server_handle) = host_api::start_server_in_thread(config)?;
    info!("Host API server started at: {}", server_addr);

    // Create a Path from the string
    let db_path = Path::new("db.yaml");

    // Check if db.yaml exists and is readable
    check_file(db_path, "db.yaml")?;

    // Use a more reliable path for the image
    let image_path = PathBuf::from("/home/ubuntu/private-ml-sdk/images/dstack-nvidia-dev-0.3.3");

    // Check if the image path exists
    if !image_path.exists() {
        error!("Image path not found: {}", image_path.display());
        error!("Please ensure the image path is correct");
        return Err(anyhow::anyhow!(
            "Image path not found: {}",
            image_path.display()
        ));
    }

    if !image_path.is_dir() {
        error!("Image path is not a directory: {}", image_path.display());
        return Err(anyhow::anyhow!(
            "Image path is not a directory: {}",
            image_path.display()
        ));
    }

    info!("Using image path: {}", image_path.display());

    // Check for metadata.json in the image path
    let metadata_path = image_path.join("metadata.json");
    check_file(&metadata_path, "Image metadata")?;

    // Convert string ports to a Vec<String>
    let ports: Vec<String> = vec![
        "tcp:0.0.0.0:13307:18023".to_string(), // quote on port 8000
        "tcp:0.0.0.0:13306:13324".to_string(),
        "tcp:127.0.0.1:18080:18056".to_string(),
        "tcp:127.0.0.1:19001:19067".to_string(), // Changed from 9000 to 9001 to avoid conflicts
    ];

    // Empty vector for GPUs
    let gpus: Vec<String> = Vec::new();

    debug!("Setting up instance");

    manager.setup_instance(
        db_path,
        Some(dir.path().to_path_buf()),
        &image_path,
        12,
        "32G",
        "500G",
        &gpus,
        &ports,
        true,
    )?;

    debug!("Adding shared file");
    manager.add_shared_file(dir.path(), "db.yaml")?;

    info!("Starting QEMU instance");
    match manager.run_instance(
        dir.path(),
        server_addr.port(),
        None,
        None,
        None,
        false,
        false,
    ) {
        Ok(_) => info!("QEMU instance started successfully"),
        Err(e) => {
            error!("Failed to start QEMU instance: {}", e);
            return Err(e);
        }
    }

    // Create a flag to track when to exit
    let running = Arc::new(AtomicBool::new(true));
    let r = running.clone();

    // Set up signal handler for graceful shutdown
    ctrlc::set_handler(move || {
        info!("Received termination signal, shutting down...");
        r.store(false, Ordering::SeqCst);
    })
    .expect("Error setting signal handler");

    // Keep the main thread running until we receive a signal
    info!("Host runner is running. Press Ctrl+C to exit or send SIGTERM.");
    info!("QEMU logs will be in the current directory: qemu_stdout.log and qemu_stderr.log");

    while running.load(Ordering::SeqCst) {
        std::thread::sleep(std::time::Duration::from_millis(100));
    }

    // Shutdown all QEMU instances before exiting
    info!("Shutting down all QEMU instances...");
    manager.shutdown_instances()?;
    info!("All instances shut down. Exiting.");

    Ok(())
}
