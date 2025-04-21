use anyhow::Context;
use clap::{Parser, Subcommand};
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

/// CLI for managing QEMU instances
#[derive(Parser)]
#[command(author, version, about, long_about = None)]
struct Cli {
    /// Sets the level of verbosity
    #[arg(short, long, default_value = "info")]
    log_level: String,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Create and run a new instance
    Run {
        /// Path to the compose file
        #[arg(short, long, default_value = "compose.yaml")]
        compose_path: PathBuf,

        /// Path to the image directory
        #[arg(short, long)]
        image_path: PathBuf,

        /// Number of CPUs to allocate
        #[arg(short = 'u', long, default_value = "12")]
        cpus: u32,

        /// Memory to allocate (e.g., "32G")
        #[arg(short, long, default_value = "32G")]
        memory: String,

        /// Disk size (e.g., "500G")
        #[arg(short, long, default_value = "500G")]
        disk: String,

        /// Port mappings in format "tcp:host_ip:host_port:guest_port"
        #[arg(short, long, value_delimiter = ',')]
        ports: Vec<String>,

        /// GPU devices to pass through
        #[arg(short, long, value_delimiter = ',')]
        gpus: Vec<String>,

        /// Use local key provider instead of remote
        #[arg(long, default_value = "true")]
        local_key_provider: bool,

        /// Enable NUMA pinning
        #[arg(long, default_value = "false")]
        pin_numa: bool,

        /// Enable hugepage support
        #[arg(long, default_value = "false")]
        hugepage: bool,
    },

    /// List all running instances
    List,

    /// Stop and remove an instance
    Stop {
        /// Instance ID to stop
        #[arg(short, long)]
        id: Option<String>,

        /// Stop all instances
        #[arg(short, long)]
        all: bool,
    },
}

fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    // Initialize tracing with the specified log level
    let log_level = match cli.log_level.to_lowercase().as_str() {
        "trace" => Level::TRACE,
        "debug" => Level::DEBUG,
        "info" => Level::INFO,
        "warn" => Level::WARN,
        "error" => Level::ERROR,
        _ => Level::INFO,
    };

    tracing_subscriber::fmt().with_max_level(log_level).init();

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

    match &cli.command {
        Commands::Run {
            compose_path,
            image_path,
            cpus,
            memory,
            disk,
            ports,
            gpus,
            local_key_provider,
            pin_numa,
            hugepage,
        } => {
            // Check if compose file exists and is readable
            check_file(compose_path, "Compose file")?;

            // Check if the image path exists
            if !image_path.exists() {
                error!("Image path not found: {}", image_path.display());
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

            // Create temporary directory for instance
            let dir = tempdir().unwrap();
            debug!("Tempdir created at: {}", dir.path().display());

            // Start the host API server
            info!("Starting host API server");
            let config = host_api::ServerConfig::new(dir.path());
            let (server_addr, _server_handle) = host_api::start_server_in_thread(config)?;
            info!("Host API server started at: {}", server_addr);

            // Set up the instance
            debug!("Setting up instance");
            manager.setup_instance(
                compose_path,
                Some(dir.path().to_path_buf()),
                image_path,
                *cpus,
                memory,
                disk,
                gpus,
                ports,
                *local_key_provider,
            )?;

            // debug!("Adding shared file");
            // manager.add_shared_file(dir.path(), compose_path.to_str().unwrap())?;

            // Run the instance
            info!("Starting QEMU instance");
            let qemu_pid = match manager.run_instance(
                dir.path(),
                server_addr.port(),
                None,
                None,
                None,
                *pin_numa,
                *hugepage,
            ) {
                Ok(pid) => {
                    info!("QEMU instance started successfully with PID: {}", pid);
                    pid
                }
                Err(e) => {
                    error!("Failed to start QEMU instance: {}", e);
                    return Err(e);
                }
            };

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
            info!(
                "QEMU logs will be in the current directory: qemu_stdout.log and qemu_stderr.log"
            );

            // Wait for either the QEMU process to exit or a termination signal
            loop {
                // Check if we received a termination signal
                if !running.load(Ordering::SeqCst) {
                    break;
                }

                // Check if the QEMU process has exited
                let status = std::process::Command::new("ps")
                    .arg("-p")
                    .arg(qemu_pid.to_string())
                    .stdout(std::process::Stdio::null())
                    .stderr(std::process::Stdio::null())
                    .status();

                match status {
                    Ok(exit_status) => {
                        if !exit_status.success() {
                            // Process no longer exists
                            info!("QEMU process with PID {} has exited", qemu_pid);
                            break;
                        }
                    }
                    Err(e) => {
                        error!("Error checking QEMU process status: {}", e);
                        break;
                    }
                }

                std::thread::sleep(std::time::Duration::from_millis(100));
            }

            // Shutdown all QEMU instances before exiting
            info!("Shutting down all QEMU instances...");
            manager.shutdown_instances()?;
            info!("All instances shut down. Exiting.");
        }
        Commands::List => {
            info!("Listing all running instances");
            // Implement listing functionality here
            // This would depend on how instances are tracked in DStackManager
            // For now, we'll just print a placeholder message
            info!("Listing functionality not yet implemented");
        }
        Commands::Stop { id, all } => {
            if *all {
                info!("Stopping all instances");
                manager.shutdown_instances()?;
                info!("All instances stopped successfully");
            } else if let Some(instance_id) = id {
                info!("Stopping instance: {}", instance_id);
                // Implement stopping a specific instance
                // This would depend on how instances are tracked in DStackManager
                info!("Stopping specific instances not yet implemented");
            } else {
                error!("Either --id or --all must be specified");
                return Err(anyhow::anyhow!("Either --id or --all must be specified"));
            }
        }
    }

    Ok(())
}
