use host_api::{start_server_in_thread, ServerConfig};
use std::thread;
use std::time::Duration;

fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    // Initialize tracing if needed
    tracing_subscriber::fmt::init();

    // Create server configuration
    let config = ServerConfig {
        kp_address: "localhost".to_string(),
        kp_port: 8080,
        vm_dir: "/tmp".to_string(),
    };

    // Start the server in a thread
    let (server_addr, server_handle) = start_server_in_thread(config)?;

    println!("Server started on http://{}", server_addr);
    println!("The server is now running in a background thread.");
    println!("Your application can continue doing other work...");

    // Simulate doing other work in the main thread
    for i in 1..=5 {
        println!("Main thread doing work... {}/5", i);
        thread::sleep(Duration::from_secs(1));
    }

    println!("Main thread work complete.");
    println!(
        "Waiting for server thread to complete (this would normally run until program exit)..."
    );

    // In a real application, you might not join the thread and just let it run
    // until the program exits. But for this example, we'll join it.
    server_handle.join().unwrap();

    Ok(())
}
