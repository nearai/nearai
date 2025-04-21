use std::fs;
use std::thread;
use std::time::Duration;

use host_api::{start_server_in_thread, ServerConfig};
use reqwest::blocking::Client;
use serde_json::json;
use tempfile::TempDir;

#[test]
fn test_notify_endpoint() {
    // Create a temporary directory for the VM directory
    let temp_dir = TempDir::new().unwrap();
    let vm_dir = temp_dir.path().to_path_buf();

    // Create shared directory inside the temp dir
    let shared_dir = vm_dir.join("shared");
    fs::create_dir_all(&shared_dir).unwrap();

    // Configure the server
    let config = ServerConfig {
        kp_address: "localhost".to_string(),
        kp_port: 8080, // This won't be used in this test
        vm_dir,
    };

    // Start the server in a thread
    let (addr, _handle) = start_server_in_thread(config).unwrap();

    // Give the server a moment to start
    thread::sleep(Duration::from_millis(100));

    // Create a client
    let client = Client::new();

    // Test the Notify endpoint
    let instance_info = "test instance info";
    let response = client
        .post(&format!("http://{}/api/Notify", addr))
        .json(&json!({
            "event": "instance.info",
            "payload": instance_info
        }))
        .send()
        .unwrap();

    assert_eq!(response.status(), 200);

    // Verify the file was created with the correct content
    let info_path = shared_dir.join(".instance_info");
    let content = fs::read_to_string(info_path).unwrap();
    assert_eq!(content, instance_info);

    // Clean up
    drop(temp_dir);
}
