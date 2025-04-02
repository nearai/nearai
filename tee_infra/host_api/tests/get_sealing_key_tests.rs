mod key_provider_mock;

use std::path::PathBuf;
use std::thread;
use std::time::Duration;

use host_api::{start_server_in_thread, ServerConfig};
use key_provider_mock::MockKeyProvider;
use reqwest::blocking::Client;
use serde_json::json;

#[test]
fn test_get_sealing_key_endpoint() {
    // Set up the mock key provider
    let mut mock_kp = MockKeyProvider::new();

    // Define test data
    let test_quote = vec![1, 2, 3, 4];
    let encrypted_key = vec![5, 6, 7, 8];
    let provider_quote = vec![9, 10, 11, 12];

    // Configure the mock
    mock_kp
        .expect_quote(test_quote.clone())
        .with_response(encrypted_key.clone(), provider_quote.clone());

    // Start the mock
    let (kp_addr, kp_port) = mock_kp.start();

    // Configure the server
    let config = ServerConfig {
        kp_address: kp_addr,
        kp_port,
        vm_dir: PathBuf::from("/tmp"), // Not used in this test
    };

    // Start the server in a thread
    let (addr, _handle) = start_server_in_thread(config).unwrap();

    // Give the server a moment to start
    thread::sleep(Duration::from_millis(100));

    // Create a blocking client
    let client = Client::new();

    // Test the GetSealingKey endpoint
    let response = client
        .post(&format!("http://{}/api/GetSealingKey", addr))
        .json(&json!({
            "quote": hex::encode(&test_quote)
        }))
        .send()
        .unwrap();

    assert_eq!(response.status(), 200);

    // Parse the response
    let response_body = response.json::<serde_json::Value>().unwrap();

    // Verify the response
    let received_encrypted_key =
        hex::decode(response_body["encrypted_key"].as_str().unwrap()).unwrap();
    let received_provider_quote =
        hex::decode(response_body["provider_quote"].as_str().unwrap()).unwrap();

    assert_eq!(received_encrypted_key, encrypted_key);
    assert_eq!(received_provider_quote, provider_quote);

    // Clean up
    mock_kp.stop();
}
